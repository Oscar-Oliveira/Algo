# -*- coding: utf-8 -*-
"""Configuração partilhada da suite de testes do Alguem.

O 'autouse=True' abaixo garante que NENHUM teste, mesmo que construa
um Alguem sem passar um Registador explícito, escreve alguma vez para
a pasta real 'alguem/logs/' ou para o ficheiro real '.estudante_id' --
tudo fica isolado numa pasta temporária, através de monkeypatch direto
às constantes dos módulos (sem variáveis de ambiente). Isto só
funciona para testes que correm DENTRO deste processo -- um monkeypatch
neste processo não tem qualquer efeito num subprocesso à parte."""
import pytest

from alguem.nucleo import registador as registador_mod
from alguem.nucleo import identidade as identidade_mod


@pytest.fixture(autouse=True)
def _isolar_logs_e_identidade(tmp_path, monkeypatch):
    monkeypatch.setattr(registador_mod, "PASTA_LOGS_POR_OMISSAO", str(tmp_path / "logs"))
    monkeypatch.setattr(identidade_mod, "CAMINHO_ID_POR_OMISSAO", str(tmp_path / ".estudante_id"))
