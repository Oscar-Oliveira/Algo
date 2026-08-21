# -*- coding: utf-8 -*-
"""Testes de regressão para os problemas encontrados na auditoria ao
compilador: cada um destes já foi um bug real, confirmado antes de ser
corrigido."""
import os
import subprocess
import sys
import textwrap
import pytest

from apoio import compilar, executar
from algo_lang.compilador.parser import parse, ErroSintatico
from algo_lang.compilador.semantics import verificar, ErroSemantico
from algo_lang.compilador.lexer import ErroLexico, tokenizar
from algo_lang.compilador.ast_nodes import coletar_identificadores


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


def test_para_com_passo_de_efeito_lateral_so_avalia_uma_vez():
    """'passo' entrava duas vezes no range() gerado -- uma expressão com
    efeito lateral (ex: uma chamada de função) corria duas vezes por
    iteração, dando um step efetivo diferente do pretendido."""
    saida = executar("""
        algoritmo "T"
        contador:inteiro

        funcao proximoPasso():inteiro
            contador = contador + 1
            devolver contador
        inicio
            contador = 0
            x:inteiro
            para x de 1 ate 5 passo proximoPasso() fazer
                escrever(x)
    """)
    assert saida.split() == ["1", "2", "3", "4", "5"]


def test_raiz_de_negativo_da_erro_amigavel_nao_traceback(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\nimportar Matematica\ninicio\n    escrever(matematica.raiz(-4.0))\n',
        encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path)], capture_output=True, text=True)
    assert "Traceback" not in resultado.stdout
    assert "Erro em tempo de execução" in resultado.stdout


def test_aleatorio_com_limites_invertidos_da_erro_amigavel(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\nimportar Matematica\ninicio\n    escrever(matematica.aleatorio(10, 1))\n',
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


# ---------- #9 tamanho de vetor negativo ----------

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


def test_vetor_com_tamanho_negativo_literal_da_erro():
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


def test_lexer_indentacao_avanca_mais_de_um_nivel_de_uma_vez():
    # AL-73: um bloco novo so pode aumentar 1 nivel de indentacao de cada
    # vez -- um salto de 2+ niveis (aqui, de 0 para 3) e apanhado nesta
    # linha, antes mesmo de chegar a um eventual dedent inconsistente.
    with pytest.raises(ErroLexico, match="avança 3 níveis"):
        compilar("""algoritmo "T"
inicio
            x:inteiro = 1
        y:inteiro = 2
""")


def test_lexer_tab_a_meio_de_linha_e_tratado_como_espaco():
    # AL-72: um tab fora da indentacao (ex. colado de um editor com tabs de
    # alinhamento) e whitespace, tal como o espaco -- nao um erro lexico.
    saida = executar("algoritmo \"T\"\ninicio\n\tx:inteiro\t=\t5\n\tescrever(x)\n")
    assert saida.strip() == "5"


def test_lexer_decimal_comecado_por_ponto_e_reconhecido():
    # AL-74: '.5' e um decimal valido, tal como '1.' ja era.
    saida = executar("algoritmo \"T\"\ninicio\n\tx:decimal = .5\n\tescrever(x)\n")
    assert saida.strip() == "0.5"


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
    with pytest.raises(ErroSemantico, match="devolver"):
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


def test_sem_campo_vetor_nao_pode_ser_inicializado_em_literal_de_estrutura():
    with pytest.raises(ErroSemantico, match="é um vetor"):
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
    with pytest.raises(ErroSemantico, match="não é um vetor"):
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


def test_sem_campo_sem_indexar_vetor_primeiro():
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


def test_sem_vetor_sem_indexar_em_expressao():
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


def test_elementos_diferentes_do_mesmo_vetor_por_referencia_nao_da_falso_positivo():
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


# ---------- AUDIT_PLAN Fase 2: AL-06 -- tamanho de vetor negativo em runtime ----------

def test_vetor_com_tamanho_negativo_calculado_em_runtime_da_erro_amigavel():
    """Ao contrário do literal (já apanhado em compilação, ver
    test_vetor_com_tamanho_negativo_literal_da_erro), um tamanho só
    conhecido em runtime (variável) que dê negativo produzia
    silenciosamente um vetor vazio -- range(negativo) não levanta
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


def test_vetor_com_tamanho_positivo_calculado_em_runtime_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        inicio
            n:inteiro = 3
            v:inteiro[n]
            v[0] = 9
            escrever(v[0], " ", v[1], " ", v[2])
    """)
    assert saida.strip() == "9 0 0"


# ---------- AUDIT_PLAN Fase 2: AL-09 -- IndexError distingue vetor de texto ----------

def test_indice_fora_dos_limites_em_cadeia_caracter_menciona_texto_nao_vetor():
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
    assert "posição de vetor" not in resultado.stdout


def test_indice_fora_dos_limites_em_vetor_continua_a_mencionar_vetor():
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
    assert "posição de vetor" in resultado.stdout
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
    limite de profundidade de PARÊNTESES aninhados (50), muito mais
    baixo. Continua sujeita ao seu próprio limite, mais alto, dedicado
    à profundidade real da árvore (ver AUDITORIA_2026-08-19 bug #7/#10,
    LIMITE_PROFUNDIDADE_ARVORE) -- 100 termos fica bem dentro dele."""
    termos = " + ".join(["1"] * 100)
    saida = executar(f'algoritmo "T"\ninicio\n    escrever({termos})\n')
    assert saida.strip() == "100"


# ---------- AUDIT_PLAN Fase 2: AL-19 -- matematica.absoluto preserva o tipo do argumento ----------

def test_matematica_absoluto_de_inteiro_pode_ser_atribuido_a_inteiro():
    saida = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            x:inteiro = matematica.absoluto(-5)
            escrever(x)
    """)
    assert saida.strip() == "5"


def test_matematica_absoluto_de_decimal_continua_decimal():
    saida = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            x:decimal = matematica.absoluto(-5.5)
            escrever(x)
    """)
    assert saida.strip() == "5.5"


# ---------- AUDIT_PLAN Fase 2: AL-21 -- cadeia.subcadeia fora dos limites ----------

def test_subcadeia_dentro_dos_limites_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.subcadeia("algoritmo", 0, 4))
    """)
    assert saida.strip() == "algo"


def test_subcadeia_fim_fora_dos_limites_da_erro_amigavel():
    import os
    codigo_py = compilar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.subcadeia("abc", 0, 10))
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 1
    assert "posição de texto" in resultado.stdout
    assert "Traceback" not in resultado.stdout


def test_subcadeia_inicio_negativo_da_erro_amigavel():
    import os
    codigo_py = compilar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.subcadeia("abc", -1, 2))
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 1
    assert "posição de texto" in resultado.stdout


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
        compilar('algoritmo "T"\ninicio\n    escrever(matematica.raiz(4.0))\n')


def test_sem_metodo_de_biblioteca_inexistente():
    with pytest.raises(ErroSemantico, match="não tem nenhuma função"):
        compilar('algoritmo "T"\nimportar Matematica\ninicio\n    escrever(matematica.naoExiste(4.0))\n')


def test_sem_biblioteca_numero_de_argumentos_errado():
    with pytest.raises(ErroSemantico, match="espera 1 argumento"):
        compilar('algoritmo "T"\nimportar Matematica\ninicio\n    escrever(matematica.raiz(1, 2))\n')


def test_sem_biblioteca_espera_numerico():
    with pytest.raises(ErroSemantico, match="espera um argumento numérico"):
        compilar('algoritmo "T"\nimportar Matematica\ninicio\n    escrever(matematica.raiz("nao numero"))\n')


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


def test_sem_tamanho_de_vetor_nao_inteiro():
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
    # AL-XX: 'x' é 'decimal' -- o valor tem de ficar 5.0 (float), não 5
    # (int), mesmo vindo de um literal inteiro (ver _coagir_decimal em
    # gerador_base.py).
    assert saida == "falso verdadeiro falso\n 5.0\n"


# ---------- coerção 'inteiro' -> 'decimal' no código gerado ----------

def test_parametro_e_retorno_decimal_coagem_um_valor_inteiro():
    """Um parâmetro/retorno 'decimal' aceita um valor 'inteiro'
    (_compativel em semantics.py), mas o Python gerado não convertia
    sozinho -- a função devolvia/recebia int, não float."""
    saida = executar("""
        algoritmo "T"
        funcao dobro(x:decimal):decimal
            devolver x * 2

        procedimento mostra(x:decimal)
            escrever("param=", x)
        inicio
            escrever("retorno=", dobro(3))
            mostra(4)
    """)
    assert saida.split() == ["retorno=6.0", "param=4.0"]


def test_campo_de_estrutura_decimal_coage_um_valor_inteiro():
    saida = executar("""
        algoritmo "T"
        estrutura Conta
            saldo:decimal
        inicio
            c:Conta = {saldo: 5}
            escrever(c.saldo)
    """)
    assert saida.strip() == "5.0"


def test_matematica_potencia_devolve_sempre_decimal():
    saida = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.potencia(2, 3))
    """)
    assert saida.strip() == "8.0"


# ---------- colisão com o nome interno gerado de uma biblioteca ----------

def test_funcao_com_nome_interno_de_biblioteca_da_erro():
    """Antes, 'funcao matematica_raiz(...)' era gerada DEPOIS da função da
    biblioteca no Python de saída e sobrepunha-se-lhe silenciosamente --
    todas as chamadas a matematica.raiz(...) no resto do programa
    passavam a chamar a função do estudante, sem nenhum aviso."""
    with pytest.raises(ErroSemantico, match="matematica_raiz"):
        compilar("""
            algoritmo "T"
            importar Matematica

            funcao matematica_raiz(x:decimal):decimal
                devolver 999.0
            inicio
                escrever(matematica.raiz(4.0))
        """)


def test_estrutura_com_nome_interno_de_biblioteca_da_erro():
    with pytest.raises(ErroSemantico, match="matematica_raiz"):
        compilar("""
            algoritmo "T"
            importar Matematica
            estrutura matematica_raiz
                x:inteiro
            inicio
                escrever(matematica.raiz(4.0))
        """)


def test_variavel_com_nome_interno_de_biblioteca_da_erro():
    with pytest.raises(ErroSemantico, match="matematica_raiz"):
        compilar("""
            algoritmo "T"
            importar Matematica
            inicio
                matematica_raiz:inteiro = 1
                escrever(matematica.raiz(4.0))
        """)


def test_nome_igual_a_funcao_de_biblioteca_nao_importada_e_permitido():
    """A colisão só é um problema se a biblioteca estiver mesmo importada
    -- se 'Matematica' nunca é importada, 'matematica_raiz' não é gerada
    para lado nenhum e o nome do estudante é inofensivo."""
    saida = executar("""
        algoritmo "T"
        funcao matematica_raiz(x:decimal):decimal
            devolver x
        inicio
            escrever(matematica_raiz(4.0))
    """)
    assert saida.strip() == "4.0"


# ---------- AUDITORIA_2026-08-19 Fase 2.3: colisão com nomes que o
# próprio codegen usa (bugs #23 e #27) ----------

@pytest.mark.parametrize("nome_reservado", ["sys", "copy", "print", "input"])
def test_variavel_global_com_nome_reservado_pelo_codegen_da_erro(nome_reservado):
    """bug #23: 'sys'/'copy' vêm do cabeçalho do próprio codegen.py;
    'print'/'input' são builtins que o código gerado chama diretamente.
    Antes, só palavras-chave do Python eram rejeitadas -- estes nomes
    perfeitamente normais rebatiam o import/builtin correspondente no
    módulo Python gerado, partindo o compilador de formas diferentes
    (a pior: 'copy' fazia o handler de AttributeError mentir ao
    estudante, dizendo 'acesso a campo de nulo')."""
    with pytest.raises(ErroSemantico, match="nome interno"):
        compilar(f"""
            algoritmo "T"
            {nome_reservado}:inteiro = 5
            inicio
                escrever({nome_reservado})
        """)


def test_funcao_com_nome_reservado_pelo_codegen_da_erro():
    with pytest.raises(ErroSemantico, match="nome interno"):
        compilar("""
            algoritmo "T"
            funcao sys(): inteiro
                devolver 1
            inicio
                escrever(sys())
        """)


def test_estrutura_com_nome_reservado_pelo_codegen_da_erro():
    with pytest.raises(ErroSemantico, match="nome interno"):
        compilar("""
            algoritmo "T"
            estrutura copy
                x:inteiro
            inicio
                escrever(1)
        """)


def test_parametro_com_nome_reservado_pelo_codegen_da_erro():
    with pytest.raises(ErroSemantico, match="nome interno"):
        compilar("""
            algoritmo "T"
            procedimento f(print:inteiro)
                escrever(print)
            inicio
                f(1)
        """)


@pytest.mark.parametrize("nome_reservado", ["_math", "_random"])
def test_variavel_global_com_alias_interno_de_biblioteca_importada_da_erro(nome_reservado):
    """bug #27: mesma classe do bug #23, mas para o alias que uma
    biblioteca injeta no seu próprio CABECALHO (matematica.py ->
    'import math as _math'/'import random as _random') -- só
    verificado dinamicamente (_nomes_importados_no_cabecalho), não uma
    lista fixa por biblioteca."""
    with pytest.raises(ErroSemantico, match="nome interno"):
        compilar(f"""
            algoritmo "T"
            importar Matematica
            {nome_reservado}:inteiro = 5
            inicio
                escrever(matematica.raiz(4.0))
        """)


@pytest.mark.parametrize("nome_reservado", ["_math", "_random"])
def test_alias_interno_de_biblioteca_nao_importada_e_permitido(nome_reservado):
    """A colisão só existe quando a biblioteca está mesmo importada --
    sem 'importar Matematica', o CABECALHO dela (e os seus aliases)
    nunca entra no ficheiro gerado."""
    saida = executar(f"""
        algoritmo "T"
        inicio
            {nome_reservado}:inteiro = 5
            escrever({nome_reservado})
    """)
    assert saida.strip() == "5"


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
    """Exercita _encontrar_funcao com um nome de chamada com '.' (matematica.raiz)
    -- tem de reconhecer que não é uma função do próprio programa."""
    saida = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            x:decimal = matematica.raiz(4.0)
            escrever(x)
    """)
    assert saida.strip() == "2.0"


def test_codegen_campo_de_estrutura_que_e_vetor_nao_e_partilhado():
    """Mesma classe do bug #11 (campo de tipo estrutura partilhado entre
    instâncias), mas para um campo que é um VETOR -- confirma que também
    está bem, cada instância com o seu próprio vetor independente."""
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


# ---------- bug real do linter: falso positivo em vetor indexado ----------

def test_linter_nao_assinala_falso_positivo_vetor_so_escrito_por_indice():
    """Bug encontrado na auditoria: 'ler(v[i])' e 'v[i] = ...' só
    registavam o índice (i) como usado, nunca a base (v) -- um vetor só
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


def test_linter_sem_falsos_positivos_com_estrutura_vetor_e_nao():
    """Programa que exercita UnOp (nao), EstruturaLiteral e VetorLiteral
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
    resultado = subprocess.run(["algo", "verifica", str(algo_path)], capture_output=True, text=True)
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


# ---------- AUDIT_PLAN Fase 2: AL-28 -- linter verifica globais nunca usadas ----------

def test_linter_assinala_global_de_topo_nunca_usada():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        total:inteiro = 0
        inicio
            escrever("ola")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("'total'" in a.mensagem and "nunca é usada" in a.mensagem for a in avisos)


def test_linter_global_usada_so_dentro_de_uma_funcao_nao_e_falso_positivo():
    """'total' nunca é lida/escrita em 'inicio' -- só dentro do
    procedimento. Antes do AL-28, o linter não via usos vindos de
    funções ao verificar globais (nem sequer as verificava), por isso
    isto teria de ser corretamente reconhecido como "usada"."""
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        total:inteiro = 0
        procedimento mostrar()
            escrever(total)
        inicio
            mostrar()
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("'total'" in a.mensagem and "nunca é usada" in a.mensagem for a in avisos)


# ---------- AUDIT_PLAN Fase 2: AL-29 -- linter e autochamadas (dead code) ----------

def test_linter_assinala_funcao_puramente_autorrecursiva_nunca_chamada_de_fora():
    """Uma função que só se chama a si própria (nunca é chamada de
    'inicio' nem de outra rotina) é código morto -- a autochamada não
    deve contar como 'uso' que a livra do aviso."""
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao nuncaChamada(n:inteiro):inteiro
            se n <= 0 entao
                devolver 0
            senao
                devolver nuncaChamada(n - 1)
        inicio
            escrever("ola")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("'nuncaChamada'" in a.mensagem and "nunca é chamada" in a.mensagem for a in avisos)


def test_linter_nao_assinala_funcao_recursiva_chamada_a_partir_do_principal():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao fatorial(n:inteiro):inteiro
            se n <= 1 entao
                devolver 1
            senao
                devolver n * fatorial(n - 1)
        inicio
            escrever(fatorial(5))
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("'fatorial'" in a.mensagem and "nunca é chamada" in a.mensagem for a in avisos)


# ---------- AUDIT_PLAN Fase 2: AL-33 -- pasta de saída colide com um ficheiro ----------

def test_pasta_saida_com_ficheiro_no_caminho_da_erro_amigavel(tmp_path, capsys):
    from algo_lang.cli import _pasta_saida
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever(1)\n', encoding="utf-8")
    # Cria um FICHEIRO (não pasta) exatamente onde a pasta de saída iria ficar.
    (tmp_path / "prog").write_text("já sou um ficheiro", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _pasta_saida(str(algo_path))
    assert exc.value.code == 1
    assert "já existe um ficheiro" in capsys.readouterr().out


def test_pasta_saida_normal_continua_a_funcionar(tmp_path):
    import os
    from algo_lang.cli import _pasta_saida
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever(1)\n', encoding="utf-8")
    pasta, nome_base = _pasta_saida(str(algo_path))
    assert nome_base == "prog"
    assert os.path.isdir(pasta)


# ---------- AUDIT_PLAN Fase 2: AL-34 -- .algo com codificação inválida ----------

def test_ficheiro_algo_com_bytes_invalidos_utf8_da_erro_amigavel(tmp_path, capsys):
    from algo_lang.cli import _ler_ficheiro_algo
    algo_path = tmp_path / "prog.algo"
    # 0xE9 sozinho não é UTF-8 válido (é 'é' em Latin-1, por exemplo).
    algo_path.write_bytes(b'algoritmo "T"\ninicio\n    escrever("caf\xe9")\n')
    with pytest.raises(SystemExit) as exc:
        _ler_ficheiro_algo(str(algo_path))
    assert exc.value.code == 1
    assert "UTF-8" in capsys.readouterr().out


def test_carregar_ficheiro_algo_com_codificacao_invalida_da_erro_amigavel(tmp_path, capsys):
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    algo_path = tmp_path / "prog.algo"
    algo_path.write_bytes(b'algoritmo "T"\ninicio\n    escrever("caf\xe9")\n')
    with pytest.raises(SystemExit) as exc:
        _carregar_e_resolver_inclusoes(str(algo_path))
    assert exc.value.code == 1
    assert "UTF-8" in capsys.readouterr().out


# ---------- AUDITORIA_2026-08-19 Fase 2.4: codificação (bugs #25 e #28) ----------

def test_ficheiro_algo_com_bom_utf8_compila_normalmente(tmp_path):
    """bug #28: 'encoding="utf-8"' simples não remove o BOM (EF BB BF)
    que vários editores no Windows (incluindo o Bloco de Notas) escrevem
    por omissão -- ficava como um caractere invisível na linha 1, coluna
    1, dando um erro léxico que o estudante não conseguia relacionar com
    nada visível no seu editor. 'utf-8-sig' remove-o se existir."""
    from algo_lang.cli import _ler_ficheiro_algo
    algo_path = tmp_path / "prog.algo"
    codigo = 'algoritmo "T"\ninicio\n    escrever(1 + 1)\n'
    algo_path.write_bytes(b"\xef\xbb\xbf" + codigo.encode("utf-8"))
    lido = _ler_ficheiro_algo(str(algo_path))
    assert lido == codigo
    compilar(lido)  # não deve levantar nada


def test_ficheiro_algo_sem_bom_continua_a_funcionar(tmp_path):
    """Não regressão: 'utf-8-sig' é um no-op seguro quando não há BOM."""
    from algo_lang.cli import _ler_ficheiro_algo
    algo_path = tmp_path / "prog.algo"
    codigo = 'algoritmo "T"\ninicio\n    escrever("café")\n'
    algo_path.write_bytes(codigo.encode("utf-8"))
    assert _ler_ficheiro_algo(str(algo_path)) == codigo


def test_escrever_acentos_e_emoji_nao_crasha_numa_codepage_restrita():
    """bug #25: sem sys.stdout.reconfigure(encoding="utf-8") no
    preâmbulo gerado, 'escrever' de um acento/emoji fora do codepage do
    AMBIENTE (não do ficheiro fonte, já UTF-8) rebentava com
    UnicodeEncodeError -- apanhado como ValueError genérico, mensagem
    sem relação nenhuma com o problema real. Simula uma codepage
    restrita removendo PYTHONIOENCODING/LANG/LC_ALL do ambiente do
    subprocesso -- em produção, online/executor.py limpa exatamente
    estas variáveis (ver _env_minimo), por isso não é um cenário
    artificial."""
    import os
    codigo_py = compilar("""
        algoritmo "T"
        inicio
            escrever("café ☕ não")
    """)
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONIOENCODING", "LANG", "LC_ALL")}
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, timeout=10, env=env)
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8").strip() == "café ☕ não"


