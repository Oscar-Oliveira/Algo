# -*- coding: utf-8 -*-
"""Fornecedor OpenRouter (https://openrouter.ai) -- dá acesso a dezenas
de modelos (OpenAI, Anthropic, Google, modelos abertos, ...) através de
uma única API, no formato de "chat completions" já usado pela OpenAI.
A lógica HTTP em si está em _base_openai_compativel.py -- este ficheiro
só define o URL e o nome."""
from __future__ import annotations

from ._base_openai_compativel import _FornecedorEstiloOpenAI


class FornecedorOpenRouter(_FornecedorEstiloOpenAI):
    URL_API = "https://openrouter.ai/api/v1/chat/completions"

    @property
    def nome(self) -> str:
        return "openrouter"
