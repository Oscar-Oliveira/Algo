# -*- coding: utf-8 -*-
"""Gerador de código Python a partir da AST da linguagem ALGO."""

from . import ast_nodes as A
from .. import bibliotecas
from .ast_nodes import texto_expr
from .gerador_base import GeradorCodigoBase, DEFAULT_POR_TIPO


class ErroInternoCompilador(Exception):
    """ARCH-03: uma falha de invariante do PRÓPRIO gerador de código --
    nunca deveria acontecer, porque verificar() (semantics.py) já
    validou o programa antes de gerar_python() correr; os sítios que
    levantam isto estão todos marcados '# pragma: no cover' por essa
    razão. Distinto de propósito de ErroSemantico (semantics.py), que
    É esperado (disparado por um erro real no programa do estudante) --
    antes, reutilizar ErroSemantico aqui fazia um bug do próprio
    compilador aparecer ao estudante como se fosse um erro de tipos
    normal no seu programa."""
    def __init__(self, mensagem):
        super().__init__(f"Erro interno do compilador: {mensagem}")


CABECALHO_RUNTIME = '''\
# ============================================================
#  Ficheiro gerado automaticamente pelo compilador ALGO
#  NAO EDITAR A MAO -- edita o ficheiro .algo original
# ============================================================

import sys
import copy

sys.setrecursionlimit(10000)


class _AlgoIndiceCadeiaInvalido(IndexError):
    """AL-09: subclasse de IndexError, para as bibliotecas de texto
    (ex. cadeia.caracter) distinguirem um índice fora dos limites de
    TEXTO de um índice fora dos limites de ARRAY -- apanhada antes do
    'except IndexError' genérico, mais abaixo neste ficheiro."""
    pass


def _algo_fmt(v):
    """Formata valores para exibicao (escrever) ao estilo portugues."""
    if isinstance(v, bool):
        return "verdadeiro" if v else "falso"
    if v is None:
        return "nulo"
    return str(v)


def _algo_escrever(*valores):
    print("".join(_algo_fmt(v) for v in valores))


def _algo_ler_inteiro(prompt=""):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Valor inválido. Introduza um número inteiro.")


def _algo_ler_decimal(prompt=""):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Valor inválido. Introduza um número decimal.")


def _algo_ler_booleano(prompt=""):
    while True:
        resp = input(prompt).strip().lower()
        if resp in ("verdadeiro", "v", "true"):
            return True
        if resp in ("falso", "f", "false"):
            return False
        print("Valor inválido. Introduza 'verdadeiro' ou 'falso'.")


def _algo_ler_texto(prompt=""):
    return input(prompt)


def _algo_ler_caracter(prompt=""):
    while True:
        resp = input(prompt)
        if len(resp) == 1:
            return resp
        print("Valor inválido. Introduza exatamente 1 caracter.")


def _algo_div(a, b):
    """div: divisao INTEIRA TRUNCADA (arredonda em direcao a zero, como
    a maioria das linguagens ensinadas em programacao introdutoria) --
    ao contrario do // nativo do Python, que arredonda para -infinito
    (ex: -7 // 2 = -4, mas -7 div 2 = -3)."""
    q, r = divmod(a, b)
    if r != 0 and (a < 0) != (b < 0):
        q += 1
    return q


def _algo_mod(a, b):
    """mod: resto da divisao truncada (_algo_div) -- sinal igual ao do
    primeiro operando, ao contrario do % nativo do Python."""
    return a - _algo_div(a, b) * b


def _algo_traduzir_valueerro(msg):
    """AL-08/UX-01: traduz as causas mais comuns de ValueError para
    portugues, em vez de mostrar sempre a mensagem crua do Python --
    mantem o generico (mensagem original entre parenteses) como
    recurso para causas nao mapeadas."""
    msg_min = msg.lower()
    if "math domain error" in msg_min:
        return ("o valor está fora do domínio válido desta operação "
                 "(ex: raiz quadrada de um número negativo).")
    if "negative number cannot be raised to a fractional power" in msg_min:
        return "não é possível elevar um número negativo a um expoente fracionário."
    if "invalid literal for int()" in msg_min:
        return "o texto não pode ser convertido para um número inteiro."
    if "could not convert string to float" in msg_min:
        return "o texto não pode ser convertido para um número decimal."
    return f"valor inválido ({msg})."


def _algo_traduzir_attributeerror(msg):
    """Num programa ALGO válido, um AttributeError só pode acontecer ao
    aceder a um campo de um valor 'nulo' -- semantics.py já garante em
    compilação que todos os outros acessos a campos existem e têm o
    tipo certo. Tenta extrair o nome do campo da mensagem nativa do
    Python (ex.: "'NoneType' object has no attribute 'seguinte'") para
    uma mensagem mais específica; sem isso, cai num genérico."""
    prefixo, sufixo = "'NoneType' object has no attribute '", "'"
    if msg.startswith(prefixo) and msg.endswith(sufixo):
        campo = msg[len(prefixo):-len(sufixo)]
        return f"tentaste aceder ao campo '{campo}' de um valor nulo."
    return "tentaste aceder a um campo de um valor nulo."  # pragma: no cover -- defensivo


def _algo_linha_do_erro(erro):
    """UX-04: percorre o traceback da excecao à procura do frame mais
    profundo que ainda corresponda a uma linha ALGO conhecida (via
    _ALGO_MAPA_LINHAS, definido mais abaixo neste ficheiro, ja que so
    fica completo depois de todo o codigo ser gerado) -- nao basta o
    frame mais profundo de todos, que costuma estar DENTRO de uma
    biblioteca (ex: matematica_raiz -> _math.sqrt), sem linha ALGO
    correspondente; fica sempre com o último frame mapeado antes de
    'descer' para código interno. Devolve None se não encontrar
    nenhum."""
    tb = erro.__traceback__
    linha_algo = None
    while tb is not None:
        candidato = _ALGO_MAPA_LINHAS.get(tb.tb_lineno)
        if candidato is not None:
            linha_algo = candidato
        tb = tb.tb_next
    return linha_algo


def _algo_sufixo_linha(erro):
    linha_algo = _algo_linha_do_erro(erro)
    return f" (linha {linha_algo})" if linha_algo else ""


_ALGO_ERRO_RUNTIME = None


def _algo_registar_erro_runtime(mensagem, linha):
    """AL-23/AL-24: substitui a deteção frágil por texto (endswith de
    frases fixas) que existia em tools/tracer.py -- cada ponto do
    runtime que apanha um erro e termina o programa regista aqui a
    mensagem e a linha, um canal que não depende de nenhuma frase
    específica nem corre o risco de um escrever() legítimo do próprio
    estudante coincidir por acaso com uma dessas frases. Chamada como
    função (não atribuição direta) de propósito -- funciona
    corretamente seja qual for o scope de onde é chamada (corpo
    principal ou dentro de uma função/procedimento), sem precisar de
    'global' em cada local de chamada."""
    global _ALGO_ERRO_RUNTIME
    _ALGO_ERRO_RUNTIME = {"mensagem": mensagem, "linha": linha}


def _algo_pot(a, b):
    """AL-57/B16: ao contrário do Python 2 (de onde a mensagem já
    traduzida em _algo_traduzir_valueerro parece ter sido portada), o
    '**' nativo do Python 3 nunca levanta ValueError para base negativa
    com expoente fracionário -- devolve silenciosamente um número
    complexo (ex.: (-8.0) ** 0.5). matematica.raiz(-1) já tinha uma
    mensagem amigável equivalente para esse domínio inválido; este é o
    caminho gémeo para o operador '^'."""
    if a < 0 and not float(b).is_integer():
        raise ValueError("negative number cannot be raised to a fractional power")
    return a ** b


def _algo_verificar_tamanho_array(tam):
    """Um tamanho de array calculado em runtime (nao um literal, ja
    apanhado em compilacao) que de negativo silenciosamente produzia
    um array vazio -- range(negativo) do Python nao levanta erro
    nenhum. ValueError e reaproveitado de propósito: ja ha um
    'except ValueError' no programa gerado que traduz para a mensagem
    amigavel de 'Erro em tempo de execucao: valor invalido (...)'."""
    if tam < 0:
        raise ValueError(f"tamanho de array não pode ser negativo (é {tam})")
    return tam

'''

