# -*- coding: utf-8 -*-
"""Gerador de Python MÍNIMO a partir da AST da linguagem ALGO -- modo
'--minimo' de 'algo compila'.

Ao contrário de codegen.py (que gera um programa robusto, com funções de
apoio, mensagens de erro amigáveis e novas tentativas em leituras
inválidas), este gerador produz o Python mais direto possível: sem
nenhuma verificação de tipos prévia (quem chama isto NÃO deve ter
corrido semantics.verificar()), sem funções de apoio -- usa
print()/input() diretamente, math./random. da biblioteca padrão do
Python em vez de reimplementações próprias, e afirmar vira o próprio
assert do Python. Se o programa ALGO tiver um erro de tipos, o Python
gerado aqui simplesmente falha a correr, com o erro nativo do Python --
é exatamente esse o objetivo: mostrar o Python "cru" por trás do ALGO."""

from . import ast_nodes as A
from .semantics import ErroSemantico

CABECALHO_RUNTIME = ""


OPS_BIN = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "div": "//", "mod": "%", "^": "**",
    "==": "==", "<>": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=",
    "e": "and", "ou": "or",
}

LEITORES_INLINE_POR_TIPO = {
    "inteiro": "int(input())",
    "decimal": "float(input())",
    "booleano": '(input() == "verdadeiro")',
    "cadeia": "input()",
    "caracter": "input()",
}

# Cada função de biblioteca ALGO mapeada para a expressão Python "nua"
# equivalente -- 'args' já vem com os argumentos traduzidos para Python.
# Módulos python que cada entrada precisa (para saber que 'import' emitir).
BIBLIOTECA_MINIMA = {
    "math.raiz": (lambda args: f"math.sqrt({args[0]})", "math"),
    "math.potencia": (lambda args: f"({args[0]} ** {args[1]})", None),
    "math.absoluto": (lambda args: f"abs({args[0]})", None),
    "math.piso": (lambda args: f"math.floor({args[0]})", "math"),
    "math.teto": (lambda args: f"math.ceil({args[0]})", "math"),
    "math.aleatorio": (lambda args: f"random.randint({args[0]}, {args[1]})", "random"),
    "cadeia.comprimento": (lambda args: f"len({args[0]})", None),
    "cadeia.maiusculas": (lambda args: f"{args[0]}.upper()", None),
    "cadeia.minusculas": (lambda args: f"{args[0]}.lower()", None),
    "cadeia.inverter": (lambda args: f"{args[0]}[::-1]", None),
    "cadeia.subcadeia": (lambda args: f"{args[0]}[{args[1]}:{args[2]}]", None),
    "cadeia.caracter": (lambda args: f"{args[0]}[{args[1]}]", None),
}

DEFAULT_POR_TIPO = {
    "inteiro": "0",
    "decimal": "0.0",
    "booleano": "False",
    "cadeia": '""',
    "caracter": '""',
}


