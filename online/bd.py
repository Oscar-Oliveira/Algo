# -*- coding: utf-8 -*-
"""Base de dados PostgreSQL -- deliberadamente simples (sem ORM), dado
que o pedido foi "sem grandes frameworks". Esquema aplicado de forma
idempotente no arranque (CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT
EXISTS), sem framework de migrações dedicado -- Postgres suporta os
dois nativamente, ao contrário do SQLite usado antes desta migração
(ver git history), que precisava de um shim manual por coluna.

Não há tabela de "programas" -- por decisão explícita, esta versão não
guarda código entre visitas (cada sessão começa vazia)."""
from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

VARIAVEL_AMBIENTE_DSN = "ONLINE_DATABASE_URL"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS estudante (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash BYTEA NOT NULL,
    id_pseudonimo TEXT NOT NULL UNIQUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    aprovado BOOLEAN NOT NULL DEFAULT TRUE,
    admin BOOLEAN NOT NULL DEFAULT FALSE,
    tentativas_login_falhadas INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS grupo (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    codigo_hash TEXT NOT NULL UNIQUE,
    codigo_cifrado BYTEA NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    criado_por INTEGER REFERENCES estudante(id)
);

CREATE TABLE IF NOT EXISTS credencial_llm (
    estudante_id INTEGER PRIMARY KEY REFERENCES estudante(id) ON DELETE CASCADE,
    fornecedor TEXT NOT NULL,
    modelo TEXT NOT NULL,
    api_key_cifrada BYTEA,
    host TEXT,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS relatorio_problema (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estudante_id INTEGER NOT NULL REFERENCES estudante(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS log_atividade (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo TEXT NOT NULL,
    ator_id INTEGER REFERENCES estudante(id) ON DELETE SET NULL,
    alvo_id INTEGER REFERENCES estudante(id) ON DELETE SET NULL,
    grupo_id INTEGER REFERENCES grupo(id) ON DELETE SET NULL,
    detalhes TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_log_atividade_criado_em ON log_atividade(criado_em);
CREATE INDEX IF NOT EXISTS idx_log_atividade_grupo ON log_atividade(grupo_id);
CREATE INDEX IF NOT EXISTS idx_log_atividade_ator ON log_atividade(ator_id);
CREATE INDEX IF NOT EXISTS idx_log_atividade_alvo ON log_atividade(alvo_id);

CREATE TABLE IF NOT EXISTS tentativa_registo (
    ip_hash TEXT PRIMARY KEY,
    tentativas INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate TIMESTAMPTZ,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE estudante ADD COLUMN IF NOT EXISTS grupo_id INTEGER REFERENCES grupo(id) ON DELETE SET NULL;
"""

_pool: ConnectionPool | None = None


def _dsn_por_omissao() -> str:
    dsn = os.environ.get(VARIAVEL_AMBIENTE_DSN)
    if not dsn:
        raise RuntimeError(
            f"A variável de ambiente {VARIAVEL_AMBIENTE_DSN} não está definida -- "
            f"define-a com a DSN do PostgreSQL antes de arrancar o servidor "
            f"(ex: postgresql://utilizador:password@host:5432/base_de_dados)."
        )
    return dsn


def _obter_pool(dsn: str | None = None) -> ConnectionPool:
    """Uma pool por DSN explícita (usada em testes, que passam a sua
    própria DSN de base de dados de teste); a pool por omissão (DSN de
    produção) é criada uma única vez, lazy, e reutilizada entre
    pedidos -- evita abrir uma ligação TCP nova a cada pedido HTTP."""
    global _pool
    if dsn is not None:
        return ConnectionPool(dsn, open=True, kwargs={"row_factory": dict_row})
    if _pool is None:
        _pool = ConnectionPool(_dsn_por_omissao(), open=True, kwargs={"row_factory": dict_row})
    return _pool


def obter_ligacao(dsn: str | None = None) -> psycopg.Connection:
    if dsn is not None:
        ligacao = psycopg.connect(dsn, row_factory=dict_row)
        ligacao.autocommit = False
        return ligacao
    ligacao = _obter_pool().getconn()
    return ligacao


def _devolver_ligacao(ligacao: psycopg.Connection, dsn: str | None) -> None:
    if dsn is not None:
        ligacao.close()
    else:
        _obter_pool().putconn(ligacao)


def preparar_bd(dsn: str | None = None) -> None:
    """Cria as tabelas/colunas em falta -- chamar uma vez ao arrancar a
    aplicação (idempotente, seguro chamar sempre)."""
    ligacao = obter_ligacao(dsn)
    try:
        with ligacao.cursor() as cursor:
            cursor.execute(ESQUEMA)
        ligacao.commit()
    finally:
        _devolver_ligacao(ligacao, dsn)


@contextmanager
def sessao_bd(dsn: str | None = None):
    """Gestor de contexto: abre, faz commit se não houver exceção, fecha
    sempre. Uso: `with sessao_bd() as bd: bd.execute(...)`."""
    ligacao = obter_ligacao(dsn)
    try:
        yield ligacao
        ligacao.commit()
    except Exception:
        ligacao.rollback()
        raise
    finally:
        _devolver_ligacao(ligacao, dsn)


class ErroBackup(Exception):
    pass


async def gerar_backup_sql(destino: str, dsn: str | None = None) -> None:
    """Escreve um dump SQL completo da base de dados em 'destino', via
    `pg_dump` (nunca uma cópia de ficheiro -- não há um único ficheiro
    para copiar, ao contrário do SQLite de antes desta migração).
    Corre em subprocesso assíncrono (nunca subprocess.run, que
    bloquearia o event loop inteiro -- mesma convenção já usada em
    executor.py para o compilador/execução de código de estudantes).
    A password NUNCA vai como argumento de linha de comandos (ficaria
    visível em listagens de processos, ex. `ps aux`) -- é passada ao
    subprocesso só através da variável de ambiente PGPASSWORD."""
    dsn = dsn or _dsn_por_omissao()
    info = conninfo_to_dict(dsn)
    password = info.pop("password", "")
    conninfo_sem_password = " ".join(f"{chave}={valor}" for chave, valor in info.items())

    ambiente = os.environ.copy()
    if password:
        ambiente["PGPASSWORD"] = password

    processo = await asyncio.create_subprocess_exec(
        "pg_dump", conninfo_sem_password, "-f", destino, "--no-owner", "--no-privileges",
        env=ambiente,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _saida, erro = await processo.communicate()
    if processo.returncode != 0:
        raise ErroBackup(f"pg_dump falhou: {erro.decode('utf-8', errors='replace')}")
