# -*- coding: utf-8 -*-
"""Configuração partilhada da suite de testes do Alguem.

O 'autouse=True' abaixo garante que NENHUM teste, mesmo que construa
um Alguem sem passar um Registador explícito, escreve alguma vez para
a pasta real 'alguem/logs/' ou para o ficheiro real '.estudante_id' --
tudo fica isolado numa pasta temporária, através de monkeypatch direto
às constantes dos módulos (sem variáveis de ambiente). Isto só
funciona para testes que correm DENTRO deste processo -- os testes que
correm o comando 'algo' a sério, num subprocesso (tests/test_consola.py
e tests/test_consola_alguem.py, na suite do ALGO), usam outra técnica:
copiam o projeto todo para uma pasta temporária e correm a partir de
lá, já que um monkeypatch neste processo não tem qualquer efeito
noutro processo."""
import pytest

from alguem.nucleo import registador as registador_mod
from alguem.nucleo import identidade as identidade_mod


@pytest.fixture(autouse=True)
def _isolar_logs_e_identidade(tmp_path, monkeypatch):
    monkeypatch.setattr(registador_mod, "PASTA_LOGS_POR_OMISSAO", str(tmp_path / "logs"))
    monkeypatch.setattr(identidade_mod, "CAMINHO_ID_POR_OMISSAO", str(tmp_path / ".estudante_id"))
