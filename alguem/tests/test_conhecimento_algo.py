# -*- coding: utf-8 -*-
"""Testes de alguem.nucleo.conhecimento_algo -- a fonte de verdade da
sintaxe que o Alguem usa nas suas pistas. O caminho normal (importar
de algo_lang) e o caminho de reserva (algo_lang inacessível) são
testados como processos separados, porque o resultado da importação
fica decidido na primeira vez que o módulo é importado no processo --
não dá para alternar dentro do mesmo processo de testes."""
import os
import subprocess
import sys


def test_referencia_de_sintaxe_vem_do_compilador_real():
    resultado = subprocess.run(
        [sys.executable, "-c",
         "from alguem.nucleo.conhecimento_algo import _FONTE, _PALAVRAS_CHAVE; "
         "print(_FONTE); print('devolver' in _PALAVRAS_CHAVE); "
         "print('retorna' in _PALAVRAS_CHAVE); print('faz' in _PALAVRAS_CHAVE)"],
        capture_output=True, text=True, cwd="/home/claude", timeout=15)
    linhas = resultado.stdout.strip().split("\n")
    assert "algo_lang" in linhas[0]
    assert linhas[1] == "True"    # 'devolver' está lá
    assert linhas[2] == "False"   # 'retorna' (sintaxe antiga) não está
    assert linhas[3] == "False"   # 'faz' isolado (sintaxe antiga) não está


def test_referencia_de_sintaxe_tem_caminho_de_reserva_se_algo_lang_faltar(tmp_path):
    """Copia só a pasta alguem/ para um sítio isolado, sem algo_lang/ ao
    lado -- é a única forma de testar genuinamente o caminho de
    reserva (só ignorar os pacotes instalados com -S não chega, porque
    o cwd real ainda tem a pasta algo_lang/ fisicamente presente)."""
    import shutil
    raiz_alguem = os.path.join(os.path.dirname(__file__), "..")
    destino = tmp_path / "alguem"
    shutil.copytree(raiz_alguem, destino, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", "tests"))
    resultado = subprocess.run(
        [sys.executable, "-S", "-W", "always", "-c",
         "import sys; "
         "sys.path.append('/usr/lib/python3.12'); "
         "sys.path.append('/usr/lib/python3.12/lib-dynload'); "
         "from alguem.nucleo.conhecimento_algo import _FONTE; print(_FONTE)"],
        capture_output=True, text=True, cwd=str(tmp_path), timeout=15)
    assert "reserva" in resultado.stdout, resultado.stdout + resultado.stderr
    assert "UserWarning" in resultado.stderr or "Warning" in resultado.stderr


# ---------- AG-30: a captura na importação cobre mais do que ImportError ----------

def test_conhecimento_algo_cai_para_reserva_se_a_importacao_falhar_por_outro_motivo():
    """Alargado de 'except ImportError' para 'except Exception' --
    algo_lang PRESENTE mas com um erro inesperado a meio da importação
    (ex: um tipo primitivo corrompido, não apenas o pacote em falta)
    também tem de cair para a lista de reserva, não propagar e impedir
    o Alguem de arrancar. Corrompe NUMERICOS de propósito para que a
    linha 'NUMERICOS | TEXTUAIS' levante TypeError, não ImportError --
    testa exatamente o alargamento, não o caminho já coberto antes."""
    import importlib
    from algo_lang.compilador import semantics as semantics_real
    import alguem.nucleo.conhecimento_algo as modulo

    numericos_originais = semantics_real.NUMERICOS
    try:
        semantics_real.NUMERICOS = ["isto-nao-e-um-set"]  # '|' com um set levanta TypeError
        importlib.reload(modulo)
        assert "reserva" in modulo._FONTE
    finally:
        semantics_real.NUMERICOS = numericos_originais
        importlib.reload(modulo)  # repõe o estado normal para os testes seguintes


def test_referencia_inclui_regras_chave_da_sintaxe():
    from alguem.nucleo.conhecimento_algo import REFERENCIA_SINTAXE
    assert "algoritmo" in REFERENCIA_SINTAXE
    assert "infinitivo" in REFERENCIA_SINTAXE.lower()
    assert "0" in REFERENCIA_SINTAXE  # arrays começam em 0
    assert "devolver" in REFERENCIA_SINTAXE


def test_system_prompt_inclui_a_referencia_de_sintaxe():
    from alguem.nucleo.system_prompt import construir_system_prompt
    from alguem.nucleo.politica_pedagogica import PoliticaPedagogica
    from alguem.nucleo.conhecimento_algo import REFERENCIA_SINTAXE
    prompt = construir_system_prompt(PoliticaPedagogica())
    assert REFERENCIA_SINTAXE in prompt
