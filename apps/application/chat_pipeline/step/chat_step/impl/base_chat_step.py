# coding=utf-8
"""
    @project: maxkb
    @Author：虎
    @file： base_chat_step.py
    @date：2024/1/9 18:25
    @desc: 对话step Base实现
"""
import json
import re
import time
import traceback
from typing import List

import uuid_utils.compat as uuid
from django.db.models import QuerySet
from django.http import StreamingHttpResponse
from django.utils.translation import gettext as _
from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import AIMessageChunk, SystemMessage, BaseMessage, HumanMessage, AIMessage
from rest_framework import status

from application.chat_pipeline.I_base_chat_pipeline import ParagraphPipelineModel
from application.chat_pipeline.pipeline_manage import PipelineManage
from application.chat_pipeline.step.chat_step.i_chat_step import IChatStep, PostResponseHandler
from application.flow.tools import Reasoning, mcp_response_generator, get_tools
from application.models import ApplicationChatUserStats, ChatUserType, Application, ApplicationApiKey, \
    ApplicationAccessToken
from common.exception.app_exception import AppApiException
from common.utils.logger import maxkb_logger
from common.utils.rsa_util import rsa_long_decrypt
from common.utils.shared_resource_auth import filter_authorized_ids
from common.utils.tool_code import ToolExecutor
from models_provider.tools import get_model_instance_by_model_workspace_id
from tools.models import Tool, ToolType


HIGH_RISK_KEYWORDS = [
    "保修", "拒保", "换新", "免费维修", "维修费用", "时效", "质量问题", "人为损坏", "判责"
]
HIGH_RISK_COMMITMENT_PHRASES = [
    "一定保修", "肯定保修", "一定换新", "肯定换新", "免费维修",
    "必然免费", "保证当天修好", "肯定是质量问题", "一定是质量问题"
]
STRONG_EVIDENCE_KEYWORDS = ["依据", "条款", "规则", "政策", "SOP", "步骤", "文档显示"]

# 纯寒暄/开场白：不走「证据不足硬拒答」，避免对「你好」也输出法务口吻（仍可能在后续走正常模型回复）
_SMALL_TALK_DEVICE_HINTS = (
    "手机", "平板", "电脑", "手表", "耳机", "笔记本", "充电器", "数据线",
    "华为", "小米", "苹果", "三星", "OPPO", "vivo", "荣耀", "一加", "魅族",
    "维修", "保修", "退换", "换新", "拒保", "坏", "故障", "碎屏", "进水", "黑屏",
    "无法", "不能", "异常", "连不上", "连不", "wifi", "WiFi", "网络", "信号",
    "发票", "激活", "序列号", "IMEI", "SN", "型号",
)
_SMALL_TALK_RE = re.compile(
    r"^\s*(你好|您好|在吗|在么|嗨|哈喽|hi|hello|早上好|下午好|晚上好|谢谢|感谢|多谢|辛苦了|再见|拜拜|好的|行|ok|OK|哈喽)"
    r"[呀啊呢噢哦！!。.…~～\s]*$"
    r"|^\s*(测试)\s*[!！。.…~～\s]*$",
    re.I,
)


def _is_greeting_or_small_talk(problem_text: str) -> bool:
    """仅问候、不涉及设备/故障意图的极短句：不做售后硬拒答。"""
    t = (problem_text or "").strip()
    if not t:
        return True
    if len(t) > 36:
        return False
    if any(h in t for h in _SMALL_TALK_DEVICE_HINTS):
        return False
    return bool(_SMALL_TALK_RE.match(t))


def _is_meta_assistant_query(problem_text: str) -> bool:
    """你是谁/能做什么 等元问题，不涉及具体设备，不必走「结论-依据-建议」长模板。"""
    t = (problem_text or "").strip()
    if not t or len(t) > 48:
        return False
    if any(h in t for h in _SMALL_TALK_DEVICE_HINTS):
        return False
    return bool(
        re.match(
            r"^\s*(你是谁|你是什么|你是干嘛的|你是干什么的|能做什么|可以做什么|你会什么|有什么功能|怎么用|如何使用)\s*[？?！!。…\s]*$",
            t,
        )
    )


