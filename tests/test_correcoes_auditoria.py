# -*- coding: utf-8 -*-
"""Testes de regressão para os problemas encontrados na auditoria ao
compilador: cada um destes já foi um bug real, confirmado antes de ser
corrigido."""
import subprocess
import sys
import textwrap
import pytest

from apoio import compilar, executar
from algo_lang.compilador.parser import parse
from algo_lang.compilador.semantics import verificar, ErroSemantico
from algo_lang.compilador.lexer import ErroLexico


# ---------- #1 estruturas comparadas por valor ----------

def test_estruturas_iguais_em_valor_comparam_como_iguais():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            a:Ponto = {x: 1}
            b:Ponto = {x: 1}
            se a == b entao
                escrever("iguais")
            senao
                escrever("diferentes")
    """)
    assert saida.strip() == "iguais"


def test_estruturas_diferentes_em_valor_comparam_como_diferentes():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            a:Ponto = {x: 1}
            b:Ponto = {x: 2}
            se a == b entao
                escrever("iguais")
            senao
                escrever("diferentes")
    """)
    assert saida.strip() == "diferentes"


def test_estruturas_aninhadas_comparam_recursivamente():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Retangulo
            canto:Ponto
        inicio
            a:Retangulo
            a.canto.x = 1
            b:Retangulo
            b.canto.x = 1
            c:Retangulo
            c.canto.x = 2
            se a == b entao
                escrever("a==b")
            se a == c entao
                escrever("a==c (nao devia acontecer)")
            senao
                escrever("a<>c")
    """)
    assert saida.strip() == "a==b\na<>c"


# ---------- #2 caracter/cadeia: direção da compatibilidade ----------

def test_cadeia_longa_nao_pode_ser_atribuida_a_caracter():
    with pytest.raises(ErroSemantico, match="caracter"):
        compilar("""
            algoritmo "T"
            inicio
                c:caracter = "isto tem mais de 1 simbolo"
        """)


def test_caracter_pode_ser_atribuido_a_cadeia():
    saida = executar("""
        algoritmo "T"
        inicio
            c:caracter = 'a'
            s:cadeia = c
            escrever(s)
    """)
    assert saida.strip() == "a"


def test_ler_para_caracter_exige_exatamente_1_simbolo():
    saida = executar("""
        algoritmo "T"
        inicio
            c:caracter
            ler(c)
            escrever("recebi: ", c)
    """, entrada="abc\nxy\nz\n")
    assert "recebi: z" in saida


def test_cadeia_e_caracter_podem_ser_comparados():
    saida = executar("""
        algoritmo "T"
        inicio
            c:caracter = 'a'
            s:cadeia = "a"
            se c == s entao
                escrever("iguais")
            senao
                escrever("diferentes")
    """)
    assert saida.strip() == "iguais"


# ---------- #3 passo 0 e ValueError genérico ----------

def test_passo_zero_literal_da_erro_de_compilacao():
    with pytest.raises(ErroSemantico, match="passo"):
        compilar("""
            algoritmo "T"
            inicio
                i:inteiro = 0
                para i de 1 ate 10 passo 0 fazer
                    escrever(i)
        """)


def test_raiz_de_negativo_da_erro_amigavel_nao_traceback(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\nimportar Math\ninicio\n    escrever(math.raiz(-4.0))\n',
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, text=True)
    assert "Traceback" not in resultado.stdout
    assert "Erro em tempo de execução" in resultado.stdout


def test_aleatorio_com_limites_invertidos_da_erro_amigavel(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\nimportar Math\ninicio\n    escrever(math.aleatorio(10, 1))\n',
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, text=True)
    assert "Traceback" not in resultado.stdout
    assert "Erro em tempo de execução" in resultado.stdout


# ---------- #4 limite de recursão ----------

def test_recursao_legitima_profunda_nao_falha():
    saida = executar("""
        algoritmo "T"
        funcao contar(n:inteiro):inteiro
            se n <= 0 entao
                devolver 0
            senao
                devolver 1 + contar(n - 1)
        inicio
            escrever(contar(5000))
    """)
    assert saida.strip() == "5000"


def test_recursao_infinita_da_mensagem_amigavel_via_cli(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\nfuncao semFim(n:inteiro):inteiro\n    devolver semFim(n + 1)\n'
        'inicio\n    escrever(semFim(1))\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, text=True, timeout=20)
    assert "recursão infinita" in resultado.stdout
    assert "Traceback" not in resultado.stdout


# ---------- #5 comentário de bloco não fechado ----------

def test_comentario_de_bloco_nao_fechado_da_erro():
    with pytest.raises(ErroLexico, match="nunca foi fechado"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                escrever(x)
            /* comentario nunca fechado
                y:inteiro = 10
        """)


def test_comentario_de_bloco_fechado_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        inicio
            /* comentario
               normal */
            x:inteiro = 5
            escrever(x)
    """)
    assert saida.strip() == "5"


# ---------- #6 linha correta em erros de senao-se / escolher-caso ----------

def test_erro_em_senao_se_reporta_a_linha_certa():
    codigo = """\
algoritmo "T"
inicio
    x:inteiro = 5
    se x > 10 entao
        escrever("a")
    senao se x + 1 entao
        escrever("b")
"""
    programa = parse(codigo)
    with pytest.raises(ErroSemantico) as exc:
        verificar(programa)
    assert exc.value.linha == 6


def test_erro_em_caso_reporta_a_linha_certa():
    codigo = """\
algoritmo "T"
inicio
    n:inteiro = 5
    escolher n
        caso 1
            escrever("um")
        caso "dois"
            escrever("dois")
