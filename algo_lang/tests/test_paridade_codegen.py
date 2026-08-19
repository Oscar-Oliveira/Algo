# -*- coding: utf-8 -*-
"""Auditoria (4ª ronda), Etapa 6 -- paridade COMPORTAMENTAL entre
codegen.py (modo normal) e codegen_minimo.py (--minimo).

O plano da auditoria (AUDITORIA_PLANO.md, Etapa 6) identifica isto como
o ponto mais fraco do histórico do projeto: `test_compila_minimo.py`
(36 testes) já cobre --minimo caso a caso, mas nenhum teste corria um
CORPUS de programas nos dois modos comparando o `stdout` byte a byte --
só paridade ESTRUTURAL (presença/ausência de funções de apoio no texto
gerado) tinha sido verificada, nunca paridade de COMPORTAMENTO em
execução real.

Achado adicional desta etapa: `test_compila_minimo.py` invoca sempre
`subprocess.run(["algo", "compila", "--minimo", ...])` -- exatamente
como as 4 falhas de `incluir` da Etapa 5, isto depende do executável
`algo` estar no PATH, o que NÃO acontece neste ambiente de sessão
(ver AUDITORIA_PROGRESSO.md). Isso torna o ficheiro inteiro
inoperável aqui (confirmado: todos os seus testes estão na lista de
falhas da baseline). Este ficheiro evita a mesma armadilha invocando
`parse`/`gerar_python`/`gerar_python_minimo` diretamente em processo
(mesmo padrão de `apoio.py::compilar`) e só usa subprocess para correr
o Python JÁ GERADO com `sys.executable` (caminho absoluto resolvido
pelo próprio Python, nunca depende do PATH) -- o mesmo truque que
mantém `apoio.py::executar` a funcionar durante toda esta auditoria
enquanto os testes baseados em `algo`/`python` como comando falham.
"""
import subprocess
import sys
import textwrap

import pytest

from algo_lang.compilador.parser import parse
from algo_lang.compilador.semantics import verificar
from algo_lang.compilador.codegen import gerar_python
from algo_lang.compilador.codegen_minimo import gerar_python_minimo


def _correr_python(codigo_py, entrada=""):
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_py],
        input=entrada, capture_output=True, text=True, timeout=10,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"o Python gerado falhou (código {resultado.returncode}):\n"
            f"{resultado.stderr}\n----- código gerado -----\n{codigo_py}")
    return resultado.stdout


def _saidas_normal_e_minimo(codigo_algo, entrada=""):
    codigo_algo = textwrap.dedent(codigo_algo)
    programa_normal = parse(codigo_algo)
    verificar(programa_normal)
    saida_normal = _correr_python(gerar_python(programa_normal), entrada)

    # AL-16 etc.: parse() é sem-estado, mas a AST é mutada em lugares
    # (ex.: _tipo_inferido em cada nó, escrito por verificar()) -- usa-se
    # uma segunda árvore, virgem, para o modo --minimo, tal como
    # cli.py faz na prática (dois comandos distintos, cada um com o seu
    # próprio parse()), para não arriscar que o modo normal "contamine"
    # a árvore que o modo mínimo vê.
    programa_minimo = parse(codigo_algo)
    saida_minimo = _correr_python(gerar_python_minimo(programa_minimo), entrada)

    return saida_normal, saida_minimo


