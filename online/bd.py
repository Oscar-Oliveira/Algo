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

-- Uma só relação para as duas ligações conta<->grupo que antes viviam
-- em sítios diferentes (estudante.grupo_id, admin_grupo) -- a
-- cardinalidade certa para cada tipo de conta é decidida pelo código
-- que lê/escreve aqui (grupos.py), não pelo esquema: um estudante tem
-- quanto muito uma linha (pertença); um admin de grupo pode ter várias
-- (âmbito de gestão); um admin global não precisa de nenhuma (já vê
-- tudo, ver estudante.admin_global).
CREATE TABLE IF NOT EXISTS estudante_grupo (
    estudante_id INTEGER NOT NULL REFERENCES estudante(id) ON DELETE CASCADE,
    grupo_id INTEGER NOT NULL REFERENCES grupo(id) ON DELETE CASCADE,
    PRIMARY KEY (estudante_id, grupo_id)
);

-- Substitui a antiga credencial_llm (uma por conta) -- ver
-- docs/interno/PlanoAlguemLLMInvestigacao.md, Fase 2. estudante_id NULL
-- = configuração global (só o admin gere); preenchido = pessoal.
CREATE TABLE IF NOT EXISTS configuracao_llm (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estudante_id INTEGER REFERENCES estudante(id) ON DELETE CASCADE,
    etiqueta TEXT NOT NULL,
    fornecedor TEXT NOT NULL,
    modelo TEXT NOT NULL,
    api_key_cifrada BYTEA,
    host TEXT,
    criado_por INTEGER REFERENCES estudante(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_configuracao_llm_estudante ON configuracao_llm(estudante_id);

-- Configuração pessoal ativa do estudante -- só para 'apoio'. O
-- guardião nunca é escolha pessoal (só existe seleção GLOBAL para ele,
-- em 'definicao', chave llm_global_guardiao_id) -- é transparente para o
-- estudante, que só escolhe um LLM (o de apoio); ver
-- configuracao_llm.PAPEIS_PESSOAIS.
CREATE TABLE IF NOT EXISTS selecao_llm_estudante (
    estudante_id INTEGER PRIMARY KEY REFERENCES estudante(id) ON DELETE CASCADE,
    apoio_config_id INTEGER REFERENCES configuracao_llm(id) ON DELETE SET NULL
);
ALTER TABLE selecao_llm_estudante DROP COLUMN IF EXISTS guardiao_config_id;

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

CREATE TABLE IF NOT EXISTS definicao (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- Histórico de execução/debug por estudante -- ver
-- docs/interno/PlanoAlguemLLMInvestigacao.md, secção 9/Fase 4.
-- Histórico completo, sem limite nem substituição (decisão validada,
-- ponto 5): cada tentativa fica com a sua própria linha, para sempre,
-- até uma eliminação explícita (secção 14).
CREATE TABLE IF NOT EXISTS execucao_codigo (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estudante_id INTEGER NOT NULL REFERENCES estudante(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    nome_ficheiro_principal TEXT NOT NULL,
    ficheiros TEXT NOT NULL,
    resultado TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_execucao_codigo_estudante ON execucao_codigo(estudante_id);
CREATE INDEX IF NOT EXISTS idx_execucao_codigo_criado_em ON execucao_codigo(criado_em);

-- Prompts do tutor/guardião, editáveis pelo admin (ver
-- docs/interno/PlanoAlguemLLMInvestigacao.md, secção 13/Fase 3). Sem
-- linha para uma 'chave', usa-se o texto por omissão do código (ver
-- online/prompts_configuraveis.py) -- mesmo padrão de 'definicao'.
CREATE TABLE IF NOT EXISTS prompt_configuravel (
    chave TEXT PRIMARY KEY,
    texto TEXT NOT NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_por INTEGER REFERENCES estudante(id) ON DELETE SET NULL
);

ALTER TABLE relatorio_problema ADD COLUMN IF NOT EXISTS visto BOOLEAN NOT NULL DEFAULT FALSE;
-- DEFAULT TRUE (não FALSE) é deliberado: além de servir de omissão
-- para linhas futuras, aplica-se também às linhas já existentes no
-- momento deste ALTER -- é assim que os admins já existentes ficam
-- automaticamente admin_global=TRUE sem precisar de um UPDATE de
-- migração à parte (ver docs/interno/PlanoAlguemLLMInvestigacao.md,
-- secção 15/Fase 1). O valor é irrelevante para contas não-admin.
ALTER TABLE estudante ADD COLUMN IF NOT EXISTS admin_global BOOLEAN NOT NULL DEFAULT TRUE;

-- Permite ao admin excluir um grupo (turma) do uso do Alguem, mesmo com
-- o interruptor global ligado -- ver grupos.grupo_bloqueia_alguem.
ALTER TABLE grupo ADD COLUMN IF NOT EXISTS alguem_ativo BOOLEAN NOT NULL DEFAULT TRUE;

-- Migração única (idempotente -- cada IF só encontra algo para migrar
-- na primeira vez que corre numa base de dados já existente; numa
-- base nova, ou depois da primeira vez, não faz nada): junta os dois
-- sítios antigos de associação conta<->grupo (estudante.grupo_id,
-- tabela admin_grupo) na nova estudante_grupo, e remove-os.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_grupo') THEN
        INSERT INTO estudante_grupo (estudante_id, grupo_id)
            SELECT admin_id, grupo_id FROM admin_grupo
            ON CONFLICT (estudante_id, grupo_id) DO NOTHING;
        DROP TABLE admin_grupo;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'estudante' AND column_name = 'grupo_id') THEN
        INSERT INTO estudante_grupo (estudante_id, grupo_id)
            SELECT id, grupo_id FROM estudante WHERE grupo_id IS NOT NULL
            ON CONFLICT (estudante_id, grupo_id) DO NOTHING;
        ALTER TABLE estudante DROP COLUMN grupo_id;
    END IF;
END $$;

-- Migração única (idempotente, mesmo espírito da anterior): credencial_llm
-- (uma credencial por conta) para configuracao_llm (várias, com etiqueta) --
-- ver docs/interno/PlanoAlguemLLMInvestigacao.md, Fase 2. Os dados antigos
-- não precisam de ficar por compatibilidade, por isso a tabela antiga é
-- eliminada a seguir a copiar o que lá estava.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credencial_llm') THEN
        INSERT INTO configuracao_llm (estudante_id, etiqueta, fornecedor, modelo, api_key_cifrada, host, criado_por, atualizado_em)
            SELECT estudante_id, fornecedor || ' · ' || modelo, fornecedor, modelo, api_key_cifrada, host, estudante_id, atualizado_em
            FROM credencial_llm;
        DROP TABLE credencial_llm;
    END IF;
END $$;
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