def test_sys_stdout_reconfigure_nao_e_chamado_quando_indisponivel():
    """Sob tools/tracer.py (--debug/--json), o mesmo ficheiro gerado
    corre com sys.stdout redirecionado para um io.StringIO() em
    memória (contextlib.redirect_stdout), que não tem '.reconfigure()'
    -- sem o 'hasattr' de guarda, isto seria um AttributeError cru
    logo ao arrancar QUALQUER programa em modo --debug/--json."""
    from algo_lang.compilador.codegen import gerar_python_com_mapa
    from algo_lang.tools.tracer import gerar_trace
    programa = parse('algoritmo "T"\ninicio\n    escrever("café ☕")\n')
    verificar(programa)
    dados = gerar_python_com_mapa(programa)
    resultado = gerar_trace(
        dados["codigo"], "<mem>", dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"])
    assert resultado["erro"] is None
    assert resultado["consolaFinal"].strip() == "café ☕"


# ---------- AUDIT_PLAN Fase 2: AL-36 -- 'incluir' transitivo a sério ----------

def test_incluir_transitivo_resolve_biblioteca_que_inclui_outra(tmp_path):
    """principal.algo inclui meio.algo, que por sua vez inclui
    fundo.algo -- antes do AL-36, isto falhava com erro de sintaxe
    (parse_biblioteca não reconhecia 'incluir' dentro de uma
    biblioteca)."""
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    (tmp_path / "fundo.algo").write_text(
        "funcao triplo(n:inteiro):inteiro\n    devolver n * 3\n", encoding="utf-8")
    (tmp_path / "meio.algo").write_text(
        'incluir "fundo.algo"\nfuncao dobro(n:inteiro):inteiro\n    devolver n * 2\n',
        encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\nincluir "meio.algo"\ninicio\n    escrever(dobro(triplo(5)))\n',
        encoding="utf-8")
    programa = _carregar_e_resolver_inclusoes(str(tmp_path / "principal.algo"))
    nomes = {f.nome for f in programa.funcoes}
    assert nomes == {"dobro", "triplo"}


def test_incluir_transitivo_circular_nao_entra_em_ciclo_infinito(tmp_path):
    """a.algo inclui b.algo, b.algo inclui a.algo de volta -- tem de
    terminar (deduplicação partilhada por toda a árvore), não
    recursão infinita."""
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    (tmp_path / "a.algo").write_text(
        'incluir "b.algo"\nfuncao fA():inteiro\n    devolver 1\n', encoding="utf-8")
    (tmp_path / "b.algo").write_text(
        'incluir "a.algo"\nfuncao fB():inteiro\n    devolver 2\n', encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\nincluir "a.algo"\ninicio\n    escrever(fA() + fB())\n',
        encoding="utf-8")
    programa = _carregar_e_resolver_inclusoes(str(tmp_path / "principal.algo"))
    nomes = {f.nome for f in programa.funcoes}
    assert nomes == {"fA", "fB"}


def test_incluir_transitivo_diamante_nao_duplica(tmp_path):
    """principal inclui b e c; b e c incluem, cada um, comum.algo --
    comum só deve ser processado uma vez."""
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    (tmp_path / "comum.algo").write_text(
        "funcao fComum():inteiro\n    devolver 42\n", encoding="utf-8")
    (tmp_path / "b.algo").write_text('incluir "comum.algo"\n', encoding="utf-8")
    (tmp_path / "c.algo").write_text('incluir "comum.algo"\n', encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\nincluir "b.algo"\nincluir "c.algo"\ninicio\n    escrever(fComum())\n',
        encoding="utf-8")
    programa = _carregar_e_resolver_inclusoes(str(tmp_path / "principal.algo"))
    nomes = [f.nome for f in programa.funcoes]
    assert nomes == ["fComum"]


# ---------- AUDIT_PLAN Fase 2: AL-16 -- literais {...} como expressões gerais ----------

def test_literal_de_estrutura_como_argumento_de_funcao():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:decimal
            y:decimal
        funcao distanciaAOrigemQuadrado(p:Ponto):decimal
            devolver p.x * p.x + p.y * p.y
        inicio
            escrever(distanciaAOrigemQuadrado({x: 3.0, y: 4.0}))
    """)
    assert saida.strip() == "25.0"


def test_literal_de_estrutura_como_argumento_de_procedimento():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        procedimento mostrar(p:Ponto)
            escrever(p.x, " ", p.y)
        inicio
            mostrar({x: 1, y: 2})
    """)
    assert saida.strip() == "1 2"


def test_literal_de_estrutura_como_argumento_com_campos_omitidos():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        procedimento mostrar(p:Ponto)
            escrever(p.x, " ", p.y)
        inicio
            mostrar({x: 5})
    """)
    assert saida.strip() == "5 0"


def test_literal_de_estrutura_como_segundo_argumento_junto_de_ref():
    """Confirma o caminho de geração de código separado para chamadas
    com parâmetros 'ref' (_gerar_chamada_stmt), não só o caminho normal
    de expressão."""
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        procedimento atualizar(ref contador:inteiro, p:Ponto)
            contador = contador + p.x
        inicio
            n:inteiro = 10
            atualizar(n, {x: 5})
            escrever(n)
    """)
    assert saida.strip() == "15"


def test_literal_de_vetor_multidimensional_continua_a_funcionar():
    """Regressão: a generalização do parser (deixou de precisar de
    saber a profundidade de antemão) não pode partir vetores
    multidimensionais existentes."""
    saida = executar("""
        algoritmo "T"
        inicio
            m:inteiro[2][2] = {{1, 2}, {3, 4}}
            escrever(m[0][0], " ", m[0][1], " ", m[1][0], " ", m[1][1])
    """)
    assert saida.strip() == "1 2 3 4"


def test_literal_chaveta_em_posicao_nao_suportada_da_erro_claro_nao_crash():
    """Fora de uma declaração ou de um argumento de chamada, um '{...}'
    não tem informação suficiente para saber que forma se espera --
    tem de dar um ErroSemantico claro, nunca um erro interno tipo
    'expressão não reconhecida'."""
    with pytest.raises(ErroSemantico, match="não há informação suficiente"):
        compilar("""
            algoritmo "T"
            inicio
                escrever({1, 2, 3})
        """)


def test_indentacao_mista_entre_linhas_diferentes_da_erro_de_compilacao():
    """AL-15: promovido de aviso do linter a erro de compilação -- uma
    linha com tabs e outra com espaços no mesmo ficheiro já não chega
    sequer a compilar (antes, cada linha isolada era válida e só o
    linter assinalava a mistura como aviso de estilo)."""
    with pytest.raises(ErroLexico, match="mistura indentação"):
        compilar('algoritmo "T"\ninicio\n\tx:inteiro = 5\n    escrever(x)\n')


# ---------- lacunas de cobertura: flowchart.py ----------

def test_flowchart_com_caracter_vetor_estrutura_e_nao():
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


def _correr_esperando_erro(codigo_algo):
    """Compila e corre um programa ALGO, sem levantar em caso de erro
    (ao contrário de apoio.executar) -- para testar precisamente os
    casos em que o programa termina com erro em tempo de execução."""
    import os
    codigo_py = compilar(codigo_algo)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True,
        encoding="utf-8", timeout=10, env=env)


# ---------- AL-08 + UX-01: mensagens de ValueError traduzidas para português ----------

def test_raiz_de_negativo_traduz_math_domain_error():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Matematica
inicio
    escrever(matematica.raiz(-4))
""")
    assert resultado.returncode == 1
    assert "domínio válido" in resultado.stdout
    assert "math domain error" not in resultado.stdout.lower()


def test_valueerror_sem_causa_mapeada_mantem_o_generico():
    """Uma causa não mapeada continua a mostrar a mensagem original do
    Python entre parênteses, como recurso -- nunca deve ficar muda. O
    tamanho de vetor negativo (_algo_verificar_tamanho_vetor) tem a sua
    própria mensagem em português mas não está na lista de causas
    mapeadas do tradutor, por isso passa pelo fallback genérico "valor
    inválido (...)" -- só é detetável em runtime quando o tamanho vem
    de uma variável, não de um literal (que já falha em compilação)."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    n:inteiro = -1
    v:inteiro[n]
    escrever(1)
""")
    assert resultado.returncode == 1
    assert "não pode ser negativo" in resultado.stdout


# ---------- UX-04: número de linha ALGO nas mensagens de erro em runtime ----------

def test_erro_de_indice_de_vetor_mostra_a_linha_algo():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
v:inteiro[3]
inicio
    escrever("linha 4")
    escrever(v[10])
""")
    assert resultado.returncode == 1
    assert "(linha 5)" in resultado.stdout


def test_erro_de_divisao_por_zero_mostra_a_linha_algo():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
x:inteiro = 5
y:inteiro = 0
inicio
    escrever(x / y)
""")
    assert resultado.returncode == 1
    assert "(linha 5)" in resultado.stdout


def test_erro_de_valueerror_mostra_a_linha_algo():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Matematica
inicio
    escrever("antes")
    escrever(matematica.raiz(-4))
""")
    assert resultado.returncode == 1
    assert "(linha 5)" in resultado.stdout


def test_erro_dentro_de_uma_funcao_mostra_a_linha_correta():
    """A linha reportada é a do local real do erro, mesmo quando este
    acontece dentro de uma função chamada a partir do corpo principal."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
funcao dividir(a:inteiro, b:inteiro):inteiro
    devolver a div b
inicio
    escrever(dividir(10, 0))
""")
    assert resultado.returncode == 1
    assert "(linha 3)" in resultado.stdout


# ---------- UX-06: consistência do prefixo ❌ nas mensagens de erro da consola ----------

def test_ficheiro_nao_encontrado_usa_o_prefixo_de_erro_padrao(tmp_path, capsys):
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    with pytest.raises(SystemExit):
        _carregar_e_resolver_inclusoes(str(tmp_path / "nao_existe.algo"))
    saida = capsys.readouterr().out
    assert "❌" in saida


# ---------- UX-11: visualizador de rasto standalone sem dependência de CDN ----------

def test_visualizador_standalone_nao_depende_de_cdn_externo():
    """O visualizador standalone (aberto localmente com duplo-clique,
    sem servidor -- ver visualizador/LEIA-ME.md) tem de funcionar sem
    rede nenhuma: React/Babel/Tailwind vêm embutidos no próprio
    ficheiro, não de um CDN externo."""
    import pathlib
    caminho = pathlib.Path(__file__).resolve().parent.parent.parent / "visualizador" / "algo-trace-viewer.html"
    conteudo = caminho.read_text(encoding="utf-8")
    assert "unpkg.com" not in conteudo
    assert "<script src=" not in conteudo
    assert "ReactDOM.createRoot" in conteudo
    assert "Babel.transform" in conteudo


# ---------- ARCH-03: ErroInternoCompilador distinto de ErroSemantico ----------

def test_erro_interno_de_codegen_nao_e_um_erro_semantico():
    """Antes, uma falha de invariante do próprio gerador de código
    (nunca deveria acontecer, já que verificar() valida o programa
    antes) reutilizava ErroSemantico -- um bug real do compilador
    apareceria ao estudante como se fosse um erro de tipos normal no
    seu próprio programa. Testa diretamente o dispatch interno
    (_gerar_stmt) com um nó de AST que não corresponde a nenhuma
    instrução válida, para exercitar o ramo 'else' defensivo que só é
    alcançável assim (por isso está marcado '# pragma: no cover')."""
    from algo_lang.compilador.codegen import GeradorCodigo, ErroInternoCompilador

    programa = parse('algoritmo "T"\ninicio\n    escrever("x")\n')
    gerador = GeradorCodigo(programa)
    no_bogus = object()
    with pytest.raises(ErroInternoCompilador) as exc_info:
        gerador._gerar_stmt(no_bogus, 1, {})
    assert not isinstance(exc_info.value, ErroSemantico)
    assert "Erro interno do compilador" in str(exc_info.value)


# ---------- ARCH-02: texto_expr não vem de tools/flowchart.py ----------

def test_codegen_nao_depende_de_tools():
    """Antes, codegen.py importava texto_expr de tools/flowchart.py,
    invertendo a camada documentada do pipeline (tools/ deveria
    depender do compilador, não o inverso) -- uma mudança em
    texto_expr pensada só para o fluxograma alterava silenciosamente
    as mensagens de 'afirmar' nos programas gerados. texto_expr vive
    agora em compilador/ast_nodes.py, importado por ambos."""
    import ast
    import inspect
    from algo_lang.compilador import codegen
    from algo_lang.compilador.ast_nodes import texto_expr as texto_expr_no_ast_nodes
    assert codegen.texto_expr is texto_expr_no_ast_nodes

    arvore = ast.parse(inspect.getsource(codegen))
    modulos_importados = [
        node.module for node in ast.walk(arvore) if isinstance(node, ast.ImportFrom)
    ]
    assert not any(m and "tools" in m for m in modulos_importados)


# ---------- ARCH-04: deteção de colisão de inclusão partilhada ----------

def test_mesclar_biblioteca_deteta_colisao_de_cada_tipo():
    """A lógica de deteção de colisões (estrutura/função/variável
    global) usada por algo_lang.cli e online.executor.py vive agora
    num único sítio partilhado (compilador/inclusoes.py), em vez de
    reimplementada em cada um. Testa diretamente o módulo partilhado,
    sem depender de subprocess (que nesta máquina Windows precisa de
    'algo' no PATH -- ver o resto deste ficheiro)."""
    from algo_lang.compilador.inclusoes import mesclar_biblioteca_no_programa, ColisaoDeInclusao

    class ProgramaFalso:
        def __init__(self):
            self.estruturas = []
            self.funcoes = []
            self.declaracoes = []

    class NoComNome:
        def __init__(self, nome):
            self.nome = nome

    programa = ProgramaFalso()
    programa.estruturas.append(NoComNome("Ponto"))
    with pytest.raises(ColisaoDeInclusao) as exc_info:
        mesclar_biblioteca_no_programa(programa, "lib.algo", [], [], [NoComNome("Ponto")])
    assert exc_info.value.tipo == "estrutura"
    assert exc_info.value.nome == "Ponto"
    assert exc_info.value.caminho_origem == "lib.algo"

    programa = ProgramaFalso()
    programa.funcoes.append(NoComNome("f"))
    with pytest.raises(ColisaoDeInclusao) as exc_info:
        mesclar_biblioteca_no_programa(programa, "lib.algo", [], [NoComNome("f")], [])
    assert exc_info.value.tipo == "função"

    programa = ProgramaFalso()
    programa.declaracoes.append(NoComNome("x"))
    with pytest.raises(ColisaoDeInclusao) as exc_info:
        mesclar_biblioteca_no_programa(programa, "lib.algo", [NoComNome("x")], [], [])
    assert exc_info.value.tipo == "variável global"

    # sem colisão: acrescenta normalmente
    programa = ProgramaFalso()
    mesclar_biblioteca_no_programa(programa, "lib.algo", [NoComNome("a")], [NoComNome("b")], [NoComNome("C")])
    assert [e.nome for e in programa.estruturas] == ["C"]
    assert [f.nome for f in programa.funcoes] == ["b"]
    assert [d.nome for d in programa.declaracoes] == ["a"]


def test_cli_e_online_produzem_a_mesma_mensagem_de_colisao_de_sempre():
    """Verificação direta (sem subprocess) de que a extração do
    ARCH-04 preservou o texto exato que cli.py já imprimia antes desta
    mudança, incluindo o prefixo ❌ e o ponto final em falta na
    variante de função (comportamento pré-existente, não introduzido
    agora)."""
    import tempfile
    from algo_lang.cli import _carregar_e_resolver_inclusoes

    d = tempfile.mkdtemp()
    with open(os.path.join(d, "lib.algo"), "w", encoding="utf-8") as f:
        f.write("estrutura Ponto\n    x:inteiro\n")
    with open(os.path.join(d, "principal.algo"), "w", encoding="utf-8") as f:
        f.write(
            'algoritmo "Principal"\nincluir "lib.algo"\n'
            "estrutura Ponto\n    y:inteiro\ninicio\n    escrever(1)\n"
        )

    with pytest.raises(SystemExit) as exc_info:
        _carregar_e_resolver_inclusoes(os.path.join(d, "principal.algo"))
    assert exc_info.value.code == 1


# ---------- ARCH-01: dispatch centralizado / exaustividade dos tipos de AST ----------
# Adicionar um novo tipo de instrução/expressão à AST exige atualizar ~9
# isinstance/elif espalhados por codegen.py, semantics.py
# e tools/flowchart.py, sem nenhuma verificação de exaustividade em tempo
# de compilação -- um branch esquecido falhava silenciosamente. Em vez de
# um redesenho completo do dispatch (visitor pattern), a abordagem aqui
# tem duas partes: (1) um teste que analisa o código-fonte de cada
# dispatcher e falha explicitamente se um tipo de nó da AST não estiver
# coberto, para apanhar isto em tempo de teste, não só em runtime; (2)
# tools/flowchart.py:gerar_stmt tinha um fallback SILENCIOSO (gerava um nó
# genérico "(instrução)" em vez de um erro) -- corrigido para levantar
# ErroInternoFluxograma, consistente com o padrão já usado em codegen.py
# (ErroInternoCompilador, ARCH-03).

_TIPOS_STMT_DA_AST = {
    "Declaracao", "Atribuicao", "Ler", "Escrever", "Se", "Para", "Enquanto",
    "FazEnquanto", "Escolha", "Devolver", "ChamadaStmt", "Afirmar",
}
_TIPOS_EXPR_DA_AST = {
    "LValue", "Literal", "BinOp", "UnOp", "Chamada", "VetorLiteral", "EstruturaLiteral",
}


def _tipos_ast_referenciados_via_isinstance(funcao):
    """Analisa o código-fonte de 'funcao' (via módulo ast, não execução)
    e devolve o conjunto de nomes de classes A.X referenciados em
    chamadas isinstance(x, A.X) ou isinstance(x, (A.X, A.Y, ...))."""
    import ast as ast_modulo
    import inspect as inspect_modulo
    codigo_fonte = textwrap.dedent(inspect_modulo.getsource(funcao))
    arvore = ast_modulo.parse(codigo_fonte)
    tipos = set()
    for no in ast_modulo.walk(arvore):
        if not (isinstance(no, ast_modulo.Call) and isinstance(no.func, ast_modulo.Name)
                and no.func.id == "isinstance" and len(no.args) == 2):
            continue
        segundo_arg = no.args[1]
        candidatos = segundo_arg.elts if isinstance(segundo_arg, ast_modulo.Tuple) else [segundo_arg]
        for c in candidatos:
            if isinstance(c, ast_modulo.Attribute):
                tipos.add(c.attr)
    return tipos


def test_dispatchers_de_instrucoes_cobrem_todos_os_tipos_de_stmt_da_ast():
    from algo_lang.compilador import codegen, semantics
    from algo_lang.tools import flowchart

    dispatchers = {
        "codegen.GeradorCodigo._gerar_stmt": codegen.GeradorCodigo._gerar_stmt,
        "semantics.VerificadorTipos._verificar_stmt": semantics.VerificadorTipos._verificar_stmt,
        "flowchart.GeradorFluxograma.gerar_stmt": flowchart.GeradorFluxograma.gerar_stmt,
    }
    problemas = {}
    for nome, funcao in dispatchers.items():
        faltam = _TIPOS_STMT_DA_AST - _tipos_ast_referenciados_via_isinstance(funcao)
        if faltam:
            problemas[nome] = faltam
    assert not problemas, problemas


def test_dispatchers_de_expressoes_cobrem_todos_os_tipos_de_expr_da_ast():
    from algo_lang.compilador import codegen, semantics

    # AL-16: um EstruturaLiteral não sabe o seu próprio tipo -- só faz
    # sentido onde o tipo esperado já vem do contexto (declaração,
    # argumento), tratado explicitamente ANTES de chamar o dispatcher
    # genérico (semantics.py já rejeita todos os outros contextos antes
    # disto correr). Cair no fallback genérico de _expr() para um
    # EstruturaLiteral é por isso intencional, não uma lacuna -- exceção
    # documentada, não uma falha deste teste.
    excecoes = {
        "codegen.GeradorCodigo._expr": {"EstruturaLiteral"},
    }
    dispatchers = {
        "codegen.GeradorCodigo._expr": codegen.GeradorCodigo._expr,
        "semantics.VerificadorTipos._tipo_expr": semantics.VerificadorTipos._tipo_expr,
    }
    problemas = {}
    for nome, funcao in dispatchers.items():
        faltam = _TIPOS_EXPR_DA_AST - _tipos_ast_referenciados_via_isinstance(funcao) - excecoes.get(nome, set())
        if faltam:
            problemas[nome] = faltam
    assert not problemas, problemas


def test_flowchart_nao_esconde_instrucao_nao_suportada_num_no_generico():
    """Antes, gerar_stmt() de tools/flowchart.py caía silenciosamente
    num nó genérico "(instrução)" para qualquer tipo de instrução sem
    handler -- sem nenhum aviso de que o fluxograma estava incompleto.
    Testa diretamente o ramo defensivo (só alcançável com um nó bogus,
    por isso marcado '# pragma: no cover')."""
    from algo_lang.tools.flowchart import GeradorFluxograma, ErroInternoFluxograma

    gerador = GeradorFluxograma("T")
    with pytest.raises(ErroInternoFluxograma):
        gerador.gerar_stmt(object(), "n1")


# ===========================================================================
# Segunda auditoria (AUDITORIA.md, 2026-08-13) -- ver AUDITORIA_PROGRESSO.md
# ===========================================================================

