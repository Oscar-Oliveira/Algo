# -*- coding: utf-8 -*-
"""Registo de bibliotecas embutidas da linguagem ALGO.

Para adicionar uma nova biblioteca, basta criar um novo ficheiro .py nesta
pasta com três variáveis:
    NOME      -- nome da biblioteca em minúsculas (ex: "matematica")
    CABECALHO -- código Python injetado uma vez no topo do ficheiro gerado
    FUNCOES   -- dicionário nome_metodo -> (categorias_args, tipo_retorno, codigo_python)
                 ou (categorias_args, tipo_retorno, codigo_python, dims_retorno)
                 -- o 4º elemento é opcional (omitido = 0, valor escalar);
                 usa-se 1 quando a função devolve um vetor do tipo indicado
                 em tipo_retorno (ex.: cadeia.dividir devolve cadeia[]).

A biblioteca fica disponível automaticamente com 'importar NomeDaBiblioteca'.
"""
import importlib
import os

_REGISTO = None


def obter_registo():
    global _REGISTO
    if _REGISTO is not None:
        return _REGISTO
    registo = {}
    pasta = os.path.dirname(__file__)
    for nome_ficheiro in sorted(os.listdir(pasta)):
        if not nome_ficheiro.endswith(".py") or nome_ficheiro == "__init__.py":
            continue
        modulo_nome = nome_ficheiro[:-3]
        modulo = importlib.import_module(f".{modulo_nome}", package=__name__)
        if hasattr(modulo, "NOME"):
            registo[modulo.NOME] = {
                "cabecalho": getattr(modulo, "CABECALHO", ""),
                "funcoes": modulo.FUNCOES,
            }
    _REGISTO = registo
    return registo
