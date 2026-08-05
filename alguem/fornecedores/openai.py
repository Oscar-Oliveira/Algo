# -*- coding: utf-8 -*-
"""Fornecedor OpenAI, API direta (https://platform.openai.com) -- o
formato "chat completions" nasceu aqui; a lógica HTTP está em
_base_openai_compativel.py."""
from __future__ import annotations

from ._base_openai_compativel import _FornecedorEstiloOpenAI


class FornecedorOpenAI(_FornecedorEstiloOpenAI):
    URL_API = "https://api.openai.com/v1/chat/completions"

    @property
    def nome(self) -> str:
        return "openai"
