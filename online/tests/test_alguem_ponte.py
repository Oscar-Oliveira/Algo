# -*- coding: utf-8 -*-
"""Testes de online.alguem_ponte -- a única adaptação necessária para
reaproveitar alguem/ no serviço web."""
import pytest

import alguem_ponte
import autenticacao
import bd
import credenciais


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


# ---------- achado 2 (PlanoAuditoria.md): revalidar o host do Ollama a cada uso ----------

def test_construir_alguem_rejeita_host_que_passou_a_apontar_para_interno():
    """_validar_host_ollama já corre em guardar_credencial, mas só uma
    vez, ao guardar -- um domínio com TTL baixo pode resolver para um
    IP público nesse momento e para um IP interno mais tarde (DNS
    rebinding). Aqui simula-se isso: guarda-se com um host válido,
    depois altera-se diretamente na BD para um IP interno (sem passar
    pela validação de guardar_credencial, tal como uma resolução DNS
    diferente também não passaria por ela) -- construir_alguem() tem
    de recusar, não só confiar no que já estava guardado."""
    id_est = autenticacao.registar("ollama@escola.pt", "password123")
    credenciais.guardar_credencial(
        id_est, "ollama", "llama3", "", host="http://exemplo.pt:11434")
    with bd.sessao_bd() as ligacao:
        ligacao.execute(
            "UPDATE credencial_llm SET host = %s WHERE estudante_id = %s",
            ("http://127.0.0.1:11434", id_est),
        )
    with pytest.raises(alguem_ponte.ErroAlguemIndisponivel, match="deixou de ser válido"):
        alguem_ponte.construir_alguem(id_est)


def test_construir_alguem_aceita_host_ollama_ainda_valido():
    id_est = autenticacao.registar("ollama2@escola.pt", "password123")
    credenciais.guardar_credencial(
        id_est, "ollama", "llama3", "", host="http://exemplo.pt:11434")
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.fornecedor.host == "http://exemplo.pt:11434"
