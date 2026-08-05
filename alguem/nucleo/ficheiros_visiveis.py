# -*- coding: utf-8 -*-
"""Descobre quais ficheiros .algo o Alguem deve "ver" a partir de um
ficheiro principal: esse ficheiro, mais qualquer um que ele inclua
(via 'incluir "..."'), recursivamente.

Propositadamente NÃO usa o parser verdadeiro do ALGO: o estudante pode
estar a pedir ajuda precisamente porque o ficheiro tem um erro de
sintaxe, e mesmo assim o Alguem deve conseguir ver o código e os
ficheiros incluídos -- por isso a deteção de 'incluir' aqui é feita por
expressão regular, tolerante a um ficheiro que não chega a compilar."""
from __future__ import annotations

import os
import re

PADRAO_INCLUIR = re.compile(r'^\s*incluir\s+"([^"]+)"', re.MULTILINE)


def resolver_ficheiros_visiveis(caminho_principal: str) -> list[tuple[str, str]]:
    """Devolve [(nome_do_ficheiro, conteudo), ...] -- o ficheiro
    principal primeiro, depois cada ficheiro incluído (na ordem em que
    aparece no código), sem repetir o mesmo ficheiro duas vezes mesmo
    que seja incluído por mais do que um caminho."""
    resultado: list[tuple[str, str]] = []
    vistos: set[str] = set()

    def _processar(caminho: str) -> None:
        caminho_abs = os.path.normpath(os.path.abspath(caminho))
        if caminho_abs in vistos:
            return
        vistos.add(caminho_abs)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()
        except OSError:
            return
        resultado.append((os.path.basename(caminho), conteudo))

        pasta_base = os.path.dirname(caminho_abs)
        for caminho_incluido in PADRAO_INCLUIR.findall(conteudo):
            caminho_completo = (
                caminho_incluido if os.path.isabs(caminho_incluido)
                else os.path.join(pasta_base, caminho_incluido)
            )
            _processar(caminho_completo)

    _processar(caminho_principal)
    return resultado
