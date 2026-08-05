# -*- coding: utf-8 -*-
"""Identificador de estudante: gerado automaticamente na primeira vez
que o Alguem corre nesta instalação, e reutilizado em todas as sessões
seguintes -- sem pedir nada ao estudante. É o que permite juntar várias
sessões da MESMA pessoa ao longo do tempo (necessário para RQ1/RQ3 da
investigação, que comparam o desempenho antes/depois de várias
interações), sem exigir nenhum sistema de contas.

Não identifica a pessoa (é só um UUID aleatório, sem nome nem email) --
só permite distinguir "esta instalação" de "outra instalação"."""
from __future__ import annotations

import os
import uuid

CAMINHO_ID_POR_OMISSAO = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".estudante_id")


def obter_id_estudante(caminho: str | None = None) -> str:
    """Lê o identificador existente, ou cria um novo na primeira vez."""
    if caminho is None:
        caminho = CAMINHO_ID_POR_OMISSAO
    if os.path.isfile(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            id_existente = f.read().strip()
        if id_existente:
            return id_existente
    novo_id = str(uuid.uuid4())
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(novo_id + "\n")
    return novo_id