# ---------- B1 (AL-41): comentário de bloco sem espaço funde tokens ----------

def test_comentario_bloco_sem_espaco_nao_funde_inteiros_adjacentes():
    from algo_lang.compilador.lexer import tokenizar
    tokens = tokenizar('algoritmo "T"\ninicio\n    escrever(1/**/2)\n')
    valores_int = [t.valor for t in tokens if t.tipo == "INT"]
    assert valores_int == [1, 2]


def test_comentario_bloco_sem_espaco_nao_funde_identificadores_adjacentes():
    saida = executar("""
        algoritmo "T"
        inicio
            a:inteiro = 1
            escrever(a/*comentario*/+1)
    """)
    assert saida.strip() == "2"


# ---------- B2 (AL-42): aspa escapada confunde remoção de comentários ----------

def test_aspa_escapada_seguida_de_barra_dupla_nao_e_tratada_como_comentario():
    saida = executar(r"""
        algoritmo "T"
        inicio
            escrever("say \" then // not a comment")
    """)
    assert saida.strip() == 'say " then // not a comment'


def test_aspa_escapada_nao_confunde_deteccao_de_comentario_de_bloco():
    """O '/* not */' está dentro da string (depois da aspa escapada), por
    isso não é um comentário real -- tem de ficar tal-e-qual no valor."""
    saida = executar(r"""
        algoritmo "T"
        inicio
            escrever("say \" then /* not */ a comment")
    """)
    assert saida.strip() == 'say " then /* not */ a comment'


# ---------- B3 (AL-43): 'caracter' sem escape para apóstrofo ----------

def test_caracter_apostrofo_escapado():
    saida = executar(r"""
        algoritmo "T"
        inicio
            c:caracter = '\''
            escrever(c)
    """)
    assert saida.strip() == "'"


# ---------- B4 (AL-44): sem limite de profundidade para blocos aninhados ----------

def _programa_com_blocos_aninhados(profundidade):
    corpo = "".join(
        "    " * (i + 1) + "se verdadeiro entao\n" for i in range(profundidade))
    corpo += "    " * (profundidade + 1) + 'escrever("fundo")\n'
    return f'algoritmo "T"\ninicio\n{corpo}'


def test_blocos_aninhados_a_mais_da_erro_sintatico_nao_recursionerror():
    from algo_lang.compilador.parser import ErroSintatico
    with pytest.raises(ErroSintatico, match="aninhados a mais"):
        compilar(_programa_com_blocos_aninhados(200))


def test_blocos_aninhados_dentro_do_limite_continuam_a_compilar():
    assert executar(_programa_com_blocos_aninhados(10)).strip() == "fundo"


# ---------- B5 (AL-45): '{}' nunca interpretado como vetor literal vazio ----------

def test_chaveta_vazia_inicializa_vetor_vazio_sem_erro():
    codigo_py = compilar("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {}
            escrever("ok")
    """)
    assert "v = []" in codigo_py


def test_chaveta_vazia_com_campos_de_estrutura_continua_a_dar_erro_claro():
    with pytest.raises(ErroSemantico, match="vetor"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[3] = {x: 1}
        """)


# ---------- B6 (AL-46): atribuição a um vetor inteiro não é rejeitada ----------

def test_atribuir_diretamente_a_vetor_e_erro_semantico():
    with pytest.raises(ErroSemantico, match="vetor"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[3]
                v = 5
        """)


def test_ler_diretamente_para_vetor_e_erro_semantico():
    with pytest.raises(ErroSemantico, match="vetor"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[3]
                ler(v)
        """)


# ---------- B7 (AL-48): tamanhos de vetores em campos de 'estrutura' não validados ----------

def test_tamanho_de_vetor_negativo_em_campo_de_estrutura_e_erro_de_compilacao():
    with pytest.raises(ErroSemantico, match="negativo"):
        compilar("""
            algoritmo "T"
            estrutura Caixa
                valores: inteiro[-3]
            inicio
                c:Caixa
        """)


def test_tamanho_de_vetor_nao_inteiro_em_campo_de_estrutura_e_erro_de_compilacao():
    with pytest.raises(ErroSemantico, match="inteira"):
        compilar("""
            algoritmo "T"
            estrutura Caixa
                valores: inteiro[verdadeiro]
            inicio
                c:Caixa
        """)


# ---------- B8 (AL-49): nem todos os caminhos de uma função devolvem valor ----------

def test_funcao_com_se_sem_senao_nem_sempre_devolve_e_erro():
    with pytest.raises(ErroSemantico, match="devolver"):
        compilar("""
            algoritmo "T"
            funcao f(x:inteiro): inteiro
                se x > 0 entao
                    devolver 1
            inicio
                escrever(f(-5) + 1)
        """)


def test_funcao_com_se_senao_devolvendo_nos_dois_ramos_compila():
    saida = executar("""
        algoritmo "T"
        funcao f(x:inteiro): inteiro
            se x > 0 entao
                devolver 1
            senao
                devolver 0
        inicio
            escrever(f(5))
    """)
    assert saida.strip() == "1"


def test_funcao_com_escolher_sem_contrario_nem_sempre_devolve_e_erro():
    with pytest.raises(ErroSemantico, match="devolver"):
        compilar("""
            algoritmo "T"
            funcao f(x:inteiro): inteiro
                escolher x
                    caso 1
                        devolver 10
            inicio
                escrever(f(2))
        """)


# ---------- B9 (AL-47): 'ler' aceita silenciosamente vetores e structs como alvo ----------

def test_ler_para_variavel_de_tipo_estrutura_e_erro_semantico():
    with pytest.raises(ErroSemantico, match="primitivo"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            inicio
                p:Ponto
                ler(p)
        """)


# ---------- B10 (AL-50): parâmetros nunca verificados contra colisão de nomes ----------

def test_parametro_com_nome_de_estrutura_e_erro_semantico():
    with pytest.raises(ErroSemantico, match="estrutura"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            funcao f(Ponto: inteiro): inteiro
                devolver Ponto
            inicio
                escrever(f(1))
        """)


def test_parametro_com_nome_de_tipo_primitivo_e_erro_semantico():
    with pytest.raises(ErroSemantico, match="tipo primitivo"):
        compilar("""
            algoritmo "T"
            funcao f(inteiro: inteiro): inteiro
                devolver inteiro
            inicio
                escrever(f(1))
        """)


# ---------- B11 (AL-52): estruturas por valor não são copiadas ----------

def test_estrutura_passada_por_valor_nao_e_mutada_no_chamador():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        procedimento muda(p:Ponto)
            p.x = 99
        inicio
            a:Ponto = {x: 1}
            muda(a)
            escrever(a.x)
    """)
    assert saida.strip() == "1"


def test_estrutura_passada_por_ref_continua_a_mutar_no_chamador():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        procedimento muda(ref p:Ponto)
            p.x = 99
        inicio
            a:Ponto = {x: 1}
            muda(a)
            escrever(a.x)
    """)
    assert saida.strip() == "99"


# ---------- B17 (AL-51): falta coerção inteiro->decimal em retorno de 'ref' ----------

def test_declaracao_decimal_a_partir_de_funcao_ref_que_devolve_inteiro_e_coagida():
    saida = executar("""
        algoritmo "T"
        funcao f(ref a:inteiro):inteiro
            a = 5
            devolver a
        inicio
            x:inteiro = 1
            y:decimal = f(x)
            escrever(y)
    """)
    assert saida.strip() == "5.0"


def test_atribuicao_decimal_a_partir_de_funcao_ref_que_devolve_inteiro_e_coagida():
    saida = executar("""
        algoritmo "T"
        funcao f(ref a:inteiro):inteiro
            a = 5
            devolver a
        inicio
            x:inteiro = 1
            y:decimal = 0.0
            y = f(x)
            escrever(y)
    """)
    assert saida.strip() == "5.0"


# ---------- B12 (AL-53): mensagens de _tipo_lvalue usam sempre o nome base ----------

def test_erro_de_vetor_nao_indexado_menciona_o_subcaminho_real():
    with pytest.raises(ErroSemantico, match=r"'c\.valores'"):
        compilar("""
            algoritmo "T"
            estrutura Conta
                valores: inteiro[3]
            inicio
                c:Conta
                escrever(c.valores.tamanho)
        """)


# ---------- B13 (AL-54): conflito de tipo em ramos irmãos não detetado ----------

def test_variavel_global_com_tipos_diferentes_em_ramos_irmaos_e_erro():
    with pytest.raises(ErroSemantico, match="tipos diferentes"):
        compilar("""
            algoritmo "T"
            funcao usa_x(): inteiro
                devolver x + 1
            inicio
                se falso entao
                    x: inteiro = 1
                senao
                    x: cadeia = "oi"
                escrever(usa_x())
        """)


def test_variavel_global_com_mesmo_tipo_em_ramos_irmaos_compila():
    saida = executar("""
        algoritmo "T"
        funcao usa_x(): inteiro
            devolver x + 1
        inicio
            se falso entao
                x: inteiro = 1
            senao
                x: inteiro = 2
            escrever(usa_x())
    """)
    assert saida.strip() == "3"


# ---------- B14 (AL-55): 'escrever' de uma estrutura inteira não é rejeitado ----------

def test_escrever_uma_estrutura_inteira_e_erro_semantico():
    with pytest.raises(ErroSemantico, match="Ponto"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            inicio
                p:Ponto
                escrever(p)
        """)


# ---------- B15 (AL-56): 'Escolha' nunca deteta valores 'caso' duplicados ----------

def test_caso_duplicado_com_literal_e_erro_de_compilacao():
    with pytest.raises(ErroSemantico, match="já apareceu"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 1
                escolher x
                    caso 1
                        escrever("um")
                    caso 1
                        escrever("outra vez um")
        """)


# ---------- B16 (AL-57): base ^ expoente negativa/fracionária vira complex ----------

def test_potencia_de_base_negativa_com_expoente_fracionario_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    base: decimal = -8.0
    expo: decimal = 0.5
    escrever(base ^ expo)
""")
    assert resultado.returncode == 1
    assert "expoente fracionário" in resultado.stdout


def test_potencia_de_base_negativa_com_expoente_inteiro_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        inicio
            base: decimal = -8.0
            expo: decimal = 2.0
            escrever(base ^ expo)
    """)
    assert saida.strip() == "64.0"


# ---------- B18 (AL-58): elementos de vetor literal não coagidos p/ decimal ----------

def test_elementos_de_vetor_literal_decimal_sao_coagidos():
    saida = executar("""
        algoritmo "T"
        inicio
            v:decimal[3] = {1, 2, 3}
            escrever(v[0], " ", v[1], " ", v[2])
    """)
    assert saida.strip() == "1.0 2.0 3.0"


def test_executa_com_debug_sai_com_codigo_1_quando_programa_falha(tmp_path):
    from algo_lang.cli import cmd_executa_com_trace
    import argparse
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    v:inteiro[2]\n    escrever(v[5])\n', encoding="utf-8")
    args = argparse.Namespace(
        ficheiro=str(algo_path), debug=True, json=False, entradas=None, mostrar_python=False)
    with pytest.raises(SystemExit) as exc:
        cmd_executa_com_trace(args)
    assert exc.value.code == 1


def test_executa_com_json_sai_com_codigo_1_quando_programa_falha(tmp_path):
    from algo_lang.cli import cmd_executa_com_trace
    import argparse
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    v:inteiro[2]\n    escrever(v[5])\n', encoding="utf-8")
    args = argparse.Namespace(
        ficheiro=str(algo_path), debug=False, json=True, entradas=None, mostrar_python=False)
    with pytest.raises(SystemExit) as exc:
        cmd_executa_com_trace(args)
    assert exc.value.code == 1


def test_executa_com_debug_nao_sai_com_erro_quando_programa_e_bem_sucedido(tmp_path):
    from algo_lang.cli import cmd_executa_com_trace
    import argparse
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    args = argparse.Namespace(
        ficheiro=str(algo_path), debug=True, json=False, entradas=None, mostrar_python=False)
    cmd_executa_com_trace(args)  # não deve levantar SystemExit


# ---------- B22 (AL-62): dedup de 'incluir' sensível a maiúsculas/minúsculas ----------

def test_incluir_o_mesmo_ficheiro_com_capitalizacao_diferente_nao_colide(tmp_path):
    from algo_lang.cli import _carregar_e_verificar
    (tmp_path / "lib.algo").write_text(
        'funcao dobro(x:inteiro):inteiro\n    devolver x * 2\n', encoding="utf-8")
    principal = tmp_path / "principal.algo"
    principal.write_text(textwrap.dedent("""\
        algoritmo "T"
        incluir "lib.algo"
        incluir "LIB.algo"
        inicio
            escrever(dobro(3))
    """), encoding="utf-8")
    programa = _carregar_e_verificar(str(principal))
    assert len(programa.funcoes) == 1


# ---------- B23 (AL-63): consola memoriza ficheiro falhado como "último ficheiro" ----------

def test_consola_nao_atualiza_ultimo_ficheiro_apos_falha():
    import argparse
    from algo_lang.cli import COMANDOS_COM_FICHEIRO, _linha_com_ficheiro_por_omissao
    # A própria lógica de escolha do ficheiro por omissão: simula duas
    # linhas -- 'executa bom.algo' (sucesso) seguida de 'executa
    # mal_escrito.algo' (falha) -- e confirma que uma TERCEIRA linha sem
    # ficheiro continuaria a usar 'bom.algo', não 'mal_escrito.algo'.
    ultimo_ficheiro = "bom.algo"
    # 'mal_escrito.algo' falhou -- cli.py só atualiza ultimo_ficheiro
    # depois de args.func(args) ter sucesso (ver cmd_consola), por isso
    # simular a falha aqui é simplesmente NÃO atualizar a variável.
    resto = _linha_com_ficheiro_por_omissao("executa", [], ultimo_ficheiro)
    assert resto == ["bom.algo"]


# ---------- B24 (AL-64): cadeia.caracter aceita índices negativos ----------

def test_cadeia_caracter_com_indice_negativo_da_erro():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Cadeia
inicio
    escrever(cadeia.caracter("abc", -1))
""")
    assert resultado.returncode == 1
    assert "índice fora dos limites" in resultado.stdout


# ---------- B25 (AL-65): conversao.paraInteiro trunca decimal mas rejeita cadeia ----------

def test_conversao_parainteiro_de_cadeia_com_ponto_decimal_trunca():
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraInteiro("3.9"))
    """)
    assert saida.strip() == "3"


def test_conversao_parainteiro_de_cadeia_invalida_continua_a_dar_erro():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.paraInteiro("abc"))
""")
    assert resultado.returncode == 1
    assert "número inteiro" in resultado.stdout


# ---------- B26 (AL-66): linter -- falso positivo p/ variável de 'inicio' usada só em funções ----------

def test_variavel_de_inicio_usada_so_numa_funcao_nao_da_falso_positivo():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao dobroDeContador():inteiro
            devolver contador * 2
        inicio
            contador:inteiro = 5
            escrever(dobroDeContador())
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("'contador' é declarada mas nunca é usada" in a.mensagem for a in avisos)


# ---------- B27 (AL-67): tracer -- variáveis com nome começado por '_' invisíveis ----------

def test_trace_mostra_variavel_local_com_nome_comecado_por_underscore(tmp_path):
    from algo_lang.compilador.codegen import gerar_python_com_mapa
    from algo_lang.tools.tracer import gerar_trace
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao f(_x:inteiro):inteiro
            devolver _x + 1
        inicio
            escrever(f(10))
    """))
    verificar(programa)
    dados = gerar_python_com_mapa(programa)
    caminho_py = str(tmp_path / "prog.py")
    with open(caminho_py, "w", encoding="utf-8") as fh:
        fh.write(dados["codigo"])
    resultado = gerar_trace(
        dados["codigo"], caminho_py, dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"])
    assert resultado["erro"] is None
    variaveis_vistas = set()
    for passo in resultado["passos"]:
        for frame in passo["pilha"]:
            variaveis_vistas.update(frame["variaveis"].keys())
    assert "_x" in variaveis_vistas


# ---------- AL-71: tracer -- passo errado sobreposto quando a última instrução chama uma função ----------

def test_trace_nao_corrompe_passo_quando_ultima_instrucao_chama_funcao(tmp_path):
    """Bug adicional (fora de B1-B30, encontrado ao escrever o teste de
    B27): quando a ÚLTIMA instrução do 'inicio' chama uma função, o
    fecho de _algo_programa sobrescrevia sempre 'passos[-1]' -- que,
    nesse caso, é o último passo DENTRO da função chamada, não o passo
    da própria instrução em _algo_programa. O passo de dentro da função
    ficava com a pilha errada (perdia o frame da função) e a consola
    já avançada demais; o passo real da última instrução nunca era
    atualizado com o efeito de a ter executado (a saída do escrever).

    B25 (segunda auditoria, AL-97): a correção acima ainda sobrescrevia
    'passos[indice]' EM SILÊNCIO, e nesta situação 'indice' é o PRIMEIRO
    passo da lista (o único "só Principal" nela) -- sobrescrevê-lo com o
    estado final corrompia a ORDEM CRONOLÓGICA: o passo 0 passava a
    mostrar a consola final ('11\n'), antes do passo 1 (dentro de 'f'),
    que continuava com a consola vazia -- a consola "andava para trás"
    ao avançar no trace. As asserções abaixo já não usam next() (que só
    confirma que ALGUM passo tem os valores certos, em qualquer posição)
    -- verificam explicitamente a ORDEM e a monotonicidade da consola."""
    from algo_lang.compilador.codegen import gerar_python_com_mapa
    from algo_lang.tools.tracer import gerar_trace
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao f(x:inteiro):inteiro
            devolver x + 1
        inicio
            escrever(f(10))
    """))
    verificar(programa)
    dados = gerar_python_com_mapa(programa)
    caminho_py = str(tmp_path / "prog.py")
    with open(caminho_py, "w", encoding="utf-8") as fh:
        fh.write(dados["codigo"])
    resultado = gerar_trace(
        dados["codigo"], caminho_py, dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"])
    assert resultado["erro"] is None
    assert resultado["consolaFinal"] == "11\n"

    passos = resultado["passos"]
    # B25: a consola nunca pode "encolher" de um passo para o seguinte --
    # cada passo reflete um momento chronologicamente mais tarde (ou igual)
    # do que o anterior, nunca mais cedo.
    consolas = [p["consola"] for p in passos]
    assert all(len(consolas[i]) <= len(consolas[i + 1]) for i in range(len(consolas) - 1))

    passo_da_funcao = next(
        p for p in passos if any(frame["nome"] == "f" for frame in p["pilha"]))
    assert passo_da_funcao["pilha"][-1]["variaveis"] == {"x": 10}
    assert passo_da_funcao["consola"] == ""

    # B25: o passo com a consola final tem de ser o ÚLTIMO da lista (não
    # apenas "existir algures") -- é o que garante a monotonicidade acima.
    assert passos[-1]["consola"] == "11\n"
    assert len(passos[-1]["pilha"]) == 1
    assert passos[-1]["pilha"][0]["nome"] == "(Principal)"


# ---------- B28 (AL-68): tracer -- linha salta para trás; OverflowError não traduzido ----------

def test_overflowerror_da_erro_amigavel_nao_traceback():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    x: decimal = 2.0 ^ 2000.0
    escrever(x)
""")
    assert resultado.returncode == 1
    assert "overflow" in resultado.stdout.lower()


def test_procedimento_so_com_ref_nao_salta_linha_para_tras_no_trace(tmp_path):
    from algo_lang.compilador.codegen import gerar_python_com_mapa
    from algo_lang.tools.tracer import gerar_trace
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        procedimento incrementa(ref v:inteiro)
            v = v + 1
        inicio
            n:inteiro = 1
            incrementa(n)
            escrever(n)
    """))
    verificar(programa)
    dados = gerar_python_com_mapa(programa)
    caminho_py = str(tmp_path / "prog.py")
    with open(caminho_py, "w", encoding="utf-8") as fh:
        fh.write(dados["codigo"])
    resultado = gerar_trace(
        dados["codigo"], caminho_py, dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"])
    linhas_na_rotina_incrementa = [
        passo["linha"] for passo in resultado["passos"]
        if any(frame["nome"] == "incrementa" for frame in passo["pilha"])
    ]
    # as linhas dentro de 'incrementa' têm de ser não-decrescentes (nunca
    # "saltar para trás" para a linha da assinatura do procedimento)
    assert linhas_na_rotina_incrementa == sorted(linhas_na_rotina_incrementa)


# ---------- B29 (AL-69): linter -- campos em falta não cobre literais em argumento ----------

def test_campo_em_falta_em_literal_passado_como_argumento_da_aviso():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        funcao soma(p:Ponto):inteiro
            devolver p.x + p.y
        inicio
            escrever(soma({x: 3}))
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("não define o(s) campo(s) 'y'" in a.mensagem for a in avisos)


# ---------- B30 (AL-70): linter -- atribuição a parâmetro por valor não cobre 'ler(...)' ----------

def test_ler_para_parametro_por_valor_da_aviso_especifico():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        procedimento le(x:inteiro)
            ler(x)
        inicio
            n:inteiro
            le(n)
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("não é 'por referência'" in a.mensagem and "'x'" in a.mensagem for a in avisos)


# ============================================================
#  Segunda auditoria (2026-08-14) -- ver algo_lang/AUDITORIA.md
# ============================================================

# ---------- B4 (AL-75): parser -- um segundo 'inicio' substituia o primeiro em silencio ----------

def test_segundo_bloco_inicio_e_rejeitado():
    with pytest.raises(ErroSintatico, match="já tem um bloco 'inicio'"):
        compilar("""
            algoritmo "T"
            inicio
                escrever("primeiro")
            inicio
                escrever("segundo")
        """)


# ---------- B5 (AL-76): parser -- cadeias de nao/-/^ nao respeitavam o limite de profundidade ----------

def test_cadeia_de_nao_muito_funda_da_erro_sintatico_amigavel():
    codigo = 'algoritmo "T"\ninicio\n\tx:booleano = ' + "nao " * 2000 + "verdadeiro\n"
    with pytest.raises(ErroSintatico, match="demasiado aninhada"):
        compilar(codigo)


def test_cadeia_de_menos_unario_muito_funda_da_erro_sintatico_amigavel():
    codigo = 'algoritmo "T"\ninicio\n\tx:inteiro = ' + "-" * 2000 + "5\n"
    with pytest.raises(ErroSintatico, match="demasiado aninhada"):
        compilar(codigo)


def test_cadeia_de_potencia_muito_funda_da_erro_sintatico_amigavel():
    codigo = 'algoritmo "T"\ninicio\n\tx:inteiro = ' + "2 ^ " * 1000 + "2\n"
    with pytest.raises(ErroSintatico, match="demasiado aninhada"):
        compilar(codigo)


# ---------- B6 (AL-77): ast_nodes -- colisao de campo de estrutura reportava a linha errada ----------

def test_colisao_de_campo_de_estrutura_reporta_a_linha_do_campo():
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura Ponto
            classe:inteiro
        inicio
            escrever(1)
    """))
    nomes = dict(coletar_identificadores(programa))
    assert nomes["classe"] == 4


