# -*- coding: utf-8 -*-
"""Nós da AST para a linguagem ALGO."""


class No:
    pass


class Programa(No):
    def __init__(self, nome, importares, inclusoes, estruturas, declaracoes, funcoes, corpo):
        self.nome = nome
        self.importares = importares         # lista de Importar
        self.inclusoes = inclusoes           # lista de Incluir
        self.estruturas = estruturas         # lista de EstruturaDef
        self.declaracoes = declaracoes       # lista de Declaracao (globais, antes de 'inicio')
        self.funcoes = funcoes               # lista de FuncaoDef
        self.corpo = corpo                   # lista de stmts (bloco 'inicio')


class EstruturaDef(No):
    def __init__(self, nome, campos, linha):
        self.nome = nome
        self.campos = campos   # lista de Declaracao (nome do campo + tipo [+ dims])
        self.linha = linha


class Importar(No):
    def __init__(self, nome, linha):
        self.nome = nome
        self.linha = linha


class Incluir(No):
    def __init__(self, caminho, linha):
        self.caminho = caminho
        self.linha = linha


class Declaracao(No):
    def __init__(self, tipo, nome, dims, linha, inicial=None, eh_constante=False):
        self.tipo = tipo
        self.nome = nome
        self.dims = dims          # lista de expressões (0, 1 ou 2 dimensões) ou None
        self.linha = linha
        self.inicial = inicial    # expressão de inicialização, ou None
        self.eh_constante = eh_constante


class Parametro(No):
    def __init__(self, nome, tipo, por_referencia):
        self.nome = nome
        self.tipo = tipo
        self.por_referencia = por_referencia


class FuncaoDef(No):
    def __init__(self, nome, tipo_retorno, parametros, corpo, linha, eh_procedimento):
        self.nome = nome
        self.tipo_retorno = tipo_retorno   # None se for procedimento
        self.parametros = parametros
        self.corpo = corpo
        self.linha = linha
        self.eh_procedimento = eh_procedimento


# ---- statements ----

class Atribuicao(No):
    def __init__(self, alvo, expr, linha):
        self.alvo = alvo
        self.expr = expr
        self.linha = linha


class Ler(No):
    def __init__(self, alvos, linha):
        self.alvos = alvos
        self.linha = linha


class Escrever(No):
    def __init__(self, exprs, linha):
        self.exprs = exprs
        self.linha = linha


class Se(No):
    def __init__(self, ramos, senao, linha):
        self.ramos = ramos
        self.senao = senao
        self.linha = linha


class Para(No):
    def __init__(self, var, ini, fim, passo, corpo, linha):
        self.var = var
        self.ini = ini
        self.fim = fim
        self.passo = passo
        self.corpo = corpo
        self.linha = linha


class Enquanto(No):
    def __init__(self, condicao, corpo, linha):
        self.condicao = condicao
        self.corpo = corpo
        self.linha = linha


class FazEnquanto(No):
    def __init__(self, corpo, condicao, linha):
        self.corpo = corpo
        self.condicao = condicao
        self.linha = linha


class Escolha(No):
    def __init__(self, expr, casos, contrario, linha):
        self.expr = expr
        self.casos = casos
        self.contrario = contrario
        self.linha = linha


class Devolver(No):
    def __init__(self, expr, linha):
        self.expr = expr
        self.linha = linha


class ChamadaStmt(No):
    def __init__(self, chamada, linha):
        self.chamada = chamada
        self.linha = linha


# ---- expressões ----

class LValue(No):
    def __init__(self, nome, acessos, linha):
        self.nome = nome
        self.acessos = acessos   # lista de ('indice', expr) ou ('campo', nome_str)
        self.linha = linha


class Literal(No):
    def __init__(self, valor, tipo, linha=0):
        self.valor = valor
        self.tipo = tipo   # 'inteiro' | 'decimal' | 'booleano' | 'cadeia' | 'caracter'
        self.linha = linha


class BinOp(No):
    def __init__(self, op, esq, dire, linha):
        self.op = op
        self.esq = esq
        self.dire = dire
        self.linha = linha


class UnOp(No):
    def __init__(self, op, operando, linha):
        self.op = op
        self.operando = operando
        self.linha = linha


class Chamada(No):
    def __init__(self, nome, args, linha):
        self.nome = nome    # pode conter '.' para chamadas de biblioteca (ex: "math.raiz")
        self.args = args
        self.linha = linha


class ArrayLiteral(No):
    def __init__(self, elementos, linha):
        self.elementos = elementos   # lista de expressões (podem ser outros ArrayLiteral, para 2D)
        self.linha = linha


class EstruturaLiteral(No):
    def __init__(self, campos, linha):
        self.campos = campos   # lista de (nome_campo, expr); campos omitidos ficam com valor por omissão
        self.linha = linha


class Afirmar(No):
    def __init__(self, condicao, mensagem, linha):
        self.condicao = condicao
        self.mensagem = mensagem   # expressão (cadeia) ou None
        self.linha = linha


# ---------------------------------------------------------------------------
# Utilitários de percurso da AST, partilhados pelo verificador de tipos, pelo
# gerador de código Python, pelo gerador de fluxogramas e pelos
# transpiladores -- evita reimplementar a mesma travessia em cada sítio.
# ---------------------------------------------------------------------------

