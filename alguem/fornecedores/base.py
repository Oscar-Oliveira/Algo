# -*- coding: utf-8 -*-
"""Abstração comum a todos os fornecedores de LLM.

Cada fornecedor concreto (OpenRouter, Gemini, ...) vive no seu próprio
ficheiro, com a sua própria classe, e traduz o formato "neutro" de
mensagens (lista de {"role": ..., "content": ...}, ao estilo OpenAI/
ChatML, que é o que o resto do Alguem usa) para o formato específico da
API desse fornecedor -- e o mesmo na direção inversa para a resposta.

Isto é o que permite trocar de fornecedor/modelo só mudando o
config.json, sem tocar em mais nada -- o resto do Alguem (política
pedagógica, escada de ajuda, o tutor em si) nunca sabe, nem precisa de
saber, qual é o fornecedor concreto por trás.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod


class ErroFornecedorLLM(Exception):
    """Erro ao comunicar com o fornecedor de LLM (rede, credenciais
    inválidas, resposta inesperada, etc.) -- sempre com uma mensagem
    pensada para ser mostrada diretamente ao utilizador, não um
    traceback cru."""
    pass


class AgenteLLM(ABC):
    """Um fornecedor de LLM concreto. 'mensagens' é sempre uma lista de
    dicionários {"role": "system"|"user"|"assistant", "content": str},
    pela ordem da conversa (a primeira pode ser "system"). Devolve
    sempre uma string com a resposta do modelo."""

    # A maioria dos fornecedores precisa de uma chave de API real -- mas
    # um fornecedor local (ex: Ollama, a correr na própria máquina) pode
    # não precisar de nenhuma. Uma subclasse que não precise de chave
    # define REQUER_API_KEY = False.
    REQUER_API_KEY = True

    def __init__(self, modelo: str, api_key: str = ""):
        if self.REQUER_API_KEY and not api_key:
            raise ErroFornecedorLLM(
                f"Falta a chave de API para o fornecedor '{self.nome}' "
                f"no config.json (em credenciais.{self.nome}.api_key)."
            )
        self.modelo = modelo
        self.api_key = api_key

    @property
    @abstractmethod
    def nome(self) -> str:
        """Identificador curto do fornecedor (usado no config.json e
        em mensagens de erro), ex: 'openrouter', 'gemini'."""

    @abstractmethod
    def responder(self, mensagens: list[dict]) -> str:
        """Envia a conversa ao modelo e devolve o texto da resposta.
        Levanta ErroFornecedorLLM em caso de falha (rede, API,
        resposta em formato inesperado)."""


def pedir_json(url: str, corpo: dict, cabecalhos: dict, nome_exibicao: str,
                timeout: int = 60) -> dict:
    """POST de 'corpo' como JSON para 'url', devolve a resposta já
    descodificada. Transporte HTTP partilhado por todos os
    fornecedores (ARCH-06) -- cada um continua a construir o seu
    próprio corpo/cabeçalhos e a interpretar a sua própria forma de
    resposta, só este bloco de rede + tratamento de erro é comum.
    'nome_exibicao' vai literal nas mensagens de erro (ex: 'Anthropic',
    'openrouter') -- não normalizado aqui, para não mudar o texto que
    cada fornecedor já mostrava antes desta extração."""
    pedido = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), method="POST", headers=cabecalhos)
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        corpo_erro = e.read().decode("utf-8", errors="replace")
        raise ErroFornecedorLLM(
            f"A {nome_exibicao} recusou o pedido (HTTP {e.code}): {corpo_erro}"
        ) from e
    except urllib.error.URLError as e:
        raise ErroFornecedorLLM(
            f"Não foi possível contactar a {nome_exibicao}: {e.reason}"
        ) from e
