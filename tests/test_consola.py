# -*- coding: utf-8 -*-
"""Testes da consola interativa ('algo' sem argumentos)."""
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap
import time
import pytest

RAIZ_PROJETO = pathlib.Path(__file__).resolve().parent.parent


def _correr_consola(entrada, timeout=15, tmp_path=None):
    """Corre a consola do ALGO num subprocesso -- a partir de uma CÓPIA
    completa do projeto, numa pasta temporária, para que o '?' (que
    chama o Alguem) escreva os logs/identidade só nessa cópia, nunca
    na pasta real do pacote alguem/. Sem variáveis de ambiente: o
    isolamento vem só de sys.path apontar para a cópia, não para o
    algo_lang/alguem instalados."""
    import tempfile
    contexto = tempfile.TemporaryDirectory() if tmp_path is None else None
    pasta_base = pathlib.Path(contexto.name) if contexto else tmp_path
    try:
        raiz_copia = pasta_base / "projeto"
        shutil.copytree(
            RAIZ_PROJETO / "algo_lang", raiz_copia / "algo_lang",
            ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(
            RAIZ_PROJETO / "alguem", raiz_copia / "alguem",
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.jsonl"))
        script = (
            f"import sys; sys.path.insert(0, {str(raiz_copia)!r}); "
            "from algo_lang.cli import main; main()"
        )
        return subprocess.run(
            [sys.executable, "-c", script], input=entrada, cwd=str(raiz_copia),
            capture_output=True, text=True, timeout=timeout)
    finally:
        if contexto:
            contexto.cleanup()


def test_consola_abre_com_algo_sem_argumentos(tmp_path):
    resultado = _correr_consola("sair\n")
    assert resultado.returncode == 0
    assert "Consola ALGO" in resultado.stdout


def test_consola_executa_um_ficheiro(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ola")\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "ola" in resultado.stdout


def test_consola_lembra_o_ultimo_ficheiro(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ola")\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nlint\nsair\n")
    assert resultado.returncode == 0
    assert "Nenhum aviso" in resultado.stdout


def test_consola_sem_ficheiro_nenhum_da_erro_amigavel(tmp_path):
    resultado = _correr_consola("lint\nsair\n")
    assert resultado.returncode == 0
    assert "ainda não usaste nenhum ficheiro" in resultado.stdout


def test_consola_erro_de_compilacao_nao_fecha_a_consola(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    x:inteiro = "nao e um inteiro"\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nexecuta {algo_path}\nsair\n")
    assert resultado.returncode == 0
    # o erro apareceu duas vezes (uma por cada 'executa') -- prova que a
    # consola voltou ao prompt em vez de fechar logo na primeira
    assert resultado.stdout.count("Erro semântico") == 2


def test_consola_comando_desconhecido_nao_fecha_a_consola(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"comando_invalido\nexecuta {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "ok" in resultado.stdout


def test_consola_linha_vazia_e_ignorada(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"\n\nexecuta {algo_path}\n\nsair\n")
    assert resultado.returncode == 0
    assert "ok" in resultado.stdout


def test_consola_ajuda_mostra_o_ficheiro_atual(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\najuda\nsair\n")
    assert resultado.returncode == 0
    assert str(algo_path) in resultado.stdout


def test_consola_ajuda_detalhada_lista_as_flags_de_cada_comando():
    resultado = _correr_consola("ajuda\nsair\n")
    assert resultado.returncode == 0
    for flag in ("--mostrar-python", "--debug", "--json", "--entradas",
                 "--minimo", "--funcao", "--formato"):
        assert flag in resultado.stdout, f"'{flag}' devia aparecer na ajuda detalhada"


def test_consola_comando_desconhecido_sugere_ajuda():
    resultado = _correr_consola("foobar\nsair\n")
    assert resultado.returncode == 0
    assert "ajuda" in resultado.stdout.lower()


def test_consola_flag_com_valor_nao_e_confundida_com_ficheiro(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"fluxograma {algo_path} --formato svg\nsair\n")
    assert resultado.returncode == 0
    assert (tmp_path / "prog" / "prog.svg").exists()


def test_consola_eof_imediato_nao_da_erro():
    resultado = _correr_consola("")
    assert resultado.returncode == 0
    assert "Traceback" not in resultado.stdout


def test_consola_ler_do_programa_nao_e_roubado_pelo_prompt_seguinte(tmp_path):
    """Bug real encontrado: como o stdin não é um terminal (é canalizado),
    um input() normal lê à frente e 'rouba' bytes que deviam chegar ao
    ler() do subprocesso lançado por 'executa'. A consola tem de ler o
    seu próprio prompt sem qualquer leitura antecipada."""
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    nome:cadeia\n    ler(nome)\n    escrever("Ola, ", nome)\n',
        encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nRita\nsair\n")
    assert resultado.returncode == 0
    assert "Ola, Rita" in resultado.stdout
    # confirma que 'Rita' não foi interpretado como o comando seguinte
    assert "invalid choice" not in resultado.stdout


def test_consola_ordem_do_output_nao_fica_baralhada_pelo_buffering(tmp_path):
    """Bug real encontrado: sem sys.stdout.flush() antes de lançar o
    subprocesso que corre o programa, o texto do próprio programa podia
    aparecer no stdout ANTES das mensagens da consola que logicamente
    vêm primeiro (o stdout da consola ficava em buffer, por não ser um
    terminal, e o subprocesso escrevia diretamente antes desse buffer
    ser esvaziado)."""
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    escrever("SAIDA_DO_PROGRAMA")\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nsair\n")
    pos_compilado = resultado.stdout.find("Compilado para")
    pos_saida = resultado.stdout.find("SAIDA_DO_PROGRAMA")
    assert pos_compilado != -1 and pos_saida != -1
    assert pos_compilado < pos_saida, (
        "'Compilado para' devia aparecer antes da saída do programa, "
        "mas a ordem ficou trocada")


def test_executa_mostrar_python(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--mostrar-python"],
        capture_output=True, text=True)
    assert resultado.returncode == 0
    assert "Código Python gerado" in resultado.stdout
    assert "def _algo_programa" in resultado.stdout


def test_executa_json_com_entradas_nao_encontrado(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--json", "--entradas", "/tmp/nao_existe_ent.txt"],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "não encontrado" in resultado.stdout


def test_executa_json_com_erro_em_tempo_de_execucao(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    v:inteiro[3]\n    escrever(v[10])\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--json"],
        capture_output=True, text=True)
    assert "Erro em tempo de execução" in resultado.stdout
    assert (tmp_path / "prog" / "prog_trace.json").exists()


def test_executa_json_limite_de_passos_excedido(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    enquanto verdadeiro fazer\n        escrever("x")\n',
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--json"],
        capture_output=True, text=True, timeout=30)
    assert "Limite de passos" in resultado.stdout


def test_fluxograma_funcao_inexistente(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "fluxograma", str(algo_path), "--funcao", "naoExiste"],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "não existe nenhuma função" in resultado.stdout


def test_fluxograma_sem_graphviz_disponivel(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    caminho_algo_bin = os.path.dirname(shutil.which("algo"))
    ambiente = dict(os.environ)
    ambiente["PATH"] = caminho_algo_bin
    resultado = subprocess.run(
        ["algo", "fluxograma", str(algo_path)],
        capture_output=True, text=True, env=ambiente)
    assert resultado.returncode == 0
    assert "Graphviz" in resultado.stdout
    assert (tmp_path / "prog" / "prog.dot").exists()
    assert not (tmp_path / "prog" / "prog.png").exists()


def test_consola_linha_sem_newline_final(tmp_path):
    """EOF a meio de uma linha (sem \\n final) ainda tem de ser lido
    corretamente -- não pode perder o último comando."""
    resultado = _correr_consola("sair")   # sem \n no fim
    assert resultado.returncode == 0
    assert "Até à próxima" in resultado.stdout


def test_consola_aspas_por_fechar():
    resultado = _correr_consola('executa "ficheiro sem fechar\nsair\n')
    assert resultado.returncode == 0
    assert "closing quotation" in resultado.stdout


def test_consola_ctrl_c_durante_um_comando_nao_fecha_a_consola(tmp_path):
    """Bug real a confirmar: um SIGINT (Ctrl+C) a meio de um 'executa'
    (ex: um ciclo infinito) tem de voltar ao prompt, não deve fechar a
    consola nem deixar um processo preso."""
    import signal
    algo_path = tmp_path / "infinito.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    enquanto verdadeiro fazer\n        escrever("x")\n',
        encoding="utf-8")
    proc = subprocess.Popen(
        ["algo"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, preexec_fn=os.setsid)
    try:
        proc.stdin.write(f"executa {algo_path}\n")
        proc.stdin.flush()
        time.sleep(1.5)
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        time.sleep(0.5)
        proc.stdin.write("sair\n")
        proc.stdin.flush()
        saida, _ = proc.communicate(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert "interrompido" in saida
    assert "Até à próxima" in saida


def test_cli_corre_via_python_dash_m():
    """python -m algo_lang.cli é uma forma alternativa de invocar o
    comando, além do 'algo' instalado -- exercita o
    'if __name__ == \"__main__\"' no fundo do módulo."""
    algo_path = "/tmp/simples_dash_m.algo"
    with open(algo_path, "w", encoding="utf-8") as f:
        f.write('algoritmo "T"\ninicio\n    escrever("ok")\n')
    resultado = subprocess.run(
        [sys.executable, "-m", "algo_lang.cli", "executa", algo_path],
        capture_output=True, text=True)
    assert resultado.returncode == 0
    assert "ok" in resultado.stdout


def test_consola_atalho_e_para_executa(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"e {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "ok" in resultado.stdout


def test_consola_atalho_c_para_compila(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"c {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "Compilado para" in resultado.stdout
    assert (tmp_path / "prog" / "prog.py").exists()


def test_consola_atalho_l_para_lint(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"e {algo_path}\nl\nsair\n")
    assert resultado.returncode == 0
    assert "Nenhum aviso" in resultado.stdout


def test_consola_atalho_f_para_fluxograma(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"f {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "Fluxograma gerado" in resultado.stdout


def test_consola_atalho_a_para_ajuda():
    resultado = _correr_consola("a\nsair\n")
    assert resultado.returncode == 0
    assert "atalho: e" in resultado.stdout


def test_consola_interrogacao_nao_e_atalho_de_ajuda():
    """Pedido explícito: '?' ficou reservado para outra coisa (chamar o
    Alguem, ver test_consola_alguem.py) -- continua a não ser sinónimo
    de 'ajuda'."""
    resultado = _correr_consola("?\nsair\nsair\n")
    assert resultado.returncode == 0
    assert "atalho: e" not in resultado.stdout
    assert "A chamar o Alguem" in resultado.stdout
