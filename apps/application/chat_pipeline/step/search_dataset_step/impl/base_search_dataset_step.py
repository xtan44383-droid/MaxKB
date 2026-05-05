# coding=utf-8
"""
    @project: maxkb
    @Author：虎
    @file： base_search_dataset_step.py
    @date：2024/1/10 10:33
    @desc:
"""
import os
import re
from typing import List, Dict

from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework.utils.formatting import lazy_format

from application.chat_pipeline.I_base_chat_pipeline import ParagraphPipelineModel
from application.chat_pipeline.step.search_dataset_step.i_search_dataset_step import ISearchDatasetStep
from common.config.embedding_config import VectorStore, ModelManage
from common.constants.permission_constants import RoleConstants
from common.database_model_manage.database_model_manage import DatabaseModelManage
from common.db.search import native_search
from common.utils.common import get_file_content
from knowledge.models import Paragraph, Knowledge
from knowledge.models import SearchMode
from maxkb.conf import PROJECT_DIR
from models_provider.models import Model
from models_provider.tools import get_model, get_model_by_id, get_model_default_params


def reset_meta(meta):
    if meta is None:
        return {'allow_download': False}
    if not meta.get('allow_download', False):
        return {'allow_download': False}
    return meta


def get_embedding_id(knowledge_id_list):
    knowledge_list = QuerySet(Knowledge).filter(id__in=knowledge_id_list)
    if len(set([knowledge.embedding_model_id for knowledge in knowledge_list])) > 1:
        raise Exception(
            _("The vector model of the associated knowledge base is inconsistent and the segmentation cannot be recalled."))
    if len(knowledge_list) == 0:
        raise Exception(_("The knowledge base setting is wrong, please reset the knowledge base"))
    return knowledge_list[0].embedding_model_id


