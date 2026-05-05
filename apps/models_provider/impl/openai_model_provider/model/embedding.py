# coding=utf-8
"""
    @project: MaxKB
    @Author：虎
    @file： embedding.py
    @date：2024/7/12 17:44
    @desc:
"""
import time
from typing import Dict, List

import openai

from models_provider.base_model_provider import MaxKBBaseModel


class OpenAIEmbeddingModel(MaxKBBaseModel):
    model_name: str
    optional_params: dict

    def __init__(self, api_key, base_url, model_name: str, optional_params: dict):
        # 兼容 OpenAI 协议网关在高并发下的偶发超时，提升知识库批量向量化稳定性
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=120.0,
            max_retries=0
        ).embeddings
        self.model_name = model_name
        self.optional_params = optional_params

    def is_cache_model(self):
        return False

    @staticmethod
    def new_instance(model_type, model_name, model_credential: Dict[str, object], **model_kwargs):
        optional_params = MaxKBBaseModel.filter_optional_params(model_kwargs)
        return OpenAIEmbeddingModel(
            api_key=model_credential.get('api_key'),
            model_name=model_name,
            base_url=model_credential.get('api_base'),
            optional_params=optional_params
        )

    def embed_query(self, text: str):
        res = self.embed_documents([text])
        return res[0]

    def embed_documents(
            self, texts: List[str], chunk_size: int | None = None
    ) -> List[List[float]]:
        # 本地重试：对超时/连接抖动做兜底，避免任务直接标记失败
        retryable_errors = (
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.InternalServerError,
        )
        last_error = None
        for attempt in range(4):
            try:
                if len(self.optional_params) > 0:
                    res = self.client.create(
                        input=texts, model=self.model_name, encoding_format="float",
                        **self.optional_params
                    )
                else:
                    res = self.client.create(input=texts, model=self.model_name, encoding_format="float")
                return [e.embedding for e in res.data]
            except retryable_errors as e:
                last_error = e
                if attempt == 3:
                    raise
                # 指数退避，给 OpenAI 兼容网关短暂恢复时间
                time.sleep(1.5 * (2 ** attempt))
        raise last_error