def _use_after_sales_plain_short_reply(problem_text: str) -> bool:
    return _is_greeting_or_small_talk(problem_text) or _is_meta_assistant_query(problem_text)


def _after_sales_plain_short_reply(problem_text: str) -> str:
    """不用大模型拼「结论/依据/建议」，避免寒暄也像写报告。"""
    t = (problem_text or "").strip()
    if re.search(r"谢谢|感谢|多谢|辛苦了", t):
        return "不客气，有设备或售后问题随时说就行。"
    if re.search(r"再见|拜拜", t):
        return "再见，有需要再找我。"
    if re.search(r"在吗|在么", t):
        return "在的。有具体问题直接说品牌、型号和现象就行。"
    if _is_meta_assistant_query(problem_text):
        return (
            "我是3C数码售后助手，主要帮你查知识库里的保修、退换、维修相关说明。"
            "你遇到实际问题可以说一下品牌、型号和故障现象，我再帮你对准查。"
        )
    return (
        "你好，我是3C数码售后助手。要是手机、平板、手表这类有问题，说一下品牌、型号和出了什么情况，我再帮你查。"
    )


def _refuse_answer(problem_text: str) -> str:
    # 不再把用户原文塞进方括号，避免出现截图里「把调试说明整段展示出来」的生硬观感
    return (
        "暂时没有在知识库里检索到能直接对照的条款或记录，我没法给你一个写得「死」的结论。\n\n"
        "如果你是在问具体设备的问题，麻烦补充一下品牌、型号、故障现象，以及购买或保修相关信息（能多说一句就多一句），我再帮你对准检索。\n\n"
        "涉及保修范围、费用、能不能换新这类敏感结论，最终以对应品牌官方售后或人工客服为准。"
    )


def _answer_has_after_sales_disclaimer(answer: str) -> bool:
    """后置拦截用：判断是否已包含拒答/免责口径，避免重复替换。"""
    if any(
        x in answer
        for x in (
            "当前知识库未提供足够依据",
            "暂时没有在知识库里检索到",
            "没法给你一个写得",
            "最终以对应品牌官方售后",
        )
    ):
        return True
    return any(k in answer for k in ["依据", "条款", "规则", "建议补充"])


def _is_after_sales_context(paragraph_list: List[ParagraphPipelineModel]) -> bool:
    return any(bool((paragraph.meta or {}).get("after_sales_mode")) for paragraph in (paragraph_list or []))


def _need_after_sales_refuse(problem_text: str, paragraph_list: List[ParagraphPipelineModel]) -> bool:
    if _is_greeting_or_small_talk(problem_text):
        return False
    if len(paragraph_list or []) == 0:
        return True
    question = problem_text or ""
    high_risk = any(keyword in question for keyword in HIGH_RISK_KEYWORDS)
    top_similarity = max([(paragraph.similarity or 0) for paragraph in paragraph_list], default=0)
    if top_similarity < 0.6 or len(paragraph_list) < 2:
        return True
    if high_risk and (top_similarity < 0.82 or len(paragraph_list) < 3):
        return True
    model_tokens = re.findall(r"[A-Za-z]{1,4}[-]?[A-Za-z0-9]{2,12}", question.upper())
    has_model_hint = len(model_tokens) > 0 or any(k in question for k in ["型号", "SN", "IMEI", "序列号"])
    if model_tokens:
        merged_context = " ".join([f"{paragraph.document_name} {paragraph.content}" for paragraph in paragraph_list]).upper()
        if not any(token in merged_context for token in model_tokens[:5]):
            return True
    if high_risk and not has_model_hint:
        return True
    merged_content = " ".join([paragraph.content or "" for paragraph in paragraph_list])
    if high_risk and not any(keyword in merged_content for keyword in STRONG_EVIDENCE_KEYWORDS):
        return True
    return False