CORPUS = [
    pytest.param("""
        algoritmo "T"
        inicio
            escrever(2 + 3 * 4 - 1)
    """, "", id="aritmetica_inteira_precedencia"),

    pytest.param("""
        algoritmo "T"
        inicio
            escrever(-7 div 2, " ", -7 mod 2, " ", 7 div -2, " ", 7 mod -2)
    """, "", id="div_mod_truncados_com_negativos"),

    pytest.param("""
        algoritmo "T"
        inicio
            escrever(7 / 2)
    """, "", id="divisao_sempre_decimal"),

    pytest.param("""
        algoritmo "T"
        inicio
            escrever(2 ^ 10, " ", 2.0 ^ 3)
    """, "", id="potencia_base_positiva"),

    pytest.param("""
        algoritmo "T"
        inicio
            n:inteiro = 3
            y:decimal = 2 ^ n
            escrever(y)
    """, "", id="potencia_inteira_com_expoente_variavel_atribuida_a_decimal"),

    pytest.param("""
        algoritmo "T"
        inicio
            escrever(2 ^ 2 ^ 2)
    """, "", id="potencia_encadeada_expoente_nao_literal"),

    pytest.param("""
        algoritmo "T"
        inicio
            escrever("ola" + " " + "mundo")
    """, "", id="concatenacao_cadeia"),

    pytest.param("""
        algoritmo "T"
        importar Cadeia
        inicio
            s:cadeia = "Ola Mundo"
            escrever(cadeia.maiusculas(s))
            escrever(cadeia.minusculas(s))
            escrever(cadeia.inverter(s))
            escrever(cadeia.comprimento(s))
            escrever(cadeia.subcadeia(s, 0, 3))
            escrever(cadeia.caracter(s, 1))
    """, "", id="biblioteca_cadeia_todos_os_metodos"),

    pytest.param("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.raiz(16.0))
            escrever(matematica.absoluto(-5))
            escrever(matematica.absoluto(-5.5))
            escrever(matematica.piso(3.7))
            escrever(matematica.teto(3.2))
            escrever(matematica.potencia(2, 10))
    """, "", id="biblioteca_matematica_deterministica"),

    pytest.param("""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraInteiro("42"))
            escrever(conversao.paraDecimal("3.14"))
            escrever(conversao.paraTexto(42))
            escrever(conversao.paraCaracter("x"))
            escrever(conversao.paraAscii('A'))
            escrever(conversao.deAscii(65))
    """, "", id="biblioteca_conversao_todos_os_metodos"),
    # 'paraBooleano' fica de fora deste caso -- devolve um booleano, que
    # diverge na FORMATAÇÃO de impressão por desenho (mesma exceção
    # documentada de test_divergencia_intencional_booleano_impresso_em_
    # minimo, abaixo), não por um bug na conversão em si.

    pytest.param("""
        algoritmo "T"
        inicio
            v:inteiro[5] = {1, 2, 3, 4, 5}
            soma:inteiro = 0
            i:inteiro
            para i de 0 ate 4 fazer
                soma = soma + v[i]
            escrever(soma)
    """, "", id="array_1d_literal_e_ciclo_para"),

    pytest.param("""
        algoritmo "T"
        inicio
            m:inteiro[2][3]
            i:inteiro
            j:inteiro
            para i de 0 ate 1 fazer
                para j de 0 ate 2 fazer
                    m[i][j] = i * 3 + j
            para i de 0 ate 1 fazer
                para j de 0 ate 2 fazer
                    escrever(m[i][j])
    """, "", id="array_2d_construido_com_default"),

    pytest.param("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {x: 3, y: 4}
            escrever(p.x, ",", p.y)
    """, "", id="estrutura_literal_simples"),

    pytest.param("""
        algoritmo "T"
        estrutura Ponto
            x:decimal
        estrutura Linha
            inicio_pt:Ponto
            fim_pt:Ponto
        inicio
            l:Linha = {inicio_pt: {x: 1.0}, fim_pt: {x: 2.0}}
            escrever(l.inicio_pt.x, " ", l.fim_pt.x)
    """, "", id="estrutura_aninhada_literal"),

    pytest.param("""
        algoritmo "T"
        funcao fibonacci(n:inteiro):inteiro
            se n <= 1 entao
                devolver n
            devolver fibonacci(n - 1) + fibonacci(n - 2)
        inicio
            escrever(fibonacci(10))
    """, "", id="recursao_fibonacci"),

    pytest.param("""
        algoritmo "T"
        procedimento trocar(ref a:inteiro, ref b:inteiro)
            temp:inteiro = a
            a = b
            b = temp
        inicio
            x:inteiro = 1
            y:inteiro = 2
            trocar(x, y)
            escrever(x, ",", y)
    """, "", id="parametros_por_referencia"),

    pytest.param("""
        algoritmo "T"
        inicio
            x:inteiro = 0
            enquanto x < 5 fazer
                escrever(x)
                x = x + 1
    """, "", id="ciclo_enquanto"),

    pytest.param("""
        algoritmo "T"
        inicio
            x:inteiro = 0
            fazer
                escrever(x)
                x = x + 1
            enquanto x < 3
    """, "", id="ciclo_faz_enquanto"),

    pytest.param("""
        algoritmo "T"
        inicio
            i:inteiro
            para i de 10 ate 0 passo -2 fazer
                escrever(i)
    """, "", id="ciclo_para_com_passo_negativo"),

    pytest.param("""
        algoritmo "T"
        inicio
            x:inteiro = 7
            se x < 5 entao
                escrever("pequeno")
            senao se x < 10 entao
                escrever("medio")
            senao
                escrever("grande")
    """, "", id="se_senao_se_senao"),

    pytest.param("""
        algoritmo "T"
        inicio
            x:inteiro = 2
            escolher x
                caso 1
                    escrever("um")
                caso 2
                    escrever("dois")
                contrario
                    escrever("outro")
    """, "", id="escolher_com_contrario"),

    pytest.param("""
        algoritmo "T"
        inicio
            afirmar 1 + 1 == 2, "matemática básica"
            escrever("passou")
    """, "", id="afirmar_verdadeiro_nao_interrompe"),

    pytest.param("""
        algoritmo "T"
        inicio
            se nao falso e (verdadeiro ou falso) entao
                escrever("logica ok")
            senao
                escrever("logica errada")
    """, "", id="operadores_logicos_dentro_de_condicao"),

    pytest.param("""
        algoritmo "T"
        inicio
            a:inteiro
            b:cadeia
            ler(a)
            ler(b)
            escrever(a, " ", b)
    """, "5\nolá\n", id="leitura_inteiro_e_cadeia"),

    pytest.param("""
        algoritmo "T"
        constante PI:decimal = 3.14
        total:inteiro = 100
        funcao dobro(n:inteiro):inteiro
            devolver n * 2
        inicio
            escrever(PI, " ", total, " ", dobro(total))
    """, "", id="globais_e_constantes"),

    pytest.param("""
        algoritmo "T"
        estrutura Pessoa
            nome:cadeia
            idade:inteiro
        inicio
            i:inteiro
            pessoas:Pessoa[2] = {{nome: "Ana", idade: 30}, {nome: "Bruno", idade: 25}}
            para i de 0 ate 1 fazer
                escrever(pessoas[i].nome, " tem ", pessoas[i].idade, " anos")
    """, "", id="array_de_literais_de_estrutura"),

    pytest.param("""
        algoritmo "T"
        estrutura No
            valor:inteiro
            proximo:No
        inicio
            terceiro:No = {valor: 3, proximo: nulo}
            segundo:No = {valor: 2, proximo: terceiro}
            primeiro:No = {valor: 1, proximo: segundo}
            n:No = primeiro
            enquanto n <> nulo fazer
                escrever(n.valor)
                n = n.proximo
    """, "", id="lista_ligada_com_nulo"),
]


