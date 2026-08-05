# -*- coding: utf-8 -*-
"""Testes do modo 'algo compila --minimo' (transpilação direta, sem
verificação de tipos, sem funções de apoio)."""
import subprocess
import sys
import textwrap
import pytest


def _compilar_minimo(tmp_path, codigo_algo, nome="prog"):
    algo_path = tmp_path / f"{nome}.algo"
    algo_path.write_text(textwrap.dedent(codigo_algo).lstrip("\n"), encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "compila", "--minimo", str(algo_path)],
        capture_output=True, text=True)
    return resultado, tmp_path / nome / f"{nome}_min.py"


def _correr(caminho_py, entrada=""):
    return subprocess.run(
        [sys.executable, str(caminho_py)], input=entrada,
        capture_output=True, text=True, timeout=15)


def test_minimo_gera_ficheiro_com_sufixo_min(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            escrever("ok")
    """)
    assert resultado.returncode == 0
    assert caminho_py.exists()


def test_minimo_nao_tem_funcoes_de_apoio(tmp_path):
    """O ponto central do pedido: nada de _algo_escrever, _algo_ler_*,
    _algo_programa, try/except -- python o mais 'nu' possível."""
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            x:inteiro
            ler(x)
            escrever(x)
    """)
    texto = caminho_py.read_text(encoding="utf-8")
    for proibido in ("_algo_escrever", "_algo_ler", "_algo_programa",
                      "try:", "except", "sys.exit", "setrecursionlimit"):
        assert proibido not in texto, f"'{proibido}' não devia aparecer no modo mínimo"


def test_minimo_executa_corretamente(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            a:inteiro
            b:inteiro
            ler(a)
            ler(b)
            escrever("Soma = ", a + b)
    """)
    assert resultado.returncode == 0
    r = _correr(caminho_py, "5\n3\n")
    assert "Soma = 8" in r.stdout


def test_minimo_booleano_e_python_puro_nao_traduzido(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            x:booleano = verdadeiro
            escrever(x)
    """)
    texto = caminho_py.read_text(encoding="utf-8")
    assert "x = True" in texto
    r = _correr(caminho_py)
    assert r.stdout.strip() == "True"   # não "verdadeiro"


def test_minimo_compila_programa_com_erro_de_tipos(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            x:inteiro = "isto nao e um inteiro"
            escrever(x + 5)
    """)
    assert resultado.returncode == 0
    assert caminho_py.exists()
    # o erro só aparece a correr, como erro nativo do Python
    r = _correr(caminho_py)
    assert r.returncode != 0
    assert "TypeError" in r.stderr


def test_modo_normal_continua_a_recusar_o_mesmo_programa(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    x:inteiro = "isto nao e um inteiro"\n    escrever(x + 5)\n',
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "compila", str(algo_path)], capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "Erro semântico" in resultado.stdout


def test_minimo_afirmar_vira_assert_nativo(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        funcao dobro(n:inteiro):inteiro
            devolver n * 2
        inicio
            afirmar dobro(5) == 10, "dobro(5) devia ser 10"
            escrever("passou")
    """)
    texto = caminho_py.read_text(encoding="utf-8")
    assert 'assert (dobro(5) == 10), "dobro(5) devia ser 10"' in texto
    r = _correr(caminho_py)
    assert "passou" in r.stdout