def _need_after_sales_post_refuse(problem_text: str, answer_text: str) -> bool:
    question = problem_text or ""
    answer = answer_text or ""
    if len(answer.strip()) == 0:
        return True
    if any(phrase in answer for phrase in HIGH_RISK_COMMITMENT_PHRASES):
        return True
    high_risk = any(keyword in question for keyword in HIGH_RISK_KEYWORDS)
    if high_risk and not _answer_has_after_sales_disclaimer(answer):
        return True
    return False


def add_access_num(chat_user_id=None, chat_user_type=None, application_id=None):
    if [ChatUserType.ANONYMOUS_USER.value, ChatUserType.CHAT_USER.value].__contains__(
            chat_user_type) and application_id is not None:
        application_public_access_client = (QuerySet(ApplicationChatUserStats).filter(chat_user_id=chat_user_id,
                                                                                      chat_user_type=chat_user_type,
                                                                                      application_id=application_id)
                                            .first())
        if application_public_access_client is not None:
            application_public_access_client.access_num = application_public_access_client.access_num + 1
            application_public_access_client.intraday_access_num = application_public_access_client.intraday_access_num + 1
            application_public_access_client.save()


def write_context(step, manage, request_token, response_token, all_text):
    step.context['message_tokens'] = request_token
    step.context['answer_tokens'] = response_token
    current_time = time.time()
    step.context['answer_text'] = all_text
    step.context['run_time'] = current_time - step.context['start_time']
    manage.context['run_time'] = current_time - manage.context['start_time']
    manage.context['message_tokens'] = manage.context['message_tokens'] + request_token
    manage.context['answer_tokens'] = manage.context['answer_tokens'] + response_token


