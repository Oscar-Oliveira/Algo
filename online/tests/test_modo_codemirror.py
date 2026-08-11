# -*- coding: utf-8 -*-
"""Testes de online.modo_codemirror."""
import importlib
import warnings

import pytest

import modo_codemirror


def test_gerar_js_modo_produz_javascript_valido_o_suficiente():
    js = modo_codemirror.gerar_js_modo()
    assert "CodeMirror.defineSimpleMode" in js
    assert "algoritmo" in js


# ---------- ON-37: aviso quando há palavra-chave não classificada ----------

def test_sem_palavras_nao_classificadas_no_estado_normal():
    """No estado normal do projeto, todas as palavras-chave do lexer já
    estão classificadas em _PALAVRAS_ACAO/_PALAVRAS_LOGICAS/tipos/
    literais -- confirma que não há nenhuma a cair silenciosamente no
    fallback 'acao'."""
    assert modo_codemirror._PALAVRAS_NAO_CLASSIFICADAS == set()


def test_avisa_quando_ha_palavra_chave_nao_classificada(monkeypatch):
    from algo_lang.compilador import lexer

    palavras_com_extra = lexer.PALAVRAS_CHAVE | {"palavra_de_teste_nao_classificada"}
    monkeypatch.setattr(lexer, "PALAVRAS_CHAVE", palavras_com_extra)
    try:
        with pytest.warns(UserWarning, match="palavra_de_teste_nao_classificada"):
            importlib.reload(modo_codemirror)
    finally:
        importlib.reload(modo_codemirror)  # repõe o estado normal para os testes seguintes
