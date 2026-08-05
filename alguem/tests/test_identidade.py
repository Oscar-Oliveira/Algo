# -*- coding: utf-8 -*-
"""Testes de alguem.nucleo.identidade."""
import os

from alguem.nucleo.identidade import obter_id_estudante


def test_gera_um_id_na_primeira_vez(tmp_path):
    caminho = str(tmp_path / ".estudante_id")
    assert not os.path.isfile(caminho)
    id_gerado = obter_id_estudante(caminho)
    assert id_gerado
    assert os.path.isfile(caminho)


def test_reutiliza_o_mesmo_id_em_chamadas_seguintes(tmp_path):
    caminho = str(tmp_path / ".estudante_id")
    id1 = obter_id_estudante(caminho)
    id2 = obter_id_estudante(caminho)
    id3 = obter_id_estudante(caminho)
    assert id1 == id2 == id3


def test_ids_gerados_em_pastas_diferentes_sao_diferentes(tmp_path):
    caminho_a = str(tmp_path / "a" / ".estudante_id")
    caminho_b = str(tmp_path / "b" / ".estudante_id")
    os.makedirs(os.path.dirname(caminho_a))
    os.makedirs(os.path.dirname(caminho_b))
    id_a = obter_id_estudante(caminho_a)
    id_b = obter_id_estudante(caminho_b)
    assert id_a != id_b


def test_nao_identifica_a_pessoa_e_so_um_uuid(tmp_path):
    """Confirma que o identificador não é, por exemplo, o nome de
    utilizador do sistema operativo -- é só um UUID aleatório."""
    import uuid
    caminho = str(tmp_path / ".estudante_id")
    id_gerado = obter_id_estudante(caminho)
    # não levanta exceção -- é um UUID válido
    uuid.UUID(id_gerado)