def test_minimo_afirmar_falso_da_assertionerror(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            afirmar 1 == 2, "nunca e verdade"
    """)
    r = _correr(caminho_py)
    assert r.returncode != 0
    assert "AssertionError" in r.stderr


@pytest.mark.parametrize("chamada_algo,esperado_python,saida_esperada", [
    ('math.raiz(16.0)', "math.sqrt(16.0)", "4.0"),
    ('math.absoluto(-5)', "abs((-5))", "5"),
    ('math.piso(2.7)', "math.floor(2.7)", "2"),
    ('math.teto(2.1)', "math.ceil(2.1)", "3"),
    ('cadeia.comprimento("abc")', 'len("abc")', "3"),
    ('cadeia.maiusculas("ola")', '"ola".upper()', "OLA"),
    ('cadeia.inverter("abc")', '"abc"[::-1]', "cba"),
    ('cadeia.subcadeia("algoritmo", 0, 4)', '"algoritmo"[0:4]', "algo"),
    ('cadeia.caracter("algoritmo", 4)', '"algoritmo"[4]', "r"),
])
def test_minimo_biblioteca_mapeia_para_python_nativo(
        tmp_path, chamada_algo, esperado_python, saida_esperada):
    lib = "Math" if chamada_algo.startswith("math.") else "Cadeia"
    resultado, caminho_py = _compilar_minimo(tmp_path, f"""
        algoritmo "T"
        importar {lib}
        inicio
            escrever({chamada_algo})
    """)
    texto = caminho_py.read_text(encoding="utf-8")
    assert esperado_python in texto
    r = _correr(caminho_py)
    assert r.stdout.strip() == saida_esperada


def test_minimo_ref_continua_a_funcionar(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        procedimento trocar(ref a:inteiro, ref b:inteiro)
            temp:inteiro = a
            a = b
            b = temp
        inicio
            x:inteiro = 3
            y:inteiro = 9
            trocar(x, y)
            escrever("x=", x, " y=", y)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "x=9 y=3"


def test_minimo_estrutura_sem_aliasing_entre_instancias(tmp_path):
    """A mesma classe de bug do #11 encontrado no compilador normal --
    tem de continuar corrigida também no gerador mínimo."""
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Retangulo
            canto:Ponto
        inicio
            a:Retangulo
            c:Retangulo
            a.canto.x = 999
            escrever("a=", a.canto.x, " c=", c.canto.x)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "a=999 c=0"


def test_minimo_estrutura_nao_gera_eq(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            p:Ponto
            escrever(p.x)
    """)
    texto = caminho_py.read_text(encoding="utf-8")
    assert "__eq__" not in texto


