# -*- coding: utf-8 -*-
"""Fornecedor OpenCode Go (https://opencode.ai/docs/providers/) -- a
gateway de modelos da OpenCode, também no formato "chat completions".
Exige subscrição OpenCode; é o fornecedor mais nicho dos disponíveis
aqui, incluído por completar a lista do documento de investigação."""
from __future__ import annotations

from ._base_openai_compativel import _FornecedorEstiloOpenAI


class FornecedorOpenCode(_FornecedorEstiloOpenAI):
    URL_API = "https://opencode.ai/zen/go/v1/chat/completions"

    @property
    def nome(self) -> str:
        return "opencode"
