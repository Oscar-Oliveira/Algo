# -*- coding: utf-8 -*-
"""Achado 1 (docs/interno/PlanoAuditoria.md): dezenas de testes invocam o
comando 'algo' diretamente via subprocesso (não python -m algo_lang.cli),
que só existe no PATH depois de algo.sh/algo.bat criar a venv -- fora
desse fluxo (ex: `pytest algo_lang/tests/` correndo direto do
repositório), falham todos com o mesmo FileNotFoundError, mascarando
qualquer falha nova real no meio delas. Testes marcados
'requer_algo_no_path' são saltados (não falham) quando o comando não
está disponível, em vez de aparecerem como falha -- continuam a correr
normalmente sempre que 'algo' estiver no PATH (localmente depois de
algo.sh/algo.bat, ou em CI com `pip install -e .`)."""
import shutil

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requer_algo_no_path: invoca o comando 'algo' via subprocesso -- "
        "salta em vez de falhar quando não está no PATH (ver algo.sh/algo.bat)",
    )


def pytest_collection_modifyitems(config, items):
    if shutil.which("algo") is not None:
        return
    salta = pytest.mark.skip(
        reason="comando 'algo' não está no PATH -- corre algo.sh/algo.bat "
        "(ou `pip install -e .`) para o disponibilizar"
    )
    for item in items:
        if "requer_algo_no_path" in item.keywords:
            item.add_marker(salta)