def test_minimo_arrays_e_matrizes(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            v:inteiro[5] = {1, 2, 3, 4, 5}
            soma:inteiro = 0
            para i de 0 ate 4 fazer
                soma = soma + v[i]
            escrever("Soma = ", soma)
            m:inteiro[2][2]
            m[0][0] = 1
            m[1][1] = 1
            escrever(m[0][0], " ", m[0][1], " ", m[1][0], " ", m[1][1])
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "Soma = 15\n1 0 0 1"


def test_minimo_recursao_funciona(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        funcao fatorial(n:inteiro):inteiro
            se n <= 1 entao
                devolver 1
            devolver n * fatorial(n - 1)
        inicio
            escrever(fatorial(5))
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "120"


def test_minimo_via_consola(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo"], input=f"compila --minimo {algo_path}\nsair\n",
        capture_output=True, text=True)
    assert resultado.returncode == 0
    assert "Compilado para" in resultado.stdout
    assert (tmp_path / "prog" / "prog_min.py").exists()


def test_minimo_declaracao_global(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        total:inteiro = 0
        constante MAX:inteiro = 100
        funcao f():inteiro
            devolver total + MAX
        inicio
            total = 5
            escrever(f())
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "105"


def test_minimo_estrutura_com_campo_array(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        estrutura Turma
            notas:inteiro[3]
        inicio
            t:Turma
            t.notas[0] = 10
            escrever(t.notas[0])
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "10"


def test_minimo_declaracao_com_literal_de_estrutura(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {x: 3, y: 4}
            escrever(p.x, ",", p.y)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "3,4"


def test_minimo_declaracao_a_partir_de_funcao_com_ref(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        funcao incrementar(ref n:inteiro):inteiro
            n = n + 1
            devolver n
        inicio
            n:inteiro = 5
            m:inteiro = incrementar(n)
            escrever("n=", n, " m=", m)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "n=6 m=6"


def test_minimo_atribuicao_a_partir_de_funcao_com_ref(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        funcao incrementar(ref n:inteiro):inteiro
            n = n + 1
            devolver n
        inicio
            n:inteiro = 5
            m:inteiro
            m = incrementar(n)
            escrever("n=", n, " m=", m)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "n=6 m=6"


def test_minimo_enquanto(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            x:inteiro = 0
            enquanto x < 3 fazer
                x = x + 1
            escrever(x)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "3"


def test_minimo_faz_enquanto(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            y:inteiro = 0
            fazer
                y = y + 1
            enquanto y < 3
            escrever(y)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "3"


def test_minimo_escolher_com_contrario(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            n:inteiro = 5
            escolher n
                caso 5
                    escrever("cinco")
                contrario
                    escrever("outro")
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "cinco"


def test_minimo_afirmar_sem_mensagem(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            afirmar 1 == 1
            escrever("passou")
    """)
    texto = caminho_py.read_text(encoding="utf-8")
    assert "assert (1 == 1)" in texto
    r = _correr(caminho_py)
    assert r.stdout.strip() == "passou"


def test_minimo_chamada_a_biblioteca_em_declaracao_atribuicao_e_solta(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        importar Math
        inicio
            x:decimal = math.raiz(16.0)
            escrever(x)
            y:decimal
            y = math.raiz(4.0)
            escrever(y)
            math.raiz(9.0)
            escrever("ok")
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "4.0\n2.0\nok"


def test_minimo_senao(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            x:inteiro = 5
            se x > 10 entao
                escrever("grande")
            senao
                escrever("pequeno")
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "pequeno"


def test_minimo_ler_campo_de_estrutura(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            p:Ponto
            ler(p.x)
            escrever(p.x)
    """)
    r = _correr(caminho_py, "42\n")
    assert r.stdout.strip() == "42"


def test_minimo_procedimento_com_ref_como_instrucao_solta(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        procedimento incrementarRef(ref n:inteiro)
            n = n + 1
        inicio
            n:inteiro = 5
            incrementarRef(n)
            escrever(n)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "6"


def test_minimo_menos_unario(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            x:inteiro = 5
            escrever(-x)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "-5"


def test_minimo_funcao_com_ref_como_instrucao_solta(tmp_path):
    """Distinto do teste com PROCEDIMENTO: uma FUNÇÃO com ref chamada
    como instrução solta também tem de descartar o valor de retorno
    corretamente (usa '_' para o resultado, só os refs interessam)."""
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        funcao incrementarRef(ref n:inteiro):inteiro
            n = n + 1
            devolver n
        inicio
            n:inteiro = 5
            incrementarRef(n)
            escrever(n)
    """)
    texto = caminho_py.read_text(encoding="utf-8")
    assert "_, n = incrementarRef(n)" in texto
    r = _correr(caminho_py)
    assert r.stdout.strip() == "6"


def test_minimo_nao_logico(tmp_path):
    resultado, caminho_py = _compilar_minimo(tmp_path, """
        algoritmo "T"
        inicio
            escrever(nao falso)
    """)
    r = _correr(caminho_py)
    assert r.stdout.strip() == "True"


def test_incluir_estrutura_sem_colisao(tmp_path):
    (tmp_path / "lib.algo").write_text(
        "estrutura Ponto\n    x:inteiro\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\n'
        'incluir "lib.algo"\n'
        "inicio\n"
        "    p:Ponto\n"
        "    p.x = 5\n"
        "    escrever(p.x)\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert "5" in resultado.stdout


def test_minimo_ficheiro_nao_encontrado():
    resultado = subprocess.run(
        ["algo", "compila", "--minimo", "/tmp/nao_existe_xyz_123.algo"],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "não encontrado" in resultado.stdout


def test_minimo_erro_de_sintaxe(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    x = )\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "compila", "--minimo", str(algo_path)],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "Erro de sintaxe" in resultado.stdout
