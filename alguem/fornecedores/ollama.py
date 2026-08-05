# -*- coding: utf-8 -*-
"""Fornecedor Ollama (https://ollama.com) -- corre modelos
completamente na máquina de quem o usa, através do endpoint compatível
com OpenAI que a Ollama expõe localmente. Não precisa de nenhuma chave
de API real (a Ollama ignora o valor, mas o cabeçalho Authorization
continua a ser enviado, com um valor qualquer, por convenção).

Especialmente relevante para este projeto: nenhum dado (perguntas do
estudante, código, respostas) sai da máquina -- resolve de vez a
preocupação de privacidade/RGPD dos logs (ver alguem/README.md) para
quem o usar, e não tem custo de API nenhum."""
from __future__ import annotations

from ._base_openai_compativel import _FornecedorEstiloOpenAI

HOST_POR_OMISSAO = "http://localhost:11434"


class FornecedorOllama(_FornecedorEstiloOpenAI):
    REQUER_API_KEY = False

    def __init__(self, modelo: str, api_key: str = "", host: str | None = HOST_POR_OMISSAO):
        super().__init__(modelo=modelo, api_key=api_key or "ollama")
        self.host = (host or HOST_POR_OMISSAO).rstrip("/")

    @property
    def URL_API(self) -> str:  # type: ignore[override]
        return f"{self.host}/v1/chat/completions"

    @property
    def nome(self) -> str:
        return "ollama"