def event_content(response,
                  chat_id,
                  chat_record_id,
                  paragraph_list: List[ParagraphPipelineModel],
                  post_response_handler: PostResponseHandler,
                  manage,
                  step,
                  chat_model,
                  message_list: List[BaseMessage],
                  problem_text: str,
                  padding_problem_text: str = None,
                  chat_user_id=None, chat_user_type=None,
                  is_ai_chat: bool = None,
                  model_setting=None):
    if model_setting is None:
        model_setting = {}
    reasoning_content_enable = model_setting.get('reasoning_content_enable', False)
    reasoning_content_start = model_setting.get('reasoning_content_start', '<think>')
    reasoning_content_end = model_setting.get('reasoning_content_end', '</think>')
    reasoning = Reasoning(reasoning_content_start,
                          reasoning_content_end)
    all_text = ''
    reasoning_content = ''
    # 售后模式下：后置合规/拒答依赖完整答案文本判断；若边生成边推送正文，可能出现“先输出高风险措辞、后无法撤回”的体验问题。
    # 因此在售后上下文且为模型生成流时，正文先缓冲，结束后再一次性输出（仍保留 reasoning 分块流式展示）。
    buffer_main_text_stream = bool(is_ai_chat) and _is_after_sales_context(paragraph_list)
    try:
        response_reasoning_content = False
        for chunk in response:
            reasoning_chunk = reasoning.get_reasoning_content(chunk)
            content_chunk = reasoning_chunk.get('content')
            if 'reasoning_content' in chunk.additional_kwargs:
                response_reasoning_content = True
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            else:
                reasoning_content_chunk = reasoning_chunk.get('reasoning_content')
            content_chunk = reasoning._normalize_content(content_chunk)
            all_text += content_chunk
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            reasoning_content += reasoning_content_chunk
            out_content_chunk = '' if buffer_main_text_stream else content_chunk
            yield manage.get_base_to_response().to_stream_chunk_response(chat_id, str(chat_record_id), 'ai-chat-node',
                                                                         [], out_content_chunk,
                                                                         False,
                                                                         0, 0, {'node_is_end': False,
                                                                                'view_type': 'many_view',
                                                                                'node_type': 'ai-chat-node',
                                                                                'real_node_id': 'ai-chat-node',
                                                                                'reasoning_content': reasoning_content_chunk if reasoning_content_enable else ''})
        reasoning_chunk = reasoning.get_end_reasoning_content()
        all_text += reasoning_chunk.get('content')
        reasoning_content_chunk = ""
        if not response_reasoning_content:
            reasoning_content_chunk = reasoning_chunk.get(
                'reasoning_content')
        end_content_chunk = reasoning_chunk.get('content')
        if buffer_main_text_stream:
            end_content_chunk = ''
        yield manage.get_base_to_response().to_stream_chunk_response(chat_id, str(chat_record_id), 'ai-chat-node',
                                                                     [], end_content_chunk,
                                                                     False,
                                                                     0, 0, {'node_is_end': False,
                                                                            'view_type': 'many_view',
                                                                            'node_type': 'ai-chat-node',
                                                                            'real_node_id': 'ai-chat-node',
                                                                            'reasoning_content'
                                                                            : reasoning_content_chunk if reasoning_content_enable else ''})
        # 流式正文在售后场景下已缓冲，这里与块式路径对齐做一次后置拦截，再一次性输出正文
        if buffer_main_text_stream:
            final_text = all_text
            if _is_after_sales_context(paragraph_list) and _need_after_sales_post_refuse(problem_text, final_text):
                final_text = _refuse_answer(problem_text)
            yield manage.get_base_to_response().to_stream_chunk_response(chat_id, str(chat_record_id), 'ai-chat-node',
                                                                         [], final_text,
                                                                         False,
                                                                         0, 0, {'node_is_end': False,
                                                                                'view_type': 'many_view',
                                                                                'node_type': 'ai-chat-node',
                                                                                'real_node_id': 'ai-chat-node',
                                                                                'reasoning_content': ''})
            all_text = final_text
        # 获取token
        if is_ai_chat:
            try:
                request_token = chat_model.get_num_tokens_from_messages(message_list)
                response_token = chat_model.get_num_tokens(all_text)
            except Exception as e:
                request_token = 0
                response_token = 0
        else:
            request_token = 0
            response_token = 0
        write_context(step, manage, request_token, response_token, all_text)
        post_response_handler.handler(chat_id, chat_record_id, paragraph_list, problem_text,
                                      all_text, manage, step, padding_problem_text,
                                      reasoning_content=reasoning_content if reasoning_content_enable else '')
        yield manage.get_base_to_response().to_stream_chunk_response(chat_id, str(chat_record_id), 'ai-chat-node',
                                                                     [], '', True,
                                                                     request_token, response_token,
                                                                     {'node_is_end': True, 'view_type': 'many_view',
                                                                      'node_type': 'ai-chat-node'})
        if not manage.debug:
            add_access_num(chat_user_id, chat_user_type, manage.context.get('application_id'))
    except Exception as e:
        maxkb_logger.error(f'{str(e)}:{traceback.format_exc()}')
        all_text = 'Exception:' + str(e)
        write_context(step, manage, 0, 0, all_text)
        post_response_handler.handler(chat_id, chat_record_id, paragraph_list, problem_text,
                                      all_text, manage, step, padding_problem_text, reasoning_content='')
        if not manage.debug:
            add_access_num(chat_user_id, chat_user_type, manage.context.get('application_id'))
        yield manage.get_base_to_response().to_stream_chunk_response(chat_id, str(chat_record_id), 'ai-chat-node',
                                                                     [], all_text,
                                                                     False,
                                                                     0, 0, {'node_is_end': False,
                                                                            'view_type': 'many_view',
                                                                            'node_type': 'ai-chat-node',
                                                                            'real_node_id': 'ai-chat-node',
                                                                            'reasoning_content': ''})


