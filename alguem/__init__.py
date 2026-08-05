# -*- coding: utf-8 -*-
"""Alguem -- tutor de algoritmia baseado em LLM, integrado com a
linguagem ALGO. Vive inteiramente aqui: algo_lang/compilador/ nunca é
alterado nem depende de nada daqui. O único ponto de contacto é o
'?' da consola do ALGO (algo_lang/cli.py), que importa este pacote
para chamar o Alguem -- essa dependência é só nessa direção."""
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