"""
    programa = parse(codigo)
    with pytest.raises(ErroSemantico) as exc:
        verificar(programa)
    assert exc.value.linha == 7


# ---------- #7/#8 mensagens sem ':' residual ----------

def test_erro_de_programa_sem_inicio_nao_menciona_dois_pontos():
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico) as exc:
        parse('algoritmo "T"\nfuncao f():inteiro\n    devolver 1\n')
    assert "inicio:" not in str(exc.value)


def test_erro_de_tipo_desconhecido_nao_menciona_dois_pontos():
    with pytest.raises(ErroSemantico) as exc:
        compilar("""
            algoritmo "T"
            inicio
                x:TipoQueNaoExiste = 5
        """)
    assert "TipoQueNaoExiste:" not in str(exc.value)


# ---------- #9 tamanho de array negativo ----------

# ---------- #11 (encontrado ao testar o #1): campos de tipo estrutura
# não podiam partilhar objeto por omissão entre instâncias ----------

def test_campo_de_tipo_estrutura_nao_e_partilhado_entre_instancias():
    """Bug encontrado ao escrever os testes do #1: o valor por omissão de
    um campo cujo tipo é outra estrutura era um 'mutable default
    argument' clássico do Python -- todas as instâncias sem inicializador
    explícito ficavam a apontar para o MESMO objeto interior."""
    saida = executar("""
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
    assert saida.strip() == "a=999 c=0"


def test_array_com_tamanho_negativo_literal_da_erro():
    with pytest.raises(ErroSemantico, match="negativo"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[-1]
        """)


# ---------- lacunas de cobertura encontradas na auditoria reforçada:
# erros do lexer nunca antes disparados por nenhum teste ----------

# ---------- lacunas de cobertura encontradas na auditoria reforçada:
# erros do lexer nunca antes disparados por nenhum teste ----------

def test_lexer_mistura_tabs_e_espacos_na_mesma_linha():
    with pytest.raises(ErroLexico, match="mistura tabs e espaços"):
        compilar("algoritmo \"T\"\ninicio\n\t x:inteiro = 5\n")


def test_lexer_espacos_nao_multiplo_de_4():
    with pytest.raises(ErroLexico, match="múltiplo de 4"):
        compilar('algoritmo "T"\ninicio\n  x:inteiro = 5\n')


def test_lexer_indentacao_inconsistente():
    with pytest.raises(ErroLexico, match="indentação inconsistente"):
        compilar("""algoritmo "T"
inicio
            x:inteiro = 1
        y:inteiro = 2
""")


def test_lexer_string_nao_fechada():
    with pytest.raises(ErroLexico, match="não fechada"):
        compilar("""
            algoritmo "T"
            inicio
                escrever("nunca fecha)
        """)


def test_lexer_caracter_nao_fechado():
    with pytest.raises(ErroLexico, match="não fechado"):
        compilar("""
            algoritmo "T"
            inicio
                x:caracter = 'a
        """)


def test_lexer_caracter_com_mais_de_1_simbolo():
    with pytest.raises(ErroLexico, match="1 símbolo"):
        compilar("""
            algoritmo "T"
            inicio
                x:caracter = 'ab'
        """)


def test_lexer_caractere_inesperado():
    with pytest.raises(ErroLexico, match="inesperado"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5 @ 2
        """)


# ---------- lacunas de cobertura: erros do parser nunca testados ----------

def test_parser_instrucao_inesperada_ao_nivel_do_topo():
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico, match="esperava-se uma declaração"):
        parse('algoritmo "T"\nescrever("ola")\ninicio\n    x:inteiro = 1\n')


def test_parser_tipo_tem_de_ser_identificador():
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico, match="esperava-se um tipo"):
        parse('algoritmo "T"\ninicio\n    x:5 = 1\n')


def test_parser_nao_pode_inicializar_varias_variaveis_na_mesma_linha():
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico, match="não é possível inicializar várias"):
        parse('algoritmo "T"\ninicio\n    a, b:inteiro = 5\n')


def test_parser_instrucao_inesperada_dentro_de_bloco():
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico, match="instrução inesperada"):
        parse('algoritmo "T"\ninicio\n    )\n')


def test_parser_expressao_inesperada():
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico, match="expressão inesperada"):
        parse('algoritmo "T"\ninicio\n    x:inteiro = )\n')


def test_parser_biblioteca_incluida_so_aceita_declaracoes_e_definicoes():
    from algo_lang.compilador.parser import parse_biblioteca, ErroSintatico
    with pytest.raises(ErroSintatico, match="ficheiro incluído"):
        parse_biblioteca("inicio\n    escrever(1)\n")


# ---------- lacunas de cobertura: erros do semantics.py nunca testados ----------

def test_sem_biblioteca_inexistente():
    with pytest.raises(ErroSemantico, match="não existe"):
        compilar('algoritmo "T"\nimportar NaoExiste\ninicio\n    escrever(1)\n')


def test_sem_funcao_duplicada():
    with pytest.raises(ErroSemantico, match="já foi definido"):
        compilar("""
            algoritmo "T"
            funcao f():inteiro
                devolver 1
            funcao f():inteiro
                devolver 2
            inicio
                escrever(f())
        """)


def test_sem_campo_de_estrutura_com_valor_inicial():
    with pytest.raises(ErroSemantico, match="não podem ter valor inicial"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro = 5
            inicio
                escrever(1)
        """)


def test_sem_campo_de_estrutura_tipo_desconhecido():
    with pytest.raises(ErroSemantico, match="tipo desconhecido"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:TipoQueNaoExiste
            inicio
                escrever(1)
        """)


def test_sem_parametro_duplicado():
    with pytest.raises(ErroSemantico, match="duplicado"):
        compilar("""
            algoritmo "T"
            funcao f(x:inteiro, x:inteiro):inteiro
                devolver x
            inicio
                escrever(f(1, 2))
        """)


def test_sem_funcao_declara_tipo_mas_nunca_devolve():
    with pytest.raises(ErroSemantico, match="nunca"):
        compilar("""
            algoritmo "T"
            funcao f():inteiro
                escrever("nunca devolve")
            inicio
                escrever(f())
        """)


def test_sem_campo_repetido_no_literal_de_estrutura():
    with pytest.raises(ErroSemantico, match="repetido"):
        compilar("""
            algoritmo "T"
            estrutura P
                x:inteiro
            inicio
                p:P = {x: 1, x: 2}
        """)


def test_sem_campo_array_nao_pode_ser_inicializado_em_literal_de_estrutura():
    with pytest.raises(ErroSemantico, match="é um array"):
        compilar("""
            algoritmo "T"
            estrutura P
                v:inteiro[3]
            inicio
                p:P = {v: 1}
        """)


