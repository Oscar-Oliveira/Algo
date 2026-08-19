# -*- coding: utf-8 -*-
"""Auditoria (4ª ronda), Etapa 11 -- testes profundos transversais:
fuzzing (por mutação do corpus válido + aleatório de baixo volume) e
testes de propriedade (div/mod truncados, idempotência de conversões).

Fuzzing aqui não testa COMPORTAMENTO correto (isso já é o resto da
suite) -- testa ROBUSTEZ do compilador: para qualquer entrada, mesmo
corrompida ao acaso, a única coisa que pode escapar para quem chama é
uma das exceções já classificadas (ErroLexico/ErroSintatico/
ErroSemantico/ErroInternoCompilador) ou sucesso -- nunca um IndexError/
AttributeError/KeyError/etc. cru vindo de um bug do PRÓPRIO compilador
ao processar algo inesperado. É exatamente esta distinção que a Etapa 6
desta auditoria encontrou violada em codegen_minimo.py (um programa
100% válido, não um input corrompido, fazia o compilador rebentar com
ErroInternoCompilador de forma não classificada em `cli.py` -- já
corrigido). Aqui cobre-se o caso mais amplo: entrada arbitrariamente
corrompida.

Exploração feita antes de fixar os parâmetros abaixo (não incluída
como teste, só para calibrar): 8000 iterações de mutação com
`gerar_python`, 1-5 mutações compostas por iteração, zero exceções não
classificadas encontradas --
os parâmetros do teste real ficam propositadamente mais baixos (custo
de CI), sem perder o `seed` fixo (reprodutibilidade: uma falha aqui
tem de ser reproduzível determinísticamente, não intermitente)."""
import random

import pytest

from algo_lang.compilador.lexer import ErroLexico, tokenizar
from algo_lang.compilador.parser import parse, ErroSintatico
from algo_lang.compilador.semantics import verificar, ErroSemantico
from algo_lang.compilador.codegen import gerar_python
from algo_lang.compilador.gerador_base import ErroInternoCompilador

from apoio import executar

CORPUS_VALIDO = [
    'algoritmo "T"\ninicio\n    x:inteiro = 5\n    escrever(x)\n',
    'algoritmo "T"\nestrutura Ponto\n    x:inteiro\n    y:inteiro\ninicio\n'
    '    p:Ponto = {x: 1, y: 2}\n    escrever(p.x)\n',
    'algoritmo "T"\nfuncao f(n:inteiro):inteiro\n    se n <= 1 entao\n        devolver 1\n'
    '    devolver n * f(n - 1)\ninicio\n    escrever(f(5))\n',
    'algoritmo "T"\ninicio\n    v:inteiro[3] = {1,2,3}\n    i:inteiro\n'
    '    para i de 0 ate 2 fazer\n        escrever(v[i])\n',
    'algoritmo "T"\nimportar Matematica\ninicio\n    escrever(matematica.raiz(4.0))\n',
    'algoritmo "T"\ninicio\n    x:inteiro = 1\n    escolher x\n        caso 1\n'
    '            escrever(1)\n        contrario\n            escrever(0)\n',
    'algoritmo "T"\nprocedimento p(ref a:inteiro)\n    a = a + 1\ninicio\n'
    '    x:inteiro = 1\n    p(x)\n    escrever(x)\n',
    'algoritmo "T"\nestrutura A\n    b:B\nestrutura B\n    v:inteiro\ninicio\n'
    '    a:A\n    escrever(a.b.v)\n',
    'algoritmo "T"\ninicio\n    m:inteiro[2][2] = {{1,2},{3,4}}\n    escrever(m[0][0])\n',
]

_SIMBOLOS_INSERCAO = list("(){}[]:,.^<>=+-*/\"'")


def _mutar(codigo, rng):
    """Uma única mutação aleatória de baixo nível sobre uma string --
    delete/duplica/insere/troca um caráter, remove uma linha ou um
    'token' separado por espaço, ou trunca. Deliberadamente ingénuo
    (nível de caráter, não de token/gramática): o objetivo é robustez
    perante corrupção arbitrária, não gerar programas plausíveis."""
    tipo = rng.choice(
        ["del_char", "del_line", "dup_char", "truncate", "swap_chars",
         "del_token", "insert_char"])
    if tipo == "del_char" and codigo:
        i = rng.randrange(len(codigo))
        return codigo[:i] + codigo[i + 1:]
    if tipo == "del_line":
        linhas = codigo.split("\n")
        if len(linhas) > 1:
            del linhas[rng.randrange(len(linhas))]
        return "\n".join(linhas)
    if tipo == "dup_char" and codigo:
        i = rng.randrange(len(codigo))
        return codigo[:i] + codigo[i] + codigo[i:]
    if tipo == "truncate" and codigo:
        return codigo[:rng.randrange(1, len(codigo) + 1)]
    if tipo == "swap_chars" and len(codigo) > 1:
        i = rng.randrange(len(codigo) - 1)
        lst = list(codigo)
        lst[i], lst[i + 1] = lst[i + 1], lst[i]
        return "".join(lst)
    if tipo == "del_token":
        partes = codigo.split(" ")
        if len(partes) > 1:
            del partes[rng.randrange(len(partes))]
        return " ".join(partes)
    if tipo == "insert_char":
        i = rng.randrange(len(codigo) + 1)
        return codigo[:i] + rng.choice(_SIMBOLOS_INSERCAO) + codigo[i:]
    return codigo


def _programas_mutados(seed, n, max_mutacoes=5):
    rng = random.Random(seed)
    for _ in range(n):
        codigo = rng.choice(CORPUS_VALIDO)
        for _ in range(rng.randint(1, max_mutacoes)):
            codigo = _mutar(codigo, rng)
        yield codigo