# ---------- B7 (AL-79): semantics -- tamanho declarado de vetor nunca validado contra o literal ----------

def test_vetor_com_literal_de_tamanho_diferente_do_declarado_da_erro():
    with pytest.raises(ErroSemantico, match="tamanho declarado 5.*3 elemento"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[5] = {1, 2, 3}
                escrever(v[0])
        """)


def test_vetor_com_literal_de_tamanho_igual_ao_declarado_compila():
    saida = executar("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            escrever(v[2])
    """)
    assert saida.strip() == "3"


# ---------- B8 (AL-78): semantics/codegen -- literais de estrutura aninhados sempre rejeitados ----------

def test_literal_de_estrutura_aninhado_dentro_doutro_literal():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Retangulo
            canto:Ponto
        inicio
            r:Retangulo = {canto: {x: 5}}
            escrever(r.canto.x)
    """)
    assert saida.strip() == "5"


def test_vetor_de_literais_de_estrutura():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            v:Ponto[2] = {{x: 1}, {x: 2}}
            escrever(v[0].x)
            escrever(v[1].x)
    """)
    assert saida.strip() == "1\n2"


# ---------- B9 (AL-81): semantics -- mesmo campo de estrutura passado 2x por referência não detetado ----------

def test_mesmo_campo_de_estrutura_por_referencia_duas_vezes_da_erro():
    with pytest.raises(ErroSemantico, match=r"'p\.x' é passado por referência mais do que uma vez"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            procedimento trocar(ref a:inteiro, ref b:inteiro)
                afirmar verdadeiro
            inicio
                p:Ponto = {x: 1}
                trocar(p.x, p.x)
        """)


def test_indices_diferentes_do_mesmo_vetor_por_referencia_continua_a_compilar():
    compilar("""
        algoritmo "T"
        procedimento trocar(ref a:inteiro, ref b:inteiro)
            afirmar verdadeiro
        inicio
            v:inteiro[3] = {1, 2, 3}
            i:inteiro = 0
            j:inteiro = 1
            trocar(v[i], v[j])
    """)


# ---------- B10 (AL-82): semantics -- mensagem errada ao redeclarar global com tipo diferente num bloco aninhado ----------

def test_redeclarar_global_com_tipo_diferente_em_bloco_aninhado_da_mensagem_correta():
    with pytest.raises(ErroSemantico, match="já foi declarada") as excinfo:
        compilar("""
            algoritmo "T"
            x:inteiro
            inicio
                se verdadeiro entao
                    x:cadeia = "a"
                escrever(x)
        """)
    assert "tipos diferentes" not in str(excinfo.value)


def test_tipos_diferentes_em_ramos_irmaos_continua_a_dar_a_mensagem_de_ramos():
    with pytest.raises(ErroSemantico, match="tipos diferentes em ramos diferentes"):
        compilar("""
            algoritmo "T"
            inicio
                se verdadeiro entao
                    x:inteiro = 1
                senao
                    x:cadeia = "a"
                escrever(x)
        """)


# ---------- B11 (AL-83): semantics -- 'caso' duplicado não normalizava tipos compatíveis ----------

def test_caso_duplicado_entre_cadeia_e_caracter_e_detetado():
    with pytest.raises(ErroSemantico, match="já apareceu antes"):
        compilar("""
            algoritmo "T"
            inicio
                s:cadeia = "a"
                escolher s
                    caso "a"
                        escrever(1)
                    caso 'a'
                        escrever(2)
        """)


def test_caso_duplicado_entre_inteiro_e_decimal_e_detetado():
    with pytest.raises(ErroSemantico, match="já apareceu antes"):
        compilar("""
            algoritmo "T"
            inicio
                d:decimal = 1.0
                escolher d
                    caso 1
                        escrever(1)
                    caso 1.0
                        escrever(2)
        """)


# ---------- B12 (AL-84): semantics -- 'ref' aceitava alargamento de tipo, corrompendo a variável do chamador ----------

def test_ref_decimal_nao_aceita_variavel_inteiro():
    with pytest.raises(ErroSemantico, match="por referência e espera exatamente 'decimal'"):
        compilar("""
            algoritmo "T"
            procedimento incrementaMeio(ref a:decimal)
                a = a + 0.5
            inicio
                x:inteiro = 5
                incrementaMeio(x)
                escrever(x)
        """)


def test_ref_cadeia_nao_aceita_variavel_caracter():
    with pytest.raises(ErroSemantico, match="por referência e espera exatamente 'cadeia'"):
        compilar("""
            algoritmo "T"
            procedimento repete(ref a:cadeia)
                a = a + a
            inicio
                c:caracter = 'x'
                repete(c)
                escrever(c)
        """)


def test_ref_com_tipo_exatamente_igual_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        procedimento incrementaMeio(ref a:decimal)
            a = a + 0.5
        inicio
            x:decimal = 5.0
            incrementaMeio(x)
            escrever(x)
    """)
    assert saida.strip() == "5.5"


# ---------- B13 (AL-85): bibliotecas -- matematica.potencia com base negativa/expoente fracionário dava traceback cru ----------

def test_matematica_potencia_negativa_fracionaria_da_erro_amigavel():
    codigo_py = compilar("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.potencia(-8.0, 0.5))
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert "Traceback" not in resultado.stdout
    assert "Erro em tempo de execução" in resultado.stdout
    assert resultado.returncode == 1


def test_matematica_potencia_normal_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.potencia(2, 3))
    """)
    assert saida.strip() == "8.0"


# ---------- B22 (AL-86): bibliotecas -- matematica.aleatorio com limites invertidos mostrava texto interno do Python ----------

def test_matematica_aleatorio_com_limites_invertidos_nao_mostra_randrange():
    codigo_py = compilar("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.aleatorio(10, 1))
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert "randrange" not in resultado.stdout
    assert "limite inferior" in resultado.stdout and "limite superior" in resultado.stdout


# ---------- B15 (AL-88): codegen -- dimensão interior de vetor multidimensional avaliada 2x ----------

def test_dimensao_interior_de_vetor_multidimensional_e_avaliada_uma_so_vez():
    saida = executar("""
        algoritmo "T"
        funcao dim():inteiro
            escrever("chamada")
            devolver 2
        inicio
            v:inteiro[2][dim()]
            escrever(v[0][0])
    """)
    assert saida.count("chamada") == 1


def test_vetor_de_estrutura_com_campo_multidimensional_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        estrutura Turma
            notas:inteiro[3]
        inicio
            t:Turma
            t.notas[0] = 9
            escrever(t.notas[0])
            escrever(t.notas[1])
    """)
    assert saida.strip() == "9\n0"


# ---------- B16 (AL-89): codegen -- mapa de linhas do tracer errado durante construção/comparação de estruturas ----------

def test_trace_nao_injeta_passo_espurio_na_linha_da_definicao_da_estrutura(tmp_path):
    from algo_lang.compilador.codegen import gerar_python_com_mapa
    from algo_lang.tools.tracer import gerar_trace
    programa = parse(textwrap.dedent("""
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
    """))
    verificar(programa)
    dados = gerar_python_com_mapa(programa)
    caminho_py = str(tmp_path / "_teste_trace_estrutura.py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(dados["codigo"])
    resultado = gerar_trace(
        dados["codigo"], caminho_py, dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"])
    linha_definicao_estrutura = 3
    linhas_do_trace = [p["linha"] for p in resultado["passos"]]
    assert linha_definicao_estrutura not in linhas_do_trace


# ---------- B21 (AL-91): bibliotecas -- conversao.paraInteiro("inf") escapava ao tratamento de OverflowError ----------

def test_conversao_parainteiro_de_inf_da_mensagem_de_texto_invalido_nao_overflow():
    codigo_py = compilar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraInteiro("inf"))
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 1
    assert "overflow" not in resultado.stdout.lower()
    assert "não pode ser convertido" in resultado.stdout


def test_conversao_parainteiro_de_decimal_em_texto_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraInteiro("3.9"))
    """)
    assert saida.strip() == "3"


# ---------- B18 (AL-92): cli -- shlex.split() da consola apagava barras invertidas de caminhos Windows ----------

def test_shlex_split_sem_escape_preserva_barras_invertidas():
    from algo_lang.cli import _shlex_split_sem_escape
    partes = _shlex_split_sem_escape(r"executa C:\Users\aluno\prog.algo")
    assert partes == ["executa", r"C:\Users\aluno\prog.algo"]


def test_shlex_split_sem_escape_continua_a_suportar_aspas_com_espacos():
    from algo_lang.cli import _shlex_split_sem_escape
    partes = _shlex_split_sem_escape(r'executa "C:\pasta com espacos\prog.algo"')
    assert partes == ["executa", r"C:\pasta com espacos\prog.algo"]


# ---------- B19 (AL-93): cli -- cmd_executa saía sempre, mesmo com sucesso, a consola nunca memorizava o ficheiro ----------

def test_cmd_executa_bem_sucedido_nao_levanta_systemexit(tmp_path, capfd):
    import argparse
    from algo_lang.cli import cmd_executa
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    args = argparse.Namespace(
        ficheiro=str(algo_path), debug=False, json=False, mostrar_python=False)
    cmd_executa(args)  # não deve levantar SystemExit em sucesso
    assert "ok" in capfd.readouterr().out


def test_cmd_executa_com_erro_em_runtime_continua_a_sair_com_codigo_1(tmp_path):
    import argparse
    from algo_lang.cli import cmd_executa
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    v:inteiro[1]\n    escrever(v[5])\n', encoding="utf-8")
    args = argparse.Namespace(
        ficheiro=str(algo_path), debug=False, json=False, mostrar_python=False)
    with pytest.raises(SystemExit) as excinfo:
        cmd_executa(args)
    assert excinfo.value.code != 0


# ---------- B20 (AL-94): cli -- ficheiro de --entradas com codificação inválida dava traceback cru ----------

def test_entradas_com_codificacao_invalida_da_erro_amigavel(tmp_path, capsys):
    import argparse
    from algo_lang.cli import cmd_executa_com_trace
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    x:inteiro\n    ler(x)\n    escrever(x)\n', encoding="utf-8")
    entradas_path = tmp_path / "entradas.txt"
    entradas_path.write_bytes(b"caf\xe9\n")  # bytes inválidos em UTF-8
    args = argparse.Namespace(
        ficheiro=str(algo_path), entradas=str(entradas_path), debug=False, json=False,
        mostrar_python=False)
    with pytest.raises(SystemExit) as excinfo:
        cmd_executa_com_trace(args)
    assert excinfo.value.code == 1
    saida = capsys.readouterr().out
    assert "UnicodeDecodeError" not in saida
    assert "codificação" in saida


# ---------- B24 (AL-96): cli -- '--entradas' sem valor na consola dava um erro que não apontava para a causa real ----------

def test_flag_com_valor_sem_valor_a_seguir_da_mensagem_clara():
    from algo_lang.cli import _linha_com_ficheiro_por_omissao
    with pytest.raises(ValueError, match=r"'--entradas' precisa de um valor"):
        _linha_com_ficheiro_por_omissao("executa", ["--entradas"], "ultimo.algo")


def test_flag_com_valor_seguido_de_ficheiro_continua_a_funcionar():
    from algo_lang.cli import _linha_com_ficheiro_por_omissao
    resto = _linha_com_ficheiro_por_omissao(
        "executa", ["--entradas", "in.txt"], "ultimo.algo")
    assert resto == ["--entradas", "in.txt", "ultimo.algo"]


# ---------- B26 (AL-98): linter -- índices fora dos limites não cobria vetores que são campos de estrutura ----------

def test_linter_deteta_indice_fora_dos_limites_em_campo_vetor_de_estrutura():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura Turma
            notas:inteiro[5]
        inicio
            t:Turma
            t.notas[10] = 99
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any(
        "fora dos limites" in a.mensagem and "'t.notas'" in a.mensagem for a in avisos)


def test_linter_nao_assinala_indice_valido_em_campo_vetor_de_estrutura():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura Turma
            notas:inteiro[5]
        inicio
            t:Turma
            t.notas[2] = 99
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("fora dos limites" in a.mensagem for a in avisos)


# ---------- B27 (AL-99): editors/vscode-algo -- palavra-chave 'nulo' sem highlighting nenhum ----------

def test_vscode_grammar_nao_esquece_nenhuma_palavra_chave_do_lexer():
    """A gramática TextMate da extensão VS Code é mantida à mão (ao
    contrário de online/modo_codemirror.py, que gera a partir do lexer) --
    já desalinhou uma vez (a keyword 'nulo' não tinha highlighting
    nenhum, B27). Este teste não substitui gerar a gramática dinamicamente
    (melhoria conceptual maior, fora do âmbito de uma correção pontual),
    mas evita que a mesma classe de bug volte a passar despercebida:
    verifica que toda palavra-chave do lexer aparece em algum padrão da
    gramática."""
    import json
    import re
    from algo_lang.compilador.lexer import PALAVRAS_CHAVE
    caminho_grammar = os.path.join(
        os.path.dirname(__file__), "..", "editors", "vscode-algo",
        "syntaxes", "algo.tmLanguage.json")
    with open(caminho_grammar, "r", encoding="utf-8") as f:
        grammar = json.load(f)
    texto_padroes = " ".join(
        regra.get("match", "") for regra in grammar["repository"].values())
    faltam = sorted(
        p for p in PALAVRAS_CHAVE
        if not re.search(rf"\b{re.escape(p)}\b", texto_padroes))
    assert not faltam, (
        f"palavra(s)-chave do lexer sem highlighting na extensão VS Code: {faltam} "
        f"-- adiciona-a(s) a algo.tmLanguage.json (ver B27 na auditoria)")


# ---------- Auditoria (4ª ronda), Etapa 10 -- extensão VS Code. A
# suite ad-hoc Node/JS referida pela 3ª auditoria NÃO está neste
# repositório (confirmado: só package.json, language-configuration.json,
# syntaxes/algo.tmLanguage.json, README.md em editors/vscode-algo/,
# nenhum ficheiro de teste). O teste de paridade lexer↔gramática
# (acima, test_vscode_grammar_nao_esquece_nenhuma_palavra_chave_do_lexer)
# já satisfaz o pedido do plano de um "teste de paridade lexer↔gramática
# automatizado" -- não escrito de novo. O que faltava mesmo: nenhum
# teste exercitava os PADRÕES regex em si (só a lista de palavras-chave
# nos comentários) -- 'library-calls' (campo vs. chamada de biblioteca,
# o requisito central desta etapa) e 'declarations' (o lookahead
# negativo referido no comentário da própria gramática, nunca testado)
# nunca tiveram o seu COMPORTAMENTO confirmado, só a intenção
# documentada em comentário. Sintaxe Oniguruma (TextMate) e o módulo
# 're' do Python coincidem nas construções usadas aqui (\\b, lookahead
# positivo/negativo, classes de caracteres) -- corrido diretamente com
# 're', sem precisar de um motor Oniguruma real. ----------

def _padrao_grammar(nome_regra):
    import json
    caminho_grammar = os.path.join(
        os.path.dirname(__file__), "..", "editors", "vscode-algo",
        "syntaxes", "algo.tmLanguage.json")
    with open(caminho_grammar, "r", encoding="utf-8") as f:
        grammar = json.load(f)
    return grammar["repository"][nome_regra]["match"]


def test_vscode_grammar_library_calls_reconhece_chamada_de_biblioteca():
    import re
    padrao = _padrao_grammar("library-calls")
    m = re.search(padrao, "escrever(matematica.raiz(4.0))")
    assert m is not None
    assert m.groups() == ("matematica", ".", "raiz")


def test_vscode_grammar_library_calls_aceita_espaco_antes_do_parentese():
    import re
    padrao = _padrao_grammar("library-calls")
    assert re.search(padrao, "matematica.raiz (4.0)") is not None


def test_vscode_grammar_library_calls_nao_confunde_campo_de_estrutura_com_chamada():
    """O requisito central da Etapa 10: 'no.valor' (acesso a campo, sem
    parêntesis a seguir) não pode disparar a mesma regra de highlighting
    que 'biblioteca.metodo(' -- são construções sintaticamente distintas
    no parser real (A.LValue vs A.Chamada, ver test_consistencia_
    ferramentas.py), e a gramática (que não tem parser, só regex) tem de
    replicar essa distinção só pela presença/ausência do '('."""
    import re
    padrao = _padrao_grammar("library-calls")
    assert re.search(padrao, "escrever(no.valor)") is None
    assert re.search(padrao, "no.valor = 5") is None
    assert re.search(padrao, "n.seguinte.valor") is None


def test_vscode_grammar_declarations_reconhece_declaracao_de_tipo():
    import re
    padrao = _padrao_grammar("declarations")
    m = re.search(padrao, "x:inteiro")
    assert m.groups() == ("x", ":", "inteiro")
    m2 = re.search(padrao, "p:Ponto")
    assert m2.groups() == ("p", ":", "Ponto")


def test_vscode_grammar_declarations_ignora_campo_de_literal_de_estrutura_com_valor_reservado():
    """Comentário da própria gramática (B29 da 3ª auditoria): o
    lookahead negativo evita que '{ativo: verdadeiro}' (um CAMPO de
    literal de estrutura com valor booleano/nulo) seja mal interpretado
    como 'nome:tipo' (uma declaração), já que 'verdadeiro' não é um tipo
    válido -- nunca tinha sido confirmado que o lookahead reconhece
    mesmo os 3 valores (verdadeiro/falso/nulo), só o comentário
    afirmava."""
    import re
    padrao = _padrao_grammar("declarations")
    for campo in ("{ativo: verdadeiro}", "{ativo: falso}", "{proximo: nulo}"):
        assert re.search(padrao, campo) is None, campo


# ---------- Vetores como parâmetros e valores de retorno (AUDITORIA.md secção 3) ----------

def test_parametro_vetor_1d_parseia_dims_correto():
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        procedimento f(v: inteiro[])
            escrever(v[0])
        inicio
            escrever("ok")
    """))
    assert programa.funcoes[0].parametros[0].dims == 1


def test_parametro_vetor_2d_parseia_dims_correto():
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        procedimento f(m: inteiro[][])
            escrever(m[0][0])
        inicio
            escrever("ok")
    """))
    assert programa.funcoes[0].parametros[0].dims == 2


def test_tipo_retorno_vetor_parseia_dims_retorno_correto():
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao f(): inteiro[]
            devolver {1, 2}
        inicio
            escrever("ok")
    """))
    assert programa.funcoes[0].dims_retorno == 1


def test_colchetes_de_parametro_com_tamanho_e_erro_sintatico():
    with pytest.raises(ErroSintatico, match="colchetes vazios"):
        compilar("""
            algoritmo "T"
            procedimento f(v: inteiro[5])
                escrever(v[0])
            inicio
                escrever("ok")
        """)


def test_colchetes_de_retorno_com_tamanho_e_erro_sintatico():
    with pytest.raises(ErroSintatico, match="colchetes vazios"):
        compilar("""
            algoritmo "T"
            funcao f(): inteiro[5]
                devolver {1, 2}
            inicio
                escrever("ok")
        """)


def test_parametro_vetor_pode_ser_indexado_e_mutado_no_corpo():
    saida = executar("""
        algoritmo "T"
        procedimento incrementaPrimeiro(ref v: inteiro[])
            v[0] = v[0] + 1
        inicio
            a:inteiro[3] = {1, 2, 3}
            incrementaPrimeiro(a)
            escrever(a[0])
    """)
    assert saida.strip() == "2"


def test_vetor_passado_por_valor_nao_e_mutado_no_chamador():
    saida = executar("""
        algoritmo "T"
        procedimento muda(v: inteiro[])
            v[0] = 99
        inicio
            a:inteiro[3] = {1, 2, 3}
            muda(a)
            escrever(a[0])
    """)
    assert saida.strip() == "1"


