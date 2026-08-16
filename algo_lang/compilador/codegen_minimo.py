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
from .gerador_base import GeradorCodigoBase, DEFAULT_POR_TIPO, ErroInternoCompilador

CABECALHO_RUNTIME = ""


OPS_BIN = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "div": "//", "mod": "%",
    "==": "==", "<>": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=",
    "e": "and", "ou": "or",
}
# AL-87/B14: '^' não está em OPS_BIN -- é tratado à parte em _expr() (como
# 'div'/'mod'), só envolvido em float(...) quando o expoente não é
# provavelmente não-negativo (ver expoente_estaticamente_nao_negativo,
# importada de semantics.py). Sem essa proteção condicional, '**' nativo do
# Python devolvia silenciosamente um 'complex' para base negativa com
# expoente fracionário -- SEM erro nenhum -- o único caso em todo --minimo
# em que um programa com erro de tipos NÃO "falha a correr com o erro
# nativo do Python" (contrato documentado no topo deste ficheiro),
# produzindo antes um resultado errado em silêncio. Ao contrário de
# matematica.potencia() (BIBLIOTECA_MINIMA, abaixo), que está DECLARADA
# para devolver sempre 'decimal' e por isso embrulha sempre em float(...),
# o operador '^' pode ser tipado 'inteiro' por semantics.py (quando o
# expoente é estaticamente não-negativo) -- envolver sempre divergia do
# modo normal nesses casos (ex.: '2 ^ 10' dava 1024.0 aqui, 1024 lá).

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
    "matematica.raiz": (lambda args: f"math.sqrt({args[0]})", "math"),
    # AL-60/B20: bibliotecas/matematica.py embrulha sempre em float(...)
    # (contrato do modo normal: matematica.potencia(2,3) dá 8.0, não 8) --
    # sem o float() aqui, --minimo dava 8 (int), divergindo do modo normal.
    "matematica.potencia": (lambda args: f"float({args[0]} ** {args[1]})", None),
    "matematica.absoluto": (lambda args: f"abs({args[0]})", None),
    "matematica.piso": (lambda args: f"math.floor({args[0]})", "math"),
    "matematica.teto": (lambda args: f"math.ceil({args[0]})", "math"),
    "matematica.aleatorio": (lambda args: f"random.randint({args[0]}, {args[1]})", "random"),
    "cadeia.comprimento": (lambda args: f"len({args[0]})", None),
    "cadeia.maiusculas": (lambda args: f"{args[0]}.upper()", None),
    "cadeia.minusculas": (lambda args: f"{args[0]}.lower()", None),
    "cadeia.inverter": (lambda args: f"{args[0]}[::-1]", None),
    "cadeia.subcadeia": (lambda args: f"{args[0]}[{args[1]}:{args[2]}]", None),
    "cadeia.caracter": (lambda args: f"{args[0]}[{args[1]}]", None),
    "conversao.paraTexto": (lambda args: f"str({args[0]})", None),
    "conversao.paraInteiro": (lambda args: f"int({args[0]})", None),
    "conversao.paraDecimal": (lambda args: f"float({args[0]})", None),
    "conversao.paraBooleano": (
        lambda args: (
            f'(False if isinstance({args[0]}, str) and {args[0]}.strip().lower() '
            f'in ("falso", "f", "false") else bool({args[0]}))'
        ), None,
    ),
    "conversao.paraCaracter": (lambda args: f"({args[0]})", None),
    "conversao.paraAscii": (lambda args: f"ord({args[0]})", None),
    "conversao.deAscii": (lambda args: f"chr({args[0]})", None),
}