class BaseSearchDatasetStep(ISearchDatasetStep):

    def execute(self, problem_text: str, knowledge_id_list: list[str], exclude_document_id_list: list[str],
                exclude_paragraph_id_list: list[str], top_n: int, similarity: float, padding_problem_text: str = None,
                search_mode: str = None,
                workspace_id=None,
                manage=None,
                **kwargs) -> List[ParagraphPipelineModel]:
        get_knowledge_list_of_authorized = DatabaseModelManage.get_model('get_knowledge_list_of_authorized')
        chat_user_type = manage.context.get('chat_user_type')
        if get_knowledge_list_of_authorized is not None and RoleConstants.CHAT_USER.value.name == chat_user_type:
            knowledge_id_list = get_knowledge_list_of_authorized(manage.context.get('chat_user_id'),
                                                                 knowledge_id_list)
        if len(knowledge_id_list) == 0:
            return []
        exec_problem_text = padding_problem_text if padding_problem_text is not None else problem_text
        model_id = get_embedding_id(knowledge_id_list)
        model = get_model_by_id(model_id, workspace_id)
        if model.model_type != "EMBEDDING":
            raise Exception(_("Model does not exist"))
        self.context['model_name'] = model.name
        default_params = get_model_default_params(model)
        embedding_model = ModelManage.get_model(model_id, lambda _id: get_model(model, **{**default_params}))
        embedding_value = embedding_model.embed_query(exec_problem_text)
        vector = VectorStore.get_embedding_vector()
        embedding_list = vector.query(exec_problem_text, embedding_value, knowledge_id_list, None,
                                      exclude_document_id_list,
                                      exclude_paragraph_id_list, True, top_n, similarity, SearchMode(search_mode))
        if embedding_list is None:
            return []
        paragraph_list = self.list_paragraph(embedding_list, vector)
        result = [self.reset_paragraph(paragraph, embedding_list) for paragraph in paragraph_list]
        result = self.after_sales_rerank(exec_problem_text, result)
        return result

    @staticmethod
    def _extract_structured_tokens(question: str) -> Dict:
        text = question or ""
        upper_text = text.upper()
        model_list = list(set(re.findall(r"[A-Za-z]{1,4}[-]?[A-Za-z0-9]{2,12}", upper_text)))
        sn_imei_list = list(set(re.findall(r"(?:SN|IMEI)[:：]?\s*([A-Za-z0-9]{6,20})", upper_text)))
        brand_candidates = ["华为", "小米", "苹果", "联想", "VIVO", "OPPO", "荣耀", "三星", "戴尔", "惠普", "THINKPAD"]
        brand_list = [b for b in brand_candidates if b in upper_text]
        return {
            "model_list": model_list[:5],
            "sn_imei_list": sn_imei_list[:3],
            "brand_list": brand_list[:3],
        }

    @staticmethod
    def _after_sales_bonus(question_tokens: Dict, row: ParagraphPipelineModel) -> float:
        text = f"{(row.document_name or '').upper()} {(row.content or '').upper()}"
        meta = row.meta or {}
        meta_models = [m.upper() for m in (meta.get("after_sales_model_tokens") or [])]
        meta_brands = [b.upper() for b in (meta.get("after_sales_brands") or [])]
        bonus = 0.0
        for model in question_tokens.get("model_list", []):
            if len(model) >= 4 and (model in text or model in meta_models):
                bonus += 0.12
        for brand in question_tokens.get("brand_list", []):
            if brand in text or brand in meta_brands:
                bonus += 0.1
        for sn_imei in question_tokens.get("sn_imei_list", []):
            if sn_imei and sn_imei in text:
                bonus += 0.18
        doc_type = meta.get("after_sales_doc_type")
        if doc_type in ("warranty_policy", "return_exchange", "fault_sop", "service_channel"):
            bonus += 0.05
        return bonus

    def after_sales_rerank(self, question: str, rows: List[ParagraphPipelineModel]) -> List[ParagraphPipelineModel]:
        if not rows:
            return rows
        # 通用库导入的段落会携带 after_sales_mode，重排仅作用于这些段落。
        after_sales_rows = [row for row in rows if bool((row.meta or {}).get("after_sales_mode"))]
        if len(after_sales_rows) == 0:
            return rows
        tokens = self._extract_structured_tokens(question)
        has_model = len(tokens.get("model_list", [])) > 0
        if has_model:
            matched = [
                row for row in rows if any(
                    m in f"{(row.document_name or '').upper()} {(row.content or '').upper()}"
                    or m in [x.upper() for x in ((row.meta or {}).get("after_sales_model_tokens") or [])]
                    for m in tokens.get("model_list", [])
                )
            ]
            if len(matched) > 0:
                rows = matched
        return sorted(
            rows,
            key=lambda row: (row.comprehensive_score or 0) + self._after_sales_bonus(tokens, row),
            reverse=True
        )

    @staticmethod
    def reset_paragraph(paragraph: Dict, embedding_list: List) -> ParagraphPipelineModel:
        filter_embedding_list = [embedding for embedding in embedding_list if
                                 str(embedding.get('paragraph_id')) == str(paragraph.get('id'))]
        if filter_embedding_list is not None and len(filter_embedding_list) > 0:
            find_embedding = filter_embedding_list[-1]
            return (ParagraphPipelineModel.builder()
                    .add_paragraph(paragraph)
                    .add_similarity(find_embedding.get('similarity'))
                    .add_comprehensive_score(find_embedding.get('comprehensive_score'))
                    .add_knowledge_name(paragraph.get('knowledge_name'))
                    .add_knowledge_type(paragraph.get('knowledge_type'))
                    .add_document_name(paragraph.get('document_name'))
                    .add_hit_handling_method(paragraph.get('hit_handling_method'))
                    .add_directly_return_similarity(paragraph.get('directly_return_similarity'))
                    .add_meta(reset_meta(paragraph.get('meta')))
                    .build())

    @staticmethod
    def get_similarity(paragraph, embedding_list: List):
        filter_embedding_list = [embedding for embedding in embedding_list if
                                 str(embedding.get('paragraph_id')) == str(paragraph.get('id'))]
        if filter_embedding_list is not None and len(filter_embedding_list) > 0:
            find_embedding = filter_embedding_list[-1]
            return find_embedding.get('comprehensive_score')
        return 0

    @staticmethod
    def list_paragraph(embedding_list: List, vector):
        paragraph_id_list = [row.get('paragraph_id') for row in embedding_list]
        if paragraph_id_list is None or len(paragraph_id_list) == 0:
            return []
        paragraph_list = native_search(QuerySet(Paragraph).filter(id__in=paragraph_id_list),
                                       get_file_content(
                                           os.path.join(PROJECT_DIR, "apps", "application", 'sql',
                                                        'list_knowledge_paragraph_by_paragraph_id.sql')),
                                       with_table_name=True)
        # 如果向量库中存在脏数据 直接删除
        if len(paragraph_list) != len(paragraph_id_list):
            exist_paragraph_list = [row.get('id') for row in paragraph_list]
            for paragraph_id in paragraph_id_list:
                if not exist_paragraph_list.__contains__(paragraph_id):
                    vector.delete_by_paragraph_id(paragraph_id)
        # 如果存在直接返回的则取直接返回段落
        hit_handling_method_paragraph = [paragraph for paragraph in paragraph_list if
                                         (paragraph.get(
                                             'hit_handling_method') == 'directly_return' and BaseSearchDatasetStep.get_similarity(
                                             paragraph, embedding_list) >= paragraph.get(
                                             'directly_return_similarity'))]
        if len(hit_handling_method_paragraph) > 0:
            # 找到评分最高的
            return [sorted(hit_handling_method_paragraph,
                           key=lambda p: BaseSearchDatasetStep.get_similarity(p, embedding_list))[-1]]
        return paragraph_list

    def get_details(self, manage, **kwargs):
        step_args = self.context.get('step_args') or {}

        return {
            'status': self.status,
            'err_message': self.err_message,
            'step_type': 'search_step',
            'paragraph_list': [row.to_dict() for row in (self.context.get('paragraph_list') or [])],
            'run_time': self.context.get('run_time') or 0,
            'problem_text': step_args.get(
                'padding_problem_text') if 'padding_problem_text' in step_args else step_args.get('problem_text'),
            'model_name': self.context.get('model_name'),
            'message_tokens': 0,
            'answer_tokens': 0,
            'cost': 0
        }
