# -*- coding: utf-8 -*-
"""Descarregar/abrir um projeto (vários ficheiros .algo) como .zip --
deliberadamente sem persistência em BD (ver notes.md): o .zip
descarregado É o registo do projeto, gerido pelo próprio estudante.
Uma vez descomprimido pelo sistema operativo, a pasta resultante já é
uma pasta normal de ficheiros .algo -- algo_lang/cli.py já sabe abri-
la e resolver 'incluir' sem nenhuma alteração, por isso este módulo só
precisa de tratar do lado do editor online (construir o .zip a
descarregar, ler o .zip ao abrir)."""
from __future__ import annotations

import io
import zipfile


class ErroProjeto(Exception):
    """Erro ao construir ou ler um .zip de projeto -- sempre por causa
    de dados vindos do estudante (nomes inválidos, .zip corrompido,
    demasiado grande), nunca um erro de programação."""


# Limites de defesa contra .zip malicioso/acidental (ex: "zip bomb" --
# um ficheiro pequeno que descomprime para muitos GB). Generosos para
# uso real (um projeto de aula tem poucos ficheiros pequenos).
NUM_MAXIMO_FICHEIROS = 50
TAMANHO_MAXIMO_DESCOMPRIMIDO_BYTES = 5_000_000


def _validar_nome(nome: str) -> None:
    if not nome or nome in (".", "..") or "/" in nome or "\\" in nome or not nome.endswith(".algo"):
        raise ErroProjeto(f"Nome de ficheiro inválido no projeto: {nome!r}")


def construir_zip_do_projeto(ficheiros: list[dict]) -> bytes:
    """A ordem dos ficheiros no .zip segue a ordem da lista recebida --
    o primeiro é sempre o 'principal' (mesma convenção do editor,
    ficheiros[0]), e extrair_zip_do_projeto devolve-os pela mesma
    ordem, para o download+upload preservar qual é o principal."""
    if not ficheiros:
        raise ErroProjeto("O projeto não tem ficheiros.")
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zf:
        for ficheiro in ficheiros:
            nome = ficheiro.get("nome", "")
            _validar_nome(nome)
            zf.writestr(nome, ficheiro.get("conteudo", ""))
    return memoria.getvalue()


def _ler_entrada_com_limite(zf: zipfile.ZipFile, info: zipfile.ZipInfo, limite_restante: int) -> bytes:
    """Lê a entrada aos pedaços em vez de zf.read(info) de uma vez --
    o campo info.file_size vem do próprio .zip e não é de confiar para
    decidir ANTES de ler se a entrada é grande demais (uma zip bomb
    pode declarar um tamanho pequeno). Aborta assim que o limite
    acumulado (entre todas as entradas) for ultrapassado."""
    pedacos = []
    total = 0
    with zf.open(info) as fonte:
        while True:
            pedaco = fonte.read(65536)
            if not pedaco:
                break
            total += len(pedaco)
            if total > limite_restante:
                raise ErroProjeto("O projeto descomprimido é demasiado grande.")
            pedacos.append(pedaco)
    return b"".join(pedacos)


def extrair_zip_do_projeto(conteudo_zip: bytes) -> list[dict]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(conteudo_zip))
    except zipfile.BadZipFile:
        raise ErroProjeto("O ficheiro não é um .zip válido.")

    entradas = [info for info in zf.infolist() if not info.is_dir()]
    if not entradas:
        raise ErroProjeto("O .zip não contém nenhum ficheiro.")
    if len(entradas) > NUM_MAXIMO_FICHEIROS:
        raise ErroProjeto("O .zip tem ficheiros a mais.")

    ficheiros = []
    tamanho_lido = 0
    for info in entradas:
        _validar_nome(info.filename)
        dados = _ler_entrada_com_limite(zf, info, TAMANHO_MAXIMO_DESCOMPRIMIDO_BYTES - tamanho_lido)
        tamanho_lido += len(dados)
        try:
            conteudo = dados.decode("utf-8")
        except UnicodeDecodeError:
            raise ErroProjeto(f"O ficheiro '{info.filename}' não é texto UTF-8 válido.")
        ficheiros.append({"nome": info.filename, "conteudo": conteudo})

    nomes = [f["nome"] for f in ficheiros]
    if len(nomes) != len(set(nomes)):
        raise ErroProjeto("O .zip tem ficheiros com nomes repetidos.")

    return ficheiros