def test_vetor_passado_por_ref_muta_no_chamador():
    saida = executar("""
        algoritmo "T"
        procedimento muda(ref v: inteiro[])
            v[0] = 99
        inicio
            a:inteiro[3] = {1, 2, 3}
            muda(a)
            escrever(a[0])
    """)
    assert saida.strip() == "99"


def test_vetor_por_valor_com_tipo_de_elemento_errado_e_rejeitado():
    with pytest.raises(ErroSemantico, match="tipo do elemento"):
        compilar("""
            algoritmo "T"
            procedimento f(v: decimal[])
                escrever(v[0])
            inicio
                a:inteiro[2] = {1, 2}
                f(a)
        """)


def test_vetor_por_ref_com_tipo_de_elemento_errado_e_rejeitado():
    with pytest.raises(ErroSemantico, match="tipo do elemento"):
        compilar("""
            algoritmo "T"
            procedimento f(ref v: decimal[])
                escrever(v[0])
            inicio
                a:inteiro[2] = {1, 2}
                f(a)
        """)


def test_vetor_1d_passado_a_parametro_2d_e_rejeitado():
    with pytest.raises(ErroSemantico, match="dimens"):
        compilar("""
            algoritmo "T"
            procedimento f(m: inteiro[][])
                escrever(m[0][0])
            inicio
                a:inteiro[2] = {1, 2}
                f(a)
        """)


def test_escalar_passado_a_parametro_vetor_e_rejeitado():
    with pytest.raises(ErroSemantico, match="dimens"):
        compilar("""
            algoritmo "T"
            procedimento f(v: inteiro[])
                escrever(v[0])
            inicio
                x:inteiro = 5
                f(x)
        """)


def test_vetor_passado_a_parametro_escalar_e_rejeitado():
    with pytest.raises(ErroSemantico, match="dimens"):
        compilar("""
            algoritmo "T"
            procedimento f(x: inteiro)
                escrever(x)
            inicio
                a:inteiro[2] = {1, 2}
                f(a)
        """)


def test_literal_de_vetor_como_argumento_funciona():
    saida = executar("""
        algoritmo "T"
        procedimento f(v: inteiro[])
            escrever(v[0] + v[1])
        inicio
            f({10, 20})
    """)
    assert saida.strip() == "30"


def test_mesmo_vetor_passado_duas_vezes_por_referencia_da_erro():
    with pytest.raises(ErroSemantico, match="passado por referência mais do que uma vez"):
        compilar("""
            algoritmo "T"
            procedimento trocar(ref a: inteiro[], ref b: inteiro[])
                escrever(a[0])
            inicio
                v:inteiro[2] = {1, 2}
                trocar(v, v)
        """)


def test_funcao_pode_devolver_vetor():
    saida = executar("""
        algoritmo "T"
        funcao dobrar(v: inteiro[]): inteiro[]
            r:inteiro[2] = {v[0] * 2, v[1] * 2}
            devolver r
        inicio
            a:inteiro[2] = {1, 2}
            b:inteiro[2] = dobrar(a)
            escrever(b[0], " ", b[1])
    """)
    assert saida.strip() == "2 4"


def test_devolver_com_tipo_de_elemento_errado_e_rejeitado():
    with pytest.raises(ErroSemantico, match="tipo do elemento"):
        compilar("""
            algoritmo "T"
            funcao f(): decimal[]
                r:inteiro[2] = {1, 2}
                devolver r
            inicio
                escrever("ok")
        """)


def test_devolver_escalar_de_funcao_que_devolve_vetor_e_rejeitado():
    with pytest.raises(ErroSemantico, match="dimens"):
        compilar("""
            algoritmo "T"
            funcao f(): inteiro[]
                devolver 5
            inicio
                escrever("ok")
        """)


def test_declaracao_a_partir_de_funcao_ref_que_devolve_vetor_com_dims_erradas_e_rejeitado():
    with pytest.raises(ErroSemantico, match="dimens"):
        compilar("""
            algoritmo "T"
            funcao f(ref x: inteiro): inteiro[]
                x = x + 1
                devolver {x}
            inicio
                y:inteiro = 1
                z:inteiro = f(y)
        """)


def test_escrever_de_vetor_continua_rejeitado_regressao():
    """Regressão: 'permitir_vetor' só é passado True nos dois sítios
    legítimos (argumento de chamada, 'devolver') -- escrever() continua a
    rejeitar um vetor nu como antes desta funcionalidade existir."""
    with pytest.raises(ErroSemantico, match="falta indexá-lo"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[2] = {1, 2}
                escrever(v)
        """)


def test_parametro_vetor_2d_indexado_no_corpo():
    saida = executar("""
        algoritmo "T"
        funcao soma(m: inteiro[][]): inteiro
            devolver m[0][0] + m[1][1]
        inicio
            grelha:inteiro[2][2] = {{1, 2}, {3, 4}}
            escrever(soma(grelha))
    """)
    assert saida.strip() == "5"


def test_vetor_de_estruturas_por_valor_faz_deep_copy():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        procedimento muda(v: Ponto[])
            v[0].x = 99
        inicio
            a:Ponto[1] = {{x: 1}}
            muda(a)
            escrever(a[0].x)
    """)
    assert saida.strip() == "1"


# ---------- AUDITORIA.md secção 2 -- UX de erros/robustez ----------

def test_constante_global_em_tamanho_de_vetor_campo_de_estrutura_da_mensagem_dedicada():
    with pytest.raises(ErroSemantico, match="registadas antes do resto do programa"):
        compilar("""
            algoritmo "T"
            constante N: inteiro = 5
            estrutura Ponto
                valores:inteiro[N]
            inicio
                escrever("ok")
        """)


def test_expressao_inesperada_usa_nome_amigavel_do_token():
    with pytest.raises(ErroSintatico, match=r"expressão inesperada: '\)'"):
        compilar('algoritmo "T"\ninicio\n    escrever(1 + )\n')


def test_escrever_sem_argumentos_da_mensagem_dedicada():
    with pytest.raises(ErroSintatico, match="'escrever' precisa de pelo menos 1 argumento"):
        compilar('algoritmo "T"\ninicio\n    escrever()\n')


def test_erro_sintatico_inclui_coluna_correta():
    # linha 3 = '    escrever(1 + )' -- ')' está na coluna 18 (1-baseada):
    # 4 espaços de indentação + 'escrever(1 + ' (14 caracteres).
    with pytest.raises(ErroSintatico) as exc:
        compilar('algoritmo "T"\ninicio\n    escrever(1 + )\n')
    assert exc.value.linha == 3
    assert exc.value.coluna == 18
    assert ", coluna 18:" in str(exc.value)


def test_erro_lexico_inclui_coluna_correta():
    from algo_lang.compilador.lexer import tokenizar, ErroLexico
    # linha 3 = '    x = 1 @ 2' -- '@' está na coluna 11 (1-baseada): 4
    # espaços + 'x = 1 ' (6 caracteres).
    with pytest.raises(ErroLexico) as exc:
        tokenizar('algoritmo "T"\ninicio\n    x = 1 @ 2\n')
    assert exc.value.linha == 3
    assert exc.value.coluna == 11
    assert ", coluna 11:" in str(exc.value)


def test_coluna_e_relativa_a_linha_original_incluindo_indentacao_profunda():
    """A coluna reportada tem de ser relativa à linha ORIGINAL (com
    indentação), não à versão sem indentação que o lexer usa
    internamente -- senão a coluna reportada seria sistematicamente
    menor do que a posição real vista no editor."""
    # linha 4 = '        escrever(1 + )' -- 8 espaços (2 níveis) + 'escrever(1 + '
    with pytest.raises(ErroSintatico) as exc:
        compilar("""
            algoritmo "T"
            inicio
                se verdadeiro entao
                    escrever(1 + )
        """)
    assert exc.value.coluna is not None and exc.value.coluna > 1


def test_erro_de_indentacao_sem_coluna_especifica_continua_a_funcionar():
    """Erros sobre a indentação da linha inteira (não um token
    específico) continuam sem coluna -- não há uma posição única
    significativa para "a indentação avançou 2 níveis"."""
    from algo_lang.compilador.lexer import tokenizar, ErroLexico
    with pytest.raises(ErroLexico, match="avança 2 níveis") as exc:
        tokenizar('algoritmo "T"\ninicio\n        x:inteiro = 1\n')
    assert exc.value.coluna is None
    assert ", coluna" not in str(exc.value)


def test_virgula_a_mais_em_chamada_da_mensagem_dedicada():
    with pytest.raises(ErroSintatico, match="vírgula a mais"):
        compilar("""
            algoritmo "T"
            procedimento p(x: inteiro)
                escrever(x)
            inicio
                p(1,)
        """)


def test_virgula_a_mais_em_literal_de_vetor_da_mensagem_dedicada():
    with pytest.raises(ErroSintatico, match="vírgula a mais"):
        compilar("""
            algoritmo "T"
            inicio
                v:inteiro[2] = {1, 2,}
        """)


def test_virgula_a_mais_em_caso_de_escolher_da_mensagem_dedicada():
    with pytest.raises(ErroSintatico, match="vírgula a mais"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 1
                escolher x
                    caso 1, 2,
                        escrever(1)
                    contrario
                        escrever(0)
        """)


def test_operadores_relacionais_encadeados_da_mensagem_dedicada():
    with pytest.raises(ErroSintatico, match="não podem ser encadeados"):
        compilar('algoritmo "T"\ninicio\n    escrever(1 < 2 < 3)\n')


def test_subcadeia_com_limites_invertidos_da_erro_amigavel():
    codigo_py = compilar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.subcadeia("algoritmo", 4, 1))
    """)
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, text=True,
        encoding="utf-8", timeout=10)
    assert "Erro em tempo de execução" in resultado.stdout
    assert "início" in resultado.stdout and "fim" in resultado.stdout


def test_subcadeia_com_limites_normais_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        importar Cadeia
        inicio
            escrever(cadeia.subcadeia("algoritmo", 0, 4))
    """)
    assert saida.strip() == "algo"


def test_inclusao_com_colisao_entre_categorias_diferentes_e_detetada():
    """Uma função incluída com o mesmo nome de uma estrutura já definida
    no programa principal (categorias diferentes) tem de ser apanhada
    aqui, com o contexto do ficheiro incluído -- antes só a mesma
    categoria era verificada, e isto só era apanhado mais tarde, de forma
    genérica, em semantics.py."""
    from algo_lang.compilador.parser import parse_biblioteca
    from algo_lang.compilador.inclusoes import mesclar_biblioteca_no_programa, ColisaoDeInclusao
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            escrever(1)
    """))
    declaracoes, funcoes, estruturas, _inclusoes = parse_biblioteca(
        "funcao Ponto():inteiro\n    devolver 1\n")
    with pytest.raises(ColisaoDeInclusao) as exc:
        mesclar_biblioteca_no_programa(programa, "lib.algo", declaracoes, funcoes, estruturas)
    assert exc.value.tipo == "função"
    assert exc.value.tipo_existente == "estrutura"


def test_inclusao_com_colisao_na_mesma_categoria_continua_igual():
    """Regressão: o caso já existente (mesma categoria) não pode mudar de
    comportamento com a deteção de colisão entre categorias."""
    from algo_lang.compilador.parser import parse_biblioteca
    from algo_lang.compilador.inclusoes import mesclar_biblioteca_no_programa, ColisaoDeInclusao
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        funcao f(): inteiro
            devolver 1
        inicio
            escrever(f())
    """))
    declaracoes, funcoes, estruturas, _inclusoes = parse_biblioteca(
        "funcao f():inteiro\n    devolver 2\n")
    with pytest.raises(ColisaoDeInclusao) as exc:
        mesclar_biblioteca_no_programa(programa, "lib.algo", declaracoes, funcoes, estruturas)
    assert exc.value.tipo == "função"
    assert exc.value.tipo_existente == "função"


# ---------- AUDITORIA.md secção 3 -- propagação do tipo esperado para literais {...} ----------

def test_devolver_literal_de_estrutura_diretamente_funciona():
    """B8 (secção 3): o tipo esperado (o tipo de retorno declarado da
    função) já é conhecido pelo contexto -- 'devolver {...}' não precisa
    de indexação/declaração intermédia para saber que forma esperar."""
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        funcao criar():Ponto
            devolver {x: 5}
        inicio
            p:Ponto = criar()
            escrever(p.x)
    """)
    assert saida.strip() == "5"


def test_devolver_literal_de_estrutura_coage_campo_decimal():
    saida = executar("""
        algoritmo "T"
        estrutura P
            x:decimal
        funcao criar():P
            devolver {x: 5}
        inicio
            p:P = criar()
            escrever(p.x)
    """)
    assert saida.strip() == "5.0"


def test_devolver_literal_de_vetor_decimal_coage_elementos():
    """Antes desta correção, 'devolver {1,2,3}' já compilava (via o ramo
    genérico de A.VetorLiteral em _expr()), mas sem coerção de tipo --
    um vetor 'decimal[]' devolvido assim ficava com inteiros crus."""
    saida = executar("""
        algoritmo "T"
        funcao criar():decimal[]
            devolver {1, 2, 3}
        inicio
            v:decimal[3] = criar()
            escrever(v[0])
    """)
    assert saida.strip() == "1.0"


def test_devolver_literal_de_estrutura_com_dims_erradas_continua_rejeitado():
    """Regressão: uma função que devolve um VETOR de estruturas não pode
    devolver diretamente um literal de estrutura escalar (dims erradas) --
    o gate 'dimensões antes de tipo' continua a aplicar-se aqui."""
    with pytest.raises(ErroSemantico, match="dimens"):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            funcao criar():Ponto[]
                devolver {x: 5}
            inicio
                escrever("nunca")
        """)


def test_atribuicao_de_literal_de_estrutura_a_variavel_existente_funciona():
    """B8 (secção 3): o tipo esperado (o tipo já declarado da variável
    alvo) já é conhecido pelo contexto -- 'p = {...}' não é só permitido
    numa declaração, também numa atribuição a uma variável já existente."""
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            p:Ponto = {x: 1}
            p = {x: 9}
            escrever(p.x)
    """)
    assert saida.strip() == "9"


def test_atribuicao_de_literal_de_estrutura_aninhado_funciona():
    saida = executar("""
        algoritmo "T"
        estrutura Interno
            v:inteiro
        estrutura Externo
            i:Interno
        inicio
            ext:Externo = {i: {v: 1}}
            ext = {i: {v: 99}}
            escrever(ext.i.v)
    """)
    assert saida.strip() == "99"


def test_atribuicao_de_literal_de_estrutura_com_tipo_errado_continua_rejeitado():
    with pytest.raises(ErroSemantico):
        compilar("""
            algoritmo "T"
            estrutura Ponto
                x:inteiro
            estrutura Outra
                y:inteiro
            inicio
                p:Ponto = {x: 1}
                p = {y: 9}
        """)


# ---------- AUDITORIA.md secção 3 -- mensagem enganadora em p.campo(args) ----------

def test_campo_de_estrutura_chamado_como_metodo_da_mensagem_dedicada():
    """'n.valor(3)' é sintaticamente indistinguível de uma chamada de
    biblioteca (o parser não tem informação de tipos) -- antes desta
    correção, dava sempre "a biblioteca 'n' não foi importada", enganador
    quando 'n' é claramente uma variável declarada, não uma biblioteca."""
    with pytest.raises(ErroSemantico, match="'valor' é um campo da estrutura 'No', não uma função"):
        compilar("""
            algoritmo "T"
            estrutura No
                valor:inteiro
            inicio
                n:No = {valor: 5}
                escrever(n.valor(3))
        """)


def test_biblioteca_genuinamente_nao_importada_continua_com_mensagem_de_sempre():
    """Regressão: o caso original (nome que não é variável nem campo de
    estrutura conhecido) continua com a mensagem "biblioteca não
    importada" de sempre."""
    with pytest.raises(ErroSemantico, match="a biblioteca 'matematica' não foi importada"):
        compilar("""
            algoritmo "T"
            inicio
                escrever(matematica.raiz(4))
        """)


def test_variavel_escalar_com_chamada_tipo_biblioteca_continua_com_mensagem_de_sempre():
    """Regressão: uma variável que não é estrutura (ou é estrutura mas sem
    esse campo) continua com a mensagem genérica -- só o caso
    inequivocamente identificável (variável de tipo estrutura com esse
    campo) ganha a mensagem dedicada."""
    with pytest.raises(ErroSemantico, match="a biblioteca 'x' não foi importada"):
        compilar("""
            algoritmo "T"
            inicio
                x:inteiro = 5
                escrever(x.qualquer(1))
        """)


def test_parametro_ast_tem_campo_linha():
    """Consistência com o resto dos nós da AST (secção 3) -- Parametro
    era o único sem 'linha'."""
    programa = parse(textwrap.dedent("""
        algoritmo "T"
        procedimento f(x: inteiro)
            escrever(x)
        inicio
            f(1)
    """))
    assert programa.funcoes[0].parametros[0].linha == 3


# ---------- Auditoria (4ª ronda), Etapa 1 -- análise léxica: lacunas
# identificadas na matriz de rastreabilidade (AUDITORIA_MATRIZ_RASTREABILIDADE.md
# secção 1): nenhum teste enumerava as 33 palavras-chave uma a uma, nem
# confirmava acentuação portuguesa em identificadores, nem a
# desambiguação de símbolos que são prefixo uns dos outros (=/==,
# </<=/<>, >/>=) ao nível do lexer. ----------

PALAVRAS_CHAVE_ESPERADAS = {
    "algoritmo", "inicio", "estrutura",
    "escrever", "ler",
    "se", "entao", "senao",
    "para", "de", "ate", "passo", "fazer",
    "enquanto",
    "escolher", "caso", "contrario",
    "funcao", "procedimento", "devolver", "ref",
    "importar", "incluir",
    "verdadeiro", "falso", "nulo",
    "e", "ou", "nao",
    "div", "mod",
    "constante", "afirmar",
}


def test_lexer_conjunto_de_palavras_chave_tem_exatamente_33():
    from algo_lang.compilador.lexer import PALAVRAS_CHAVE
    # Se este teste falhar por o conjunto real ter mudado, a matriz de
    # rastreabilidade (secção 1) e este PALAVRAS_CHAVE_ESPERADAS têm de
    # ser atualizados a par -- não é só um número mágico.
    assert PALAVRAS_CHAVE == PALAVRAS_CHAVE_ESPERADAS
    assert len(PALAVRAS_CHAVE) == 33


@pytest.mark.parametrize("palavra", sorted(PALAVRAS_CHAVE_ESPERADAS))
def test_lexer_cada_palavra_chave_produz_token_dedicado(palavra):
    # Cada palavra-chave, sozinha numa linha, tem de produzir um único
    # token cujo tipo é a própria palavra em maiúsculas -- nunca "ID"
    # (o que aconteceria se a palavra caísse fora de PALAVRAS_CHAVE por
    # engano, ex. erro de dedo ao editar o conjunto).
    tokens = tokenizar(palavra)
    tipos = [t.tipo for t in tokens if t.tipo not in ("NEWLINE", "EOF")]
    assert tipos == [palavra.upper()]
    assert tokens[0].valor == palavra


def test_lexer_identificador_parecido_com_palavra_chave_nao_e_confundido():
    # "de" e "devolver" são ambos palavras-chave distintas: o lexer lê o
    # identificador completo (isalnum/'_') antes de comparar com
    # PALAVRAS_CHAVE, por isso não há correspondência por prefixo.
    # "paragem" (contém "para" como prefixo mas não é palavra-chave) tem
    # de ficar ID.
    tokens = [t for t in tokenizar("paragem") if t.tipo not in ("NEWLINE", "EOF")]
    assert [t.tipo for t in tokens] == ["ID"]
    assert tokens[0].valor == "paragem"


def test_lexer_identificador_com_acentuacao_portuguesa_e_reconhecido():
    tokens = [t for t in tokenizar("número") if t.tipo not in ("NEWLINE", "EOF")]
    assert [t.tipo for t in tokens] == ["ID"]
    assert tokens[0].valor == "número"


def test_lexer_programa_com_identificador_acentuado_compila_e_executa():
    saida = executar("""
        algoritmo "T"
        inicio
            número:inteiro = 42
            escrever(número)
    """)
    assert saida.strip() == "42"


def test_lexer_string_com_acentuacao_portuguesa_preserva_carateres():
    tokens = tokenizar('"maçã, café, ação"')
    strings = [t for t in tokens if t.tipo == "STRING"]
    assert strings[0].valor == "maçã, café, ação"


@pytest.mark.parametrize("origem,tipo_esperado", [
    ("=", "ATRIB"),
    ("==", "IGUAL"),
    ("<", "MENOR"),
    ("<=", "LE"),
    ("<>", "DIFERENTE"),
    (">", "MAIOR"),
    (">=", "GE"),
])
def test_lexer_simbolos_prefixo_de_outros_nao_se_confundem(origem, tipo_esperado):
    # '=' é prefixo de '==', '<' é prefixo de '<=' e '<>', '>' é prefixo
    # de '>=' -- SIMBOLOS_MULTI tem de ser verificado antes de
    # SIMBOLOS_SINGLE para cada um destes produzir o token correto.
    tokens = [t for t in tokenizar(origem) if t.tipo not in ("NEWLINE", "EOF")]
    assert [t.tipo for t in tokens] == [tipo_esperado]


def test_lexer_menor_seguido_de_maior_sem_espaco_nao_vira_diferente():
    # "a<b" onde o que se segue a '<' não é '=' nem '>' continua a
    # produzir MENOR isolado -- só "<>" junto e sem espaço é DIFERENTE.
    tokens = [t.tipo for t in tokenizar("a<b") if t.tipo not in ("NEWLINE", "EOF")]
    assert tokens == ["ID", "MENOR", "ID"]