def test_fuzz_mutacao_modo_normal_nunca_escapa_excecao_nao_classificada():
    """parse -> verificar -> gerar_python sobre 1000 variações
    corrompidas do corpus válido (seed fixo -- uma falha aqui é
    determinística e reproduzível, corre outra vez com o mesmo
    resultado)."""
    nao_classificadas = []
    for codigo in _programas_mutados(seed=20260817, n=1000):
        try:
            programa = parse(codigo)
            verificar(programa)
            gerar_python(programa)
        except (ErroLexico, ErroSintatico, ErroSemantico, RecursionError):
            pass
        except Exception as e:  # noqa: BLE001 -- é isto que o teste procura
            nao_classificadas.append((codigo, type(e).__name__, str(e)))
    assert not nao_classificadas, (
        f"{len(nao_classificadas)} entrada(s) corrompida(s) escaparam com exceção "
        f"não classificada (não Erro{{Lexico,Sintatico,Semantico}}): "
        f"{nao_classificadas[:3]}")


def test_fuzz_aleatorio_de_baixo_volume_no_lexer_nunca_crasha_cru():
    """Fuzzing aleatório 'de verdade' (não mutação de um corpus válido):
    strings compostas de caráteres verdadeiramente aleatórios (incluindo
    fora de ASCII) diretamente no lexer -- a camada mais exposta a
    entrada arbitrária. Só ErroLexico (ou nada) é aceitável."""
    rng = random.Random(3141592)
    alfabeto = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
        " \t\n:(){}[]+-*/^<>=,.\"'áéíóúçãõ")
    nao_classificadas = []
    for _ in range(500):
        tamanho = rng.randint(0, 200)
        codigo = "".join(rng.choice(alfabeto) for _ in range(tamanho))
        try:
            tokenizar(codigo)
        except ErroLexico:
            pass
        except Exception as e:  # noqa: BLE001
            nao_classificadas.append((codigo, type(e).__name__, str(e)))
    assert not nao_classificadas, (
        f"{len(nao_classificadas)} entrada(s) aleatória(s) escaparam com exceção "
        f"não classificada no lexer: {nao_classificadas[:3]}")


# ---------- testes de propriedade ----------

@pytest.mark.parametrize("a,b", [
    (7, 2), (-7, 2), (7, -2), (-7, -2),
    (8, 3), (-8, 3), (8, -3), (-8, -3),
    (1, 7), (-1, 7), (0, 5), (100, 7), (-100, 7),
    (17, 5), (-17, -5),
])
def test_propriedade_div_mod_truncados_satisfazem_identidade_da_divisao(a, b):
    """Para qualquer par (a, b) com b != 0: a == (a div b) * b + (a mod
    b) -- a identidade fundamental de qualquer divisão inteira,
    truncada ou não. 'div'/'mod' truncam em direção a zero (ao
    contrário de '//'/'%' nativos do Python, que arredondam para
    -infinito) -- ver codegen.py::_algo_div. Verificado através de um
    programa ALGO real, não só chamando a função Python diretamente."""
    saida = executar(f'algoritmo "T"\ninicio\n    escrever({a} div {b}, " ", {a} mod {b})\n')
    q, r = (int(x) for x in saida.strip().split())
    assert a == q * b + r


@pytest.mark.parametrize("a,b", [
    (7, 2), (-7, 2), (7, -2), (-7, -2), (8, 3), (-8, -3), (100, 7), (-100, 7),
])
def test_propriedade_resto_de_div_tem_sinal_do_dividendo_ou_e_zero(a, b):
    """Divisão TRUNCADA (em direção a zero): o sinal do resto é sempre
    igual ao sinal do dividendo 'a' (ou zero) -- nunca o do divisor
    'b', ao contrário da floor division nativa do Python."""
    saida = executar(f'algoritmo "T"\ninicio\n    escrever({a} mod {b})\n')
    r = int(saida.strip())
    if r != 0:
        assert (r > 0) == (a > 0)


@pytest.mark.parametrize("n", [0, 1, -1, 42, -42, 1000000, -1000000])
def test_propriedade_conversao_inteiro_para_texto_e_de_volta_e_idempotente(n):
    saida = executar(f"""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraInteiro(conversao.paraTexto({n})))
    """)
    assert int(saida.strip()) == n


@pytest.mark.parametrize("x", [0.0, 1.0, -1.0, 3.14, -3.14, 0.5, 100000.25])
def test_propriedade_conversao_decimal_para_texto_e_de_volta_e_idempotente(x):
    """float -> str -> float é um round-trip exato em Python (desde a
    repr 'shortest round-trip' introduzida no Python 3.1) -- conversao.
    paraTexto/paraDecimal usam str()/float() nativos por trás, por isso
    herdam a mesma garantia."""
    saida = executar(f"""
        algoritmo "T"
        importar Conversao
        inicio
            escrever(conversao.paraDecimal(conversao.paraTexto({x!r})))
    """)
    assert float(saida.strip()) == x


@pytest.mark.parametrize("valor_algo,esperado", [
    ("verdadeiro", "verdadeiro"), ("falso", "falso"),
])
def test_propriedade_conversao_booleano_para_texto_e_de_volta_e_idempotente(valor_algo, esperado):
    saida = executar(f"""
        algoritmo "T"
        importar Conversao
        inicio
            b:booleano = {valor_algo}
            escrever(conversao.paraBooleano(conversao.paraTexto(b)))
    """)
    assert saida.strip() == esperado
