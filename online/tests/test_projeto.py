# -*- coding: utf-8 -*-
import io
import zipfile

import pytest

import projeto


# ---------- construir_zip_do_projeto ----------

def test_construir_zip_do_projeto_gera_zip_com_os_ficheiros():
    ficheiros = [
        {"nome": "principal.algo", "conteudo": 'algoritmo "T"\ninicio\nfim\n'},
        {"nome": "biblioteca.algo", "conteudo": "funcao dobro(x: inteiro): inteiro\n"},
    ]
    conteudo_zip = projeto.construir_zip_do_projeto(ficheiros)
    zf = zipfile.ZipFile(io.BytesIO(conteudo_zip))
    assert zf.namelist() == ["principal.algo", "biblioteca.algo"]
    assert zf.read("principal.algo").decode("utf-8") == ficheiros[0]["conteudo"]


def test_construir_zip_do_projeto_rejeita_sem_ficheiros():
    with pytest.raises(projeto.ErroProjeto):
        projeto.construir_zip_do_projeto([])


def test_construir_zip_do_projeto_rejeita_nome_com_caminho():
    with pytest.raises(projeto.ErroProjeto):
        projeto.construir_zip_do_projeto([{"nome": "../fora.algo", "conteudo": ""}])


def test_construir_zip_do_projeto_rejeita_nome_sem_extensao_algo():
    with pytest.raises(projeto.ErroProjeto):
        projeto.construir_zip_do_projeto([{"nome": "principal.txt", "conteudo": ""}])


# ---------- extrair_zip_do_projeto ----------

def _zip_de(ficheiros: dict) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as zf:
        for nome, conteudo in ficheiros.items():
            zf.writestr(nome, conteudo)
    return memoria.getvalue()


def test_extrair_zip_do_projeto_devolve_os_ficheiros_pela_mesma_ordem():
    conteudo_zip = projeto.construir_zip_do_projeto([
        {"nome": "principal.algo", "conteudo": "a"},
        {"nome": "biblioteca.algo", "conteudo": "b"},
    ])
    ficheiros = projeto.extrair_zip_do_projeto(conteudo_zip)
    assert ficheiros == [
        {"nome": "principal.algo", "conteudo": "a"},
        {"nome": "biblioteca.algo", "conteudo": "b"},
    ]


def test_extrair_zip_do_projeto_rejeita_zip_invalido():
    with pytest.raises(projeto.ErroProjeto):
        projeto.extrair_zip_do_projeto(b"nao e um zip")


def test_extrair_zip_do_projeto_rejeita_zip_vazio():
    with pytest.raises(projeto.ErroProjeto):
        projeto.extrair_zip_do_projeto(_zip_de({}))


def test_extrair_zip_do_projeto_rejeita_nome_com_caminho():
    with pytest.raises(projeto.ErroProjeto):
        projeto.extrair_zip_do_projeto(_zip_de({"../fora.algo": "x"}))


def test_extrair_zip_do_projeto_rejeita_nome_sem_extensao_algo():
    with pytest.raises(projeto.ErroProjeto):
        projeto.extrair_zip_do_projeto(_zip_de({"principal.txt": "x"}))


def test_extrair_zip_do_projeto_rejeita_conteudo_nao_utf8():
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as zf:
        zf.writestr("principal.algo", b"\xff\xfe\x00\x01")
    with pytest.raises(projeto.ErroProjeto):
        projeto.extrair_zip_do_projeto(memoria.getvalue())


def test_extrair_zip_do_projeto_rejeita_demasiado_grande():
    conteudo_enorme = "x" * (projeto.TAMANHO_MAXIMO_DESCOMPRIMIDO_BYTES + 1)
    with pytest.raises(projeto.ErroProjeto):
        projeto.extrair_zip_do_projeto(_zip_de({"principal.algo": conteudo_enorme}))


def test_extrair_zip_do_projeto_rejeita_demasiados_ficheiros():
    ficheiros = {f"f{i}.algo": "x" for i in range(projeto.NUM_MAXIMO_FICHEIROS + 1)}
    with pytest.raises(projeto.ErroProjeto):
        projeto.extrair_zip_do_projeto(_zip_de(ficheiros))