def test_sem_atribuir_de_procedimento_com_ref_da_erro():
    with pytest.raises(ErroSemantico, match="não devolve valor"):
        compilar("""
            algoritmo "T"
            procedimento p(ref a:inteiro)
                a = 5
            inicio
                x:inteiro = 1
                x = p(x)
        """)


def test_sem_atribuir_tipo_incompativel_vindo_de_chamada_com_ref():
    with pytest.raises(ErroSemantico, match="não é possível atribuir"):
        compilar("""
            algoritmo "T"
            funcao f(ref a:inteiro):inteiro
                a = 5
                devolver a
            inicio
                x:inteiro = 1
                s:cadeia = "inicial"
                s = f(x)
        """)


def test_sem_variavel_de_controlo_do_para_tem_de_ser_inteira():
    with pytest.raises(ErroSemantico, match="tem de ser"):
        compilar("""
            algoritmo "T"
            inicio
                s:cadeia = "a"
                para s de 1 ate 3 fazer
                    escrever(s)
        """)


def test_sem_variavel_de_controlo_do_para_nao_pode_ser_constante():
    with pytest.raises(ErroSemantico, match="constante"):
        compilar("""
            algoritmo "T"
            constante N:inteiro = 5
            inicio
                para N de 1 ate 10 fazer
                    escrever(N)
        """)


def test_sem_limite_do_para_tem_de_ser_inteiro():
    with pytest.raises(ErroSemantico, match="tem de ser inteiro"):
        compilar("""
            algoritmo "T"
            inicio
                i:inteiro = 0
                para i de "a" ate 10 fazer
                    escrever(i)
        """)


def test_sem_passo_do_para_tem_de_ser_inteiro():
    with pytest.raises(ErroSemantico, match="passo.*tem de ser inteiro"):
        compilar("""
            algoritmo "T"
            inicio
                i:inteiro = 0
                para i de 1 ate 10 passo "x" fazer
                    escrever(i)
        """)


def test_sem_faz_enquanto_condicao_nao_booleana():
    with pytest.raises(ErroSemantico, match="fazer\\.\\.\\.enquanto.*booleana"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 1
                fazer
                    x = x + 1
                enquanto x
        """)


def test_sem_devolver_fora_de_funcao():
    with pytest.raises(ErroSemantico, match="'devolver' só pode ser usado"):
        compilar("""
            algoritmo "T"
            procedimento p()
                devolver 5
            inicio
                p()
        """)


def test_sem_devolver_tipo_incompativel():
    with pytest.raises(ErroSemantico, match="mas está a devolver"):
        compilar("""
            algoritmo "T"
            funcao f():inteiro
                devolver "texto"
            inicio
                escrever(f())
        """)


def test_sem_indexar_variavel_escalar():
    with pytest.raises(ErroSemantico, match="não é um array"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                escrever(x[0])
        """)


def test_sem_indice_nao_inteiro():
    with pytest.raises(ErroSemantico, match="índice.*tem de ser inteiro"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[3]
                escrever(v["a"])
        """)


def test_sem_campo_sem_indexar_array_primeiro():
    with pytest.raises(ErroSemantico, match="falta indexá-lo"):
        compilar("""
            algoritmo "T"
            estrutura P
                x:inteiro
            inicio
                v:P[3]
                escrever(v.x)
        """)


def test_sem_campo_em_algo_que_nao_e_estrutura():
    with pytest.raises(ErroSemantico, match="não é uma estrutura"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                escrever(x.campo)
        """)


def test_sem_array_sem_indexar_em_expressao():
    with pytest.raises(ErroSemantico, match="falta indexá-lo"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[3]
                escrever(v)
        """)


def test_sem_nao_aplicado_a_nao_booleano():
    with pytest.raises(ErroSemantico, match="'nao' só se aplica"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                escrever(nao x)
        """)


def test_sem_menos_unario_em_nao_numero():
    with pytest.raises(ErroSemantico, match="unário só se aplica"):
        compilar("""
            algoritmo "T"
            inicio
                s:cadeia = "a"
                escrever(-s)
        """)


def test_sem_chamada_com_ref_dentro_de_expressao():
    with pytest.raises(ErroSemantico, match="não pode ser usada dentro de uma expressão"):
        compilar("""
            algoritmo "T"
            funcao f(ref a:inteiro):inteiro
                devolver a
            inicio
                y:inteiro = 1
                x:inteiro = 1 + f(y)
        """)


def test_sem_procedimento_usado_como_valor():
    with pytest.raises(ErroSemantico, match="não devolve valor"):
        compilar("""
            algoritmo "T"
            procedimento p()
                escrever("oi")
            inicio
                x:inteiro = p()
        """)


def test_sem_mais_com_tipos_incompativeis():
    with pytest.raises(ErroSemantico, match="'\\+' só pode ser usado"):
        compilar("""
            algoritmo "T"
            inicio
                x:booleano = verdadeiro
                escrever(1 + x)
        """)


def test_sem_menos_com_tipos_nao_numericos():
    with pytest.raises(ErroSemantico, match="'-' só pode ser usado entre números"):
        compilar("""
            algoritmo "T"
            inicio
                s:cadeia = "a"
                escrever(s - s)
        """)


def test_sem_divisao_com_tipos_nao_numericos():
    with pytest.raises(ErroSemantico, match="'/' só pode ser usado entre números"):
        compilar("""
            algoritmo "T"
            inicio
                s:cadeia = "a"
                escrever(s / s)
        """)


def test_sem_div_exige_inteiros():
    with pytest.raises(ErroSemantico, match="exige dois valores inteiros"):
        compilar('algoritmo "T"\ninicio\n    escrever(5.0 div 2)\n')


# ---------- AUDIT_PLAN Fase 2: AL-04 -- mesma variável passada 2x por referência ----------

def test_mesma_variavel_simples_passada_duas_vezes_por_referencia_da_erro():
    with pytest.raises(ErroSemantico, match="mais do que uma vez"):
        compilar("""
            algoritmo "T"
            procedimento trocar(ref a:inteiro, ref b:inteiro)
                temp:inteiro = a
                a = b
                b = temp
            inicio
                x:inteiro = 1
                trocar(x, x)
        """)