OPS_BIN = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "==": "==", "<>": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=",
    "e": "and", "ou": "or",
}

LEITORES_POR_TIPO = {
    "inteiro": "_algo_ler_inteiro",
    "decimal": "_algo_ler_decimal",
    "booleano": "_algo_ler_booleano",
    "cadeia": "_algo_ler_texto",
    "caracter": "_algo_ler_caracter",
}


class GeradorCodigo(GeradorCodigoBase):
    def __init__(self, programa: A.Programa):
        super().__init__(programa)
        self.registo_bibliotecas = bibliotecas.obter_registo()

    # -------- ponto de entrada --------
    def gerar(self) -> str:
        self.linhas = CABECALHO_RUNTIME.split("\n")

        self.estruturas = {}
        for e in self.programa.estruturas:
            campos = {}
            for c in e.campos:
                dims_n = 0 if c.dims is None else len(c.dims)
                campos[c.nome] = (c.tipo, dims_n)
            self.estruturas[e.nome] = campos

        for imp in self.programa.importares:
            info = self.registo_bibliotecas.get(imp.nome.lower())
            if info is None:  # pragma: no cover -- semantics.py já validou que a biblioteca existe
                continue
            if info["cabecalho"]:
                self.linhas.extend(info["cabecalho"].split("\n"))
            for _nome_metodo, (_cats, _tipo, codigo_py) in info["funcoes"].items():
                self.linhas.extend(codigo_py.split("\n"))

        for e in self.programa.estruturas:
            self._gerar_estrutura(e)

        # tabela de globais = declarações de topo + tudo o que é declarado dentro de 'inicio'
        for d in self.programa.declaracoes:
            self.tabela_tipos_globais[d.nome] = d.tipo
        A.coletar_declaracoes_tipadas(self.programa.corpo, self.tabela_tipos_globais)

        # as funções são geradas antes das globais: o corpo de uma função só
        # é executado quando é chamada, por isso é seguro defini-la aqui
        # mesmo que só venha a ser usada no inicializador de uma global a seguir
        for f in self.programa.funcoes:
            self._gerar_funcao(f)

        for d in self.programa.declaracoes:
            self._linha_algo_atual = d.linha
            self._gerar_declaracao(d, 0, self.tabela_tipos_globais)
        self._linha_algo_atual = None
        if self.programa.declaracoes:
            self.linhas.append("")

        self.emit("def _algo_programa():", 0)
        if self.tabela_tipos_globais:
            self.emit(f"global {', '.join(self.tabela_tipos_globais)}", 1)
        corpo_vazio = not self.programa.corpo
        if corpo_vazio:  # pragma: no cover -- o parser exige >=1 instrução após 'inicio'
            self.emit("pass", 1)
        tipos = dict(self.tabela_tipos_globais)
        for stmt in self.programa.corpo:
            self._gerar_stmt(stmt, 1, tipos)
        self._linha_algo_atual = None
        self.linhas.append("")

        # UX-04: o mapa de linhas (.py gerado -> linha ALGO original) já
        # é sempre construído durante a geração (ver emit()) -- embutido
        # aqui como dados simples no próprio ficheiro gerado, para os
        # handlers de erro em runtime logo a seguir conseguirem mostrar
        # a que linha ALGO corresponde um erro, mesmo fora do modo
        # --debug (que usa este mesmo mapa de forma independente, via
        # tools/tracer.py, correndo o programa sob sys.settrace()).
        self.linhas.append(f"_ALGO_MAPA_LINHAS = {self.mapa_linhas!r}")
        self.linhas.append("")

        self.emit('if __name__ == "__main__":', 0)
        self.emit("try:", 1)
        self.emit("_algo_programa()", 2)
        self.emit("except _AlgoIndiceCadeiaInvalido as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de '
            'texto que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except IndexError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de '
            'array que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except ZeroDivisionError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: divisão por zero.{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        # AL-68/B28: sem isto, um OverflowError (ex.: 'x:decimal =
        # 2.0 ^ 2000.0') propagava como traceback Python cru -- não
        # estava entre as exceções traduzidas, mesmo fora do tracer.
        self.emit("except OverflowError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: o resultado é grande demais para ser '
            'representado (overflow numérico).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except RecursionError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: recursão infinita '
            '(a função nunca chega ao caso base).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except AttributeError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: '
            '{_algo_traduzir_attributeerror(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except ValueError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: '
            '{_algo_traduzir_valueerro(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.linhas.append("")
        return "\n".join(self.linhas)

    def _gerar_estrutura(self, e: A.EstruturaDef):
        # AL-89/B16: propositadamente NÃO associado a 'e.linha' (a linha da
        # definição 'estrutura X') -- ao contrário de uma instrução normal,
        # o corpo de '__init__'/'__eq__' só corre em RUNTIME, sempre que
        # uma instância é criada ou comparada, nunca na linha da própria
        # definição. Mapeá-lo para 'e.linha' fazia o tracer (--debug/--json)
        # injetar passos espúrios (linha da definição, pilha do chamador)
        # sempre que uma estrutura era construída/comparada. Deixando
        # '_linha_algo_atual' em None aqui, 'emit()' não regista nenhuma
        # entrada em mapa_linhas para estas linhas -- tracer.py já ignora
        # de propósito qualquer linha sem entrada (ver 'if linha_algo is
        # None: return tracer').
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
                # AL-39: se 'c.tipo' é (direta ou mutuamente) recursivo,
                # construir a instância por omissão nunca terminaria --
                # fica 'None' (nulo), tal como o estudante teria de
                # escrever explicitamente para terminar uma lista ligada.
                valor_default = "None" if c.tipo in recursivas else self._valor_default(c.tipo)
                self.emit(f"self.{c.nome} = {c.nome} if {c.nome} is not None else {valor_default}", 2)
            else:
                self.emit(f"self.{c.nome} = {c.nome}", 2)
        self.emit("def __eq__(self, outro):", 1)
        self.emit(f"if not isinstance(outro, {e.nome}):", 2)
        self.emit("return NotImplemented", 3)
        if e.campos:
            condicoes = " and ".join(f"self.{c.nome} == outro.{c.nome}" for c in e.campos)
        else:  # pragma: no cover -- o parser exige >=1 campo em 'estrutura'
            condicoes = "True"
        self.emit(f"return {condicoes}", 2)
        self._linha_algo_atual = None
        self.linhas.append("")

    # -------- declarações --------
    def _gerar_lista_args(self, args, f_def, tipos) -> str:
        """AL-16: um argumento pode ser um literal de estrutura (ex.:
        f({x: 1, y: 2})) -- precisa do tipo do PARÂMETRO correspondente
        para saber que classe Python construir (o literal em si não sabe
        o seu próprio tipo). Partilhado entre chamadas usadas como
        expressão e chamadas usadas como instrução solta (esta última
        com o seu próprio caminho de geração para parâmetros 'ref')."""
        args_py = []
        for i, a in enumerate(args):
            param = f_def.parametros[i] if f_def is not None and i < len(f_def.parametros) else None
            if isinstance(a, A.EstruturaLiteral) and param is not None:
                args_py.append(self._expr_estrutura_literal(a, param.tipo, tipos))
            elif param is not None:
                expr_py = self._coagir_decimal(self._expr(a, tipos), param.tipo, a)
                if not param.por_referencia and param.tipo in self.estruturas:
                    # AL-52/B11: um parâmetro de tipo 'estrutura' sem 'ref'
                    # é por VALOR -- semantics.py já garante todo o
                    # contrato de 'ref' (778-820), mas o Python gerado
                    # nunca copiava o objeto, só passava a MESMA
                    # referência. Uma mutação de campo dentro da função
                    # (ex.: 'p.x = 99') vazava silenciosamente para quem
                    # chamou. Um literal de estrutura ({...}, tratado no
                    # 'if' acima) já é uma instância nova -- não precisa
                    # de cópia.
                    expr_py = f"copy.deepcopy({expr_py})"
                args_py.append(expr_py)
            else:
                args_py.append(self._expr(a, tipos))
        return ", ".join(args_py)

    def _expr_estrutura_literal(self, lit: A.EstruturaLiteral, tipo_nome: str, tipos) -> str:
        """AL-16: um A.EstruturaLiteral não sabe o seu próprio tipo (só os
        campos) -- quem chama tem sempre de indicar 'tipo_nome' a partir
        do contexto (o tipo declarado, ou o tipo do parâmetro que recebe
        o literal numa chamada)."""
        campos_decl = self.estruturas.get(tipo_nome, {})
        partes = []
        for nome, valor in lit.campos:
            tipo_campo = campos_decl.get(nome, ("", 0))[0]
            if isinstance(valor, A.EstruturaLiteral):
                # AL-78/B8: literal de estrutura aninhado dentro doutro --
                # 'valor' não tem 'self._expr()' próprio (só faz sentido
                # com o tipo do campo, já conhecido aqui), por isso
                # recursão direta em vez de _expr()/_coagir_decimal (que só
                # tratam valores primitivos).
                expr_py = self._expr_estrutura_literal(valor, tipo_campo, tipos)
            else:
                expr_py = self._coagir_decimal(self._expr(valor, tipos), tipo_campo, valor)
            partes.append(f"{nome}={expr_py}")
        return f"{tipo_nome}({', '.join(partes)})"

    def _expr_array_literal(self, lit: A.ArrayLiteral, tipo_elemento: str, tipos) -> str:
        """AL-58/B18: coage cada elemento individualmente para o tipo
        alvo (ex.: inteiro -> decimal), tal como _expr_estrutura_literal
        já faz para campos de estrutura -- o dispatcher genérico de
        _expr() para A.ArrayLiteral não sabe o tipo alvo, por isso nunca
        coagia nada (v:decimal[3] = {1, 2, 3} imprimia '1 2 3', não
        '1.0 2.0 3.0'). Recursivo para suportar arrays aninhados
        (multidimensionais)."""
        partes = []
        for elem in lit.elementos:
            if isinstance(elem, A.ArrayLiteral):
                partes.append(self._expr_array_literal(elem, tipo_elemento, tipos))
            elif isinstance(elem, A.EstruturaLiteral):
                # AL-78/B8: elemento de array que é ele próprio um literal
                # de estrutura (ex.: array de estruturas).
                partes.append(self._expr_estrutura_literal(elem, tipo_elemento, tipos))
            else:
                partes.append(self._coagir_decimal(self._expr(elem, tipos), tipo_elemento, elem))
        return f"[{', '.join(partes)}]"

    def _gerar_declaracao(self, d: A.Declaracao, nivel, tipos):
        if d.inicial is not None and isinstance(d.inicial, A.ArrayLiteral):
            self.emit(f"{d.nome} = {self._expr_array_literal(d.inicial, d.tipo, tipos)}", nivel)
            return
        if d.inicial is not None and isinstance(d.inicial, A.EstruturaLiteral):
            if d.dims is not None:
                # AL-45/B5: '{}' vazio inicializando um array -- semantics.py
                # já garantiu que só chega aqui com campos vazios.
                self.emit(f"{d.nome} = []", nivel)
                return
            self.emit(f"{d.nome} = {self._expr_estrutura_literal(d.inicial, d.tipo, tipos)}", nivel)
            return
        if d.inicial is not None and isinstance(d.inicial, A.Chamada):
            f_def = self._encontrar_funcao(d.inicial.nome)
            if f_def and any(p.por_referencia for p in f_def.parametros):
                out_vars = [
                    self._lvalue_de_expr(a, tipos)
                    for p, a in zip(f_def.parametros, d.inicial.args)
                    if p.por_referencia
                ]
                args_str = self._gerar_lista_args(d.inicial.args, f_def, tipos)
                self.emit(f"{d.nome}, {', '.join(out_vars)} = {d.inicial.nome}({args_str})", nivel)
                # AL-51/B17: o valor de retorno principal nunca passava por
                # _coagir_decimal neste caminho -- 'y:decimal = f(x)' com
                # 'f' a devolver 'inteiro' ficava com o inteiro cru.
                valor_coagido = self._coagir_decimal(d.nome, d.tipo, d.inicial)
                if valor_coagido != d.nome:
                    self.emit(f"{d.nome} = {valor_coagido}", nivel)
                return
        if d.inicial is not None:
            expr_py = self._coagir_decimal(self._expr(d.inicial, tipos), d.tipo, d.inicial)
            self.emit(f"{d.nome} = {expr_py}", nivel)
        elif d.dims is None:
            self.emit(f"{d.nome} = {self._valor_default(d.tipo)}", nivel)
        else:
            expr = self._construir_array_aninhado(d.tipo, d.dims, tipos, nivel)
            self.emit(f"{d.nome} = {expr}", nivel)

    def _gerar_atribuicao(self, stmt: A.Atribuicao, nivel, tipos):
        """AL-51/B17: sobrepõe gerador_base.py só para o caminho de chamada
        com parâmetros 'ref' -- precisa de _gerar_lista_args (coerção
        inteiro->decimal nos argumentos, cópia de estruturas por valor --
        AL-52/B11) e de coagir o valor de retorno principal; nenhum dos
        dois existe em codegen_minimo.py (fica com o comportamento cru da
        base partilhada, de propósito -- ver a mesma duplicação já
        existente em _gerar_chamada_stmt)."""
        if isinstance(stmt.expr, A.Chamada):
            f_def = self._encontrar_funcao(stmt.expr.nome)
            if f_def and any(p.por_referencia for p in f_def.parametros):
                out_vars = [
                    self._lvalue_de_expr(a, tipos)
                    for p, a in zip(f_def.parametros, stmt.expr.args)
                    if p.por_referencia
                ]
                args_str = self._gerar_lista_args(stmt.expr.args, f_def, tipos)
                alvo = self._lvalue(stmt.alvo, tipos)
                self.emit(f"{alvo}, {', '.join(out_vars)} = {stmt.expr.nome}({args_str})", nivel)
                tipo_alvo = self._tipo_final_lvalue(stmt.alvo, tipos)
                valor_coagido = self._coagir_decimal(alvo, tipo_alvo, stmt.expr)
                if valor_coagido != alvo:
                    self.emit(f"{alvo} = {valor_coagido}", nivel)
                return
        super()._gerar_atribuicao(stmt, nivel, tipos)

    def _construir_array_aninhado(self, tipo, dims_exprs, tipos, nivel):
        """Constrói a expressão Python de um array com N dimensões, ex:
        [[0 for _ in range(c)] for _ in range(l)] para 2D.

        AL-88/B15: cada dimensão é avaliada UMA VEZ, para uma variável
        temporária emitida antes da expressão, em vez de inline -- sem
        isto, a dimensão INTERIOR de um array multidimensional era
        reavaliada uma vez por iteração da dimensão exterior (a
        compreensão de listas aninhada do Python reavalia o 'range()'
        interior a cada volta), duplicando o efeito de uma expressão de
        dimensão com efeitos laterais (ex.: uma chamada de função). Mesmo
        princípio que _gerar_para já aplica a 'passo'. 'nivel' é onde as
        atribuições temporárias são emitidas -- tem de ser o mesmo nível
        de indentação de quem usa a expressão devolvida logo a seguir."""
        if not dims_exprs:
            return self._valor_default(tipo)
        temps = []
        for i, dim_expr in enumerate(dims_exprs):
            nome_temp = f"_algo_dim{i}"
            self.emit(f"{nome_temp} = {self._expr(dim_expr, tipos)}", nivel)
            temps.append(nome_temp)
        expr = self._valor_default(tipo)
        for nome_temp in reversed(temps):
            expr = f"[{expr} for _ in range(_algo_verificar_tamanho_array({nome_temp}))]"
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
            self.emit(f"_algo_escrever({args})", nivel)
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
            valor = self._coagir_decimal(self._expr(stmt.expr, tipos), self.tipo_retorno_atual, stmt.expr)
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
        # texto_expr() devolve texto não escapado (pode conter aspas/chavetas/backslash
        # vindos de literais do próprio código do estudante). repr() gera um literal
        # Python seguro para esse texto — nunca é reavaliado como f-string/código no
        # programa gerado, ao contrário de o interpolar diretamente numa f-string.
        prefixo_literal = repr(f"❌ Afirmação falhou (linha {stmt.linha}): {texto_expr(stmt.condicao)}")
        self.emit(f"if not ({cond_py}):", nivel)
        if stmt.mensagem is not None:
            msg_py = self._expr(stmt.mensagem, tipos)
            self.emit(f'_algo_msg = {prefixo_literal} + " — " + str({msg_py})', nivel + 1)
        else:
            self.emit(f'_algo_msg = {prefixo_literal}', nivel + 1)
        self.emit("print(_algo_msg)", nivel + 1)
        self.emit(f"_algo_registar_erro_runtime(_algo_msg, {stmt.linha})", nivel + 1)
        self.emit("sys.exit(1)", nivel + 1)

    def _gerar_ler(self, stmt: A.Ler, nivel, tipos):
        for alvo in stmt.alvos:
            tipo = self._tipo_final_lvalue(alvo, tipos)
            leitor = LEITORES_POR_TIPO.get(tipo, "_algo_ler_texto")
            destino = self._lvalue(alvo, tipos)
            self.emit(f"{destino} = {leitor}()", nivel)

    def _gerar_chamada_stmt(self, stmt: A.ChamadaStmt, nivel, tipos):
        chamada = stmt.chamada
        f_def = self._encontrar_funcao(chamada.nome)
        if f_def and any(p.por_referencia for p in f_def.parametros):
            out_vars = [
                self._lvalue_de_expr(a, tipos)
                for p, a in zip(f_def.parametros, chamada.args)
                if p.por_referencia
            ]
            args_str = self._gerar_lista_args(chamada.args, f_def, tipos)
            if f_def.eh_procedimento:
                self.emit(f"{', '.join(out_vars)} = {chamada.nome}({args_str})", nivel)
            else:
                self.emit(f"_, {', '.join(out_vars)} = {chamada.nome}({args_str})", nivel)
        else:
            self.emit(self._expr(chamada, tipos), nivel)

    def _lvalue_de_expr(self, expr, tipos):
        if isinstance(expr, A.LValue):
            return self._lvalue(expr, tipos)
        raise ErroInternoCompilador(  # pragma: no cover -- semantics.py já valida isto antes
            "argumentos passados por referência têm de ser uma variável, um "
            "elemento de array ou um campo")

    # -------- lvalue / expressões --------
    def _expr(self, expr, tipos):
        if expr is None:  # pragma: no cover -- nenhum chamador passa None (todos são guardados)
            return ""
        if isinstance(expr, A.Literal):
            if expr.tipo in ("cadeia", "caracter"):
                # AL-13: repr() em vez de escapar à mão -- desde que o
                # lexer passou a suportar \n dentro de literais, o valor
                # pode conter uma quebra de linha real, que um simples
                # '"..."' não representa em Python; repr() trata sempre
                # corretamente aspas, backslash e quebras de linha.
                return repr(expr.valor)
            if expr.tipo == "booleano":
                return "True" if expr.valor else "False"
            return repr(expr.valor)
        if isinstance(expr, A.LValue):
            return self._lvalue(expr, tipos)
        if isinstance(expr, A.BinOp):
            if expr.op in ("div", "mod"):
                # AL-05: divisão truncada, não a floor division nativa do
                # Python -- ver _algo_div/_algo_mod no cabeçalho.
                funcao = "_algo_div" if expr.op == "div" else "_algo_mod"
                return f"{funcao}({self._expr(expr.esq, tipos)}, {self._expr(expr.dire, tipos)})"
            if expr.op == "^":
                # AL-57/B16: ver _algo_pot no cabeçalho -- '**' nativo do
                # Python devolve complex silenciosamente para base
                # negativa com expoente fracionário.
                return f"_algo_pot({self._expr(expr.esq, tipos)}, {self._expr(expr.dire, tipos)})"
            op = OPS_BIN[expr.op]
            return f"({self._expr(expr.esq, tipos)} {op} {self._expr(expr.dire, tipos)})"
        if isinstance(expr, A.UnOp):
            if expr.op == "nao":
                return f"(not {self._expr(expr.operando, tipos)})"
            if expr.op == "-":
                return f"(-{self._expr(expr.operando, tipos)})"
        if isinstance(expr, A.Chamada):
            args = self._gerar_lista_args(expr.args, self._encontrar_funcao(expr.nome), tipos)
            nome_py = expr.nome.replace(".", "_") if "." in expr.nome else expr.nome
            return f"{nome_py}({args})"
        if isinstance(expr, A.ArrayLiteral):  # pragma: no cover -- semantics.py (_tipo_expr, AL-16) já rejeita um ArrayLiteral fora dos dois contextos tratados por _gerar_declaracao/_expr_array_literal e _expr_estrutura_literal antes de chegar aqui
            elementos = ", ".join(self._expr(e, tipos) for e in expr.elementos)
            return f"[{elementos}]"
        raise ErroInternoCompilador(  # pragma: no cover -- todos os tipos de expressão da AST são tratados acima
            f"expressão não suportada: {type(expr).__name__} (linha {getattr(expr, 'linha', 0)})")


def gerar_python(programa: A.Programa) -> str:
    return GeradorCodigo(programa).gerar()


def gerar_python_com_mapa(programa: A.Programa):
    """Como gerar_python(), mas devolve também o mapa de linhas (linha do
    .py -> linha do .algo original) e os nomes globais/funções -- usado
    pela ferramenta de trace (algo_lang.tools.tracer) para conseguir
    mostrar, a cada passo da execução real, a que linha do .algo
    corresponde e quais são as variáveis globais visíveis. O compilador
    em si não sabe nada de debug/trace -- só devolve esta informação de
    correspondência de linhas, que é sempre gerada (é meta-informação
    inofensiva, não código extra dentro do programa)."""
    gerador = GeradorCodigo(programa)
    codigo = gerador.gerar()
    return {
        "codigo": codigo,
        "mapa_linhas": dict(gerador.mapa_linhas),
        "nomes_globais": list(gerador.tabela_tipos_globais.keys()),
        "nomes_funcoes": [f.nome for f in programa.funcoes],
    }
