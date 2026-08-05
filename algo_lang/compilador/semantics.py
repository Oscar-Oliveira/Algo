# -*- coding: utf-8 -*-
"""Verificador de tipos em tempo de compilação para a linguagem ALGO."""

import keyword

from . import ast_nodes as A
from .. import bibliotecas

NUMERICOS = {"inteiro", "decimal"}
TEXTUAIS = {"cadeia", "caracter"}


class ErroSemantico(Exception):
    def __init__(self, mensagem, linha):
        super().__init__(f"Erro semântico na linha {linha}: {mensagem}")
        self.linha = linha


def verificar_nomes_python(programa):
    """As palavras-chave do ALGO (se, para, fazer...) não têm nada a ver
    com as do Python -- por isso um identificador como 'class' ou
    'import' é perfeitamente válido em ALGO, mas geraria Python
    sintaticamente inválido (a variável seria traduzida diretamente para
    o mesmo nome). Isto corre sempre, em qualquer modo de compilação
    (incluindo --minimo, que salta a verificação de TIPOS mas não esta
    verificação -- não é sobre tipos, é sobre o nome sequer poder existir
    em Python)."""
    for nome, linha in A.coletar_identificadores(programa):
        if keyword.iskeyword(nome):
            raise ErroSemantico(
                f"'{nome}' não pode ser usado como nome -- é uma palavra "
                f"reservada do Python (a linguagem que o ALGO gera por trás), "
                f"mesmo não sendo uma palavra reservada do ALGO", linha)


class Escopo:
    """Escopo de uma função/procedimento: nomes locais próprios, com
    fallback para as variáveis globais do programa (visíveis para leitura
    e escrita, mas não redeclaráveis localmente)."""

    def __init__(self, globais):
        self.globais = globais
        self.locais = {}

    def __contains__(self, nome):
        return nome in self.locais or nome in self.globais

    def __getitem__(self, nome):
        if nome in self.locais:
            return self.locais[nome]
        return self.globais[nome]

    def __setitem__(self, nome, valor):
        self.locais[nome] = valor