def test_variaveis_diferentes_por_referencia_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        procedimento trocar(ref a:inteiro, ref b:inteiro)
            temp:inteiro = a
            a = b
            b = temp
        inicio
            x:inteiro = 1
            y:inteiro = 2
            trocar(x, y)
            escrever(x, " ", y)
    """)
    assert saida.strip() == "2 1"


def test_elementos_diferentes_do_mesmo_array_por_referencia_nao_da_falso_positivo():
    """v[0] e v[1] partilham o nome base 'v' mas são posições diferentes
    -- não deve ser assinalado como a mesma variável repetida."""
    saida = executar("""
        algoritmo "T"
        procedimento trocar(ref a:inteiro, ref b:inteiro)
            temp:inteiro = a
            a = b
            b = temp
        inicio
            v:inteiro[2] = {1, 2}
            trocar(v[0], v[1])
            escrever(v[0], " ", v[1])
    """)
    assert saida.strip() == "2 1"


# ---------- AUDIT_PLAN Fase 2: AL-05 -- div/mod truncados, não floor ----------

def test_div_mod_com_operandos_positivos_inalterado():
    saida = executar('algoritmo "T"\ninicio\n    escrever(7 div 2, " ", 7 mod 2)\n')
    assert saida.strip() == "3 1"


def test_div_mod_com_dividendo_negativo_e_truncado_nao_floor():
    """-7 div 2: floor (Python //) dava -4; truncado (em direção a
    zero, o que a maioria dos alunos espera de pseudocódigo) é -3."""
    saida = executar('algoritmo "T"\ninicio\n    escrever(-7 div 2, " ", -7 mod 2)\n')
    assert saida.strip() == "-3 -1"


def test_div_mod_com_divisor_negativo_e_truncado_nao_floor():
    saida = executar('algoritmo "T"\ninicio\n    escrever(7 div -2, " ", 7 mod -2)\n')
    assert saida.strip() == "-3 1"


def test_div_mod_com_ambos_negativos():
    saida = executar('algoritmo "T"\ninicio\n    escrever(-7 div -2, " ", -7 mod -2)\n')
    assert saida.strip() == "3 -1"


def test_minimo_div_mod_tambem_e_truncado_e_sem_funcoes_de_apoio():
    """O modo --minimo tem de refletir a MESMA semântica da linguagem
    (não pode divergir do modo normal), mas continua sem funções de
    apoio -- ver test_minimo_nao_tem_funcoes_de_apoio."""
    from algo_lang.compilador.codegen_minimo import gerar_python_minimo
    programa = parse('algoritmo "T"\ninicio\n    escrever(-7 div 2, -7 mod 2)\n')
    codigo_py = gerar_python_minimo(programa)
    assert "_algo_" not in codigo_py
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, text=True, timeout=10)
    assert resultado.stdout.strip() == "-3-1"


# ---------- AUDIT_PLAN Fase 2: AL-06 -- tamanho de array negativo em runtime ----------

def test_array_com_tamanho_negativo_calculado_em_runtime_da_erro_amigavel():
    """Ao contrário do literal (já apanhado em compilação, ver
    test_array_com_tamanho_negativo_literal_da_erro), um tamanho só
    conhecido em runtime (variável) que dê negativo produzia
    silenciosamente um array vazio -- range(negativo) não levanta
    erro nenhum no Python."""
    import os
    codigo_py = compilar("""
        algoritmo "T"
        inicio
            n:inteiro = -3
            v:inteiro[n]
            escrever("nunca chega aqui")
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 1
    assert "nunca chega aqui" not in resultado.stdout
    assert "não pode ser negativo" in resultado.stdout


def test_array_com_tamanho_positivo_calculado_em_runtime_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        inicio
            n:inteiro = 3
            v:inteiro[n]
            v[0] = 9
            escrever(v[0], " ", v[1], " ", v[2])
    """)
    assert saida.strip() == "9 0 0"


# ---------- AUDIT_PLAN Fase 2: AL-09 -- IndexError distingue array de texto ----------

def test_indice_fora_dos_limites_em_cadeia_caracter_menciona_texto_nao_array():
    import os
    codigo_py = compilar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.caracter("abc", 10))
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 1
    assert "posição de texto" in resultado.stdout
    assert "posição de array" not in resultado.stdout


def test_indice_fora_dos_limites_em_array_continua_a_mencionar_array():
    import os
    codigo_py = compilar("""
        algoritmo "T"
        inicio
            v:inteiro[3]
            escrever(v[10])
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 1
    assert "posição de array" in resultado.stdout
    assert "posição de texto" not in resultado.stdout


# ---------- AUDIT_PLAN Fase 2: AL-13 -- escapes em literais de texto ----------

def test_escape_de_aspa_dentro_de_string():
    saida = executar(r'''algoritmo "T"
inicio
    escrever("ele disse \"ola\"")
''')
    assert saida.strip() == 'ele disse "ola"'


def test_escape_de_barra_invertida_dentro_de_string():
    saida = executar(r'''algoritmo "T"
inicio
    escrever("c:\\pasta")
''')
    assert saida.strip() == r"c:\pasta"


def test_escape_de_quebra_de_linha_dentro_de_string():
    saida = executar(r'''algoritmo "T"
inicio
    escrever("linha1\nlinha2")
''')
    assert saida.strip() == "linha1\nlinha2"


def test_backslash_seguido_de_escape_desconhecido_fica_literal():
    """'\\t' não é um escape reconhecido (só \\", \\\\, \\n são) -- fica
    tal-e-qual (backslash + t) em vez de virar tab ou desaparecer."""
    saida = executar(r'''algoritmo "T"
inicio
    escrever("a\tb")
''')
    assert saida.strip() == r"a\tb"


def test_minimo_tambem_suporta_escapes_de_string():
    from algo_lang.compilador.codegen_minimo import gerar_python_minimo
    programa = parse(r'''algoritmo "T"
inicio
    escrever("ele disse \"ola\"")
''')
    codigo_py = gerar_python_minimo(programa)
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, text=True, timeout=10)
    assert resultado.stdout.strip() == 'ele disse "ola"'


