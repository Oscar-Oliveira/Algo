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


# As duas linhas seguintes têm de correr ANTES de qualquer módulo de
# teste importar main.py (que falha ao arrancar sem elas) -- por isso
# ficam aqui, ao nível do módulo, não dentro de uma fixture. Isto não
# é o mesmo tipo de variável de ambiente que foi deliberadamente
# evitado no resto do projeto (essas serviam para REDIRECIONAR
# caminhos de ficheiros só para isolar testes); estas são a própria
# forma como a aplicação exige as suas chaves de segurança, em
# produção tal como em testes -- o valor aqui é só fixo para testes,
# nunca reutilizado a sério.
os.environ.setdefault("ONLINE_CHAVE_SESSAO", "chave-de-sessao-de-teste-1234567890")
os.environ.setdefault("ONLINE_CHAVE_CIFRAGEM", cifragem.gerar_chave_nova())


@pytest.fixture(autouse=True)
def _isolar_tudo(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "CAMINHO_BD_POR_OMISSAO", str(tmp_path / "teste.db"))

    from alguem.nucleo import registador as registador_mod
    from alguem.nucleo import identidade as identidade_mod
    monkeypatch.setattr(registador_mod, "PASTA_LOGS_POR_OMISSAO", str(tmp_path / "logs_alguem"))
    monkeypatch.setattr(identidade_mod, "CAMINHO_ID_POR_OMISSAO", str(tmp_path / ".estudante_id"))

    bd.preparar_bd()
    yield


@pytest.fixture
def caminho_bd(tmp_path):
    return str(tmp_path / "teste.db")
