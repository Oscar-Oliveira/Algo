# -*- coding: utf-8 -*-
from .base import AgenteLLM, ErroFornecedorLLM
from .openrouter import FornecedorOpenRouter
from .gemini import FornecedorGemini
from .openai import FornecedorOpenAI
from .anthropic import FornecedorAnthropic
from .huggingface import FornecedorHuggingFace
from .ollama import FornecedorOllama
from .opencode import FornecedorOpenCode

FORNECEDORES = {
    "openrouter": FornecedorOpenRouter,
    "gemini": FornecedorGemini,
    "openai": FornecedorOpenAI,
    "anthropic": FornecedorAnthropic,
    "huggingface": FornecedorHuggingFace,
    "ollama": FornecedorOllama,
    "opencode": FornecedorOpenCode,
}


def criar_fornecedor(nome: str, modelo: str, api_key: str = "", **extras) -> AgenteLLM:
    """Instancia o fornecedor certo a partir do nome (tal como aparece
    no config.json, em 'fornecedor'). Acrescentar um fornecedor novo é
    só escrever a classe no seu próprio ficheiro (ver base.py) e
    registá-la aqui.

    '**extras' passa por diante quaisquer outros campos que o
    config.json tenha em credenciais.<fornecedor> além de 'api_key' --
    hoje só a Ollama usa isto ('host'), mas mantém a porta aberta para
    outros fornecedores que venham a precisar de mais alguma coisa."""
    classe = FORNECEDORES.get(nome)
    if classe is None:
        disponiveis = ", ".join(sorted(FORNECEDORES))
        raise ErroFornecedorLLM(
            f"Fornecedor '{nome}' desconhecido. Disponíveis: {disponiveis}."
        )
    try:
        return classe(modelo=modelo, api_key=api_key, **extras)
    except TypeError as e:
        raise ErroFornecedorLLM(
            f"Configuração inválida para o fornecedor '{nome}' -- verifica "
            f"os campos em credenciais.{nome} no config.json ({e})."
        ) from e