# ---------- AUDIT_PLAN Fase 2: AL-18 -- limite de profundidade no parser ----------

def test_expressao_fortemente_aninhada_da_erro_sintatico_amigavel():
    from algo_lang.compilador.parser import ErroSintatico
    profundidade = 200
    codigo = 'algoritmo "T"\ninicio\n    x:inteiro = ' + "(" * profundidade + "1" + ")" * profundidade + "\n"
    with pytest.raises(ErroSintatico, match="demasiado aninhada"):
        parse(codigo)


def test_expressao_moderadamente_aninhada_continua_a_funcionar():
    saida = executar('algoritmo "T"\ninicio\n    escrever(((((1 + 2))) * (3 - 1)))\n')
    assert saida.strip() == "6"


def test_cadeia_longa_de_operadores_sem_parenteses_nao_e_afetada():
    """Uma cadeia longa do MESMO operador (a+b+c+...) é tratada de
    forma iterativa (while), não recursiva -- não deve disparar o
    limite de profundidade, ao contrário de parênteses aninhados."""
    termos = " + ".join(["1"] * 200)
    saida = executar(f'algoritmo "T"\ninicio\n    escrever({termos})\n')
    assert saida.strip() == "200"


# ---------- AUDIT_PLAN Fase 2: AL-19 -- math.absoluto preserva o tipo do argumento ----------

def test_math_absoluto_de_inteiro_pode_ser_atribuido_a_inteiro():
    saida = executar("""
        algoritmo "T"
        importar Math
        inicio
            x:inteiro = math.absoluto(-5)
            escrever(x)
    """)
    assert saida.strip() == "5"


def test_math_absoluto_de_decimal_continua_decimal():
    saida = executar("""
        algoritmo "T"
        importar Math
        inicio
            x:decimal = math.absoluto(-5.5)
            escrever(x)
    """)
    assert saida.strip() == "5.5"


# ---------- AUDIT_PLAN Fase 2: AL-02 -- ^ com expoente negativo ----------

def test_potencia_com_expoente_literal_nao_negativo_continua_inteiro():
    saida = executar('algoritmo "T"\ninicio\n    x:inteiro = 2 ^ 3\n    escrever(x)\n')
    assert saida.strip() == "8"


def test_potencia_com_expoente_literal_negativo_nao_pode_ser_inteiro():
    with pytest.raises(ErroSemantico, match="não é possível inicializar"):
        compilar('algoritmo "T"\ninicio\n    x:inteiro = 2 ^ -1\n')


def test_potencia_com_expoente_literal_negativo_e_decimal():
    saida = executar('algoritmo "T"\ninicio\n    x:decimal = 2 ^ -1\n    escrever(x)\n')
    assert saida.strip() == "0.5"


def test_potencia_com_expoente_variavel_e_tratada_como_decimal():
    """Sinal do expoente é desconhecido em compilação -- tem de ser
    tipado 'decimal' mesmo que o valor em runtime venha a ser
    não-negativo, para nunca esconder um float dentro de um 'inteiro'."""
    with pytest.raises(ErroSemantico, match="não é possível inicializar"):
        compilar("""
            algoritmo "T"
            inicio
                n:inteiro = 3
                x:inteiro = 2 ^ n
        """)


def test_sem_comparacao_incomparavel():
    with pytest.raises(ErroSemantico, match="não é possível comparar"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                s:cadeia = "a"
                escrever(x == s)
        """)


def test_sem_relacional_com_tipos_errados():
    with pytest.raises(ErroSemantico, match="só pode ser usado entre números ou entre"):
        compilar("""
            algoritmo "T"
            inicio
                a:booleano = verdadeiro
                b:booleano = falso
                escrever(a < b)
        """)


def test_sem_e_ou_com_nao_booleano():
    with pytest.raises(ErroSemantico, match="só pode ser usado entre valores booleanos"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                escrever(x e verdadeiro)
        """)


def test_sem_biblioteca_nao_importada():
    with pytest.raises(ErroSemantico, match="não foi importada"):
        compilar('algoritmo "T"\ninicio\n    escrever(math.raiz(4.0))\n')


def test_sem_metodo_de_biblioteca_inexistente():
    with pytest.raises(ErroSemantico, match="não tem nenhuma função"):
        compilar('algoritmo "T"\nimportar Math\ninicio\n    escrever(math.naoExiste(4.0))\n')


def test_sem_biblioteca_numero_de_argumentos_errado():
    with pytest.raises(ErroSemantico, match="espera 1 argumento"):
        compilar('algoritmo "T"\nimportar Math\ninicio\n    escrever(math.raiz(1, 2))\n')


def test_sem_biblioteca_espera_numerico():
    with pytest.raises(ErroSemantico, match="espera um argumento numérico"):
        compilar('algoritmo "T"\nimportar Math\ninicio\n    escrever(math.raiz("nao numero"))\n')


def test_sem_biblioteca_espera_texto():
    with pytest.raises(ErroSemantico, match="espera texto"):
        compilar('algoritmo "T"\nimportar Cadeia\ninicio\n    escrever(cadeia.comprimento(5))\n')


def test_sem_biblioteca_espera_inteiro():
    with pytest.raises(ErroSemantico, match="espera um inteiro"):
        compilar('algoritmo "T"\nimportar Cadeia\ninicio\n    escrever(cadeia.subcadeia("abc", 1.5, 2))\n')


def test_cadeia_caracter_devolve_o_caracter_na_posicao():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            s:cadeia = "algoritmo"
            escrever(cadeia.caracter(s, 0), cadeia.caracter(s, 4))
    """)
    assert saida.strip() == "ar"


def test_cadeia_caracter_aceita_caracter_como_primeiro_argumento():
    """A categoria 'cadeia' também aceita 'caracter' (TEXTUAIS), tal como
    as outras funções da biblioteca Cadeia."""
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            c:caracter = 'x'
            escrever(cadeia.caracter(c, 0))
    """)
    assert saida.strip() == "x"