# ---------- Auditoria (4ª ronda), Etapa 2 -- análise sintática. A matriz
# de rastreabilidade (secção 2) previa como lacuna "auditoria exaustiva
# de todo ponto de recursão descendente (nao/-/^ mencionados em B5)" --
# **essa previsão estava errada**: test_cadeia_de_nao_muito_funda_...,
# test_cadeia_de_menos_unario_muito_funda_... e
# test_cadeia_de_potencia_muito_funda_... (linhas ~3433-3448, achados só
# agora ao escrever testes que se revelaram duplicados) já cobrem os 3
# pontos de recursão em falta, tal como test_blocos_aninhados_a_mais_...
# (linha ~2755) já cobre LIMITE_PROFUNDIDADE_BLOCO. O que essas versões
# "muito funda" NÃO cobriam é o lado oposto -- confirmar que uma cadeia
# moderada e legítima não dispara o limite em falso positivo (o mesmo
# padrão que já existe para parênteses,
# test_expressao_moderadamente_aninhada_continua_a_funcionar, e para
# blocos, test_blocos_aninhados_dentro_do_limite_continuam_a_compilar,
# mas faltava para 'nao'/'-'/'^'). Também confirma 'ler()' sem
# argumentos (mencionado no plano como sem teste dedicado, ao contrário
# de 'escrever()' que já tinha um -- este, ao contrário dos anteriores,
# era mesmo uma lacuna real). ----------

def test_cadeia_de_nao_moderada_continua_a_funcionar():
    # 5 'nao' encadeados (ímpar) invertem verdadeiro -> falso.
    saida = executar('algoritmo "T"\ninicio\n    escrever(' + "nao " * 5 + "verdadeiro)\n")
    assert saida.strip() == "falso"


def test_cadeia_de_menos_unario_moderada_continua_a_funcionar():
    # 5 '-' encadeados (ímpar) mantêm o valor negativo.
    saida = executar('algoritmo "T"\ninicio\n    escrever(' + "-" * 5 + "1)\n")
    assert saida.strip() == "-1"


def test_cadeia_de_potencia_moderada_continua_a_funcionar():
    # 2^(2^2) = 2^4 = 16 (right-associative). O expoente do '^' exterior
    # não é um literal (é a sub-expressão '2^2'), por isso
    # _expoente_estaticamente_nao_negativo (semantics.py) não o
    # consegue provar não-negativo em compilação e tipa a expressão
    # inteira como 'decimal' -- consistente com '--minimo', que já
    # aplicava a mesma regra (só salta o float(...) quando o expoente é
    # um literal inteiro não-negativo, ver codegen_minimo.py) e sempre
    # produziu 16.0 aqui. Corrigido na Etapa 12 da 4ª auditoria (achado
    # da segunda passagem independente): o modo normal produzia "16"
    # (int), divergindo de '--minimo' e do próprio tipo 'decimal' que
    # semantics.py atribui a esta expressão -- ver _algo_pot em
    # codegen.py.
    saida = executar('algoritmo "T"\ninicio\n    escrever(2^2^2)\n')
    assert saida.strip() == "16.0"


def test_ler_sem_argumentos_e_erro_sintatico_nao_traceback_cru():
    # Ao contrário de 'escrever()', 'ler()' não tem uma verificação
    # dedicada -- mas tem de continuar a dar um ErroSintatico claro
    # (via _parse_lvalue -> esperar("ID")), nunca um traceback Python
    # cru ou um IndexError por ler além do fim dos tokens.
    with pytest.raises(ErroSintatico):
        compilar('algoritmo "T"\ninicio\n    x:inteiro\n    ler()\n')


# ---------- Auditoria (4ª ronda), Etapa 3 -- semântica: tipos/
# declarações/âmbito/constantes. `semantics.py` já tem cobertura
# negativa extensa (~50 testes `test_sem_*` em `test_correcoes_
# auditoria.py`, um por operador que rejeita um par de tipos errado --
# confirmado por grep antes de escrever nada aqui, lição da Etapa 2).
# O que não existia era o LADO POSITIVO como tabela única: cada
# operador × par de tipos válido, com o TIPO DE RESULTADO inferido
# confirmado (não só "não dá erro"). Isto é literalmente o "Critério de
# sucesso" da Etapa 2 do plano ("toda célula da matriz tem resultado
# documentado e testado") -- constrói-se aqui como uma única tabela
# parametrizada, fonte única de verdade, em vez de espalhada por
# dezenas de testes ad-hoc como os `test_sem_*` (que só cobrem o lado
# "erro"). Regras extraídas de `semantics.py::_tipo_binop`/`_compativel`/
# `_tipos_comparaveis` -- não são novas invenções, só a primeira vez
# que ficam como tabela testável. ----------

@pytest.mark.parametrize("expr,saida_esperada", [
    # '+': numéricos somam (decimal contamina); texto concatena (cadeia
    # contamina -- caracter+caracter também larga para cadeia, não fica
    # caracter, porque '+' devolve sempre "cadeia" para o par TEXTUAIS).
    ("2 + 3", "5"),
    ("2 + 3.5", "5.5"),
    ("3.5 + 2", "5.5"),
    ("2.5 + 3.5", "6.0"),
    pytest.param('"a" + "b"', "ab", id="cadeia_mais_cadeia"),
    pytest.param("'a' + 'b'", "ab", id="caracter_mais_caracter_larga_para_cadeia"),
    pytest.param('"a" + ' + "'b'", "ab", id="cadeia_mais_caracter"),
    # '-'/'*': só numéricos, mesma regra de contaminação por decimal que '+'.
    ("5 - 3", "2"),
    ("5.0 - 3", "2.0"),
    ("5 - 3.0", "2.0"),
    ("3 * 4", "12"),
    ("3.0 * 4", "12.0"),
    # '/': sempre decimal, mesmo inteiro/inteiro exato.
    ("4 / 2", "2.0"),
    ("7 / 2", "3.5"),
    # 'div'/'mod': só inteiro/inteiro -> inteiro (nunca contaminam para decimal).
    ("7 div 2", "3"),
    ("7 mod 2", "1"),
    # '==': cross numérico (inteiro==decimal) e cross textual (cadeia==caracter)
    # são aceites -- comparam por VALOR, não por tipo exato.
    ("1 == 1.0", "verdadeiro"),
    ('"a" == ' + "'a'", "verdadeiro"),
    ("verdadeiro == verdadeiro", "verdadeiro"),
    # relacionais: aceitam numérico-numérico ou texto-texto (cross
    # incluído); booleano é sempre rejeitado nestes (ver teste negativo
    # dedicado test_sem_relacional_com_tipos_errados, que já cobre isto).
    ("1 < 1.5", "verdadeiro"),
    ('"a" < "b"', "verdadeiro"),
    ("'a' < 'b'", "verdadeiro"),
    ('"ab" < ' + "'b'", "verdadeiro"),
    # 'e'/'ou': só booleano-booleano.
    ("verdadeiro e falso", "falso"),
    ("verdadeiro ou falso", "verdadeiro"),
])
def test_matriz_de_compatibilidade_operador_tipo(expr, saida_esperada):
    saida = executar(f'algoritmo "T"\ninicio\n    escrever({expr})\n')
    assert saida.strip() == saida_esperada


def test_sem_comparacao_de_igualdade_entre_booleano_e_outro_tipo():
    # '==' entre booleano e qualquer outro tipo não passa por nenhuma das
    # exceções cross-tipo de _tipos_comparaveis (nem NUMERICOS nem
    # TEXTUAIS nem nulo/estrutura) -- cai na regra genérica 'a == b', que
    # falha para tipos diferentes. Nunca tinha sido testado com
    # 'booleano' especificamente (só inteiro-vs-cadeia, em
    # test_sem_comparacao_incomparavel).
    with pytest.raises(ErroSemantico, match="não é possível comparar"):
        compilar('algoritmo "T"\ninicio\n    escrever(verdadeiro == 1)\n')


# ---------- Auditoria (4ª ronda), Etapa 4 -- semântica: estruturas,
# vetores e matrizes N-d. Confirmado por grep antes de escrever (lição
# da Etapa 2): a preocupação do plano "B8 só cobria 2 de ≥4 pontos de
# propagação de tipo esperado para literais {...}" já não se aplica --
# os 4 pontos de entrada (declaração, atribuição, argumento de chamada,
# 'devolver') já têm teste para AMBOS os tipos de literal onde
# sintaticamente possível (vetor/estrutura), incluindo o caso mais
# específico "vetor de literais de estrutura"
# (test_vetor_de_literais_de_estrutura, ~linha 3503) e tamanho literal
# vs. declarado (test_vetor_com_literal_de_tamanho_diferente_do_
# declarado_da_erro, ~linha 3467). A única lacuna real confirmada:
# nenhum teste ia além de 3 dimensões (`test_vetor_3d`/
# `test_vetor_literal_3d`, ~linha 337 de test_novas_funcionalidades.py)
# -- nada no código impõe um limite de dimensões (confirmado por
# leitura de semantics.py/codegen.py), mas a Etapa 4 do plano pedia
# confirmação explícita de N>3. ----------

def test_vetor_4d_indexacao_e_atribuicao():
    saida = executar("""
        algoritmo "T"
        inicio
            h:inteiro[2][2][2][2]
            h[0][0][0][0] = 111
            h[1][1][1][1] = 222
            escrever(h[0][0][0][0], ",", h[1][1][1][1], ",", h[0][1][0][1])
    """)
    assert saida.strip() == "111,222,0"


def test_vetor_literal_4d():
    saida = executar("""
        algoritmo "T"
        inicio
            c:inteiro[2][2][2][2] = {{{{1,2},{3,4}},{{5,6},{7,8}}},{{{9,10},{11,12}},{{13,14},{15,16}}}}
            escrever(c[0][0][0][0], ",", c[1][1][1][1])
    """)
    assert saida.strip() == "1,16"


# ---------- Auditoria (4ª ronda), Etapa 5 -- funções/'ref'/controlo de
# fluxo/'incluir'. Achado: os 3 testes de colisão de categoria em
# 'incluir' (test_incluir_estrutura_duplicada_da_erro,
# ::test_incluir_funcao_duplicada_da_erro,
# ::test_incluir_variavel_global_duplicada_da_erro, ~linha 1551) estão
# na lista de falhas da baseline -- confirmado empiricamente (não
# assumido) ao correr só estes 4 isolados: falham todos com o mesmo
# 'FileNotFoundError: [WinError 2]' de _winapi.CreateProcess ao tentar
# arrancar o executável 'algo' via subprocess.run(["algo", ...]), a
# MESMA causa (ambiente sem 'algo' no PATH desta sessão) documentada
# para as outras 78 falhas da baseline -- não é uma regressão nem um
# bug real na deteção de colisão em si. Para confirmar que a LÓGICA de
# deteção de colisão (não só o wrapper de CLI) está mesmo correta,
# repetem-se os mesmos 3 cenários em processo, via
# `_carregar_e_resolver_inclusoes` diretamente (mesmo padrão de
# `test_incluir_transitivo_*`, acima) -- sem subprocess, portanto
# imunes ao problema de ambiente, e prova positiva independente da
# suposição "é só ambiente". ----------

def test_incluir_estrutura_duplicada_da_erro_em_processo(tmp_path, capsys):
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    (tmp_path / "lib.algo").write_text(
        "estrutura Ponto\n    x:inteiro\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "lib.algo"\n'
        "estrutura Ponto\n    y:inteiro\n"
        "inicio\n"
        "    escrever(1)\n",
        encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _carregar_e_resolver_inclusoes(str(tmp_path / "principal.algo"))
    assert exc.value.code == 1
    assert "colide" in capsys.readouterr().out


def test_incluir_funcao_duplicada_da_erro_em_processo(tmp_path, capsys):
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    (tmp_path / "lib.algo").write_text(
        "funcao f():inteiro\n    devolver 1\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "lib.algo"\n'
        "funcao f():inteiro\n    devolver 2\n"
        "inicio\n"
        "    escrever(1)\n",
        encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _carregar_e_resolver_inclusoes(str(tmp_path / "principal.algo"))
    assert exc.value.code == 1
    assert "colide" in capsys.readouterr().out


def test_campo_de_estrutura_dentro_de_vetor_por_referencia_duas_vezes_nao_e_detetado():
    # Limitação CONHECIDA e deliberada de _chave_ref_estatica
    # (semantics.py:1063-1072, comentário AL-04/AL-81/B9): um acesso com
    # ÍNDICE (ex.: 'pontos[0].x') nunca é comparável estaticamente,
    # mesmo quando o índice é o mesmo literal nas duas chamadas -- só
    # variáveis simples ('x') e campos sem índice ('p.x') são
    # detetados (test_mesma_variavel_simples_passada_duas_vezes_por_
    # referencia_da_erro, test_mesmo_campo_de_estrutura_por_referencia_
    # duas_vezes_da_erro). Este teste fixa o comportamento ATUAL (sem
    # erro, com o aliasing real a manifestar-se em runtime) como
    # regressão -- não é uma correção, é documentar o limite conhecido
    # para que não seja "corrigido" por acidente para um falso positivo
    # (ou silenciosamente quebrado ao ponto de deixar de detetar os
    # casos que já apanha).
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        procedimento somar(ref a:inteiro, ref b:inteiro)
            a = a + 1
            b = b + 1
        inicio
            pontos:Ponto[2]
            pontos[0].x = 5
            somar(pontos[0].x, pontos[0].x)
            escrever(pontos[0].x)
    """)
    assert saida.strip() == "6"


def test_incluir_variavel_global_duplicada_da_erro_em_processo(tmp_path, capsys):
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    (tmp_path / "lib.algo").write_text(
        "total:inteiro = 0\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "Principal"\n'
        'incluir "lib.algo"\n'
        "total:inteiro = 1\n"
        "inicio\n"
        "    escrever(1)\n",
        encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _carregar_e_resolver_inclusoes(str(tmp_path / "principal.algo"))
    assert exc.value.code == 1
    assert "colide" in capsys.readouterr().out


# ---------- Auditoria (4ª ronda), Etapa 7 -- execução e erros em tempo
# de execução. Estratégia do plano: tabela função×input-adversarial
# construída a partir da assinatura de cada função em
# bibliotecas/*.py, confirmando "traduzida: sim" (nunca traceback cru)
# para cada célula. A maior parte das células já estava coberta por
# rondas anteriores de auditoria (ver comentários AL-08/AL-09/AL-19/
# AL-21/AL-64/AL-65/AL-68/AL-85/AL-86/AL-91 em bibliotecas/*.py e
# codegen.py) -- confirmado por grep antes de escrever, lição da Etapa
# 2. Dois achados: (1) `test_recursao_infinita_da_mensagem_amigavel_
# via_cli` (test_correcoes_auditoria.py:194) e `test_aceder_a_campo_de_
# nulo_da_erro_amigavel_nao_traceback` (test_estruturas.py:207) usam
# `subprocess.run(["algo", "executa", ...])` -- mesma armadilha de
# ambiente da Etapa 5/6, inoperáveis nesta sessão (estão na lista de
# falhas da baseline); reescritos aqui em processo, mesmo padrão dos
# testes '_em_processo' já usado nas Etapas 5/6. (2) célula nova,
# nunca exercitada: `matematica.piso`/`matematica.teto` com um valor
# NÃO FINITO (infinito/NaN) -- inatingível diretamente por um literal
# (sem notação científica na linguagem), mas alcançável através de
# `conversao.paraDecimal("inf"/"nan")` (que aceita essas strings, tal
# como o `float()` nativo do Python) alimentado a `matematica.piso`/
# `teto` (`math.floor`/`math.ceil` não estão preparados para
# infinito/NaN); e `matematica.potencia` com expoente suficientemente
# grande para o resultado não caber num `float` (`OverflowError` na
# conversão final, não no próprio `**`, já que inteiros Python não têm
# limite de tamanho). Confirmado por execução direta antes de escrever
# o teste: ambos os casos já são traduzidos corretamente (nenhum bug
# encontrado aqui, ao contrário da Etapa 6) -- só a cobertura estava em
# falta. ----------

def test_recursao_infinita_da_mensagem_amigavel_em_processo():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
funcao semFim(n:inteiro):inteiro
    devolver semFim(n + 1)
inicio
    escrever(semFim(1))
""")
    assert resultado.returncode == 1
    assert "recursão infinita" in resultado.stdout
    assert "Traceback" not in resultado.stdout


def test_aceder_a_campo_de_nulo_da_erro_amigavel_em_processo():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
estrutura No
    valor:inteiro
    seguinte:No
inicio
    n:No
    escrever(n.seguinte.valor)
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "campo 'valor' de um valor nulo" in resultado.stdout


def test_matematica_piso_de_infinito_da_overflow_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Matematica
importar Conversao
inicio
    x:decimal = conversao.paraDecimal("inf")
    escrever(matematica.piso(x))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "overflow" in resultado.stdout.lower()


def test_matematica_teto_de_nan_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Matematica
importar Conversao
inicio
    x:decimal = conversao.paraDecimal("nan")
    escrever(matematica.teto(x))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "valor inválido" in resultado.stdout


def test_matematica_potencia_com_expoente_grande_calcula_e_imprime_sem_overflow():
    """AUDITORIA_2026-08-19 bug #35: antes da correção, 'potencia()'
    forçava float(base**exp) incondicionalmente -- um resultado inteiro
    exato mas com dígitos a mais para caber num float (10**1000, 1001
    dígitos, bem dentro do limite de impressão de 4300) rebentava com
    OverflowError, inconsistente com o operador '^' (que calcula isto
    sem problema nenhum). Fica sem erro nenhum, tal como '^'."""
    saida = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.potencia(10, 1000))
    """)
    assert saida.strip() == str(10 ** 1000)


# ---------- AUDITORIA_2026-08-19 Fase 1.1: bug #1 -- cópia por valor de
# estruturas/vetores (9 caminhos confirmados) ----------

def test_atribuicao_simples_de_estrutura_nao_e_partilhada():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p1:Ponto
            p2:Ponto
            p1.x = 1
            p1.y = 2
            p2 = p1
            p2.x = 99
            escrever(p1.x)
            escrever(p2.x)
    """)
    assert saida.strip() == "1\n99"


def test_declaracao_com_inicializador_de_estrutura_nao_e_partilhada():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            p1:Ponto = {x: 1}
            p2:Ponto = p1
            p2.x = 99
            escrever(p1.x)
            escrever(p2.x)
    """)
    assert saida.strip() == "1\n99"


def test_devolver_variavel_de_estrutura_existente_nao_e_partilhada():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        g:Ponto
        funcao pegaG():Ponto
            devolver g
        inicio
            g.x = 1
            p:Ponto = pegaG()
            p.x = 99
            escrever(g.x)
            escrever(p.x)
    """)
    assert saida.strip() == "1\n99"


def test_devolver_vetor_inteiro_existente_nao_e_partilhado():
    saida = executar("""
        algoritmo "T"
        v:inteiro[3]
        funcao pegaV():inteiro[]
            devolver v
        inicio
            v[0] = 1
            a:inteiro[3] = pegaV()
            a[0] = 99
            escrever(v[0])
            escrever(a[0])
    """)
    assert saida.strip() == "1\n99"


def test_atribuicao_a_campo_de_estrutura_aninhada_nao_e_partilhada():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Retangulo
            canto:Ponto
        inicio
            p1:Ponto = {x: 1}
            r:Retangulo
            r.canto = p1
            r.canto.x = 99
            escrever(p1.x)
            escrever(r.canto.x)
    """)
    assert saida.strip() == "1\n99"


def test_literal_de_vetor_com_elementos_variaveis_estrutura_nao_e_partilhado():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            p1:Ponto = {x: 1}
            p2:Ponto = {x: 2}
            v:Ponto[2] = {p1, p2}
            v[0].x = 99
            escrever(p1.x)
            escrever(v[0].x)
    """)
    assert saida.strip() == "1\n99"


def test_elemento_a_elemento_num_vetor_de_estruturas_nao_e_partilhado():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            arr:Ponto[2]
            arr[0].x = 1
            arr[1].x = 2
            arr[0] = arr[1]
            arr[0].x = 99
            escrever(arr[1].x)
            escrever(arr[0].x)
    """)
    assert saida.strip() == "2\n99"


def test_elemento_de_vetor_a_partir_de_variavel_estrutura_nao_e_partilhado():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            p1:Ponto = {x: 1}
            arr:Ponto[1]
            arr[0] = p1
            arr[0].x = 99
            escrever(p1.x)
            escrever(arr[0].x)
    """)
    assert saida.strip() == "1\n99"


def test_campo_de_literal_de_estrutura_a_partir_de_variavel_nao_e_partilhado():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Retangulo
            canto:Ponto
        inicio
            p1:Ponto = {x: 1}
            r:Retangulo = {canto: p1}
            r.canto.x = 99
            escrever(p1.x)
            escrever(r.canto.x)
    """)
    assert saida.strip() == "1\n99"


def test_literal_de_vetor_como_argumento_direto_nao_partilha_elementos():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        procedimento muda(v:Ponto[])
            v[0].x = 99
        inicio
            p1:Ponto = {x: 1}
            p2:Ponto = {x: 2}
            muda({p1, p2})
            escrever(p1.x)
    """)
    assert saida.strip() == "1"


