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

RAIZ_PROJETO = pathlib.Path(__file__).resolve().parent.parent.parent


def _correr_consola(entrada, timeout=15, tmp_path=None):
    """Corre a consola do ALGO num subprocesso -- a partir de uma CÓPIA
    completa de algo_lang/, numa pasta temporária, para que os testes
    nunca escrevam artefactos (.py/.dot/.json gerados) na árvore real do
    repositório. Sem variáveis de ambiente: o isolamento vem só de
    sys.path apontar para a cópia, não para o algo_lang instalado."""
    import tempfile
    contexto = tempfile.TemporaryDirectory() if tmp_path is None else None
    pasta_base = pathlib.Path(contexto.name) if contexto else tmp_path
    try:
        raiz_copia = pasta_base / "projeto"
        shutil.copytree(
            RAIZ_PROJETO / "algo_lang", raiz_copia / "algo_lang",
            ignore=shutil.ignore_patterns("__pycache__", "tests"))
        script = (
            f"import sys; sys.path.insert(0, {str(raiz_copia)!r}); "
            "from algo_lang.cli import main; main()"
        )
        # PYTHONIOENCODING=utf-8 (para o processo FILHO) + encoding="utf-8"
        # explícito aqui (para o PAI decodificar o que o filho escreveu):
        # sem os dois, um caminho gerado por tempfile que confunda o
        # shlex.split() da consola (backslashes do Windows interpretados
        # como escapes) pode acabar por imprimir uma mensagem de erro com
        # "❌" (UX-06) -- sem o primeiro, UnicodeEncodeError no filho ao
        # escrever; sem o segundo, UnicodeDecodeError na thread leitora
        # do subprocess.run ao tentar decodificar UTF-8 como cp1252 (o
        # 'text=True' sozinho usa a codificação preferida do SO, cp1252
        # neste Windows). Mesma causa de fundo da AL-35, aqui a afetar só
        # este helper de testes (algo.bat já força chcp 65001/PYTHONIOENCODING).
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run(
            [sys.executable, "-c", script], input=entrada, cwd=str(raiz_copia),
            capture_output=True, encoding="utf-8", timeout=timeout, env=env)
    finally:
        if contexto:
            contexto.cleanup()


def test_consola_abre_com_algo_sem_argumentos(tmp_path):
    resultado = _correr_consola("sair\n")
    assert resultado.returncode == 0
    assert "Consola ALGO" in resultado.stdout


def test_consola_mostra_logo_ascii_no_banner(tmp_path):
    """FEAT-03: só ASCII puro -- confirma que não há nenhum caráter
    fora do intervalo ASCII no logo, para nunca aparecer partido numa
    consola Windows sem code page UTF-8."""
    from algo_lang.cli import _LOGO_ASCII
    assert all(ord(c) < 128 for c in _LOGO_ASCII)
    resultado = _correr_consola("sair\n")
    assert resultado.returncode == 0
    assert _LOGO_ASCII.strip("\n") in resultado.stdout


def test_consola_executa_um_ficheiro(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ola")\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "ola" in resultado.stdout


def test_consola_lembra_o_ultimo_ficheiro(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ola")\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nverifica\nsair\n")
    assert resultado.returncode == 0
    assert "Nenhum aviso" in resultado.stdout


def test_consola_sem_ficheiro_nenhum_da_erro_amigavel(tmp_path):
    resultado = _correr_consola("verifica\nsair\n")
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


def test_consola_lembra_ficheiro_mesmo_apos_erro_semantico(tmp_path):
    """Um ficheiro que EXISTE mas falha (erro semântico) tem de ficar
    como 'ultimo_ficheiro' na mesma -- só um ficheiro que não existe (typo
    no nome) é que não deve substituir o último ficheiro que funcionou."""
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    x:inteiro = "nao e um inteiro"\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nexecuta\nsair\n")
    assert resultado.returncode == 0
    assert "ainda não usaste nenhum ficheiro" not in resultado.stdout
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
                 "--funcao", "--formato"):
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


def test_consola_compila_nao_existe(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"compila {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "escreve 'ajuda'" in resultado.stdout
    assert not (tmp_path / "prog" / "prog.py").exists()


def test_consola_atalho_v_para_verifica(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"e {algo_path}\nv\nsair\n")
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


def test_consola_atalho_s_para_sair():
    resultado = _correr_consola("s\n")
    assert resultado.returncode == 0
    assert "Até à próxima!" in resultado.stdout


def test_consola_interrogacao_nao_e_atalho_de_ajuda():
    """'?' não está ligado a nenhum comando (o Alguem deixou de fazer
    parte da consola do ALGO -- só continua acessível via online/) --
    confirma que continua a não ser sinónimo de 'ajuda', só um comando
    desconhecido como outro qualquer."""
    resultado = _correr_consola("?\nsair\n")
    assert resultado.returncode == 0
    assert "atalho: e" not in resultado.stdout
    assert "escreve 'ajuda'" in resultado.stdout


# ---------- Auditoria (4ª ronda), Etapa 8 -- aplicação de consola.
# Lacuna prevista pelo plano: nome de ficheiro com Unicode/acentuação
# nunca tinha teste dedicado (confirmado por grep antes de escrever,
# nenhum ficheiro do repositório usava um nome de ficheiro acentuado
# em nenhum teste). Confirmado por execução direta antes de escrever o
# teste: já funciona corretamente (nenhum bug encontrado). ----------

def test_consola_executa_ficheiro_com_nome_acentuado(tmp_path):
    algo_path = tmp_path / "cálculo_média.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = _correr_consola(f"executa {algo_path}\nsair\n")
    assert resultado.returncode == 0
    assert "ok" in resultado.stdout
    assert (tmp_path / "cálculo_média" / "cálculo_média.py").exists()
