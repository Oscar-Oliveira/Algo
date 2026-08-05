# -*- coding: utf-8 -*-
"""Base de dados SQLite -- deliberadamente simples (sem ORM), dado que
o pedido foi "sem grandes frameworks" e o esquema é pequeno: contas de
estudante, e a credencial de LLM que cada um traz e configura.

Não há tabela de "programas" -- por decisão explícita, esta versão não
guarda código entre visitas (cada sessão começa vazia)."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

# Numa subpasta dedicada (não ao lado do código) -- é essa subpasta que
# fica montada como volume Docker, para os dados sobreviverem a um
# reinício do contentor sem precisar de nenhuma variável de ambiente
# nova (mantém a mesma filosofia já usada no resto do projeto).
_PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
os.makedirs(_PASTA_DADOS, exist_ok=True)
CAMINHO_BD_POR_OMISSAO = os.path.join(_PASTA_DADOS, "dados.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS estudante (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash BLOB NOT NULL,
    id_pseudonimo TEXT NOT NULL UNIQUE,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS credencial_llm (
    estudante_id INTEGER PRIMARY KEY REFERENCES estudante(id) ON DELETE CASCADE,
    fornecedor TEXT NOT NULL,
    modelo TEXT NOT NULL,
    api_key_cifrada BLOB,
    host TEXT,
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def obter_ligacao(caminho_bd: str | None = None) -> sqlite3.Connection:
    if caminho_bd is None:
        caminho_bd = CAMINHO_BD_POR_OMISSAO
    ligacao = sqlite3.connect(caminho_bd)
    ligacao.row_factory = sqlite3.Row
    ligacao.execute("PRAGMA foreign_keys = ON")
    return ligacao


def preparar_bd(caminho_bd: str | None = None) -> None:
    """Cria as tabelas se ainda não existirem -- chamar uma vez ao
    arrancar a aplicação (idempotente, seguro chamar sempre)."""
    with obter_ligacao(caminho_bd) as ligacao:
        ligacao.executescript(ESQUEMA)


@contextmanager
def sessao_bd(caminho_bd: str | None = None):
    """Gestor de contexto: abre, faz commit se não houver exceção, fecha
    sempre. Uso: `with sessao_bd() as bd: bd.execute(...)`."""
    ligacao = obter_ligacao(caminho_bd)
    try:
        yield ligacao
        ligacao.commit()
    finally:
        ligacao.close()