def test_cadeia_caracter_indice_fora_dos_limites_da_erro_amigavel(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\nimportar Cadeia\ninicio\n    escrever(cadeia.caracter("abc", 10))\n',
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, text=True)
    assert "Traceback" not in resultado.stdout
    assert "índice fora dos limites" in resultado.stdout


def test_cadeia_caracter_tipo_errado_no_primeiro_argumento():
    with pytest.raises(ErroSemantico, match="espera texto"):
        compilar('algoritmo "T"\nimportar Cadeia\ninicio\n    escrever(cadeia.caracter(5, 0))\n')


def test_cadeia_caracter_tipo_errado_no_segundo_argumento():
    with pytest.raises(ErroSemantico, match="espera um inteiro"):
        compilar('algoritmo "T"\nimportar Cadeia\ninicio\n    escrever(cadeia.caracter("abc", "x"))\n')


def test_sem_funcao_nao_definida():
    with pytest.raises(ErroSemantico, match="não foi definido"):
        compilar('algoritmo "T"\ninicio\n    escrever(naoExiste(1))\n')


def test_sem_numero_de_argumentos_errado_utilizador():
    with pytest.raises(ErroSemantico, match="espera 1 argumento"):
        compilar("""
            algoritmo "T"
            funcao f(a:inteiro):inteiro
                devolver a
            inicio
                escrever(f(1, 2))
        """)


def test_sem_argumento_ref_nao_e_lvalue():
    with pytest.raises(ErroSemantico, match="expressão calculada"):
        compilar("""
            algoritmo "T"
            procedimento p(ref a:inteiro)
                a = 5
            inicio
                p(1 + 2)
        """)


def test_sem_argumento_ref_variavel_nao_declarada():
    with pytest.raises(ErroSemantico, match="não foi declarada"):
        compilar("""
            algoritmo "T"
            procedimento p(ref a:inteiro)
                a = 5
            inicio
                p(naoDeclarada)
        """)


def test_sem_parametro_tipo_incompativel_utilizador():
    with pytest.raises(ErroSemantico, match="mas recebeu"):
        compilar("""
            algoritmo "T"
            funcao f(a:inteiro):inteiro
                devolver a
            inicio
                escrever(f("texto"))
        """)


def test_sem_variavel_ja_declarada():
    with pytest.raises(ErroSemantico, match="já foi declarada"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 1
                x:inteiro = 2
        """)


def test_sem_tamanho_de_array_nao_inteiro():
    with pytest.raises(ErroSemantico, match="tem de ser uma expressão inteira"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro["cinco"]
        """)


def test_sem_declaracao_a_partir_de_procedimento_com_ref():
    with pytest.raises(ErroSemantico, match="não devolve valor"):
        compilar("""
            algoritmo "T"
            procedimento p(ref a:inteiro)
                a = 5
            inicio
                x:inteiro = 1
                y:inteiro = p(x)
        """)


def test_sem_declaracao_tipo_incompativel_de_chamada_com_ref():
    with pytest.raises(ErroSemantico, match="não é possível inicializar"):
        compilar("""
            algoritmo "T"
            funcao f(ref a:inteiro):inteiro
                a = 5
                devolver a
            inicio
                x:inteiro = 1
                s:cadeia = f(x)
        """)


def test_sem_enquanto_condicao_nao_booleana():
    with pytest.raises(ErroSemantico, match="'enquanto' tem de ser booleana"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                enquanto x fazer
                    x = x - 1
        """)


def test_sem_caminhos_de_sucesso_logicos_e_conversao_numerica():
    """Confirma explicitamente os caminhos de SUCESSO (não de erro) de
    nao/e/ou e da conversão inteiro->decimal -- surpreendentemente não
    apareciam cobertos por nenhum teste existente."""
    saida = executar("""
        algoritmo "T"
        inicio
            a:booleano = verdadeiro
            b:booleano = falso
            escrever(a e b, " ", a ou b, " ", nao a)
            x:decimal = 5
            escrever(" ", x)
    """)
    assert saida == "falso verdadeiro falso\n 5\n"


# ---------- lacunas de cobertura: codegen.py ----------

def test_codegen_atribuicao_a_partir_de_funcao_com_ref():
    saida = executar("""
        algoritmo "T"
        funcao incrementar(ref x:inteiro):inteiro
            x = x + 1
            devolver x
        inicio
            y:inteiro = 5
            z:inteiro
            z = incrementar(y)
            escrever(y, " ", z)
    """)
    assert saida.strip() == "6 6"


def test_codegen_funcao_com_ref_chamada_como_instrucao_solta():
    saida = executar("""
        algoritmo "T"
        funcao incrementar(ref x:inteiro):inteiro
            x = x + 1
            devolver x
        inicio
            y:inteiro = 5
            incrementar(y)
            escrever(y)
    """)
    assert saida.strip() == "6"


def test_codegen_ler_campo_de_estrutura_aninhado():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Retangulo
            canto:Ponto
        inicio
            r:Retangulo
            ler(r.canto.x)
            escrever(r.canto.x)
    """, entrada="42\n")
    assert saida.strip() == "42"


def test_codegen_chamada_a_biblioteca_nao_e_confundida_com_funcao_do_utilizador():
    """Exercita _encontrar_funcao com um nome de chamada com '.' (math.raiz)
    -- tem de reconhecer que não é uma função do próprio programa."""
    saida = executar("""
        algoritmo "T"
        importar Math
        inicio
            x:decimal = math.raiz(4.0)
            escrever(x)
    """)
    assert saida.strip() == "2.0"


def test_codegen_campo_de_estrutura_que_e_array_nao_e_partilhado():
    """Mesma classe do bug #11 (campo de tipo estrutura partilhado entre
    instâncias), mas para um campo que é um ARRAY -- confirma que também
    está bem, cada instância com o seu próprio array independente."""
    saida = executar("""
        algoritmo "T"
        estrutura Turma
            notas:inteiro[3]
        inicio
            a:Turma
            b:Turma
            a.notas[0] = 99
            escrever("a=", a.notas[0], " b=", b.notas[0])
    """)
    assert saida.strip() == "a=99 b=0"