def subblocos(stmt):
    """Devolve a lista de blocos de instruções aninhados dentro de uma
    instrução composta (se/para/enquanto/fazer-enquanto/escolher). Uma
    instrução simples (atribuição, escrever, ...) devolve uma lista vazia.
    """
    blocos = []
    if isinstance(stmt, Se):
        blocos.extend(corpo for _cond, corpo in stmt.ramos)
        if stmt.senao:
            blocos.append(stmt.senao)
    elif isinstance(stmt, (Para, Enquanto, FazEnquanto)):
        blocos.append(stmt.corpo)
    elif isinstance(stmt, Escolha):
        blocos.extend(corpo for _valores, corpo in stmt.casos)
        if stmt.contrario:
            blocos.append(stmt.contrario)
    return blocos


def coletar_declaracoes_tipadas(stmts, destino):
    """Percorre recursivamente uma lista de instruções (incluindo dentro de
    blocos aninhados) e regista em 'destino' (dict nome -> tipo) todas as
    variáveis declaradas com 'nome:tipo' e as variáveis de controlo dos
    ciclos 'para'. Usado para saber, em qualquer ponto da geração de
    código, que variáveis existem e de que tipo são."""
    for s in stmts:
        if isinstance(s, Declaracao):
            destino[s.nome] = s.tipo
        elif isinstance(s, Para):
            destino.setdefault(s.var, "inteiro")
        for bloco in subblocos(s):
            coletar_declaracoes_tipadas(bloco, destino)


def coletar_identificadores(programa):
    """Devolve a lista de todos os identificadores (nome, linha) que o
    programa declara -- variáveis (globais e locais, em qualquer nível de
    aninhamento), variáveis de controlo de 'para', parâmetros, nomes de
    função/procedimento, nomes de estrutura e nomes de campo. Usado para
    verificar se algum colide com uma palavra reservada do PYTHON (não do
    ALGO) -- coisas como 'class' ou 'import' são identificadores válidos
    em ALGO, mas gerariam Python sintaticamente inválido."""
    nomes = []

    def _de_stmts(stmts):
        for s in stmts:
            if isinstance(s, Declaracao):
                nomes.append((s.nome, s.linha))
            elif isinstance(s, Para):
                nomes.append((s.var, s.linha))
            for bloco in subblocos(s):
                _de_stmts(bloco)

    for d in programa.declaracoes:
        nomes.append((d.nome, d.linha))
    _de_stmts(programa.corpo)

    for f in programa.funcoes:
        nomes.append((f.nome, f.linha))
        for p in f.parametros:
            nomes.append((p.nome, f.linha))
        _de_stmts(f.corpo)

    for e in programa.estruturas:
        nomes.append((e.nome, e.linha))
        for c in e.campos:
            nomes.append((c.nome, e.linha))

    return nomes


def texto_expr(expr):
    """Representação textual legível de uma expressão -- usada nos
    rótulos do fluxograma (tools/flowchart.py) e nas mensagens de
    'afirmar' (compilador/codegen.py). ARCH-02: vive aqui, não em
    tools/flowchart.py, porque tools/ deve depender do compilador, não
    o inverso -- codegen.py importar isto de tools/flowchart.py fazia
    uma mudança pensada só para o fluxograma alterar silenciosamente as
    mensagens de 'afirmar' nos programas gerados.

    Devolve texto NÃO escapado -- pode conter aspas/chavetas/backslash
    vindos de literais do próprio código do estudante. Nunca embutir o
    resultado diretamente numa f-string ou noutro código a reavaliar
    (usar repr() para isso, como em codegen.py:_gerar_afirmar); os
    chamadores em tools/flowchart.py passam sempre o resultado por
    _escapar() antes de o inserir num rótulo DOT."""
    if isinstance(expr, Literal):
        if expr.tipo == "cadeia":
            return f'"{expr.valor}"'
        if expr.tipo == "caracter":
            return f"'{expr.valor}'"
        if expr.tipo == "booleano":
            return "verdadeiro" if expr.valor else "falso"
        return str(expr.valor)
    if isinstance(expr, LValue):
        base = expr.nome
        for tag, valor in expr.acessos:
            base += f"[{texto_expr(valor)}]" if tag == "indice" else f".{valor}"
        return base
    if isinstance(expr, BinOp):
        return f"{texto_expr(expr.esq)} {expr.op} {texto_expr(expr.dire)}"
    if isinstance(expr, UnOp):
        return f"{expr.op} {texto_expr(expr.operando)}"
    if isinstance(expr, Chamada):
        args = ", ".join(texto_expr(a) for a in expr.args)
        return f"{expr.nome}({args})"
    if isinstance(expr, ArrayLiteral):
        return "{" + ", ".join(texto_expr(e) for e in expr.elementos) + "}"
    if isinstance(expr, EstruturaLiteral):
        campos = ", ".join(f"{nome}: {texto_expr(valor)}" for nome, valor in expr.campos)
        return "{" + campos + "}"
    return "?"  # pragma: no cover -- os 7 tipos de expressão da AST estão todos tratados acima