@pytest.mark.parametrize("codigo_algo,entrada", CORPUS)
def test_paridade_comportamental_normal_vs_minimo(codigo_algo, entrada):
    saida_normal, saida_minimo = _saidas_normal_e_minimo(codigo_algo, entrada)
    assert saida_normal == saida_minimo


# ---------- divergências intencionais e já documentadas (NÃO fazem
# parte do corpus acima -- confirmam explicitamente que a exceção
# continua a comportar-se como descrito, não que os dois modos
# coincidem). Cada uma já tinha teste próprio antes desta etapa
# (test_compila_minimo.py, inoperável aqui por depender do 'algo' no
# PATH); reescritos aqui em processo, pela mesma razão dos testes
# '_em_processo' da Etapa 5. ----------

def test_divergencia_intencional_array_por_valor_e_mutado_no_chamador_em_minimo():
    """Documentado como DIVERGÊNCIA INTENCIONAL (test_minimo_array_por_
    valor_e_mutado_no_chamador_divergencia_intencional em
    test_compila_minimo.py): o modo normal faz cópia defensiva de um
    array passado por valor; --minimo passa a lista Python nua (sem
    cópia), por isso um array "por valor" ainda é mutado no chamador em
    --minimo, mas NÃO no modo normal -- é o próprio contrato documentado
    de --minimo ('sem funções de apoio', incluindo a que faria a cópia)."""
    codigo_algo = textwrap.dedent("""
        algoritmo "T"
        procedimento mutar(v:inteiro[])
            v[0] = 99
        inicio
            a:inteiro[3] = {1, 2, 3}
            mutar(a)
            escrever(a[0])
    """)
    programa_normal = parse(codigo_algo)
    verificar(programa_normal)
    saida_normal = _correr_python(gerar_python(programa_normal))
    programa_minimo = parse(codigo_algo)
    saida_minimo = _correr_python(gerar_python_minimo(programa_minimo))
    assert saida_normal.strip() == "1"
    assert saida_minimo.strip() == "99"
    assert saida_normal != saida_minimo