def test_parser_mensagem_de_erro_com_token_sem_nome_amigavel():
    """Confirma o caminho genérico de _nome_amigavel para tokens que não
    estão no dicionário NOMES_AMIGAVEIS (ex: INT)."""
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico, match=r"int \(5\)"):
        parse('algoritmo "T"\ninicio\n    x = 5 5\n')


# ---------- lacuna grave encontrada: 'incluir' nunca era testado ----------

def test_incluir_funciona_de_ponta_a_ponta(tmp_path):
    (tmp_path / "geometria.algo").write_text(
        "funcao areaCirculo(raio:decimal):decimal\n"
        "    pi:decimal = 3.14159\n"
        "    devolver pi * raio * raio\n",
        encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "geometria.algo"\n'
        "inicio\n"
        "    escrever(areaCirculo(2.0))\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert "12.56636" in resultado.stdout


def test_incluir_ficheiro_inexistente_da_erro(tmp_path):
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "naoexiste.algo"\n'
        "inicio\n"
        "    escrever(1)\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "não encontrado" in resultado.stdout


def test_incluir_estrutura_duplicada_da_erro(tmp_path):
    (tmp_path / "lib.algo").write_text(
        "estrutura Ponto\n    x:inteiro\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "lib.algo"\n'
        "estrutura Ponto\n    y:inteiro\n"
        "inicio\n"
        "    escrever(1)\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "colide" in resultado.stdout


def test_incluir_funcao_duplicada_da_erro(tmp_path):
    (tmp_path / "lib.algo").write_text(
        "funcao f():inteiro\n    devolver 1\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "lib.algo"\n'
        "funcao f():inteiro\n    devolver 2\n"
        "inicio\n"
        "    escrever(f())\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "colide" in resultado.stdout


def test_incluir_variavel_global_duplicada_da_erro(tmp_path):
    (tmp_path / "lib.algo").write_text(
        "total:inteiro = 0\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "lib.algo"\n'
        "total:inteiro = 1\n"
        "inicio\n"
        "    escrever(total)\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode != 0
    assert "colide" in resultado.stdout


def test_incluir_constante(tmp_path):
    (tmp_path / "lib.algo").write_text(
        "constante PI:decimal = 3.14\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "lib.algo"\n'
        "inicio\n"
        "    escrever(PI)\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert "3.14" in resultado.stdout


def test_parser_ler_multiplas_variaveis():
    saida = executar("""
        algoritmo "T"
        inicio
            a:inteiro
            b:inteiro
            ler(a, b)
            escrever(a, " ", b)
    """, entrada="1\n2\n")
    assert saida.strip() == "1 2"


def test_parser_chamada_a_biblioteca_como_instrucao_solta():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            cadeia.maiusculas("a")
            escrever("ok")
    """)
    assert saida.strip() == "ok"


def test_parser_expressao_entre_parenteses():
    saida = executar('algoritmo "T"\ninicio\n    escrever((1 + 2) * 3)\n')
    assert saida.strip() == "9"


def test_lexer_indentacao_por_tabs_funciona():
    """Regra explícita da linguagem: indentação por tabs OU grupos de 4
    espaços. Os testes de erro (mistura, espaços não múltiplos de 4) já
    existiam, mas faltava confirmar o caminho de SUCESSO com tabs."""
    saida = executar("algoritmo \"T\"\ninicio\n\tx:inteiro = 5\n\tse x > 0 entao\n\t\tescrever(\"positivo\")\n")
    assert saida.strip() == "positivo"


def test_parser_literal_de_estrutura_vazio():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {}
            escrever(p.x, " ", p.y)
    """)
    assert saida.strip() == "0 0"


# ---------- bug real do linter: falso positivo em array indexado ----------

def test_linter_nao_assinala_falso_positivo_array_so_escrito_por_indice():
    """Bug encontrado na auditoria: 'ler(v[i])' e 'v[i] = ...' só
    registavam o índice (i) como usado, nunca a base (v) -- um array só
    alguma vez escrito/lido por índice era incorretamente assinalado como
    'nunca usado'."""
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            v:inteiro[3]
            i:inteiro = 0
            ler(v[i])
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("'v'" in a.mensagem and "nunca é usada" in a.mensagem for a in avisos)


def test_linter_ainda_assinala_atribuicao_simples_nunca_lida():
    """Confirma que a correção acima não voltou a quebrar a deteção
    original: 'x = 5' sozinho (sem acessos) continua a NÃO contar como
    'usado' -- é exatamente essa a atribuição simples nunca lida que
    queremos detetar."""
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            x = 10
            escrever("nunca le x")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("'x'" in a.mensagem and "nunca é usada" in a.mensagem for a in avisos)


def test_linter_sem_falsos_positivos_com_estrutura_array_e_nao():
    """Programa que exercita UnOp (nao), EstruturaLiteral e ArrayLiteral
    dentro do linter -- nenhuma destas variáveis deve ser assinalada."""
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        funcao dobro(n:inteiro):inteiro
            devolver n * 2
        inicio
            a:inteiro = 5
            b:booleano = nao verdadeiro
            p:Ponto = {x: a}
            v:inteiro[2] = {1, 2}
            escrever(b, " ", p.x, " ", v[0], " ", dobro(a))
            afirmar a > 0, "positivo"
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert avisos == []


def test_linter_sem_falsos_positivos_com_para_passo_enquanto_escolha():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao dobro(n:inteiro):inteiro
            devolver n * 2
        inicio
            total:inteiro = 0
            i:inteiro = 0
            para i de 1 ate 3 passo 1 fazer
                total = total + i
            enquanto total > 100 fazer
                total = total - 1
            escolher total
                caso 1, 2
                    escrever("baixo")
                contrario
                    escrever("outro")
            escrever(dobro(total))
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert avisos == []


def test_linter_variavel_de_ciclo_global_dentro_de_funcao_nao_e_assinalada(tmp_path):
    """'para <nomeGlobal> de ... fazer' dentro de uma função trata a
    variável de ciclo como local (sombra a global), não deve dar aviso de
    'acede diretamente à global'."""
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(textwrap.dedent("""
        algoritmo "T"
        total:inteiro = 0
        procedimento f()
            para total de 1 ate 3 fazer
                escrever(total)
        inicio
            f()
    """), encoding="utf-8")
    resultado = subprocess.run(["algo", "lint", str(algo_path)], capture_output=True, text=True)
    assert "acede diretamente" not in resultado.stdout


def test_linter_ler_para_global_dentro_de_funcao_e_assinalado():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        total:inteiro = 0
        procedimento f()
            ler(total)
        inicio
            f()
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("acede diretamente" in a.mensagem for a in avisos)


def test_linter_comparacao_de_campos_diferentes_nao_e_assinalada():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura P
            x:inteiro
            y:inteiro
        inicio
            p:P
            se p.x == p.y entao
                escrever("a")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("sempre verdadeira" in a.mensagem for a in avisos)


def test_linter_comparacao_mesmo_indice_literal_e_assinalada():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            se v[1] == v[1] entao
                escrever("a")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("sempre verdadeira" in a.mensagem for a in avisos)


def test_linter_comparacao_mesmo_campo_objetos_diferentes_nao_e_assinalada():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura P
            x:inteiro
        inicio
            p:P
            q:P
            se p.x == q.x entao
                escrever("a")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("sempre verdadeira" in a.mensagem for a in avisos)


def test_linter_constante_declarada_em_bloco_aninhado_nao_e_falso_positivo():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            se x > 0 entao
                constante DOBRO_X:inteiro = 10
                escrever(DOBRO_X)
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert avisos == []


def test_indentacao_mista_entre_linhas_diferentes_da_erro_de_compilacao():
    """AL-15: promovido de aviso do linter a erro de compilação -- uma
    linha com tabs e outra com espaços no mesmo ficheiro já não chega
    sequer a compilar (antes, cada linha isolada era válida e só o
    linter assinalava a mistura como aviso de estilo)."""
    with pytest.raises(ErroLexico, match="mistura indentação"):
        compilar('algoritmo "T"\ninicio\n\tx:inteiro = 5\n    escrever(x)\n')


# ---------- lacunas de cobertura: flowchart.py ----------

def test_flowchart_com_caracter_array_estrutura_e_nao():
    from algo_lang.tools.flowchart import gerar_dot
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura P
            x:inteiro
        inicio
            c:caracter = 'a'
            v:inteiro[2] = {1, 2}
            p:P = {x: 1}
            n:inteiro = 5
            afirmar nao (n == 0), "n nao pode ser zero"
            escrever(c, v[0], p.x)
    """))
    verificar(programa)
    dot = gerar_dot(programa.corpo, programa.nome)
    assert "{1, 2}" in dot
    assert "{x: 1}" in dot
    assert "nao" in dot


def test_flowchart_declaracao_sem_valor_inicial():
    from algo_lang.tools.flowchart import gerar_dot
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            x:inteiro
            escrever(x)
    """))
    verificar(programa)
    dot = gerar_dot(programa.corpo, programa.nome)
    assert "declarar x: inteiro" in dot


def test_flowchart_faz_enquanto():
    from algo_lang.tools.flowchart import gerar_dot
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            x:inteiro = 0
            fazer
                x = x + 1
            enquanto x < 3
            escrever(x)
    """))
    verificar(programa)
    dot = gerar_dot(programa.corpo, programa.nome)
    assert dot.count("diamond") == 1


def test_flowchart_escolha_sem_contrario():
    from algo_lang.tools.flowchart import gerar_dot
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            n:inteiro = 1
            escolher n
                caso 1
                    escrever("um")
    """))
    verificar(programa)
    dot = gerar_dot(programa.corpo, programa.nome)
    assert 'label="contrario"' in dot


