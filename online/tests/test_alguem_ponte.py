# -*- coding: utf-8 -*-
"""Testes de online.alguem_ponte -- a única adaptação necessária para
reaproveitar alguem/ no serviço web."""
import alguem_ponte


# ---------- ON-26: mesmo limite de AG-28 aplicado no ponto de entrada do online ----------

def test_limitar_ficheiros_visiveis_dentro_do_limite_fica_intacto():
    ficheiros = [("a.algo", "conteudo a"), ("b.algo", "conteudo b")]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    assert resultado == ficheiros


def test_limitar_ficheiros_visiveis_corta_pelo_numero_de_ficheiros(monkeypatch):
    monkeypatch.setattr(alguem_ponte, "LIMITE_FICHEIROS", 2)
    ficheiros = [(f"f{i}.algo", f"conteudo {i}") for i in range(5)]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    assert len(resultado) == 2


def test_limitar_ficheiros_visiveis_trunca_por_bytes_totais(monkeypatch):
    monkeypatch.setattr(alguem_ponte, "LIMITE_BYTES_TOTAL", 20)
    ficheiros = [("grande.algo", "x" * 100)]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    assert len(resultado) == 1
    nome, conteudo = resultado[0]
    assert "truncado" in conteudo


def test_limitar_ficheiros_visiveis_para_de_incluir_apos_esgotar_bytes(monkeypatch):
    monkeypatch.setattr(alguem_ponte, "LIMITE_BYTES_TOTAL", 15)
    ficheiros = [("a.algo", "x" * 10), ("b.algo", "y" * 10), ("c.algo", "z" * 10)]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    nomes = [n for n, _ in resultado]
    # a.algo entra inteiro (10 bytes), b.algo entra truncado (esgota o
    # orçamento de 15), c.algo não entra de todo
    assert nomes == ["a.algo", "b.algo"]
    assert "truncado" in dict(resultado)["b.algo"]