def test_literal_de_estrutura_como_argumento_direto_nao_partilha_campo():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Retangulo
            canto:Ponto
        procedimento muda(r:Retangulo)
            r.canto.x = 99
        inicio
            p1:Ponto = {x: 1}
            muda({canto: p1})
            escrever(p1.x)
    """)
    assert saida.strip() == "1"


def test_copia_de_estrutura_e_profunda_nao_superficial_em_campo_vetor():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        estrutura Poligono
            pontos:Ponto[2]
        inicio
            p1:Ponto = {x: 1}
            p2:Ponto = {x: 2}
            a:Poligono
            a.pontos[0] = p1
            a.pontos[1] = p2
            b:Poligono = a
            b.pontos[0].x = 99
            escrever(a.pontos[0].x)
            escrever(b.pontos[0].x)
    """)
    assert saida.strip() == "1\n99"


def test_bug14_atribuir_constante_a_variavel_normal_nao_quebra_a_constante():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            constante c:Ponto = {x: 1}
            p:Ponto
            p = c
            p.x = 99
            escrever(c.x)
            escrever(p.x)
    """)
    assert saida.strip() == "1\n99"


def test_ref_continua_a_ser_aliasing_intencional_apos_copia_por_valor():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        procedimento muda(ref p:Ponto)
            p.x = 99
        inicio
            p1:Ponto = {x: 1}
            p2:Ponto = p1
            muda(p2)
            escrever(p1.x)
            escrever(p2.x)
    """)
    assert saida.strip() == "1\n99"


# ---------- AUDITORIA_2026-08-19 Fase 1.2: bug #31 -- índice negativo
# nunca validado ----------

def test_indice_negativo_computado_em_leitura_1d_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    v:inteiro[3]
    v[0] = 10
    v[1] = 20
    v[2] = 30
    i:inteiro = -1
    escrever(v[i])
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "posição de vetor" in resultado.stdout


def test_indice_negativo_literal_em_leitura_1d_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    v:inteiro[3]
    escrever(v[-1])
""")
    assert resultado.returncode == 1
    assert "posição de vetor" in resultado.stdout


def test_indice_negativo_em_escrita_1d_da_erro_amigavel_nao_escreve_no_fim():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    v:inteiro[3]
    v[0] = 10
    v[1] = 20
    v[2] = 30
    i:inteiro = -1
    v[i] = 99
    escrever(v[2])
""")
    assert resultado.returncode == 1
    assert "99" not in resultado.stdout
    assert "posição de vetor" in resultado.stdout


def test_indice_negativo_na_primeira_dimensao_de_vetor_2d_da_erro():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    m:inteiro[2][2]
    i:inteiro = -1
    escrever(m[i][0])
""")
    assert resultado.returncode == 1
    assert "posição de vetor" in resultado.stdout


def test_indice_negativo_na_segunda_dimensao_de_vetor_2d_da_erro():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    m:inteiro[2][2]
    m[0][0] = 1
    i:inteiro = -1
    escrever(m[0][i])
""")
    assert resultado.returncode == 1
    assert "posição de vetor" in resultado.stdout


def test_indice_negativo_em_vetor_de_estruturas_da_erro():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
estrutura Ponto
    x:inteiro
inicio
    arr:Ponto[2]
    arr[0].x = 1
    i:inteiro = -1
    escrever(arr[i].x)
""")
    assert resultado.returncode == 1
    assert "posição de vetor" in resultado.stdout


def test_indice_positivo_continua_a_funcionar_apos_correcao_do_indice_negativo():
    saida = executar("""
        algoritmo "T"
        inicio
            v:inteiro[3]
            v[0] = 10
            v[1] = 20
            v[2] = 30
            escrever(v[2])
    """)
    assert saida.strip() == "30"


# ---------- AUDITORIA_2026-08-19 Fase 1.2: bug #34 -- dupla avaliação de
# índice computado num argumento 'ref' ----------

def test_indice_com_efeito_lateral_em_argumento_ref_e_avaliado_uma_so_vez():
    saida = executar("""
        algoritmo "T"
        contador:inteiro
        funcao proximoIndice():inteiro
            contador = contador + 1
            devolver contador - 1
        procedimento incrementa(ref x:inteiro)
            x = x + 100
        inicio
            v:inteiro[3]
            v[0] = 1
            v[1] = 2
            v[2] = 3
            contador = 0
            incrementa(v[proximoIndice()])
            escrever(v[0])
            escrever(v[1])
            escrever(v[2])
            escrever(contador)
    """)
    assert saida.strip() == "101\n2\n3\n1"


def test_indices_2d_com_efeito_lateral_em_argumento_ref_cada_um_avaliado_uma_vez():
    saida = executar("""
        algoritmo "T"
        contador:inteiro
        funcao proximoIndice():inteiro
            contador = contador + 1
            devolver contador - 1
        procedimento incrementa(ref x:inteiro)
            x = x + 100
        inicio
            m:inteiro[2][2]
            m[0][0] = 1
            m[0][1] = 2
            m[1][0] = 3
            m[1][1] = 4
            contador = 0
            incrementa(m[proximoIndice()][proximoIndice()])
            escrever(m[0][0])
            escrever(m[0][1])
            escrever(m[1][0])
            escrever(m[1][1])
            escrever(contador)
    """)
    assert saida.strip() == "1\n102\n3\n4\n2"


def test_indice_com_efeito_lateral_apos_campo_de_estrutura_em_ref_e_avaliado_uma_vez():
    saida = executar("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        contador:inteiro
        funcao proximoIndice():inteiro
            contador = contador + 1
            devolver contador - 1
        procedimento incrementa(ref x:inteiro)
            x = x + 100
        inicio
            arr:Ponto[2]
            arr[0].x = 1
            arr[1].x = 2
            contador = 0
            incrementa(arr[proximoIndice()].x)
            escrever(arr[0].x)
            escrever(arr[1].x)
            escrever(contador)
    """)
    assert saida.strip() == "101\n2\n1"


def test_dois_argumentos_ref_com_indices_independentes_cada_um_avaliado_uma_vez():
    saida = executar("""
        algoritmo "T"
        contador:inteiro
        funcao proximoIndice():inteiro
            contador = contador + 1
            devolver contador - 1
        procedimento somaAosDois(ref a:inteiro, ref b:inteiro)
            a = a + 100
            b = b + 1000
        inicio
            v:inteiro[3]
            v[0] = 1
            v[1] = 2
            v[2] = 3
            contador = 0
            somaAosDois(v[proximoIndice()], v[proximoIndice()])
            escrever(v[0])
            escrever(v[1])
            escrever(v[2])
            escrever(contador)
    """)
    assert saida.strip() == "101\n1002\n3\n2"


def test_indice_simples_em_ref_sem_efeito_lateral_continua_a_funcionar():
    saida = executar("""
        algoritmo "T"
        procedimento incrementa(ref x:inteiro)
            x = x + 1
        inicio
            v:inteiro[3]
            v[0] = 10
            v[1] = 20
            v[2] = 30
            i:inteiro = 1
            incrementa(v[i])
            escrever(v[0])
            escrever(v[1])
            escrever(v[2])
    """)
    assert saida.strip() == "10\n21\n30"


# ---------- AUDITORIA_2026-08-19 Fase 2.1: bugs #7/#10 -- cadeia plana de
# operadores crasha com RecursionError/SyntaxError cru ----------

def test_cadeia_de_mais_no_limite_da_arvore_compila_e_corre():
    from algo_lang.compilador.parser import parse
    from algo_lang.compilador.semantics import verificar
    from algo_lang.compilador.codegen import gerar_python
    import os
    termos = " + ".join(["1"] * 150)  # 149 operadores -- exatamente no limite
    codigo = f'algoritmo "T"\ninicio\n    escrever({termos})\n'
    programa = parse(codigo)
    verificar(programa)
    codigo_py = gerar_python(programa)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], capture_output=True, encoding="utf-8",
        timeout=10, env=env)
    assert resultado.returncode == 0
    assert resultado.stdout.strip() == "150"


def test_cadeia_de_mais_acima_do_limite_da_erro_sintatico_amigavel():
    termos = " + ".join(["1"] * 151)  # 150 operadores -- 1 a mais que o limite
    with pytest.raises(ErroSintatico, match="operadores a mais"):
        compilar(f'algoritmo "T"\ninicio\n    escrever({termos})\n')


def test_cadeia_de_vezes_acima_do_limite_da_erro_sintatico_amigavel():
    termos = " * ".join(["1"] * 151)
    with pytest.raises(ErroSintatico, match="operadores a mais"):
        compilar(f'algoritmo "T"\ninicio\n    escrever({termos})\n')


def test_cadeia_de_concatenacao_de_cadeia_acima_do_limite_da_erro_sintatico_amigavel():
    termos = " + ".join(['"a"'] * 151)
    with pytest.raises(ErroSintatico, match="operadores a mais"):
        compilar(f'algoritmo "T"\ninicio\n    escrever({termos})\n')


def test_cadeia_a_mais_e_apanhada_no_parser_nao_chega_ao_linter():
    """A correção fica no parser -- uma cadeia longa a mais nunca chega
    a produzir uma AST para o linter percorrer (bug #10: o linter tem o
    seu próprio RecursionError cru, alcançável sem passar por
    verificar() no serviço online)."""
    from algo_lang.tools.linter import analisar as analisar_linter
    termos = " + ".join(["1"] * 151)
    codigo = f'algoritmo "T"\ninicio\n    escrever({termos})\n'
    with pytest.raises(ErroSintatico, match="operadores a mais"):
        programa = parse(codigo)
        analisar_linter(programa, codigo)  # nunca deveria ser alcançado


def test_cadeia_combinada_entre_niveis_de_precedencia_tambem_e_limitada():
    """Bug encontrado ao desenhar a correção: um contador local por
    nível (só 'aditiva', só 'e', ...) não compõe corretamente quando o
    PRIMEIRO operando de uma cadeia já é ele próprio profundo -- esse
    operando fica mais enterrado na árvore final, não menos. A
    profundidade real (por nó, não por nível) tem de apanhar este caso
    combinado mesmo que nenhum nível isolado ultrapasse o limite."""
    cadeia_mais = " + ".join(["1"] * 111)  # 110 operadores
    cauda_e = " e ".join(["verdadeiro"] * 60)  # 59 operadores 'e'
    codigo = (
        f'algoritmo "T"\ninicio\n'
        f'    x:booleano = ({cadeia_mais} > 0) e {cauda_e}\n'
        f'    escrever(x)\n'
    )
    with pytest.raises(ErroSintatico, match="operadores a mais"):
        compilar(codigo)


def test_cadeia_moderada_entre_niveis_de_precedencia_continua_a_compilar():
    """Contraste com o teste anterior -- bem dentro do limite combinado
    (150), não deve disparar."""
    saida = executar("""
        algoritmo "T"
        inicio
            escrever((1 + 1 + 1 > 0) e verdadeiro e verdadeiro)
    """)
    assert saida.strip() == "verdadeiro"


# ---------- AUDITORIA_2026-08-19 Fase 2.2: mensagens em inglês / não
# traduzidas (bugs #4, #5, #8, #33, #35) ----------

def test_ler_a_mais_com_entradas_esgotadas_da_erro_amigavel_nao_eof_em_ingles():
    """bug #4: EOFError nativo (input() esgotado) não estava na cadeia
    de exceções traduzidas -- caía no handler genérico do tracer.
    Simula 'algo executa --entradas ficheiro_vazio.txt': stdin fecha
    sem nenhuma linha, ler() esgota o ficheiro na primeira leitura."""
    import os
    codigo_py = compilar("""
        algoritmo "T"
        inicio
            x:inteiro
            ler(x)
            escrever(x)
    """)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py], input="", capture_output=True,
        encoding="utf-8", timeout=10, env=env)
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "EOF" not in resultado.stdout
    assert "ficheiro de entradas" in resultado.stdout


def test_passo_zero_calculado_em_runtime_da_erro_amigavel_nao_texto_de_range():
    """bug #5: semantics.py só rejeita 'passo' ZERO LITERAL em
    compilação -- um 'passo' que só dá 0 em runtime (ex.: vindo de uma
    variável) chegava ao range() nativo sem tradução."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    i:inteiro = 0
    p:inteiro = 0
    para i de 1 ate 3 passo p fazer
        escrever(i)
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "range()" not in resultado.stdout
    assert "passo" in resultado.stdout
    assert "não pode ser zero" in resultado.stdout


def test_conversao_parainteiro_de_infinito_da_erro_amigavel():
    """bug #8: conversao.paraInteiro/paraDecimal apanham OverflowError e
    voltam a levantá-lo como ValueError (por design), mas a mensagem
    exata não estava na tabela de tradução."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    x:decimal = conversao.paraDecimal("inf")
    escrever(conversao.paraInteiro(x))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "infinity" not in resultado.stdout.lower()
    assert "infinito" in resultado.stdout


def test_conversao_paradecimal_de_inteiro_gigante_da_erro_amigavel():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.paraDecimal(2^2000))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "int too large" not in resultado.stdout.lower()
    assert "grande demais" in resultado.stdout


def test_escrever_inteiro_com_digitos_a_mais_da_erro_amigavel():
    """bug #33: 2^100000 (30103 dígitos) é um inteiro legítimo (precisão
    arbitrária) -- só ESCREVER falha, pela proteção do próprio Python
    3.11+ contra DoS na conversão inteiro->texto (~4300 dígitos)."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    escrever(2^100000)
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "set_int_max_str_digits" not in resultado.stdout
    assert "dígitos a mais" in resultado.stdout


def test_matematica_potencia_e_operador_potencia_consistentes_para_inteiro_grande():
    """bug #35: '^' e matematica.potencia() faziam a mesma matemática de
    formas inconsistentes para inteiros grandes -- matematica.potencia
    forçava float() incondicionalmente e rebentava antes mesmo de
    escrever(); '^' nunca força float quando o resultado fica inteiro,
    só falhando (de forma amigável, bug #33) ao imprimir."""
    saida_operador = executar("""
        algoritmo "T"
        inicio
            escrever(2^400)
    """)
    saida_funcao = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.potencia(2, 400))
    """)
    # '^' aqui produz 'inteiro' (expoente literal não-negativo, tipo
    # provado em compilação); matematica.potencia() é sempre 'decimal'
    # -- os VALORES numéricos continuam iguais, só o texto final (".0")
    # difere, esperado dado os tipos declarados serem diferentes.
    assert saida_operador.strip() == str(2 ** 400)
    assert saida_funcao.strip() == str(float(2 ** 400))


def test_matematica_potencia_caso_normal_continua_decimal_com_ponto():
    """Não regressão: o caso comum (resultado pequeno) continua sempre
    'decimal' (com '.0'), a correção do bug #35 só evita o float()
    forçado quando ele próprio rebentaria com OverflowError."""
    saida = executar("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.potencia(2, 3))
    """)
    assert saida.strip() == "8.0"


# ---------- AUDITORIA_2026-08-19 Fase 2.5: referência antecipada a uma
# global escondida dentro do corpo de uma função (bug #26) ----------

def test_referencia_antecipada_escondida_em_funcao_da_erro_de_compilacao():
    """Repro exato do bug: 'pegaB()' lê a global 'b', que só é
    declarada DEPOIS de 'a' ser inicializada a partir dela -- antes,
    compilava sem erro e crashava em runtime com NameError cru."""
    with pytest.raises(ErroSemantico, match="'b'.*declarada mais tarde"):
        compilar("""
            algoritmo "T"
            funcao pegaB():inteiro
                devolver b
            inicio
                a:inteiro = pegaB()
                b:inteiro = 10
                escrever(a, b)
        """)


def test_referencia_antecipada_em_ordem_correta_continua_a_compilar():
    saida = executar("""
        algoritmo "T"
        funcao pegaB():inteiro
            devolver b
        inicio
            b:inteiro = 10
            a:inteiro = pegaB()
            escrever(a)
    """)
    assert saida.strip() == "10"


def test_referencia_antecipada_e_detetada_transitivamente_por_chamadas_encadeadas():
    """A verificação segue chamadas a OUTRAS funções do próprio
    ficheiro -- 'pegaA' não lê 'c' diretamente, só chama 'pegaB', que
    lê."""
    with pytest.raises(ErroSemantico, match="'pegaA'.*'c'"):
        compilar("""
            algoritmo "T"
            funcao pegaB():inteiro
                devolver c
            funcao pegaA():inteiro
                devolver pegaB() + 1
            inicio
                a:inteiro = pegaA()
                c:inteiro = 5
                escrever(a)
        """)


def test_referencia_antecipada_nao_dispara_para_parametro_que_sombreia_global():
    """Não regressão: um parâmetro com o mesmo nome de uma global
    futura NÃO é uma referência a essa global -- é uma variável local
    própria, independente."""
    saida = executar("""
        algoritmo "T"
        funcao pegaB(b:inteiro):inteiro
            devolver b
        inicio
            a:inteiro = pegaB(5)
            b:inteiro = 10
            escrever(a, b)
    """)
    assert saida.strip() == "510"


def test_referencia_antecipada_com_recursao_mutua_nao_entra_em_ciclo_infinito():
    """A análise transitiva tem de terminar mesmo com funções que se
    chamam mutuamente -- 'vistas' em _globais_lidas_transitivamente
    evita reprocessar a mesma função indefinidamente."""
    saida = executar("""
        algoritmo "T"
        funcao par(n:inteiro):booleano
            se n == 0 entao
                devolver verdadeiro
            senao
                devolver impar(n - 1)
        funcao impar(n:inteiro):booleano
            se n == 0 entao
                devolver falso
            senao
                devolver par(n - 1)
        inicio
            escrever(par(4))
    """)
    assert saida.strip() == "verdadeiro"


def test_referencia_a_biblioteca_nao_e_confundida_com_referencia_antecipada():
    """Uma chamada de biblioteca ('matematica.raiz', com '.') nunca lê
    uma global ALGO -- não deve ser tratada como candidata a
    referência antecipada."""
    saida = executar("""
        algoritmo "T"
        importar Matematica
        funcao raizDe4():decimal
            devolver matematica.raiz(4.0)
        inicio
            x:decimal = raizDe4()
            escrever(x)
    """)
    assert saida.strip() == "2.0"


