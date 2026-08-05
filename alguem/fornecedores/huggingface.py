# -*- coding: utf-8 -*-
"""Fornecedor HuggingFace, via Inference Providers
(https://huggingface.co/docs/inference-providers) -- desde que a HF
adotou um router compatível com o formato "chat completions" da
OpenAI, é só mais um caso de _base_openai_compativel.py.

O campo 'modelo' aqui costuma incluir o fornecedor de inferência por
trás, separado por ':' -- ex: "deepseek-ai/DeepSeek-V4-Pro:deepinfra"
ou "openai/gpt-oss-120b:cerebras". Sem esse sufixo, a HF escolhe um
fornecedor automaticamente."""
from __future__ import annotations

from ._base_openai_compativel import _FornecedorEstiloOpenAI


class FornecedorHuggingFace(_FornecedorEstiloOpenAI):
    URL_API = "https://router.huggingface.co/v1/chat/completions"

    @property
    def nome(self) -> str:
        return "huggingface"