class GeradorCodigo(GeradorCodigoBase):
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
        if "matematica" in nomes_bibliotecas_importadas:
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
        recursivas = self._estruturas_recursivas()
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
                self.emit(f"if {c.nome} is None:", 2)
                valor_default = self._construir_array_aninhado(c.tipo, c.dims, {}, 3)
                self.emit(f"{c.nome} = {valor_default}", 3)
                self.emit(f"self.{c.nome} = {c.nome}", 2)
            elif c.tipo not in DEFAULT_POR_TIPO:
                # AL-39: campo de tipo (direta ou mutuamente) recursivo --
                # ver a mesma nota em codegen.py.
                valor_default = "None" if c.tipo in recursivas else self._valor_default(c.tipo)
                self.emit(f"self.{c.nome} = {c.nome} if {c.nome} is not None else {valor_default}", 2)
            else:
                self.emit(f"self.{c.nome} = {c.nome}", 2)
        self._linha_algo_atual = None
        self.linhas.append("")

    # -------- declarações --------
    def _gerar_declaracao(self, d: A.Declaracao, nivel, tipos):
        if d.inicial is not None and isinstance(d.inicial, A.EstruturaLiteral):
            if d.dims is not None:
                # AL-45/B5: '{}' vazio inicializando um array -- mesma
                # correção que codegen.py, para --minimo não divergir do
                # modo normal num programa ALGO válido.
                self.emit(f"{d.nome} = []", nivel)
                return
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
            expr = self._construir_array_aninhado(d.tipo, d.dims, tipos, nivel)
            self.emit(f"{d.nome} = {expr}", nivel)

    def _construir_array_aninhado(self, tipo, dims_exprs, tipos, nivel):
        """Constrói a expressão Python de um array com N dimensões, ex:
        [[0 for _ in range(c)] for _ in range(l)] para 2D.

        AL-88/B15: cada dimensão é avaliada UMA VEZ, para uma variável
        temporária emitida antes da expressão -- ver a mesma nota em
        codegen.py (idêntico aqui, exceto que --minimo não envolve o
        tamanho em nenhuma verificação de runtime, por desenho)."""
        if not dims_exprs:
            return self._valor_default(tipo)
        temps = []
        for i, dim_expr in enumerate(dims_exprs):
            nome_temp = f"_algo_dim{i}"
            self.emit(f"{nome_temp} = {self._expr(dim_expr, tipos)}", nivel)
            temps.append(nome_temp)
        expr = self._valor_default(tipo)
        for nome_temp in reversed(temps):
            expr = f"[{expr} for _ in range({nome_temp})]"
        return expr

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
            if isinstance(stmt.expr, A.EstruturaLiteral):
                # Mesmo padrão de _gerar_declaracao, acima -- sem isto, o
                # PRÓPRIO COMPILADOR rebentava ("expressão não suportada")
                # em programas --minimo válidos que devolvem um literal de
                # estrutura diretamente, já que _expr() não tem ramo nenhum
                # para A.EstruturaLiteral.
                kwargs = ", ".join(
                    f"{nome}={self._expr(valor, tipos)}" for nome, valor in stmt.expr.campos)
                valor = f"{self.tipo_retorno_atual}({kwargs})"
            else:
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
            raise ErroInternoCompilador(
                f"instrução não suportada: {type(stmt).__name__} (linha {getattr(stmt, 'linha', 0)})")

    def _gerar_afirmar(self, stmt: A.Afirmar, nivel, tipos):
        cond_py = self._expr(stmt.condicao, tipos)
        if stmt.mensagem is not None:
            msg_py = self._expr(stmt.mensagem, tipos)
            self.emit(f"assert {cond_py}, {msg_py}", nivel)
        else:
            self.emit(f"assert {cond_py}", nivel)

    def _gerar_ler(self, stmt: A.Ler, nivel, tipos):
        for alvo in stmt.alvos:
            tipo = self._tipo_final_lvalue(alvo, tipos)
            leitor = LEITORES_INLINE_POR_TIPO.get(tipo, "input()")
            destino = self._lvalue(alvo, tipos)
            self.emit(f"{destino} = {leitor}", nivel)

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
        # AL-90/B17: ao contrário de codegen.py, --minimo salta
        # semantics.verificar() de propósito, por isso NÃO pode assumir
        # que um argumento de um parâmetro 'ref' é sempre uma variável
        # (essa validação só existe no modo normal) -- levantar
        # ErroSemantico aqui era um erro de COMPILAÇÃO, contradizendo o
        # contrato de --minimo ("gera sempre Python, falha só a correr,
        # com o erro nativo do Python"). Gera a tradução da expressão na
        # mesma (mesmo não sendo um alvo de atribuição válido) e deixa o
        # próprio Python falhar nativamente (ex.: SyntaxError) ao correr.
        return self._expr(expr, tipos)

    # -------- lvalue / expressões --------
    def _expr(self, expr, tipos):
        if expr is None:  # pragma: no cover -- nenhum chamador passa None (todos são guardados)
            return ""
        if isinstance(expr, A.Literal):
            if expr.tipo in ("cadeia", "caracter"):
                # AL-13: repr() -- ver a mesma nota em codegen.py.
                return repr(expr.valor)
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
                # AL-59/B19: a versão anterior ('int(e / d)') passava por
                # float, perdendo precisão para inteiros grandes (acima de
                # ~2^52) -- diverge do modo normal, que usa divmod() exato
                # (_algo_div). Reescrito com // (floor division exata, sem
                # float) mais uma correção de +1 quando os sinais diferem
                # (floor division arredonda para -infinito; div trunca em
                # direção a zero) -- mesma fórmula, sem função de apoio.
                e = self._expr(expr.esq, tipos)
                d = self._expr(expr.dire, tipos)
                divisao = f"(-(-({e}) // ({d})) if (({e}) < 0) != (({d}) < 0) else ({e}) // ({d}))"
                if expr.op == "div":
                    return divisao
                return f"(({e}) - {divisao} * ({d}))"
            if expr.op == "^":
                # AL-87/B14: ver nota em OPS_BIN, acima -- mas envolver
                # SEMPRE em float(...) divergia do modo normal sempre que o
                # expoente é um inteiro literal não-negativo (ex.: '2 ^ 10'
                # dava 1024.0 aqui, 1024 no modo normal, porque '**' nativo
                # já preserva int/float sozinho nesse caso e não há mais
                # nenhuma coerção decimal a acontecer numa posição solta
                # como 'escrever(2^10)'). CUIDADO: a condição para saltar o
                # float(...) tem de exigir um INTEIRO não-negativo, não só
                # um valor não-negativo -- um expoente fracionário
                # não-negativo (ex.: 0.5) com base negativa também produz
                # 'complex' silenciosamente, o mesmo perigo que esta
                # proteção existe para evitar (confirmado ao reintroduzir
                # o bug por engano: reaproveitar a verificação de SINAL de
                # semantics.py aqui, que só é válida no contexto onde é
                # usada lá, não chega).
                base = self._expr(expr.esq, tipos)
                exp = self._expr(expr.dire, tipos)
                if isinstance(expr.dire, A.Literal) and expr.dire.tipo == "inteiro" and expr.dire.valor >= 0:
                    return f"({base} ** {exp})"
                return f"float({base} ** {exp})"
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
        if isinstance(expr, A.EstruturaLiteral):
            # Ao contrário de ArrayLiteral (que vira uma lista Python sem
            # precisar de saber o tipo), um literal de estrutura precisa do
            # NOME do construtor a chamar -- não há como adivinhar qual
            # 'estrutura' se quer aqui sem o tipo esperado do contexto
            # (só disponível nos sítios que já têm tratamento dedicado:
            # declaração, argumento de chamada, devolver, atribuição). Um
            # literal de estrutura fora desses sítios (ex.: dentro de
            # escrever(...) ou de uma expressão aritmética) não tem solução
            # correta possível mesmo em --minimo -- mensagem específica em
            # vez do genérico "expressão não suportada".
            raise ErroInternoCompilador(
                f"um literal de estrutura '{{...}}' só pode aparecer onde o tipo é "
                f"conhecido pelo contexto (declaração, argumento de chamada, "
                f"'devolver', atribuição) -- mesmo em --minimo; usa uma variável "
                f"intermédia (linha {getattr(expr, 'linha', 0)})")
        raise ErroInternoCompilador(  # pragma: no cover -- todos os outros tipos de expressão da AST são tratados acima
            f"expressão não suportada: {type(expr).__name__} (linha {getattr(expr, 'linha', 0)})")


def gerar_python_minimo(programa: A.Programa) -> str:
    return GeradorCodigo(programa).gerar()