class GeradorCodigo:
    def __init__(self, programa: A.Programa):
        self.programa = programa
        self.linhas = []
        self.tabela_tipos_globais = {}   # nome -> tipo (tudo o que é global no programa)
        self.refs_atuais = []            # nomes ref da função a gerar neste momento
        self.estruturas = {}
        self.mapa_linhas = {}            # nº de linha do .py gerado -> nº de linha do .algo original
        self._linha_algo_atual = None    # linha ALGO da instrução a ser gerada neste momento

    def emit(self, texto, nivel):
        self.linhas.append("    " * nivel + texto)
        if self._linha_algo_atual is not None:
            self.mapa_linhas[len(self.linhas)] = self._linha_algo_atual

    # -------- ponto de entrada --------
    def gerar(self) -> str:
        self.linhas = [
            "# Ficheiro gerado por 'algo compila --minimo' -- Python o mais direto",
            "# possível a partir do .algo original, sem verificação de tipos prévia",
            "# nem funções de apoio: se o ALGO tinha um erro de tipos, este ficheiro",
            "# simplesmente falha a correr, com o erro nativo do Python.",
        ]

        modulos_python = set()
        nomes_bibliotecas_importadas = {imp.nome.lower() for imp in self.programa.importares}
        if "math" in nomes_bibliotecas_importadas:
            modulos_python.add("math")
            modulos_python.add("random")
        for mod in sorted(modulos_python):
            self.linhas.append(f"import {mod}")
        if modulos_python:
            self.linhas.append("")
        self.linhas.append("")

        self.estruturas = {}
        for e in self.programa.estruturas:
            campos = {}
            for c in e.campos:
                dims_n = 0 if c.dims is None else len(c.dims)
                campos[c.nome] = (c.tipo, dims_n)
            self.estruturas[e.nome] = campos

        for e in self.programa.estruturas:
            self._gerar_estrutura(e)

        # tabela de globais = declarações de topo + tudo o que é declarado dentro de 'inicio'
        for d in self.programa.declaracoes:
            self.tabela_tipos_globais[d.nome] = d.tipo
        A.coletar_declaracoes_tipadas(self.programa.corpo, self.tabela_tipos_globais)

        for f in self.programa.funcoes:
            self._gerar_funcao(f)

        for d in self.programa.declaracoes:
            self._linha_algo_atual = d.linha
            self._gerar_declaracao(d, 0, self.tabela_tipos_globais)
        self._linha_algo_atual = None
        if self.programa.declaracoes:
            self.linhas.append("")

        tipos = dict(self.tabela_tipos_globais)
        for stmt in self.programa.corpo:
            self._gerar_stmt(stmt, 0, tipos)
        self._linha_algo_atual = None
        self.linhas.append("")
        return "\n".join(self.linhas)

    def _gerar_estrutura(self, e: A.EstruturaDef):
        self._linha_algo_atual = e.linha
        params_kwargs = []
        for c in e.campos:
            if c.dims is not None or c.tipo not in DEFAULT_POR_TIPO:
                # array OU campo de tipo estrutura: o valor por omissão tem
                # de ser construído dentro do __init__, nunca como valor
                # por omissão direto do parâmetro -- um valor por omissão
                # de parâmetro só é avaliado UMA VEZ (quando a classe é
                # definida), por isso todas as instâncias partilhariam o
                # mesmo objeto ("mutable default argument", um erro
                # clássico do Python) em vez de cada uma ter o seu próprio
                params_kwargs.append(f"{c.nome}=None")
            else:
                params_kwargs.append(f"{c.nome}={self._valor_default(c.tipo)}")
        assinatura = ", ".join(["self"] + params_kwargs)
        self.emit(f"class {e.nome}:", 0)
        self.emit(f"def __init__({assinatura}):", 1)
        if not e.campos:  # pragma: no cover -- o parser exige >=1 campo em 'estrutura'
            self.emit("pass", 2)
        for c in e.campos:
            if c.dims is not None:
                valor_default = self._construir_array_aninhado(c.tipo, c.dims, {})
                self.emit(f"self.{c.nome} = {c.nome} if {c.nome} is not None else {valor_default}", 2)
            elif c.tipo not in DEFAULT_POR_TIPO:
                valor_default = self._valor_default(c.tipo)
                self.emit(f"self.{c.nome} = {c.nome} if {c.nome} is not None else {valor_default}", 2)
            else:
                self.emit(f"self.{c.nome} = {c.nome}", 2)
        self._linha_algo_atual = None
        self.linhas.append("")

    # -------- declarações --------
    def _valor_default(self, tipo):
        if tipo in DEFAULT_POR_TIPO:
            return DEFAULT_POR_TIPO[tipo]
        return f"{tipo}()"   # instância por omissão de uma estrutura

    def _gerar_declaracao(self, d: A.Declaracao, nivel, tipos):
        if d.inicial is not None and isinstance(d.inicial, A.EstruturaLiteral):
            kwargs = ", ".join(
                f"{nome}={self._expr(valor, tipos)}" for nome, valor in d.inicial.campos)
            self.emit(f"{d.nome} = {d.tipo}({kwargs})", nivel)
            return
        if d.inicial is not None and isinstance(d.inicial, A.Chamada):
            f_def = self._encontrar_funcao(d.inicial.nome)
            if f_def and any(p.por_referencia for p in f_def.parametros):
                out_vars = [
                    self._lvalue_de_expr(a, tipos)
                    for p, a in zip(f_def.parametros, d.inicial.args)
                    if p.por_referencia
                ]
                args_str = ", ".join(self._expr(a, tipos) for a in d.inicial.args)
                self.emit(f"{d.nome}, {', '.join(out_vars)} = {d.inicial.nome}({args_str})", nivel)
                return
        if d.inicial is not None:
            self.emit(f"{d.nome} = {self._expr(d.inicial, tipos)}", nivel)
        elif d.dims is None:
            self.emit(f"{d.nome} = {self._valor_default(d.tipo)}", nivel)
        else:
            self.emit(f"{d.nome} = {self._construir_array_aninhado(d.tipo, d.dims, tipos)}", nivel)

    def _construir_array_aninhado(self, tipo, dims_exprs, tipos):
        """Constrói recursivamente a expressão Python de um array com N
        dimensões, ex: [[0 for _ in range(c)] for _ in range(l)] para 2D."""
        if not dims_exprs:
            return self._valor_default(tipo)
        tam = self._expr(dims_exprs[0], tipos)
        interior = self._construir_array_aninhado(tipo, dims_exprs[1:], tipos)
        return f"[{interior} for _ in range({tam})]"

    # -------- funções --------
    def _gerar_funcao(self, f: A.FuncaoDef):
        self._linha_algo_atual = f.linha
        params_py = [p.nome for p in f.parametros]
        self.emit(f"def {f.nome}({', '.join(params_py)}):", 0)

        nomes_locais = {p.nome for p in f.parametros}
        nomes_locais_dict = {}
        A.coletar_declaracoes_tipadas(f.corpo, nomes_locais_dict)
        nomes_locais |= set(nomes_locais_dict.keys())

        nomes_globais_usadas = [n for n in self.tabela_tipos_globais if n not in nomes_locais]
        if nomes_globais_usadas:
            self.emit(f"global {', '.join(nomes_globais_usadas)}", 1)

        tipos_locais = dict(self.tabela_tipos_globais)
        for p in f.parametros:
            tipos_locais[p.nome] = p.tipo

        self.refs_atuais = [p.nome for p in f.parametros if p.por_referencia]

        if not f.corpo:  # pragma: no cover -- o parser exige >=1 instrução no corpo
            self.emit("pass", 1)
        for stmt in f.corpo:
            self._gerar_stmt(stmt, 1, tipos_locais)

        if f.eh_procedimento and self.refs_atuais:
            self._linha_algo_atual = f.linha
            self.emit(f"return {', '.join(self.refs_atuais)}", 1)

        self.refs_atuais = []
        self._linha_algo_atual = None
        self.linhas.append("")

    # -------- statements --------
    def _gerar_stmt(self, stmt, nivel, tipos):
        if getattr(stmt, "linha", None) is not None:
            self._linha_algo_atual = stmt.linha
        if isinstance(stmt, A.Declaracao):
            tipos[stmt.nome] = stmt.tipo
            self._gerar_declaracao(stmt, nivel, tipos)
        elif isinstance(stmt, A.Atribuicao):
            self._gerar_atribuicao(stmt, nivel, tipos)
        elif isinstance(stmt, A.Ler):
            self._gerar_ler(stmt, nivel, tipos)
        elif isinstance(stmt, A.Escrever):
            args = ", ".join(self._expr(e, tipos) for e in stmt.exprs)
            self.emit(f'print({args}, sep="")', nivel)
        elif isinstance(stmt, A.Se):
            self._gerar_se(stmt, nivel, tipos)
        elif isinstance(stmt, A.Para):
            self._gerar_para(stmt, nivel, tipos)
        elif isinstance(stmt, A.Enquanto):
            self.emit(f"while {self._expr(stmt.condicao, tipos)}:", nivel)
            self._gerar_corpo(stmt.corpo, nivel + 1, tipos)
        elif isinstance(stmt, A.FazEnquanto):
            self.emit("while True:", nivel)
            self._gerar_corpo(stmt.corpo, nivel + 1, tipos)
            self.emit(f"if not ({self._expr(stmt.condicao, tipos)}):", nivel + 1)
            self.emit("break", nivel + 2)
        elif isinstance(stmt, A.Escolha):
            self._gerar_escolha(stmt, nivel, tipos)
        elif isinstance(stmt, A.Devolver):
            valor = self._expr(stmt.expr, tipos)
            if self.refs_atuais:
                self.emit(f"return {valor}, {', '.join(self.refs_atuais)}", nivel)
            else:
                self.emit(f"return {valor}", nivel)
        elif isinstance(stmt, A.ChamadaStmt):
            self._gerar_chamada_stmt(stmt, nivel, tipos)
        elif isinstance(stmt, A.Afirmar):
            self._gerar_afirmar(stmt, nivel, tipos)
        else:  # pragma: no cover -- todos os tipos de instrução da AST são tratados acima
            raise ErroSemantico(f"instrução não suportada: {type(stmt).__name__}", getattr(stmt, "linha", 0))

    def _gerar_afirmar(self, stmt: A.Afirmar, nivel, tipos):
        cond_py = self._expr(stmt.condicao, tipos)
        if stmt.mensagem is not None:
            msg_py = self._expr(stmt.mensagem, tipos)
            self.emit(f"assert {cond_py}, {msg_py}", nivel)
        else:
            self.emit(f"assert {cond_py}", nivel)

    def _gerar_corpo(self, corpo, nivel, tipos):
        if not corpo:  # pragma: no cover -- o parser exige >=1 instrução em qualquer bloco
            self.emit("pass", nivel)
            return
        for stmt in corpo:
            self._gerar_stmt(stmt, nivel, tipos)

    def _gerar_atribuicao(self, stmt: A.Atribuicao, nivel, tipos):
        if isinstance(stmt.expr, A.Chamada):
            f_def = self._encontrar_funcao(stmt.expr.nome)
            if f_def and any(p.por_referencia for p in f_def.parametros):
                out_vars = [
                    self._lvalue_de_expr(a, tipos)
                    for p, a in zip(f_def.parametros, stmt.expr.args)
                    if p.por_referencia
                ]
                args_str = ", ".join(self._expr(a, tipos) for a in stmt.expr.args)
                alvo = self._lvalue(stmt.alvo, tipos)
                self.emit(f"{alvo}, {', '.join(out_vars)} = {stmt.expr.nome}({args_str})", nivel)
                return
        alvo = self._lvalue(stmt.alvo, tipos)
        expr = self._expr(stmt.expr, tipos)
        self.emit(f"{alvo} = {expr}", nivel)

    def _gerar_ler(self, stmt: A.Ler, nivel, tipos):
        for alvo in stmt.alvos:
            tipo = self._tipo_final_lvalue(alvo, tipos)
            leitor = LEITORES_INLINE_POR_TIPO.get(tipo, "input()")
            destino = self._lvalue(alvo, tipos)
            self.emit(f"{destino} = {leitor}", nivel)

    def _gerar_se(self, stmt: A.Se, nivel, tipos):
        primeiro = True
        for cond, corpo in stmt.ramos:
            self._linha_algo_atual = getattr(cond, "linha", stmt.linha)
            palavra = "if" if primeiro else "elif"
            self.emit(f"{palavra} {self._expr(cond, tipos)}:", nivel)
            self._gerar_corpo(corpo, nivel + 1, tipos)
            primeiro = False
        if stmt.senao is not None:
            self.emit("else:", nivel)
            self._gerar_corpo(stmt.senao, nivel + 1, tipos)

    def _gerar_para(self, stmt: A.Para, nivel, tipos):
        ini = self._expr(stmt.ini, tipos)
        fim = self._expr(stmt.fim, tipos)
        passo = self._expr(stmt.passo, tipos) if stmt.passo else "1"
        self.emit(
            f"for {stmt.var} in range({ini}, ({fim}) + (1 if ({passo}) > 0 else -1), {passo}):",
            nivel,
        )
        tipos_loop = dict(tipos)
        tipos_loop[stmt.var] = "inteiro"
        self._gerar_corpo(stmt.corpo, nivel + 1, tipos_loop)

    def _gerar_escolha(self, stmt: A.Escolha, nivel, tipos):
        var_tmp = "_algo_escolha_val"
        self.emit(f"{var_tmp} = {self._expr(stmt.expr, tipos)}", nivel)
        primeiro = True
        for valores, corpo in stmt.casos:
            self._linha_algo_atual = getattr(valores[0], "linha", stmt.linha)
            comparacoes = " or ".join(f"{var_tmp} == {self._expr(v, tipos)}" for v in valores)
            palavra = "if" if primeiro else "elif"
            self.emit(f"{palavra} {comparacoes}:", nivel)
            self._gerar_corpo(corpo, nivel + 1, tipos)
            primeiro = False
        if stmt.contrario is not None:
            self.emit("else:", nivel)
            self._gerar_corpo(stmt.contrario, nivel + 1, tipos)

    def _gerar_chamada_stmt(self, stmt: A.ChamadaStmt, nivel, tipos):
        chamada = stmt.chamada
        f_def = self._encontrar_funcao(chamada.nome)
        if f_def and any(p.por_referencia for p in f_def.parametros):
            out_vars = [
                self._lvalue_de_expr(a, tipos)
                for p, a in zip(f_def.parametros, chamada.args)
                if p.por_referencia
            ]
            args_str = ", ".join(self._expr(a, tipos) for a in chamada.args)
            if f_def.eh_procedimento:
                self.emit(f"{', '.join(out_vars)} = {chamada.nome}({args_str})", nivel)
            else:
                self.emit(f"_, {', '.join(out_vars)} = {chamada.nome}({args_str})", nivel)
        else:
            self.emit(self._expr(chamada, tipos), nivel)

    def _lvalue_de_expr(self, expr, tipos):
        if isinstance(expr, A.LValue):
            return self._lvalue(expr, tipos)
        raise ErroSemantico(  # pragma: no cover -- semantics.py já valida isto antes
            "argumentos passados por referência têm de ser uma variável, um "
            "elemento de array ou um campo", 0)

    def _encontrar_funcao(self, nome):
        if "." in nome:
            return None
        for f in self.programa.funcoes:
            if f.nome == nome:
                return f
        return None  # pragma: no cover -- semantics.py já garante que existe, se não tiver "."

    # -------- lvalue / expressões --------
    def _lvalue(self, lv: A.LValue, tipos):
        base = lv.nome
        for tag, valor in lv.acessos:
            if tag == "indice":
                base += f"[{self._expr(valor, tipos)}]"
            else:
                base += f".{valor}"
        return base

    def _tipo_final_lvalue(self, lv: A.LValue, tipos):
        """Resolve o tipo final de um LValue (percorrendo acessos a campos
        de estrutura) para escolher o leitor certo em 'ler(...)'."""
        tipo_atual = tipos.get(lv.nome, "cadeia")
        for tag, valor in lv.acessos:
            if tag == "campo":
                campos = self.estruturas.get(tipo_atual, {})
                tipo_atual = campos.get(valor, ("cadeia", 0))[0]
        return tipo_atual

    def _expr(self, expr, tipos):
        if expr is None:  # pragma: no cover -- nenhum chamador passa None (todos são guardados)
            return ""
        if isinstance(expr, A.Literal):
            if expr.tipo in ("cadeia", "caracter"):
                escapado = expr.valor.replace("\\", "\\\\").replace('"', '\\"')
                return f'"{escapado}"'
            if expr.tipo == "booleano":
                return "True" if expr.valor else "False"
            return repr(expr.valor)
        if isinstance(expr, A.LValue):
            return self._lvalue(expr, tipos)
        if isinstance(expr, A.BinOp):
            if expr.op in ("div", "mod"):
                # AL-05: divisão truncada (arredonda em direção a zero),
                # não a floor division nativa do Python -- inline em vez
                # de função de apoio, para se manter fiel ao espírito
                # deste modo (Python o mais direto possível).
                e = self._expr(expr.esq, tipos)
                d = self._expr(expr.dire, tipos)
                if expr.op == "div":
                    return f"int({e} / {d})"
                return f"({e} - int({e} / {d}) * {d})"
            op = OPS_BIN[expr.op]
            return f"({self._expr(expr.esq, tipos)} {op} {self._expr(expr.dire, tipos)})"
        if isinstance(expr, A.UnOp):
            if expr.op == "nao":
                return f"(not {self._expr(expr.operando, tipos)})"
            if expr.op == "-":
                return f"(-{self._expr(expr.operando, tipos)})"
        if isinstance(expr, A.Chamada):
            args = [self._expr(a, tipos) for a in expr.args]
            if expr.nome in BIBLIOTECA_MINIMA:
                construtor, _modulo = BIBLIOTECA_MINIMA[expr.nome]
                return construtor(args)
            return f"{expr.nome}({', '.join(args)})"
        if isinstance(expr, A.ArrayLiteral):
            elementos = ", ".join(self._expr(e, tipos) for e in expr.elementos)
            return f"[{elementos}]"
        raise ErroSemantico(  # pragma: no cover -- todos os tipos de expressão da AST são tratados acima
            f"expressão não suportada: {type(expr).__name__}", getattr(expr, "linha", 0))


def gerar_python_minimo(programa: A.Programa) -> str:
    return GeradorCodigo(programa).gerar()