class BaseChatStep(IChatStep):
    def execute(self, message_list: List[BaseMessage],
                chat_id,
                problem_text,
                post_response_handler: PostResponseHandler,
                model_id: str = None,
                workspace_id: str = None,
                paragraph_list=None,
                manage: PipelineManage = None,
                padding_problem_text: str = None,
                stream: bool = True,
                chat_user_id=None, chat_user_type=None,
                no_references_setting=None,
                model_params_setting=None,
                model_setting=None,
                mcp_tool_ids=None,
                mcp_servers='',
                mcp_source="referencing",
                tool_ids=None,
                application_ids=None,
                skill_tool_ids=None,
                mcp_output_enable=True,
                **kwargs):
        chat_model = get_model_instance_by_model_workspace_id(model_id, workspace_id,
                                                              **(model_params_setting or {})) if model_id is not None else None
        if stream:
            return self.execute_stream(message_list, chat_id, problem_text, post_response_handler, chat_model,
                                       paragraph_list,
                                       manage, padding_problem_text, chat_user_id, chat_user_type,
                                       no_references_setting,
                                       model_setting,
                                       mcp_tool_ids, mcp_servers, mcp_source, tool_ids,
                                       application_ids,
                                       skill_tool_ids,
                                       workspace_id,
                                       mcp_output_enable)
        else:
            return self.execute_block(message_list, chat_id, problem_text, post_response_handler, chat_model,
                                      paragraph_list,
                                      manage, padding_problem_text, chat_user_id, chat_user_type, no_references_setting,
                                      model_setting,
                                      mcp_tool_ids, mcp_servers, mcp_source, tool_ids,
                                      application_ids,
                                      skill_tool_ids,
                                      workspace_id,
                                      mcp_output_enable)

    def get_details(self, manage, **kwargs):
        return {
            'status': self.status,
            'err_message': self.err_message,
            'step_type': 'chat_step',
            'run_time': self.context.get('run_time') or 0,
            'model_id': str(manage.context['model_id']),
            'message_list': self.reset_message_list(self.context['step_args'].get('message_list'),
                                                    self.context.get('answer_text')),
            'message_tokens': self.context.get('message_tokens'),
            'answer_tokens': self.context.get('answer_tokens'),
            'cost': 0,
        }

    @staticmethod
    def reset_message_list(message_list: List[BaseMessage], answer_text):
        result = [{'role': 'user' if isinstance(message, HumanMessage) else (
            'system' if isinstance(message, SystemMessage) else 'ai'), 'content': message.content} for
                  message
                  in
                  message_list]
        result.append({'role': 'ai', 'content': answer_text})
        return result

    def _handle_mcp_request(self, mcp_source, mcp_servers, mcp_tool_ids, tool_ids,
                            application_ids, skill_tool_ids, mcp_output_enable, chat_model, message_list, agent_id,
                            chat_id, workspace_id):

        mcp_servers_config = {}

        # 迁移过来mcp_source是None
        if mcp_source is None:
            mcp_source = 'custom'
        # 兼容老数据
        if not mcp_tool_ids:
            mcp_tool_ids = []
        if mcp_source == 'custom' and mcp_servers:
            ToolExecutor().validate_mcp_transport(mcp_servers)
            mcp_servers_config = json.loads(mcp_servers)
        elif mcp_tool_ids:
            mcp_tools = QuerySet(Tool).filter(id__in=mcp_tool_ids).values()
            for mcp_tool in mcp_tools:
                if mcp_tool and mcp_tool['is_active']:
                    mcp_servers_config = {**mcp_servers_config, **json.loads(mcp_tool['code'])}

        tool_init_params = {}
        tools = get_tools("APPLICATION", agent_id, tool_ids,
                          workspace_id)
        if tool_ids and len(tool_ids) > 0:  # 如果有工具ID，则将其转换为MCP
            self.context['tool_ids'] = tool_ids
            for tool_id in tool_ids:
                tool = QuerySet(Tool).filter(id=tool_id, tool_type=ToolType.CUSTOM).first()
                if tool is None or tool.is_active is False:
                    continue
                executor = ToolExecutor()
                if tool.init_params is not None:
                    params = json.loads(rsa_long_decrypt(tool.init_params))
                    tool_init_params = json.loads(rsa_long_decrypt(tool.init_params))
                else:
                    params = {}
                tool_config = executor.get_tool_mcp_config(tool, params)

                mcp_servers_config[str(tool.id)] = tool_config

        if application_ids and len(application_ids) > 0:
            self.context['application_ids'] = application_ids
            for application_id in application_ids:
                app = QuerySet(Application).filter(id=application_id, is_publish=True).first()
                if app is None:
                    continue
                app_key = QuerySet(ApplicationApiKey).filter(application_id=application_id, is_active=True).first()
                if app_key is not None:
                    api_key = app_key.secret_key
                    application_access_token = QuerySet(ApplicationAccessToken).filter(
                        application_id=app_key.application_id
                    ).first()
                    if application_access_token is not None and application_access_token.authentication:
                        raise AppApiException(
                            500,
                            _('Agent 【{name}】 access token authentication is not supported for agent tool').format(
                                name=app.name)
                        )
                else:
                    raise AppApiException(
                        500,
                        _('Agent Key is required for agent tool 【{name}】').format(name=app.name)
                    )
                executor = ToolExecutor()
                app_config = executor.get_app_mcp_config(api_key)
                mcp_servers_config[app.name] = app_config

        if skill_tool_ids and len(skill_tool_ids) > 0:
            self.context['skill_tool_ids'] = skill_tool_ids
            skill_file_items = []

            for tool_id in skill_tool_ids:
                tool = QuerySet(Tool).filter(id=tool_id, is_active=True).first()
                if tool is None or tool.is_active is False:
                    continue
                init_params_default_value = {i["field"]: i.get('default_value') for i in tool.init_field_list}
                if tool.init_params is not None:
                    params = init_params_default_value | json.loads(rsa_long_decrypt(tool.init_params))
                else:
                    params = init_params_default_value

                skill_file_items.append({
                    'tool_id': str(tool.id),
                    'file_id': tool.code,
                    'params': params
                })
            mcp_servers_config['skills'] = skill_file_items

        if len(mcp_servers_config) > 0 or len(tools) > 0:
            source_id = agent_id
            source_type = 'APPLICATION'
            return mcp_response_generator(
                chat_model, message_list, json.dumps(mcp_servers_config), mcp_output_enable,
                tool_init_params, source_id, source_type, chat_id, tools
            )

        return None

    def get_stream_result(self, message_list: List[BaseMessage],
                          chat_model: BaseChatModel = None,
                          paragraph_list=None,
                          no_references_setting=None,
                          problem_text=None,
                          mcp_tool_ids=None,
                          mcp_servers='',
                          mcp_source="referencing",
                          tool_ids=None,
                          application_ids=None,
                          skill_tool_ids=None,
                          workspace_id=None,
                          mcp_output_enable=True,
                          agent_id=None,
                          chat_id=None
                          ):
        if paragraph_list is None:
            paragraph_list = []
        if _is_after_sales_context(paragraph_list) and _use_after_sales_plain_short_reply(problem_text):
            return iter([AIMessageChunk(content=_after_sales_plain_short_reply(problem_text))]), False
        if _is_after_sales_context(paragraph_list) and _need_after_sales_refuse(problem_text, paragraph_list):
            return iter([AIMessageChunk(content=_refuse_answer(problem_text))]), False
        directly_return_chunk_list = [AIMessageChunk(content=paragraph.content)
                                      for paragraph in paragraph_list if (
                                              paragraph.hit_handling_method == 'directly_return' and paragraph.similarity >= paragraph.directly_return_similarity)]
        if directly_return_chunk_list is not None and len(directly_return_chunk_list) > 0:
            return iter(directly_return_chunk_list), False
        elif len(paragraph_list) == 0 and no_references_setting.get(
                'status') == 'designated_answer':
            return iter(
                [AIMessageChunk(content=no_references_setting.get('value').replace('{question}', problem_text))]), False
        if chat_model is None:
            return iter([AIMessageChunk(
                _('Sorry, the AI model is not configured. Please go to the application to set up the AI model first.'))]), False
        else:
            # 过滤tool_id
            all_tool_ids = list(set(
                (mcp_tool_ids or []) +
                (tool_ids or []) +
                (skill_tool_ids or [])
            ))
            authorized_set = set(filter_authorized_ids('tool', all_tool_ids, workspace_id))

            mcp_tool_ids = [i for i in (mcp_tool_ids or []) if i in authorized_set]
            tool_ids = [i for i in (tool_ids or []) if i in authorized_set]
            skill_tool_ids = [i for i in (skill_tool_ids or []) if i in authorized_set]
            # 处理 MCP 请求
            mcp_result = self._handle_mcp_request(
                mcp_source, mcp_servers, mcp_tool_ids, tool_ids,
                application_ids, skill_tool_ids, mcp_output_enable, chat_model,
                message_list, agent_id, chat_id, workspace_id
            )
            if mcp_result:
                return mcp_result, True
            return chat_model.stream(message_list), True

    def execute_stream(self, message_list: List[BaseMessage],
                       chat_id,
                       problem_text,
                       post_response_handler: PostResponseHandler,
                       chat_model: BaseChatModel = None,
                       paragraph_list=None,
                       manage: PipelineManage = None,
                       padding_problem_text: str = None,
                       chat_user_id=None, chat_user_type=None,
                       no_references_setting=None,
                       model_setting=None,
                       mcp_tool_ids=None,
                       mcp_servers='',
                       mcp_source="referencing",
                       tool_ids=None,
                       application_ids=None,
                       skill_tool_ids=None,
                       workspace_id=None,
                       mcp_output_enable=True):
        chat_result, is_ai_chat = self.get_stream_result(message_list, chat_model, paragraph_list,
                                                         no_references_setting, problem_text, mcp_tool_ids,
                                                         mcp_servers, mcp_source, tool_ids,
                                                         application_ids, skill_tool_ids, workspace_id,
                                                         mcp_output_enable, manage.context.get('application_id'),
                                                         chat_id)
        chat_record_id = self.context.get('step_args', {}).get('chat_record_id') if self.context.get('step_args',
                                                                                                     {}).get(
            'chat_record_id') else uuid.uuid7()
        r = StreamingHttpResponse(
            streaming_content=event_content(chat_result, chat_id, chat_record_id, paragraph_list,
                                            post_response_handler, manage, self, chat_model, message_list, problem_text,
                                            padding_problem_text, chat_user_id, chat_user_type, is_ai_chat,
                                            model_setting),
            content_type='text/event-stream;charset=utf-8')

        r['Cache-Control'] = 'no-cache'
        return r

    def get_block_result(self, message_list: List[BaseMessage],
                         chat_model: BaseChatModel = None,
                         paragraph_list=None,
                         no_references_setting=None,
                         problem_text=None,
                         mcp_tool_ids=None,
                         mcp_servers='',
                         mcp_source="referencing",
                         tool_ids=None,
                         application_ids=None,
                         skill_tool_ids=None,
                         workspace_id=None,
                         mcp_output_enable=True,
                         application_id=None,
                         chat_id=None
                         ):
        if paragraph_list is None:
            paragraph_list = []
        if _is_after_sales_context(paragraph_list) and _use_after_sales_plain_short_reply(problem_text):
            return AIMessage(_after_sales_plain_short_reply(problem_text)), False
        if _is_after_sales_context(paragraph_list) and _need_after_sales_refuse(problem_text, paragraph_list):
            return AIMessage(_refuse_answer(problem_text)), False
        directly_return_chunk_list = [AIMessageChunk(content=paragraph.content)
                                      for paragraph in paragraph_list if (
                                              paragraph.hit_handling_method == 'directly_return' and paragraph.similarity >= paragraph.directly_return_similarity)]
        if directly_return_chunk_list is not None and len(directly_return_chunk_list) > 0:
            return directly_return_chunk_list[0], False
        elif len(paragraph_list) == 0 and no_references_setting.get(
                'status') == 'designated_answer':
            return AIMessage(no_references_setting.get('value').replace('{question}', problem_text)), False
        if chat_model is None:
            return AIMessage(
                _('Sorry, the AI model is not configured. Please go to the application to set up the AI model first.')), False
        else:
            # 过滤tool_id
            all_tool_ids = list(set(
                (mcp_tool_ids or []) +
                (tool_ids or []) +
                (skill_tool_ids or [])
            ))
            authorized_set = set(filter_authorized_ids('tool', all_tool_ids, workspace_id))

            mcp_tool_ids = [i for i in (mcp_tool_ids or []) if i in authorized_set]
            tool_ids = [i for i in (tool_ids or []) if i in authorized_set]
            skill_tool_ids = [i for i in (skill_tool_ids or []) if i in authorized_set]
            # 处理 MCP 请求
            mcp_result = self._handle_mcp_request(
                mcp_source, mcp_servers, mcp_tool_ids, tool_ids,
                application_ids, skill_tool_ids, mcp_output_enable,
                chat_model, message_list, application_id, chat_id, workspace_id
            )
            if mcp_result:
                return mcp_result, True
            return chat_model.invoke(message_list), True

    def execute_block(self, message_list: List[BaseMessage],
                      chat_id,
                      problem_text,
                      post_response_handler: PostResponseHandler,
                      chat_model: BaseChatModel = None,
                      paragraph_list=None,
                      manage: PipelineManage = None,
                      padding_problem_text: str = None,
                      chat_user_id=None, chat_user_type=None, no_references_setting=None,
                      model_setting=None,
                      mcp_tool_ids=None,
                      mcp_servers='',
                      mcp_source="referencing",
                      tool_ids=None,
                      application_ids=None,
                      skill_tool_ids=None,
                      workspace_id=None,
                      mcp_output_enable=True):
        reasoning_content_enable = model_setting.get('reasoning_content_enable', False)
        reasoning_content_start = model_setting.get('reasoning_content_start', '<think>')
        reasoning_content_end = model_setting.get('reasoning_content_end', '</think>')
        reasoning = Reasoning(reasoning_content_start,
                              reasoning_content_end)
        chat_record_id = uuid.uuid7()
        # 调用模型
        try:
            chat_result, is_ai_chat = self.get_block_result(message_list, chat_model, paragraph_list,
                                                            no_references_setting, problem_text,
                                                            mcp_tool_ids, mcp_servers, mcp_source,
                                                            tool_ids, application_ids, skill_tool_ids, workspace_id,
                                                            mcp_output_enable, manage.context.get('application_id'),
                                                            chat_id)
            if is_ai_chat:
                request_token = chat_model.get_num_tokens_from_messages(message_list)
                response_token = chat_model.get_num_tokens(chat_result.content)
            else:
                request_token = 0
                response_token = 0
            write_context(self, manage, request_token, response_token, chat_result.content)
            reasoning_result = reasoning.get_reasoning_content(chat_result)
            reasoning_result_end = reasoning.get_end_reasoning_content()
            content = reasoning_result.get('content') + reasoning_result_end.get('content')
            if _is_after_sales_context(paragraph_list) and _need_after_sales_post_refuse(problem_text, content):
                content = _refuse_answer(problem_text)
            if 'reasoning_content' in chat_result.response_metadata:
                reasoning_content = (chat_result.response_metadata.get('reasoning_content', '') or '')
            else:
                reasoning_content = (reasoning_result.get('reasoning_content') or "") + (reasoning_result_end.get(
                    'reasoning_content') or "")
            post_response_handler.handler(chat_id, chat_record_id, paragraph_list, problem_text,
                                          content, manage, self, padding_problem_text,
                                          reasoning_content=reasoning_content)
            if not manage.debug:
                add_access_num(chat_user_id, chat_user_type, manage.context.get('application_id'))
            return manage.get_base_to_response().to_block_response(str(chat_id), str(chat_record_id),
                                                                   content, True,
                                                                   request_token, response_token,
                                                                   {
                                                                       'reasoning_content': reasoning_content if reasoning_content_enable else '',
                                                                       'answer_list': [{
                                                                           'content': content,
                                                                           'reasoning_content': reasoning_content if reasoning_content_enable else ''
                                                                       }]})
        except Exception as e:
            all_text = 'Exception:' + str(e)
            write_context(self, manage, 0, 0, all_text)
            post_response_handler.handler(chat_id, chat_record_id, paragraph_list, problem_text,
                                          all_text, manage, self, padding_problem_text, reasoning_content='')
            if not manage.debug:
                add_access_num(chat_user_id, chat_user_type, manage.context.get('application_id'))
            return manage.get_base_to_response().to_block_response(str(chat_id), str(chat_record_id), all_text, True, 0,
                                                                   0, _status=status.HTTP_500_INTERNAL_SERVER_ERROR)