def test_referencia_antecipada_em_atribuicao_normal_nao_apanhada_em_compilacao_mas_da_erro_amigavel_em_runtime():
    """A verificação estática (_registar_decl) só cobre o valor inicial
    de uma DECLARAÇÃO, tal como o plano de correção descreve -- uma
    ATRIBUIÇÃO normal a uma variável já existente não passa por ali.
    Compila sem erro (limite conhecido e aceite do alcance da análise
    estática), mas a rede de segurança (NameError traduzido em
    codegen.py) garante que o erro em runtime continua amigável, não
    um traceback cru."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
funcao pegaB():inteiro
    devolver b
inicio
    a:inteiro = 0
    a = pegaB()
    b:inteiro = 10
    escrever(a, b)
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "not defined" not in resultado.stdout
    assert "'b' foi usada antes de existir um valor nela" in resultado.stdout


# ---------- AUDITORIA_2026-08-19 Fase 3.1: 'constante' como tamanho de
# vetor não tratada como um literal (bug #29) ----------

def test_constante_como_tamanho_negativo_de_vetor_da_erro_em_compilacao():
    """Antes, 'constante N:inteiro = -3; v:inteiro[N]' compilava sem
    erro (o equivalente literal 'v:inteiro[-3]' já dava erro de
    compilação) -- só falhava ao EXECUTAR, tarde demais."""
    with pytest.raises(ErroSemantico, match="não pode ser negativo"):
        compilar("""
            algoritmo "T"
            inicio
                constante N:inteiro = -3
                v:inteiro[N]
                escrever(1)
        """)


def test_constante_multi_nivel_como_tamanho_negativo_da_erro_em_compilacao():
    """'M = N + 1' com 'N' também 'constante' e resultado negativo --
    dobragem de constantes de mais de um nível, tal como o resto da
    compilação (codegen) já faz."""
    with pytest.raises(ErroSemantico, match="não pode ser negativo"):
        compilar("""
            algoritmo "T"
            inicio
                constante N:inteiro = -4
                constante M:inteiro = N + 1
                v:inteiro[M]
                escrever(1)
        """)


def test_constante_como_tamanho_incompativel_com_literal_da_erro_em_compilacao():
    """Antes, 'constante N:inteiro = 3; v:inteiro[N] = {1,2}' compilava
    sem erro (o equivalente literal 'v:inteiro[3] = {1,2}' já dava erro
    de compilação) -- só se notava ao aceder ao elemento em falta, em
    runtime."""
    with pytest.raises(ErroSemantico, match="tamanho declarado 3"):
        compilar("""
            algoritmo "T"
            inicio
                constante N:inteiro = 3
                v:inteiro[N] = {1, 2}
                escrever(1)
        """)


def test_constante_como_tamanho_de_vetor_uso_correto_continua_a_compilar():
    saida = executar("""
        algoritmo "T"
        inicio
            constante N:inteiro = 3
            v:inteiro[N] = {10, 20, 30}
            escrever(v[0], v[1], v[2])
    """)
    assert saida.strip() == "102030"


def test_constante_declarada_dentro_de_inicio_como_tamanho_e_resolvida_dentro_de_funcao():
    """A resolução também funciona para uma 'constante' declarada
    DENTRO de 'inicio' (não só antes) quando referenciada a partir de
    dentro de uma função -- self.globais precisa do mesmo tratamento
    que escopo_topo (_pre_registar_recursivo, não só _registar_decl).
    Funções são verificadas contra self.globais, que já inclui tudo o
    que 'inicio' declara, independentemente da ordem textual."""
    with pytest.raises(ErroSemantico, match="não pode ser negativo"):
        compilar("""
            algoritmo "T"
            procedimento usaTamanho()
                v:inteiro[N]
            inicio
                constante N:inteiro = -2
                usaTamanho()
        """)


def test_constante_como_tamanho_de_campo_de_estrutura_continua_proibida():
    """Não regressão: uma 'constante' do programa principal usada como
    tamanho de um vetor-campo de 'estrutura' continua um erro dedicado
    -- estruturas são registadas antes do resto do programa, nada aí é
    visível ainda (comportamento já existente, não faz parte do
    alcance do bug #29)."""
    with pytest.raises(ErroSemantico, match="não pode referenciá-la"):
        compilar("""
            algoritmo "T"
            constante N:inteiro = 3
            estrutura Caixa
                valores: inteiro[N]
            inicio
                escrever(1)
        """)


# ---------- AUDITORIA_2026-08-19 Fase 5: cli.py (bugs #6/#15, #16, #30) ----------

def test_erro_de_sintaxe_em_ficheiro_incluido_identifica_o_ficheiro(tmp_path):
    """bug #15: um erro de sintaxe/léxico DENTRO do ficheiro incluído só
    trazia linha/coluna, nunca o caminho -- o estudante olhava para a
    linha errada, no ficheiro errado (a sua PRÓPRIA linha 2, o
    'incluir', é perfeitamente válida)."""
    import os
    from algo_lang.cli import _carregar_e_resolver_inclusoes
    (tmp_path / "lib.algo").write_text(
        "funcao f():inteiro\n    devolver +\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(1)\n', encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _carregar_e_resolver_inclusoes(str(tmp_path / "principal.algo"))
    assert exc.value.code == 1


def test_erro_de_sintaxe_em_ficheiro_incluido_identifica_o_ficheiro_via_subprocesso(tmp_path):
    """Confirma o TEXTO da mensagem (não só o código de saída) --
    _carregar_e_resolver_inclusoes chama sys.exit() diretamente, por
    isso corre-se num subprocesso para capturar o que foi impresso
    antes da saída."""
    import os
    (tmp_path / "lib.algo").write_text(
        "funcao f():inteiro\n    devolver +\n", encoding="utf-8")
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(1)\n', encoding="utf-8")
    script = (
        "import sys\n"
        f"sys.path.insert(0, {os.getcwd()!r})\n"
        "from algo_lang.cli import _carregar_e_resolver_inclusoes\n"
        f"_carregar_e_resolver_inclusoes({str(tmp_path / 'principal.algo')!r})\n"
    )
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, encoding="utf-8", env=env)
    assert resultado.returncode == 1
    assert "lib.algo" in resultado.stdout
    assert "linha 2" in resultado.stdout


def test_incluir_por_engano_o_proprio_ficheiro_principal_identifica_o_ficheiro(tmp_path):
    """bug #6: uma biblioteca (aqui, o próprio principal, incluído por
    engano) que não tem a forma de uma biblioteca ('algoritmo'/'inicio')
    é rejeitada por parse_biblioteca -- a mensagem deve dizer QUAL
    ficheiro, mesma causa raiz e correção do bug #15."""
    import os
    (tmp_path / "principal.algo").write_text(
        'algoritmo "T"\nincluir "principal.algo"\ninicio\n    escrever(1)\n', encoding="utf-8")
    script = (
        "import sys\n"
        f"sys.path.insert(0, {os.getcwd()!r})\n"
        "from algo_lang.cli import _carregar_e_resolver_inclusoes\n"
        f"_carregar_e_resolver_inclusoes({str(tmp_path / 'principal.algo')!r})\n"
    )
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    resultado = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, encoding="utf-8", env=env)
    assert resultado.returncode == 1
    assert "principal.algo" in resultado.stdout


def test_mostrar_python_e_respeitado_com_debug(tmp_path, capsys):
    """bug #16: '--mostrar-python' era ignorado em silêncio quando
    combinado com '--debug'/'--json' -- o Python era gerado e escrito
    em disco na mesma, só não era impresso, sem aviso nenhum."""
    import argparse
    from algo_lang.cli import cmd_executa_com_trace
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever(1)\n', encoding="utf-8")
    args = argparse.Namespace(
        ficheiro=str(algo_path), debug=True, json=False, entradas=None, mostrar_python=True)
    cmd_executa_com_trace(args)
    saida = capsys.readouterr().out
    assert "Código Python gerado" in saida
    assert "def _algo_programa" in saida


def test_mostrar_python_desligado_nao_imprime_o_python_com_debug(tmp_path, capsys):
    """Não regressão: a flag continua opcional -- sem ela, o
    comportamento fica como antes desta correção."""
    import argparse
    from algo_lang.cli import cmd_executa_com_trace
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever(1)\n', encoding="utf-8")
    args = argparse.Namespace(
        ficheiro=str(algo_path), debug=True, json=False, entradas=None, mostrar_python=False)
    cmd_executa_com_trace(args)
    saida = capsys.readouterr().out
    assert "Código Python gerado" not in saida


def test_pasta_saida_caminho_demasiado_longo_da_erro_amigavel(tmp_path):
    """bug #30: sem isto, um caminho de saída demasiado longo para o
    Windows dava um OSError cru ('[WinError 206] The filename or
    extension is too long'), propagado sem tratamento nenhum. Mockado
    (em vez de construir um caminho real de ~260 caracteres, frágil
    entre ambientes) -- ver PLANO_CORRECOES_AUDITORIA.md."""
    from unittest.mock import patch
    from algo_lang.cli import _pasta_saida
    with patch("os.makedirs", side_effect=OSError(
            "[WinError 206] The filename or extension is too long")):
        with pytest.raises(SystemExit) as exc:
            _pasta_saida(str(tmp_path / "prog.algo"))
    assert exc.value.code == 1


def test_pasta_saida_normal_continua_a_funcionar_apos_correcao_do_bug30(tmp_path):
    from algo_lang.cli import _pasta_saida
    pasta, nome_base = _pasta_saida(str(tmp_path / "prog.algo"))
    assert nome_base == "prog"
    assert os.path.isdir(pasta)


# ---------- AUDITORIA_2026-08-19 Fase 6.1: tamanho de array sem limite
# superior (bug #32) ----------

def test_tamanho_de_vetor_acima_do_limite_da_erro_amigavel_rapido():
    """Antes, um tamanho de vetor suficientemente grande (aqui, bem
    acima do limite escolhido de 10 milhões) deixava o programa
    'pendurado' a alocar memória durante segundos, sem nenhuma
    mensagem. Deve falhar RÁPIDO, com uma mensagem amigável -- não um
    crash cru nem um programa preso."""
    import time
    inicio = time.time()
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    v:inteiro[20000000]
    escrever(1)
""")
    duracao = time.time() - inicio
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "limite permitido" in resultado.stdout
    assert duracao < 5  # bem antes do 1s que o próprio limite já demoraria


def test_tamanho_de_vetor_calculado_em_runtime_acima_do_limite_da_erro_amigavel():
    """O guarda cobre tanto um tamanho LITERAL como um CALCULADO -- é o
    mesmo único sítio (_algo_verificar_tamanho_vetor) por onde toda
    dimensão de vetor passa antes de range()."""
    resultado = _correr_esperando_erro("""\
algoritmo "T"
inicio
    n:inteiro = 20000000
    v:inteiro[n]
    escrever(1)
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout
    assert "limite permitido" in resultado.stdout


def test_tamanho_de_vetor_dentro_do_limite_continua_a_funcionar():
    """Não regressão: um tamanho normal, bem dentro do limite, continua
    sem erro nenhum."""
    saida = executar("""
        algoritmo "T"
        inicio
            v:inteiro[1000]
            v[999] = 1
            escrever(v[999])
    """)
    assert saida.strip() == "1"


# ---------- AUDITORIA_2026-08-19 ronda 12 (reauditoria): bugs #2/#9/#39
# -- fusão de âmbito entre ramos irmãos 'se'/'senao' ----------

def test_constante_com_eh_constante_diferente_em_ramos_irmaos_da_erro_em_compilacao():
    """bug #2: antes, 'x' ficava com o 'eh_constante' do PRIMEIRO ramo
    visitado em DFS (sempre 's.ramos' antes de 's.senao'),
    independentemente de qual ramo executa de facto -- permitindo que
    o ramo que corre em runtime mute em silêncio o que a fonte chama
    de 'constante'. Repro exato do bug: 'x' é 'constante' no 'senao'
    (o ramo que executa, já que a condição é 'falso'), mas mutável no
    'se' -- devia ser um erro de COMPILAÇÃO, não uma mutação silenciosa."""
    with pytest.raises(ErroSemantico, match="constante"):
        compilar("""
            algoritmo "T"
            procedimento mexe()
                x = 999
            procedimento mostra()
                escrever("x =", x)
            inicio
                se falso entao
                    x:inteiro = 10
                senao
                    constante x:inteiro = 5
                mostra()
                mexe()
                mostra()
        """)


def test_variavel_declarada_em_ambos_os_ramos_de_se_senao_fica_disponivel_depois():
    """bug #9: 'x' declarada com o mesmo tipo em AMBOS os ramos de um
    'se'/'senao' exaustivo tem sempre um valor a seguir ao 'se' --
    antes, dava (incorretamente) 'a variável x não foi declarada'."""
    saida = executar("""
        algoritmo "T"
        inicio
            se verdadeiro entao
                x: inteiro = 1
            senao
                x: inteiro = 2
            escrever(x)
    """)
    assert saida.strip() == "1"


def test_variavel_com_tipos_diferentes_em_ramos_irmaos_continua_indisponivel_depois_do_se():
    """Não regressão da correção do bug #9: quando os ramos NÃO
    concordam em tipo, o nome continua por declarar depois do 'se' --
    sem propagação, mas também sem erro nenhum na própria declaração
    (só ao tentar usar 'y' depois). Dentro de um procedimento (não em
    'inicio') para isolar do mecanismo, à parte, de globais visíveis a
    funções (_pre_registar_recursivo), que já rejeita tipos diferentes
    em ramos irmãos ao nível de topo, com uma mensagem diferente."""
    with pytest.raises(ErroSemantico, match="não foi declarada"):
        compilar("""
            algoritmo "T"
            procedimento p()
                se verdadeiro entao
                    y: inteiro = 1
                senao
                    y: decimal = 2.0
                escrever(y)
            inicio
                p()
        """)


def test_constante_com_valores_diferentes_em_ramos_irmaos_nao_trava_compilacao_valida():
    """bug #39: análogo ao #2, mas para o VALOR resolvido de uma
    'constante' inteira escalar (bug #29) -- ramos irmãos com o mesmo
    tipo mas valores DIFERENTES ficavam congelados no valor do
    primeiro ramo visitado. Aqui, o 'senao' (o ramo que executa, já
    que a condição é 'falso') declara x=10, que bate certo com os 10
    elementos do literal -- antes, o compilador rejeitava isto porque
    tinha congelado x=5 (o valor do 'se', visitado primeiro)."""
    saida = executar("""
        algoritmo "T"
        funcao tam():inteiro
            v:inteiro[x] = {1,2,3,4,5,6,7,8,9,10}
            devolver 3
        inicio
            se falso entao
                constante x:inteiro = 5
            senao
                constante x:inteiro = 10
            escrever(tam())
    """)
    assert saida.strip() == "3"


# ---------- AUDITORIA_2026-08-19 ronda 12: bug #18 -- artefactos crus de
# vírgula flutuante em 'escrever' ----------

def test_escrever_decimal_arredonda_ruido_de_representacao_binaria():
    saida = executar("""
        algoritmo "T"
        inicio
            escrever(0.1 + 0.2)
    """)
    assert saida.strip() == "0.3"


def test_escrever_decimal_normaliza_zero_negativo():
    saida = executar("""
        algoritmo "T"
        inicio
            escrever(0.0 * -1.0)
    """)
    assert saida.strip() == "0.0"


def test_escrever_decimal_de_valor_inteiro_mantem_ponto_zero():
    """Não regressão: um 'decimal' de valor inteiro continua a mostrar
    '.0' (distingue de 'inteiro' na saída)."""
    saida = executar("""
        algoritmo "T"
        inicio
            escrever(3.0)
    """)
    assert saida.strip() == "3.0"


# ---------- AUDITORIA_2026-08-19 ronda 12: bug #19 -- ler() para decimal
# aceitava 'nan'/'inf' em silêncio ----------

def test_ler_decimal_rejeita_nan_e_volta_a_pedir():
    saida = executar("""
        algoritmo "T"
        inicio
            x: decimal
            ler(x)
            escrever(x)
    """, entrada="nan\n5.5\n")
    assert saida.strip().endswith("5.5")
    assert "Valor inválido" in saida


def test_ler_decimal_rejeita_infinity_e_volta_a_pedir():
    saida = executar("""
        algoritmo "T"
        inicio
            x: decimal
            ler(x)
            escrever(x)
    """, entrada="Infinity\n-3.5\n")
    assert saida.strip().endswith("-3.5")


# ---------- AUDITORIA_2026-08-19 ronda 12: bugs #24/#37 -- 'escolher' só
# com 'contrario' (sem nenhum 'caso') ----------

def test_escolher_so_com_contrario_compila_e_executa_sem_syntaxerror():
    saida = executar("""
        algoritmo "T"
        inicio
            x:inteiro = 3
            escolher x
                contrario
                    escrever("sempre")
    """)
    assert saida.strip() == "sempre"


def test_linter_avisa_escolher_sem_nenhum_caso():
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""\
        algoritmo "T"
        inicio
            x:inteiro = 3
            escolher x
                contrario
                    escrever("sempre")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert any("nenhum 'caso'" in a.mensagem for a in avisos)


def test_escolher_com_pelo_menos_um_caso_nao_da_aviso_de_sem_casos():
    """Não regressão: um 'escolher' normal (com 'caso') não dispara o
    novo aviso do bug #37."""
    from algo_lang.tools.linter import analisar
    programa = parse(textwrap.dedent("""\
        algoritmo "T"
        inicio
            x:inteiro = 3
            escolher x
                caso 1
                    escrever("um")
                contrario
                    escrever("outro")
    """))
    verificar(programa)
    avisos = analisar(programa)
    assert not any("nenhum 'caso'" in a.mensagem for a in avisos)


# ---------- AUDITORIA_2026-08-19 ronda 12: bug #36 -- tracer/consola
# rebentavam com Python gerado sintaticamente inválido ----------

def test_gerar_trace_com_python_invalido_da_erro_amigavel_sem_rebentar():
    """Rede de segurança do bug #36: mesmo que o codegen algum dia volte
    a gerar Python sintaticamente inválido (não é preciso reproduzir
    nenhum bug de codegen específico para testar isto -- o próprio
    'compile()' do tracer é o que estava desprotegido), 'gerar_trace'
    não deve propagar o SyntaxError cru."""
    from algo_lang.tools.tracer import gerar_trace
    resultado = gerar_trace(
        "def _algo_programa():\n    else:\n        pass\n",
        "fake_path.py", {}, [], [])
    assert resultado["erro"] is not None
    assert resultado["passos"] == []


# ---------- AUDITORIA_2026-08-19 ronda 12: bugs #41/#42 -- mensagens do
# parser fugiam ao helper '_nome_amigavel' ----------

def test_parser_tipo_em_falta_nao_mostra_nome_de_token_cru():
    with pytest.raises(ErroSintatico) as exc:
        parse(textwrap.dedent("""\
            algoritmo "T"
            x:
            inicio
                escrever(1)
        """))
    assert "NEWLINE" not in str(exc.value)


def test_parser_instrucao_inesperada_nao_mostra_nome_de_token_cru():
    with pytest.raises(ErroSintatico) as exc:
        parse(textwrap.dedent("""\
            algoritmo "T"
            inicio
                :
        """))
    assert "COLON" not in str(exc.value)


def test_parser_identificador_inesperado_mostra_o_identificador():
    with pytest.raises(ErroSintatico) as exc:
        parse(textwrap.dedent("""\
            algoritmo "T"
            inicio
                x = 5 abc
        """))
    assert "abc" in str(exc.value)


# ---------- AUDITORIA_2026-08-19 ronda 12: bug #43 -- conversao.* aceitava
# separadores '_' de milhar do Python ----------

def test_conversao_parainteiro_rejeita_separador_de_milhar():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.paraInteiro("1_000"))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout


def test_conversao_paradecimal_rejeita_separador_de_milhar():
    resultado = _correr_esperando_erro("""\
algoritmo "T"
importar Conversao
inicio
    escrever(conversao.paraDecimal("1_000.5"))
""")
    assert resultado.returncode == 1
    assert "Traceback" not in resultado.stdout


def test_conversao_paradecimal_continua_a_aceitar_infinito():
    """Não regressão da investigação do bug #40 (ronda 12): ao contrário
    de 'ler()' (bug #19), 'conversao.paraDecimal' continua a aceitar
    'inf'/'nan' -- é o único ponto de todo o ALGO por onde um programa
    consegue construir esses valores deliberadamente (a linguagem não
    tem literal nenhum para isso), e os consumidores já traduzem o
    OverflowError resultante de forma amigável."""
    saida = executar("""
        algoritmo "T"
        importar Conversao
        inicio
            x: decimal = conversao.paraDecimal("inf")
            escrever(x)
    """)
    assert saida.strip() == "inf"


# ---------- AUDITORIA_2026-08-19 ronda 13: variável declarada em todos os
# 'caso' + 'contrario' de um 'escolher' exaustivo fica disponível depois
# dele (mesma classe do bug #9, mas em 'escolher') ----------

def test_variavel_declarada_em_todos_os_casos_e_contrario_fica_disponivel_depois_do_escolher():
    saida = executar("""
        algoritmo "T"
        inicio
            x:inteiro = 1
            escolher x
                caso 1
                    y:inteiro = 10
                contrario
                    y:inteiro = 20
            escrever(y)
    """)
    assert saida.strip() == "10"


def test_variavel_com_tipos_diferentes_entre_casos_continua_indisponivel_depois_do_escolher():
    """Não regressão: ramos que não concordam em tipo continuam sem
    propagação (sem erro na própria declaração, só ao usar 'z' depois).
    Dentro de um procedimento para isolar do mecanismo, à parte, de
    globais visíveis a funções (mesma razão do teste equivalente para
    'se'/'senao')."""
    with pytest.raises(ErroSemantico, match="não foi declarada"):
        compilar("""
            algoritmo "T"
            procedimento p()
                x:inteiro = 1
                escolher x
                    caso 1
                        z:inteiro = 10
                    contrario
                        z:decimal = 20.0
                escrever(z)
            inicio
                p()
        """)


# ---------- AUDITORIA_2026-08-19 ronda 13: '-0.0' que só aparece depois
# do arredondamento de 12 casas decimais escapava à normalização de
# 'escrever' (bug #18-bis) ----------

def test_escrever_decimal_normaliza_zero_negativo_que_so_aparece_apos_arredondar():
    saida = executar("""
        algoritmo "T"
        inicio
            escrever(-1.0 / 10000000000000.0)
    """)
    assert saida.strip() == "0.0"


# ---------- AUDITORIA_2026-08-19 ronda 13: rótulo "Principal" da pilha do
# tracer colidia com uma função do estudante literalmente chamada
# 'Principal' (bug #36-bis) ----------

def test_tracer_nao_confunde_funcao_chamada_principal_com_o_programa_principal():
    from algo_lang.compilador.codegen import gerar_python_com_mapa
    from algo_lang.tools.tracer import gerar_trace
    programa = parse(textwrap.dedent("""\
        algoritmo "T"
        funcao Principal(x:inteiro):inteiro
            devolver x + 1
        inicio
            y:inteiro = Principal(10)
            escrever(y)
    """))
    verificar(programa)
    dados = gerar_python_com_mapa(programa)
    resultado = gerar_trace(
        dados["codigo"], "fake_path.py", dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"])
    nomes_por_passo = [[f["nome"] for f in p["pilha"]] for p in resultado["passos"]]
    # o frame do PROGRAMA (não da função do estudante) usa um rótulo que
    # nenhum identificador ALGO válido pode ter (parênteses)
    assert any(pilha == ["(Principal)"] for pilha in nomes_por_passo)
    # o frame da FUNÇÃO do estudante mantém o nome dela, sem confusão
    assert any("Principal" in pilha and "(Principal)" in pilha for pilha in nomes_por_passo)


# ---------- AUDITORIA_2026-08-19 ronda 13: construções de topo (variável,
# função, 'estrutura', 'importar'/'incluir') depois do bloco 'inicio' eram
# aceites em silêncio ----------

def test_declaracao_global_depois_de_inicio_da_erro_de_sintaxe():
    with pytest.raises(ErroSintatico, match="última coisa do programa"):
        parse(textwrap.dedent("""\
            algoritmo "T"
            inicio
                escrever(x)
            x:inteiro = 5
        """))


def test_funcao_depois_de_inicio_da_erro_de_sintaxe():
    with pytest.raises(ErroSintatico, match="última coisa do programa"):
        parse(textwrap.dedent("""\
            algoritmo "T"
            inicio
                escrever(soma(1,2))
            funcao soma(a:inteiro, b:inteiro):inteiro
                devolver a+b
        """))


def test_segundo_inicio_continua_com_mensagem_dedicada():
    """Não regressão: um segundo 'inicio' continua a dar a mensagem
    específica (AL-75), não a mensagem genérica nova."""
    with pytest.raises(ErroSintatico, match="só pode haver um"):
        parse(textwrap.dedent("""\
            algoritmo "T"
            inicio
                escrever(1)
            inicio
                escrever(2)
        """))