class VerificadorTipos:
    def __init__(self, programa: A.Programa):
        self.programa = programa
        self.registo_bibliotecas = bibliotecas.obter_registo()
        self.bibliotecas_importadas = {}   # nome_minusculo -> info do registo
        for imp in programa.importares:
            chave = imp.nome.lower()
            if chave not in self.registo_bibliotecas:
                disponiveis = ", ".join(sorted(self.registo_bibliotecas)) or "(nenhuma)"
                raise ErroSemantico(
                    f"biblioteca '{imp.nome}' não existe. Bibliotecas disponíveis: "
                    f"{disponiveis}", imp.linha)
            self.bibliotecas_importadas[chave] = self.registo_bibliotecas[chave]

        self.funcoes = {}
        for f in programa.funcoes:
            if f.nome in self.funcoes:
                raise ErroSemantico(f"'{f.nome}' já foi definido anteriormente", f.linha)
            self.funcoes[f.nome] = f

        self.estruturas = {}   # nome_estrutura -> {campo: (tipo, dims)}
        linhas_dos_campos = {}   # (nome_estrutura, nome_campo) -> linha (só para mensagens de erro)
        for e in programa.estruturas:
            if e.nome in self.estruturas:
                raise ErroSemantico(f"a estrutura '{e.nome}' já foi definida", e.linha)
            campos = {}
            for c in e.campos:
                if c.nome in campos:
                    raise ErroSemantico(
                        f"a estrutura '{e.nome}' tem o campo '{c.nome}' duplicado", c.linha)
                if c.inicial is not None:
                    raise ErroSemantico(
                        "os campos de uma estrutura não podem ter valor inicial", c.linha)
                dims_n = 0 if c.dims is None else len(c.dims)
                campos[c.nome] = (c.tipo, dims_n)
                linhas_dos_campos[(e.nome, c.nome)] = c.linha
            self.estruturas[e.nome] = campos

        # valida os tipos dos campos só depois de todas as estruturas estarem
        # registadas, para permitir referências cruzadas entre estruturas
        # (ex: 'estrutura A' pode ter um campo do tipo 'B', definida a seguir)
        for nome_estrutura, campos in self.estruturas.items():
            for nome_campo, (tipo, _dims) in campos.items():
                if tipo not in NUMERICOS | TEXTUAIS | {"booleano"} and tipo not in self.estruturas:
                    linha = linhas_dos_campos[(nome_estrutura, nome_campo)]
                    raise ErroSemantico(
                        f"o campo '{nome_campo}' da estrutura '{nome_estrutura}' tem tipo "
                        f"desconhecido '{tipo}'", linha)

    def _validar_tipo(self, tipo, linha):
        if tipo in NUMERICOS or tipo in TEXTUAIS or tipo == "booleano":
            return
        if tipo in self.estruturas:
            return
        raise ErroSemantico(
            f"tipo '{tipo}' desconhecido (não é um tipo primitivo nem uma "
            f"estrutura definida com 'estrutura {tipo}')", linha)

    # ---------- ponto de entrada ----------
    def verificar(self):
        escopo_topo = {}
        for d in self.programa.declaracoes:
            self._registar_decl(escopo_topo, d)

        # tabela de globais visível às funções = declarações de topo + as
        # que vierem a ser declaradas dentro do bloco 'inicio'
        self.globais = dict(escopo_topo)
        self._pre_registar_recursivo(self.programa.corpo, self.globais)

        for f in self.programa.funcoes:
            self._verificar_funcao(f)

        self._verificar_bloco(self.programa.corpo, escopo_topo, ctx_funcao=None)

    def _pre_registar_recursivo(self, stmts, destino):
        for s in stmts:
            if isinstance(s, A.Declaracao) and s.nome not in destino:
                dims_n = 0 if s.dims is None else len(s.dims)
                destino[s.nome] = (s.tipo, dims_n, s.eh_constante)
            for bloco in A.subblocos(s):
                self._pre_registar_recursivo(bloco, destino)

    # ---------- funções ----------
    def _verificar_funcao(self, f: A.FuncaoDef):
        escopo = Escopo(self.globais)
        for p in f.parametros:
            if p.nome in escopo.locais:
                raise ErroSemantico(f"parâmetro '{p.nome}' duplicado", f.linha)
            self._validar_tipo(p.tipo, f.linha)
            escopo.locais[p.nome] = (p.tipo, 0, False)
        if f.tipo_retorno is not None:
            self._validar_tipo(f.tipo_retorno, f.linha)

        self._verificar_bloco(f.corpo, escopo, ctx_funcao=f)

        if not f.eh_procedimento and not self._contem_devolver(f.corpo):
            raise ErroSemantico(
                f"a função '{f.nome}' declara devolver '{f.tipo_retorno}' mas nunca "
                f"usa 'devolver'", f.linha)

    def _contem_devolver(self, corpo):
        for s in corpo:
            if isinstance(s, A.Devolver):
                return True
            for bloco in A.subblocos(s):
                if self._contem_devolver(bloco):
                    return True
        return False

    # ---------- declarações ----------
    def _registar_decl(self, escopo, d: A.Declaracao):
        ja_declarado = (d.nome in escopo.locais) if isinstance(escopo, Escopo) else (d.nome in escopo)
        if ja_declarado:
            raise ErroSemantico(f"a variável '{d.nome}' já foi declarada", d.linha)
        self._validar_tipo(d.tipo, d.linha)
        if d.eh_constante:
            if d.inicial is None:  # pragma: no cover -- o parser já exige '=' em 'constante'
                raise ErroSemantico(
                    f"a constante '{d.nome}' tem de ser inicializada com um valor", d.linha)
            if d.dims is not None:  # pragma: no cover -- 'constante' não tem sintaxe de array no parser
                raise ErroSemantico("uma constante não pode ser um array", d.linha)
        if d.dims:
            for dim_expr in d.dims:
                tipo, _ = self._tipo_expr(dim_expr, escopo)
                if tipo != "inteiro":
                    raise ErroSemantico(
                        "o tamanho de um array tem de ser uma expressão inteira", d.linha)
                valor_literal = self._valor_literal_negativo(dim_expr)
                if valor_literal is not None:
                    raise ErroSemantico(
                        f"o tamanho de um array não pode ser negativo (é {valor_literal})",
                        dim_expr.linha)
        if d.inicial is not None:
            if isinstance(d.inicial, A.ArrayLiteral):
                if d.dims is None:  # pragma: no cover -- o parser só produz ArrayLiteral quando dims existe
                    raise ErroSemantico(
                        f"'{d.nome}' não é um array; não pode ser inicializado com {{...}}",
                        d.linha)
                self._verificar_array_literal(d.inicial, d.tipo, len(d.dims), escopo)
            elif isinstance(d.inicial, A.EstruturaLiteral):
                if d.dims is not None:  # pragma: no cover -- o parser só produz EstruturaLiteral quando dims é None
                    raise ErroSemantico(
                        f"'{d.nome}' é um array; usa '{{valor, valor, ...}}' para o "
                        f"inicializar, não '{{campo: valor}}'", d.linha)
                self._verificar_estrutura_literal(d.inicial, d.tipo, escopo)
            elif isinstance(d.inicial, A.Chamada) and self._tem_ref(d.inicial):
                tipo_inicial = self._verificar_chamada(d.inicial, escopo)
                if tipo_inicial is None:
                    raise ErroSemantico(
                        f"'{d.inicial.nome}' é um procedimento e não devolve valor", d.linha)
                if not self._compativel(d.tipo, tipo_inicial):
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' (tipo '{d.tipo}') com um "
                        f"valor do tipo '{tipo_inicial}'", d.linha)
            else:
                tipo_inicial, _ = self._tipo_expr(d.inicial, escopo)
                if not self._compativel(d.tipo, tipo_inicial):
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' (tipo '{d.tipo}') com um "
                        f"valor do tipo '{tipo_inicial}'", d.linha)
        dims_n = 0 if d.dims is None else len(d.dims)
        escopo[d.nome] = (d.tipo, dims_n, d.eh_constante)

    def _valor_literal_negativo(self, expr):
        """Devolve o valor se 'expr' for um literal negativo -- reconhece
        tanto um Literal já negativo como (o caso mais comum, já que o
        lexer nunca produz um número negativo) UnOp('-', Literal(N)).
        Devolve None se não for um literal negativo reconhecível."""
        if isinstance(expr, A.Literal) and isinstance(expr.valor, (int, float)) and expr.valor < 0:  # pragma: no cover -- o lexer nunca produz um Literal já negativo (ver UnOp abaixo)
            return expr.valor
        if isinstance(expr, A.UnOp) and expr.op == "-" and isinstance(expr.operando, A.Literal):
            return -expr.operando.valor
        return None

    def _verificar_estrutura_literal(self, lit: A.EstruturaLiteral, tipo_esperado, escopo):
        if tipo_esperado not in self.estruturas:
            raise ErroSemantico(
                f"'{{campo: valor, ...}}' só pode inicializar uma estrutura; "
                f"'{tipo_esperado}' não é uma estrutura", lit.linha)
        campos_da_estrutura = self.estruturas[tipo_esperado]
        vistos = set()
        for nome_campo, expr in lit.campos:
            if nome_campo in vistos:
                raise ErroSemantico(
                    f"campo '{nome_campo}' repetido no literal de '{tipo_esperado}'",
                    lit.linha)
            vistos.add(nome_campo)
            if nome_campo not in campos_da_estrutura:
                disponiveis = ", ".join(sorted(campos_da_estrutura))
                raise ErroSemantico(
                    f"a estrutura '{tipo_esperado}' não tem nenhum campo '{nome_campo}'. "
                    f"Campos disponíveis: {disponiveis}", lit.linha)
            tipo_campo, dims_campo = campos_da_estrutura[nome_campo]
            if dims_campo > 0:
                raise ErroSemantico(
                    f"o campo '{nome_campo}' é um array; não pode ser inicializado "
                    f"diretamente num literal de estrutura", lit.linha)
            tipo_valor, _ = self._tipo_expr(expr, escopo)
            if not self._compativel(tipo_campo, tipo_valor):
                raise ErroSemantico(
                    f"o campo '{nome_campo}' de '{tipo_esperado}' espera '{tipo_campo}' "
                    f"mas recebeu '{tipo_valor}'", lit.linha)

    def _verificar_array_literal(self, lit: A.ArrayLiteral, tipo_elemento, profundidade, escopo):
        for elem in lit.elementos:
            if profundidade > 1:
                if not isinstance(elem, A.ArrayLiteral):  # pragma: no cover -- o parser já exige '{' aninhado neste caso
                    raise ErroSemantico(
                        f"esperava-se uma lista aninhada {{...}} (o array tem "
                        f"{profundidade} dimensões)", lit.linha)
                self._verificar_array_literal(elem, tipo_elemento, profundidade - 1, escopo)
            else:
                if isinstance(elem, A.ArrayLiteral):  # pragma: no cover -- o parser já rejeita '{' a mais
                    raise ErroSemantico(
                        "demasiados níveis de aninhamento em {...} para as dimensões "
                        "declaradas", lit.linha)
                tipo_elem, _ = self._tipo_expr(elem, escopo)
                if not self._compativel(tipo_elemento, tipo_elem):
                    raise ErroSemantico(
                        f"elemento do array é do tipo '{tipo_elem}', esperava-se "
                        f"'{tipo_elemento}'", lit.linha)

    # ---------- blocos / instruções ----------
    def _verificar_bloco(self, stmts, escopo, ctx_funcao):
        for s in stmts:
            self._verificar_stmt(s, escopo, ctx_funcao)

    def _tem_ref(self, chamada: A.Chamada):
        if "." in chamada.nome:
            return False
        f_def = self.funcoes.get(chamada.nome)
        return f_def is not None and any(p.por_referencia for p in f_def.parametros)

    def _verificar_stmt(self, s, escopo, ctx_funcao):
        if isinstance(s, A.Declaracao):
            self._registar_decl(escopo, s)

        elif isinstance(s, A.Atribuicao):
            self._verificar_nao_constante(s.alvo, escopo, "atribuir a")
            tipo_alvo, _ = self._tipo_lvalue(s.alvo, escopo)
            if isinstance(s.expr, A.Chamada) and self._tem_ref(s.expr):
                tipo_retorno = self._verificar_chamada(s.expr, escopo)
                if tipo_retorno is None:
                    raise ErroSemantico(
                        f"'{s.expr.nome}' é um procedimento e não devolve valor",
                        s.linha)
                if not self._compativel(tipo_alvo, tipo_retorno):
                    raise ErroSemantico(
                        f"não é possível atribuir um valor do tipo '{tipo_retorno}' à "
                        f"variável '{s.alvo.nome}' (tipo '{tipo_alvo}')", s.linha)
            else:
                tipo_expr, _ = self._tipo_expr(s.expr, escopo)
                if not self._compativel(tipo_alvo, tipo_expr):
                    raise ErroSemantico(
                        f"não é possível atribuir um valor do tipo '{tipo_expr}' à "
                        f"variável '{s.alvo.nome}' (tipo '{tipo_alvo}')", s.linha)

        elif isinstance(s, A.Ler):
            for alvo in s.alvos:
                self._verificar_nao_constante(alvo, escopo, "ler para")
                self._tipo_lvalue(alvo, escopo)

        elif isinstance(s, A.Escrever):
            for e in s.exprs:
                self._tipo_expr(e, escopo)

        elif isinstance(s, A.Se):
            for cond, corpo in s.ramos:
                tipo, _ = self._tipo_expr(cond, escopo)
                if tipo != "booleano":
                    raise ErroSemantico(
                        f"a condição de 'se' tem de ser booleana (é '{tipo}')",
                        getattr(cond, "linha", s.linha))
                self._verificar_bloco(corpo, escopo, ctx_funcao)
            if s.senao is not None:
                self._verificar_bloco(s.senao, escopo, ctx_funcao)

        elif isinstance(s, A.Para):
            if s.var in escopo and escopo[s.var][:2] != ("inteiro", 0):
                raise ErroSemantico(
                    f"a variável de controlo '{s.var}' do ciclo 'para' tem de ser "
                    f"inteiro", s.linha)
            if s.var in escopo and escopo[s.var][2]:
                raise ErroSemantico(
                    f"'{s.var}' é uma constante; não pode ser usada como variável "
                    f"de controlo de um ciclo 'para'", s.linha)
            if s.var not in escopo:
                escopo[s.var] = ("inteiro", 0, False)
            for expr, rotulo in ((s.ini, "inicial"), (s.fim, "final")):
                tipo, _ = self._tipo_expr(expr, escopo)
                if tipo != "inteiro":
                    raise ErroSemantico(
                        f"o valor {rotulo} do ciclo 'para' tem de ser inteiro (é "
                        f"'{tipo}')", s.linha)
            if s.passo is not None:
                tipo, _ = self._tipo_expr(s.passo, escopo)
                if tipo != "inteiro":
                    raise ErroSemantico("o 'passo' do ciclo 'para' tem de ser inteiro", s.linha)
                if isinstance(s.passo, A.Literal) and s.passo.valor == 0:
                    raise ErroSemantico(
                        "o 'passo' de um ciclo 'para' não pode ser 0 (o ciclo nunca "
                        "avançaria)", s.passo.linha)
            self._verificar_bloco(s.corpo, escopo, ctx_funcao)

        elif isinstance(s, A.Enquanto):
            tipo, _ = self._tipo_expr(s.condicao, escopo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'enquanto' tem de ser booleana (é '{tipo}')", s.linha)
            self._verificar_bloco(s.corpo, escopo, ctx_funcao)

        elif isinstance(s, A.FazEnquanto):
            self._verificar_bloco(s.corpo, escopo, ctx_funcao)
            tipo, _ = self._tipo_expr(s.condicao, escopo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'fazer...enquanto' tem de ser booleana (é "
                    f"'{tipo}')", s.linha)

        elif isinstance(s, A.Escolha):
            tipo_base, _ = self._tipo_expr(s.expr, escopo)
            for valores, corpo in s.casos:
                for v in valores:
                    tipo_v, _ = self._tipo_expr(v, escopo)
                    if not self._tipos_comparaveis(tipo_base, tipo_v):
                        raise ErroSemantico(
                            f"o valor de 'caso' é do tipo '{tipo_v}', incompatível com "
                            f"'{tipo_base}' de 'escolher'", getattr(v, "linha", s.linha))
                self._verificar_bloco(corpo, escopo, ctx_funcao)
            if s.contrario is not None:
                self._verificar_bloco(s.contrario, escopo, ctx_funcao)

        elif isinstance(s, A.Devolver):
            if ctx_funcao is None or ctx_funcao.eh_procedimento:
                raise ErroSemantico(
                    "'devolver' só pode ser usado dentro de uma função", s.linha)
            tipo, _ = self._tipo_expr(s.expr, escopo)
            if not self._compativel(ctx_funcao.tipo_retorno, tipo):
                raise ErroSemantico(
                    f"a função '{ctx_funcao.nome}' devolve '{ctx_funcao.tipo_retorno}' "
                    f"mas está a devolver um valor do tipo '{tipo}'", s.linha)

        elif isinstance(s, A.ChamadaStmt):
            self._verificar_chamada(s.chamada, escopo)

        elif isinstance(s, A.Afirmar):
            tipo, _ = self._tipo_expr(s.condicao, escopo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'afirmar' tem de ser booleana (é '{tipo}')", s.linha)
            if s.mensagem is not None:
                tipo_msg, _ = self._tipo_expr(s.mensagem, escopo)
                if tipo_msg not in TEXTUAIS:
                    raise ErroSemantico(
                        f"a mensagem de 'afirmar' tem de ser texto (é '{tipo_msg}')", s.linha)

        else:  # pragma: no cover -- todos os tipos de instrução da AST são tratados acima
            raise ErroSemantico(f"instrução não reconhecida: {type(s).__name__}", getattr(s, "linha", 0))

    # ---------- expressões ----------
    def _verificar_nao_constante(self, lv: A.LValue, escopo, acao):
        if lv.nome in escopo and len(escopo[lv.nome]) > 2 and escopo[lv.nome][2]:
            raise ErroSemantico(
                f"não é possível {acao} '{lv.nome}': é uma constante", lv.linha)

    def _tipo_lvalue(self, lv: A.LValue, escopo):
        if lv.nome not in escopo:
            raise ErroSemantico(f"a variável '{lv.nome}' não foi declarada", lv.linha)
        tipo, dims = escopo[lv.nome][0], escopo[lv.nome][1]
        for tag, valor in lv.acessos:
            if tag == "indice":
                if dims <= 0:
                    raise ErroSemantico(
                        f"'{lv.nome}' não é um array; não pode ser indexado", lv.linha)
                tipo_idx, _ = self._tipo_expr(valor, escopo)
                if tipo_idx != "inteiro":
                    raise ErroSemantico(
                        f"o índice de '{lv.nome}' tem de ser inteiro (é '{tipo_idx}')",
                        lv.linha)
                dims -= 1
            else:  # "campo"
                if dims > 0:
                    raise ErroSemantico(
                        f"'{lv.nome}' é um array; falta indexá-lo antes de aceder a "
                        f"'.{valor}'", lv.linha)
                if tipo not in self.estruturas:
                    raise ErroSemantico(
                        f"'{tipo}' não é uma estrutura; não tem campo '{valor}'", lv.linha)
                campos = self.estruturas[tipo]
                if valor not in campos:
                    disponiveis = ", ".join(sorted(campos))
                    raise ErroSemantico(
                        f"a estrutura '{tipo}' não tem nenhum campo '{valor}'. "
                        f"Campos disponíveis: {disponiveis}", lv.linha)
                tipo, dims = campos[valor]
        return tipo, dims

    def _tipo_expr(self, expr, escopo):
        if isinstance(expr, A.Literal):
            return expr.tipo, 0
        if isinstance(expr, A.LValue):
            tipo, dims = self._tipo_lvalue(expr, escopo)
            if dims > 0:
                raise ErroSemantico(
                    f"'{expr.nome}' é um array; falta indexá-lo (ex: {expr.nome}[i])",
                    expr.linha)
            return tipo, 0
        if isinstance(expr, A.BinOp):
            return self._tipo_binop(expr, escopo)
        if isinstance(expr, A.UnOp):
            tipo, _ = self._tipo_expr(expr.operando, escopo)
            if expr.op == "nao":
                if tipo != "booleano":
                    raise ErroSemantico(
                        f"'nao' só se aplica a valores booleanos (é '{tipo}')", expr.linha)
                return "booleano", 0
            if expr.op == "-":
                if tipo not in NUMERICOS:
                    raise ErroSemantico(
                        f"'-' unário só se aplica a números (é '{tipo}')", expr.linha)
                return tipo, 0
        if isinstance(expr, A.Chamada):
            if self._tem_ref(expr):
                raise ErroSemantico(
                    f"'{expr.nome}' tem parâmetros por referência e não pode ser "
                    f"usada dentro de uma expressão; usa-a como instrução, ex: "
                    f"'x = {expr.nome}(...)'", expr.linha)
            tipo_retorno = self._verificar_chamada(expr, escopo)
            if tipo_retorno is None:
                raise ErroSemantico(
                    f"'{expr.nome}' é um procedimento e não devolve valor; não pode "
                    f"ser usado dentro de uma expressão", expr.linha)
            return tipo_retorno, 0
        raise ErroSemantico(  # pragma: no cover -- todos os tipos de expressão da AST são tratados acima
            f"expressão não reconhecida: {type(expr).__name__}", getattr(expr, "linha", 0))

    def _tipo_binop(self, expr: A.BinOp, escopo):
        t_e, _ = self._tipo_expr(expr.esq, escopo)
        t_d, _ = self._tipo_expr(expr.dire, escopo)
        op = expr.op

        if op == "+":
            if t_e in NUMERICOS and t_d in NUMERICOS:
                return ("decimal" if "decimal" in (t_e, t_d) else "inteiro"), 0
            if t_e in TEXTUAIS and t_d in TEXTUAIS:
                return "cadeia", 0
            raise ErroSemantico(
                f"'+' só pode ser usado entre dois números (soma) ou entre dois "
                f"textos (concatenação) — tens '{t_e}' e '{t_d}'", expr.linha)

        if op in ("-", "*", "^"):
            if t_e not in NUMERICOS or t_d not in NUMERICOS:
                raise ErroSemantico(
                    f"o operador '{op}' só pode ser usado entre números (tens "
                    f"'{t_e}' e '{t_d}')", expr.linha)
            return ("decimal" if "decimal" in (t_e, t_d) else "inteiro"), 0

        if op == "/":
            if t_e not in NUMERICOS or t_d not in NUMERICOS:
                raise ErroSemantico(
                    f"o operador '/' só pode ser usado entre números (tens "
                    f"'{t_e}' e '{t_d}')", expr.linha)
            return "decimal", 0

        if op in ("div", "mod"):
            if t_e != "inteiro" or t_d != "inteiro":
                raise ErroSemantico(
                    f"o operador '{op}' exige dois valores inteiros (tens "
                    f"'{t_e}' e '{t_d}')", expr.linha)
            return "inteiro", 0

        if op in ("==", "<>"):
            if not self._tipos_comparaveis(t_e, t_d):
                raise ErroSemantico(
                    f"não é possível comparar '{t_e}' com '{t_d}'", expr.linha)
            return "booleano", 0

        if op in ("<", ">", "<=", ">="):
            ambos_num = t_e in NUMERICOS and t_d in NUMERICOS
            ambos_texto = t_e in TEXTUAIS and t_d in TEXTUAIS
            if not (ambos_num or ambos_texto):
                raise ErroSemantico(
                    f"o operador '{op}' só pode ser usado entre números ou entre "
                    f"texto (tens '{t_e}' e '{t_d}')", expr.linha)
            return "booleano", 0

        if op in ("e", "ou"):
            if t_e != "booleano" or t_d != "booleano":
                raise ErroSemantico(
                    f"o operador '{op}' só pode ser usado entre valores booleanos "
                    f"(tens '{t_e}' e '{t_d}')", expr.linha)
            return "booleano", 0

        raise ErroSemantico(f"operador desconhecido '{op}'", expr.linha)  # pragma: no cover -- o parser só produz operadores conhecidos

    def _tipos_comparaveis(self, a, b):
        if a in NUMERICOS and b in NUMERICOS:
            return True
        if a in TEXTUAIS and b in TEXTUAIS:
            return True
        return a == b

    def _compativel(self, tipo_alvo, tipo_valor):
        if tipo_alvo == tipo_valor:
            return True
        if tipo_alvo == "decimal" and tipo_valor == "inteiro":
            return True
        if tipo_alvo == "cadeia" and tipo_valor == "caracter":
            return True
        return False

    # ---------- chamadas ----------
    def _verificar_chamada(self, chamada: A.Chamada, escopo):
        if "." in chamada.nome:
            biblioteca, metodo = chamada.nome.split(".", 1)
            if biblioteca not in self.bibliotecas_importadas:
                raise ErroSemantico(
                    f"a biblioteca '{biblioteca}' não foi importada — usa "
                    f"'importar {biblioteca.capitalize()}' no topo do ficheiro",
                    chamada.linha)
            info = self.bibliotecas_importadas[biblioteca]
            if metodo not in info["funcoes"]:
                disponiveis = ", ".join(sorted(info["funcoes"]))
                raise ErroSemantico(
                    f"'{biblioteca}' não tem nenhuma função '{metodo}'. Disponíveis: "
                    f"{disponiveis}", chamada.linha)
            categorias, tipo_retorno, _codigo = info["funcoes"][metodo]
            if len(chamada.args) != len(categorias):
                raise ErroSemantico(
                    f"'{chamada.nome}' espera {len(categorias)} argumento(s), "
                    f"recebeu {len(chamada.args)}", chamada.linha)
            for arg, categoria in zip(chamada.args, categorias):
                tipo, _ = self._tipo_expr(arg, escopo)
                if categoria == "numeric" and tipo not in NUMERICOS:
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um argumento numérico (é '{tipo}')",
                        chamada.linha)
                if categoria == "cadeia" and tipo not in TEXTUAIS:
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera texto (é '{tipo}')", chamada.linha)
                if categoria == "inteiro" and tipo != "inteiro":
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um inteiro (é '{tipo}')", chamada.linha)
            return tipo_retorno

        f_def = self.funcoes.get(chamada.nome)
        if f_def is None:
            raise ErroSemantico(
                f"função ou procedimento '{chamada.nome}' não foi definido", chamada.linha)
        if len(chamada.args) != len(f_def.parametros):
            raise ErroSemantico(
                f"'{chamada.nome}' espera {len(f_def.parametros)} argumento(s), "
                f"recebeu {len(chamada.args)}", chamada.linha)
        for arg, p in zip(chamada.args, f_def.parametros):
            if p.por_referencia:
                if not isinstance(arg, A.LValue):
                    raise ErroSemantico(
                        f"o argumento para o parâmetro por referência '{p.nome}' tem "
                        f"de ser uma variável, um elemento de array ou um campo, não "
                        f"uma expressão calculada", chamada.linha)
                if arg.nome not in escopo:
                    raise ErroSemantico(
                        f"a variável '{arg.nome}' não foi declarada", chamada.linha)
                if len(escopo[arg.nome]) > 2 and escopo[arg.nome][2]:
                    raise ErroSemantico(
                        f"'{arg.nome}' é uma constante; não pode ser passada por "
                        f"referência ao parâmetro '{p.nome}'", chamada.linha)
            tipo, _ = self._tipo_expr(arg, escopo)
            if not self._compativel(p.tipo, tipo):
                raise ErroSemantico(
                    f"o parâmetro '{p.nome}' de '{chamada.nome}' espera "
                    f"'{p.tipo}' mas recebeu '{tipo}'", chamada.linha)
        return None if f_def.eh_procedimento else f_def.tipo_retorno


def verificar(programa: A.Programa):
    verificar_nomes_python(programa)
    VerificadorTipos(programa).verificar()
