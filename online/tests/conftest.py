# -*- coding: utf-8 -*-
"""Isola cada teste: base de dados própria, chave de cifragem própria,
e (para quem chama o Alguem) a pasta de logs redirecionada por
monkeypatch -- nunca variáveis de ambiente, nunca a pasta real do
pacote alguem/ (mesma técnica já usada em alguem/tests/conftest.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import bd
import cifragem


# As linhas seguintes têm de correr ANTES de qualquer módulo de teste
# importar main.py (que falha ao arrancar sem elas) -- por isso ficam
# aqui, ao nível do módulo, não dentro de uma fixture. Isto não é o
# mesmo tipo de variável de ambiente que foi deliberadamente evitado
# no resto do projeto (essas serviam para REDIRECIONAR caminhos de
# ficheiros só para isolar testes); estas são a própria forma como a
# aplicação exige as suas chaves/configuração, em produção tal como em
# testes -- o valor aqui é só fixo para testes, nunca reutilizado a
# sério.
os.environ.setdefault("ONLINE_CHAVE_SESSAO", "chave-de-sessao-de-teste-1234567890")
os.environ.setdefault("ONLINE_CHAVE_CIFRAGEM", cifragem.gerar_chave_nova())
# Base de dados de teste dedicada -- nunca a de produção. Correr os
# testes localmente exige um PostgreSQL acessível nesta DSN (ver
# online/README.md); em CI, um serviço de container equivalente.
_DSN_TESTE = os.environ.setdefault(
    "ONLINE_TEST_DATABASE_URL", "postgresql://postgres:teste@localhost:5433/algo_teste"
)

# Nomes de todas as tabelas da app, na ordem correta para TRUNCATE ...
# CASCADE não precisar de se preocupar com a ordem (CASCADE já trata
# das dependências de chave estrangeira sozinho).
_TABELAS = (
    "log_atividade", "tentativa_registo", "relatorio_problema", "execucao_codigo",
    "selecao_llm_estudante", "configuracao_llm", "estudante_grupo", "estudante", "grupo", "definicao",
    "prompt_configuravel",
)


@pytest.fixture(autouse=True)
def _isolar_tudo(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "VARIAVEL_AMBIENTE_DSN", "ONLINE_TEST_DATABASE_URL")
    bd.preparar_bd(_DSN_TESTE)
    with bd.sessao_bd(_DSN_TESTE) as ligacao:
        ligacao.execute(f"TRUNCATE {', '.join(_TABELAS)} RESTART IDENTITY CASCADE")

    from alguem.nucleo import registador as registador_mod
    from alguem.nucleo import identidade as identidade_mod
    monkeypatch.setattr(registador_mod, "PASTA_LOGS_POR_OMISSAO", str(tmp_path / "logs_alguem"))
    monkeypatch.setattr(identidade_mod, "CAMINHO_ID_POR_OMISSAO", str(tmp_path / ".estudante_id"))


@pytest.fixture
def dsn():
    return _DSN_TESTE


def pytest_sessionfinish(session, exitstatus):
    """Fecha a pool de ligações por omissão no fim da sessão de testes
    -- sem isto, as threads da pool ficam à espera de ser recolhidas
    pelo interpretador no shutdown, gerando avisos de "couldn't stop
    thread" que não indicam nenhum problema real."""
    if bd._pool is not None:
        bd._pool.close()