def test_incluir_o_mesmo_ficheiro_duas_vezes_nao_da_erro(tmp_path):
    """cli.py deduplica inclusões pelo caminho absoluto -- incluir o
    mesmo ficheiro duas vezes (ex: dependência em diamante) não deve
    causar 'já foi definido'."""
    (tmp_path / "lib.algo").write_text(
        "funcao f():inteiro\n    devolver 1\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\n'
        'incluir "lib.algo"\n'
        'incluir "lib.algo"\n'
        "inicio\n"
        "    escrever(f())\n",
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(tmp_path / "principal.algo")],
        capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert "1" in resultado.stdout


# ---------- AUDIT_PLAN Fase 0: AL-01 / AL-32 -- RCE via 'afirmar' ----------

def test_afirmar_com_chavetas_na_condicao_nao_executa_codigo(tmp_path):
    """AL-01: a condição de 'afirmar' é reproduzida na mensagem de erro.
    Antes da correção, era interpolada diretamente numa f-string do Python
    gerado sem escapar chavetas -- uma condição contendo
    '{__import__(...)...}' executava código Python arbitrário ao falhar."""
    import os
    marcador = tmp_path / "pwned.txt"
    payload = "{__import__('builtins').open('" + marcador.as_posix() + "','w').write('x')}"
    codigo_py = compilar(f"""
        algoritmo "T"
        inicio
            s:cadeia = "abc"
            afirmar s == "{payload}"
    """)
    # PYTHONIOENCODING força UTF-8 no stdout do subprocesso -- sem isto, o
    # emoji da mensagem de erro pode falhar a codificar em consolas Windows
    # sem code page UTF-8 (falha de ambiente pré-existente, ver AL-35;
    # não é isso que este teste está a verificar).
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 1
    assert not marcador.exists()
    assert "__import__" in resultado.stdout


def test_flowchart_texto_expr_com_chavetas_produz_dot_seguro():
    """AL-32: mesma classe de defeito em tools/flowchart.py -- confirma que
    chavetas/aspas vindas de um literal do estudante aparecem tal-e-qual no
    rótulo DOT (nunca reavaliadas como código, DOT não é executável)."""
    from algo_lang.tools.flowchart import gerar_dot
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        inicio
            s:cadeia = "abc"
            afirmar s == "{codigo malicioso}"
    """))
    verificar(programa)
    dot = gerar_dot(programa.corpo, programa.nome)
    assert "{codigo malicioso}" in dot