def test_divergencia_intencional_booleano_impresso_em_minimo():
    """Documentado como DIVERGÊNCIA INTENCIONAL (test_minimo_booleano_e_
    python_puro_nao_traduzido em test_compila_minimo.py): o modo normal
    traduz um booleano para 'verdadeiro'/'falso' ao escrever; --minimo
    usa print() diretamente sobre o bool nativo do Python, por isso
    aparece 'True'/'False' -- é o próprio contrato documentado de
    --minimo ('sem funções de apoio', incluindo a que traduziria)."""
    codigo_algo = textwrap.dedent("""
        algoritmo "T"
        inicio
            escrever(nao falso e (verdadeiro ou falso))
    """)
    programa_normal = parse(codigo_algo)
    verificar(programa_normal)
    saida_normal = _correr_python(gerar_python(programa_normal))
    programa_minimo = parse(codigo_algo)
    saida_minimo = _correr_python(gerar_python_minimo(programa_minimo))
    assert saida_normal.strip() == "verdadeiro"
    assert saida_minimo.strip() == "True"
    assert saida_normal != saida_minimo


# ---------- Achado real da Etapa 6 (bug, não divergência documentada):
# um literal '{...}' aninhado (struct-em-struct, ou struct-em-array) --
# ou até um literal de estrutura NÃO aninhado passado como argumento de
# chamada -- fazia o PRÓPRIO COMPILADOR --minimo rebentar com
# ErroInternoCompilador, num programa 100% válido que compila e corre
# normalmente em modo normal. Causa: codegen_minimo.py nunca teve o
# par _expr_estrutura_literal/_expr_array_literal que codegen.py já
# tinha desde AL-78/B8 -- cada sítio que conhece o tipo esperado
# construía os campos/elementos chamando _expr() genérico, que não tem
# ramo nenhum para A.EstruturaLiteral. Corrigido em codegen_minimo.py
# (+ gerador_base.py::_gerar_atribuicao, partilhado) adicionando esse
# par de métodos e usando-o nos 4 pontos de entrada -- exatamente como
# codegen.py já fazia. Dois dos 4 pontos (declaração) já ficam
# cobertos pelo corpus acima (estrutura_aninhada_literal,
# array_de_literais_de_estrutura); os outros 2 (argumento de chamada,
# atribuição -- devolver também tinha o mesmo bug mas partilha o mesmo
# código-fonte de declaração) têm teste dedicado aqui, cada um falhava
# com ErroInternoCompilador antes desta correção. ----------

def test_literal_de_estrutura_como_argumento_de_chamada_em_minimo():
    codigo_algo = textwrap.dedent("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        procedimento mostrar(p:Ponto)
            escrever(p.x, " ", p.y)
        inicio
            mostrar({x: 1, y: 2})
    """)
    saida_normal, saida_minimo = _saidas_normal_e_minimo(codigo_algo)
    assert saida_normal == saida_minimo == "1 2\n"


def test_literal_de_estrutura_aninhado_em_atribuicao_em_minimo():
    codigo_algo = textwrap.dedent("""
        algoritmo "T"
        estrutura Ponto
            x:decimal
        estrutura Linha
            inicio_pt:Ponto
        inicio
            l:Linha
            l = {inicio_pt: {x: 1.0}}
            escrever(l.inicio_pt.x)
    """)
    saida_normal, saida_minimo = _saidas_normal_e_minimo(codigo_algo)
    assert saida_normal == saida_minimo == "1.0\n"


def test_literal_de_estrutura_aninhado_em_devolver_em_minimo():
    codigo_algo = textwrap.dedent("""
        algoritmo "T"
        estrutura Ponto
            x:decimal
        estrutura Linha
            inicio_pt:Ponto
        funcao criar():Linha
            devolver {inicio_pt: {x: 1.0}}
        inicio
            l:Linha = criar()
            escrever(l.inicio_pt.x)
    """)
    saida_normal, saida_minimo = _saidas_normal_e_minimo(codigo_algo)
    assert saida_normal == saida_minimo == "1.0\n"
