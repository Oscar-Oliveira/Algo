# -*- coding: utf-8 -*-
"""Alguem -- tutor de algoritmia baseado em LLM, integrado com a
linguagem ALGO. Vive inteiramente aqui: algo_lang/compilador/ nunca é
alterado nem depende de nada daqui. Não tem cli.py próprio nem está
ligado à consola do ALGO -- a única forma de o invocar é através do
serviço web (online/alguem_ponte.py:construir_alguem)."""
from .config import criar_alguem, carregar_config, ErroConfiguracao
from .nucleo import (
    Alguem, PoliticaPedagogica, GuardiaoPedagogico, Classificacao,
    Registador, obter_id_estudante,
)
from .nucleo.ficheiros_visiveis import resolver_ficheiros_visiveis
from .fornecedores import ErroFornecedorLLM

__all__ = [
    "criar_alguem", "carregar_config", "ErroConfiguracao",
    "Alguem", "PoliticaPedagogica", "GuardiaoPedagogico", "Classificacao",
    "Registador", "obter_id_estudante",
    "ErroFornecedorLLM", "resolver_ficheiros_visiveis",
]
