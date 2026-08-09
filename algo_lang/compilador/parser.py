# -*- coding: utf-8 -*-
"""Parser recursivo-descendente para a linguagem ALGO."""

from .lexer import tokenizar
from . import ast_nodes as A

NOMES_AMIGAVEIS = {
    "COLON": "':'", "COMMA": "','", "LPAREN": "'('", "RPAREN": "')'",
    "LBRACKET": "'['", "RBRACKET": "']'", "ATRIB": "'='", "DOT": "'.'",
    "LBRACE": "'{'", "RBRACE": "'}'",
    "NEWLINE": "fim de linha", "INDENT": "aumento de indentação",
    "DEDENT": "diminuição de indentação", "EOF": "fim do ficheiro",
    "ENTAO": "'entao'", "FAZER": "'fazer'", "ID": "um identificador",
}


def _nome_amigavel(tipo, valor=None):
    if tipo in NOMES_AMIGAVEIS:
        return NOMES_AMIGAVEIS[tipo]
    if valor is not None:
        return f"{tipo.lower()} ({valor!r})"
    return tipo.lower()  # pragma: no cover -- todo token sem nome amigável tem valor


class ErroSintatico(Exception):
    def __init__(self, mensagem, linha):
        super().__init__(f"Erro de sintaxe na linha {linha}: {mensagem}")
        self.linha = linha


LIMITE_PROFUNDIDADE_EXPR = 50


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self._profundidade_expr = 0

    # ---------- utilidades ----------
    def atual(self):
        return self.tokens[self.pos]

    def ver(self, tipo):
        return self.atual().tipo == tipo

    def avancar(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def esperar(self, tipo, msg=None):
        if not self.ver(tipo):
            atual = self.atual()
            raise ErroSintatico(
                msg or f"esperava-se {_nome_amigavel(tipo)} mas encontrou "
                       f"{_nome_amigavel(atual.tipo, atual.valor)}",
                atual.linha,
            )
        return self.avancar()

    # ---------- programa ----------
    def parse_programa(self):
        self.esperar("ALGORITMO")
        nome_tok = self.esperar("STRING")
        self.esperar("NEWLINE")

        importares = []
        inclusoes = []
        estruturas = []
        declaracoes = []
        funcoes = []
        corpo = None

        while not self.ver("EOF"):
            if self.ver("IMPORTAR"):
                importares.append(self._parse_importar())
            elif self.ver("INCLUIR"):
                inclusoes.append(self._parse_incluir())
            elif self.ver("ESTRUTURA"):
                estruturas.append(self._parse_estrutura_def())
            elif self.ver("FUNCAO") or self.ver("PROCEDIMENTO"):
                funcoes.append(self._parse_funcao_def())
            elif self.ver("CONSTANTE"):
                declaracoes.append(self._parse_constante())
            elif self.ver("ID"):
                declaracoes.extend(self._parse_declaracao_global())
            elif self.ver("INICIO"):
                corpo = self._parse_bloco_inicio()
            else:
                raise ErroSintatico(
                    f"esperava-se uma declaração de variável, 'constante', 'estrutura', "
                    f"'funcao', 'procedimento' ou 'inicio', encontrou {self.atual().tipo}",
                    self.atual().linha)

        if corpo is None:
            raise ErroSintatico("o programa tem de ter um bloco 'inicio'", self.atual().linha)

        return A.Programa(nome_tok.valor, importares, inclusoes, estruturas,
                           declaracoes, funcoes, corpo)

    def _parse_estrutura_def(self):
        linha = self.atual().linha
        self.esperar("ESTRUTURA")
        nome_tok = self.esperar("ID")
        self.esperar("NEWLINE")
        self.esperar("INDENT")
        campos = []
        while not self.ver("DEDENT"):
            campos.extend(self._parse_declaracao_comum())
        self.esperar("DEDENT")
        return A.EstruturaDef(nome_tok.valor, campos, linha)

    def _parse_importar(self):
        linha = self.atual().linha
        self.esperar("IMPORTAR")
        nome_tok = self.esperar("ID")
        self.esperar("NEWLINE")
        return A.Importar(nome_tok.valor, linha)

    def _parse_incluir(self):
        linha = self.atual().linha
        self.esperar("INCLUIR")
        caminho_tok = self.esperar("STRING")
        self.esperar("NEWLINE")
        return A.Incluir(caminho_tok.valor, linha)

    def _parse_tipo(self):
        """Um 'tipo' é sintaticamente apenas um identificador -- pode ser um
        tipo primitivo (inteiro, decimal, ...) ou o nome de uma 'estrutura'.
        Propositadamente NÃO são palavras reservadas (para não colidirem com
        nomes de bibliotecas como 'cadeia'/'math' ou de estruturas do
        utilizador); a validade do tipo é confirmada mais tarde, em
        semantics.py, quando já sabemos que estruturas foram definidas."""
        tok = self.atual()
        if tok.tipo != "ID":
            raise ErroSintatico(f"esperava-se um tipo, encontrou {tok.tipo}", tok.linha)
        self.avancar()
        return tok.valor

    # declaração global (fora de funções/procedimentos, antes de 'inicio')
    def _parse_declaracao_global(self):
        return self._parse_declaracao_comum()

    def _parse_declaracao_comum(self):
        """Assume que o token atual é o primeiro ID de uma lista de nomes,
        seguido de ':' e do tipo. Já confirmado pelo chamador via lookahead."""
        linha = self.atual().linha
        nomes = [self.esperar("ID").valor]
        while self.ver("COMMA"):
            self.avancar()
            nomes.append(self.esperar("ID").valor)
        self.esperar("COLON")
        tipo = self._parse_tipo()
        dims = None
        if self.ver("LBRACKET"):
            dims = []
            while self.ver("LBRACKET"):
                self.avancar()
                dims.append(self._parse_expr())
                self.esperar("RBRACKET")
        inicial = None
        if self.ver("ATRIB"):
            self.avancar()
            if len(nomes) > 1:
                raise ErroSintatico(
                    "não é possível inicializar várias variáveis na mesma linha", linha)
            if dims is not None:
                inicial = self._parse_array_literal(len(dims))
            elif self.ver("LBRACE"):
                if self._proximo_parece_campo_literal():
                    inicial = self._parse_estrutura_literal()
                else:
                    raise ErroSintatico(
                        f"'{{...}}' só pode inicializar um array (falta '[tamanho]' a "
                        f"seguir ao tipo de '{nomes[0]}') ou uma estrutura (com a forma "
                        f"'{{campo: valor, ...}}')", linha)
            else:
                inicial = self._parse_expr()
        self.esperar("NEWLINE")
        return [A.Declaracao(tipo, nome, dims, linha, inicial) for nome in nomes]

    def _parse_array_literal(self, profundidade):
        linha = self.atual().linha
        self.esperar("LBRACE")
        elementos = []
        if not self.ver("RBRACE"):
            elementos.append(self._parse_elemento_array_literal(profundidade))
            while self.ver("COMMA"):
                self.avancar()
                elementos.append(self._parse_elemento_array_literal(profundidade))
        self.esperar("RBRACE")
        return A.ArrayLiteral(elementos, linha)

    def _parse_elemento_array_literal(self, profundidade):
        if profundidade > 1:
            return self._parse_array_literal(profundidade - 1)
        if self.ver("LBRACE"):
            raise ErroSintatico(
                "'{...}' a mais para as dimensões declaradas do array", self.atual().linha)
        return self._parse_expr()

    def _proximo_parece_campo_literal(self):
        """Olha para os tokens a seguir a '{' (sem consumir) para decidir se
        parece um literal de estrutura ('{campo: valor, ...}' ou '{}') em
        vez de uma lista de valores de array mal colocada."""
        prox1 = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        prox2 = self.tokens[self.pos + 2] if self.pos + 2 < len(self.tokens) else None
        if prox1 is not None and prox1.tipo == "RBRACE":
            return True
        return prox1 is not None and prox1.tipo == "ID" and prox2 is not None and prox2.tipo == "COLON"

    def _parse_estrutura_literal(self):
        """Sintaxe: { campo: expr, campo: expr, ... } -- campos omitidos
        ficam com o valor por omissão do seu tipo."""
        linha = self.atual().linha
        self.esperar("LBRACE")
        campos = []
        if not self.ver("RBRACE"):
            campos.append(self._parse_campo_literal())
            while self.ver("COMMA"):
                self.avancar()
                campos.append(self._parse_campo_literal())
        self.esperar("RBRACE")
        return A.EstruturaLiteral(campos, linha)

    def _parse_campo_literal(self):
        nome_tok = self.esperar("ID")
        self.esperar("COLON")
        valor = self._parse_expr()
        return (nome_tok.valor, valor)

    def _parse_constante(self):
        linha = self.atual().linha
        self.esperar("CONSTANTE")
        nome_tok = self.esperar("ID")
        self.esperar("COLON")
        tipo = self._parse_tipo()
        self.esperar("ATRIB")
        valor = self._parse_expr()
        self.esperar("NEWLINE")
        return A.Declaracao(tipo, nome_tok.valor, None, linha, inicial=valor, eh_constante=True)

    def _parse_afirmar(self):
        linha = self.atual().linha
        self.esperar("AFIRMAR")
        condicao = self._parse_expr()
        mensagem = None
        if self.ver("COMMA"):
            self.avancar()
            mensagem = self._parse_expr()
        self.esperar("NEWLINE")
        return A.Afirmar(condicao, mensagem, linha)

    def _parse_funcao_def(self):
        eh_proc = self.ver("PROCEDIMENTO")
        linha = self.atual().linha
        if eh_proc:
            self.avancar()
        else:
            self.esperar("FUNCAO")
        nome_tok = self.esperar("ID")
        self.esperar("LPAREN")
        params = []
        if not self.ver("RPAREN"):
            params.append(self._parse_param())
            while self.ver("COMMA"):
                self.avancar()
                params.append(self._parse_param())
        self.esperar("RPAREN")
        tipo_retorno = None
        if not eh_proc:
            self.esperar("COLON")
            tipo_retorno = self._parse_tipo()
        self.esperar("NEWLINE")
        corpo = self._parse_bloco_stmts()
        return A.FuncaoDef(nome_tok.valor, tipo_retorno, params, corpo, linha, eh_proc)

    def _parse_param(self):
        por_ref = False
        if self.ver("REF"):
            self.avancar()
            por_ref = True
        nome_tok = self.esperar("ID")
        self.esperar("COLON")
        tipo = self._parse_tipo()
        return A.Parametro(nome_tok.valor, tipo, por_ref)

    def _parse_bloco_inicio(self):
        self.esperar("INICIO")
        self.esperar("NEWLINE")
        return self._parse_bloco_stmts()

    def _parse_bloco_stmts(self):
        self.esperar("INDENT")
        stmts = []
        while not self.ver("DEDENT"):
            item = self._parse_stmt()
            if isinstance(item, list):
                stmts.extend(item)
            else:
                stmts.append(item)
        self.esperar("DEDENT")
        return stmts

    # ---------- statements ----------
    def _parse_stmt(self):
        tok = self.atual()
        if tok.tipo == "LER":
            return self._parse_ler()
        if tok.tipo == "ESCREVER":
            return self._parse_escrever()
        if tok.tipo == "SE":
            return self._parse_se()
        if tok.tipo == "PARA":
            return self._parse_para()
        if tok.tipo == "ENQUANTO":
            return self._parse_enquanto()
        if tok.tipo == "FAZER":
            return self._parse_faz_enquanto()
        if tok.tipo == "ESCOLHER":
            return self._parse_escolha()
        if tok.tipo == "DEVOLVER":
            return self._parse_devolver()
        if tok.tipo == "CONSTANTE":
            return self._parse_constante()
        if tok.tipo == "AFIRMAR":
            return self._parse_afirmar()
        if tok.tipo == "ID":
            return self._parse_decl_atrib_ou_chamada()
        raise ErroSintatico(f"instrução inesperada: {tok.tipo}", tok.linha)

    def _parse_decl_atrib_ou_chamada(self):
        """Tenta interpretar como declaração (nome[, nome...]:tipo); caso
        contrário, recua e interpreta como atribuição ou chamada."""
        pos_salva = self.pos
        self.avancar()
        while self.ver("COMMA"):
            self.avancar()
            if not self.ver("ID"):  # pragma: no cover -- caso extremo de vírgula a mais; acaba por dar erro sintático a seguir de qualquer forma
                break
            self.avancar()
        if self.ver("COLON"):
            self.pos = pos_salva
            return self._parse_declaracao_comum()
        self.pos = pos_salva
        return self._parse_atribuicao_ou_chamada()

    def _parse_ler(self):
        linha = self.atual().linha
        self.esperar("LER")
        self.esperar("LPAREN")
        alvos = [self._parse_lvalue()]
        while self.ver("COMMA"):
            self.avancar()
            alvos.append(self._parse_lvalue())
        self.esperar("RPAREN")
        self.esperar("NEWLINE")
        return A.Ler(alvos, linha)

    def _parse_escrever(self):
        linha = self.atual().linha
        self.esperar("ESCREVER")
        self.esperar("LPAREN")
        exprs = [self._parse_expr()]
        while self.ver("COMMA"):
            self.avancar()
            exprs.append(self._parse_expr())
        self.esperar("RPAREN")
        self.esperar("NEWLINE")
        return A.Escrever(exprs, linha)

    def _parse_se(self):
        linha = self.atual().linha
        self.esperar("SE")
        cond = self._parse_expr()
        self.esperar("ENTAO")
        self.esperar("NEWLINE")
        corpo = self._parse_bloco_stmts()
        ramos = [(cond, corpo)]
        senao = None
        while self.ver("SENAO"):
            self.avancar()
            if self.ver("SE"):
                self.avancar()
                cond2 = self._parse_expr()
                self.esperar("ENTAO")
                self.esperar("NEWLINE")
                corpo2 = self._parse_bloco_stmts()
                ramos.append((cond2, corpo2))
            else:
                self.esperar("NEWLINE")
                senao = self._parse_bloco_stmts()
                break
        return A.Se(ramos, senao, linha)

    def _parse_para(self):
        linha = self.atual().linha
        self.esperar("PARA")
        var_tok = self.esperar("ID")
        self.esperar("DE")
        ini = self._parse_expr()
        self.esperar("ATE")
        fim = self._parse_expr()
        passo = None
        if self.ver("PASSO"):
            self.avancar()
            passo = self._parse_expr()
        self.esperar("FAZER")
        self.esperar("NEWLINE")
        corpo = self._parse_bloco_stmts()
        return A.Para(var_tok.valor, ini, fim, passo, corpo, linha)

    def _parse_enquanto(self):
        linha = self.atual().linha
        self.esperar("ENQUANTO")
        cond = self._parse_expr()
        self.esperar("FAZER")
        self.esperar("NEWLINE")
        corpo = self._parse_bloco_stmts()
        return A.Enquanto(cond, corpo, linha)

    def _parse_faz_enquanto(self):
        linha = self.atual().linha
        self.esperar("FAZER")
        self.esperar("NEWLINE")
        corpo = self._parse_bloco_stmts()
        self.esperar("ENQUANTO")
        cond = self._parse_expr()
        self.esperar("NEWLINE")
        return A.FazEnquanto(corpo, cond, linha)

    def _parse_escolha(self):
        linha = self.atual().linha
        self.esperar("ESCOLHER")
        expr = self._parse_expr()
        self.esperar("NEWLINE")
        self.esperar("INDENT")
        casos = []
        contrario = None
        while self.ver("CASO"):
            self.avancar()
            valores = [self._parse_expr()]
            while self.ver("COMMA"):
                self.avancar()
                valores.append(self._parse_expr())
            self.esperar("NEWLINE")
            corpo = self._parse_bloco_stmts()
            casos.append((valores, corpo))
        if self.ver("CONTRARIO"):
            self.avancar()
            self.esperar("NEWLINE")
            contrario = self._parse_bloco_stmts()
        self.esperar("DEDENT")
        return A.Escolha(expr, casos, contrario, linha)

    def _parse_devolver(self):
        linha = self.atual().linha
        self.esperar("DEVOLVER")
        expr = self._parse_expr()
        self.esperar("NEWLINE")
        return A.Devolver(expr, linha)

    def _parse_chamada_biblioteca_ou_none(self):
        """Se o token atual for ID e formar 'biblioteca.metodo(' devolve a
        Chamada correspondente; caso contrário não consome nada e devolve None."""
        pos_salva = self.pos
        nome_tok = self.esperar("ID")
        if self.ver("DOT"):
            self.avancar()
            parte2 = self.esperar("ID")
            if self.ver("LPAREN"):
                nome = f"{nome_tok.valor}.{parte2.valor}"
                self.avancar()
                args = []
                if not self.ver("RPAREN"):
                    args.append(self._parse_expr())
                    while self.ver("COMMA"):
                        self.avancar()
                        args.append(self._parse_expr())
                self.esperar("RPAREN")
                return A.Chamada(nome, args, nome_tok.linha)
        self.pos = pos_salva
        return None

    def _parse_acessos(self):
        """Consome uma sequência de '.campo' e '[indice]' e devolve a lista
        de acessos correspondente."""
        acessos = []
        while self.ver("DOT") or self.ver("LBRACKET"):
            if self.ver("DOT"):
                self.avancar()
                campo_tok = self.esperar("ID")
                acessos.append(("campo", campo_tok.valor))
            else:
                self.avancar()
                expr = self._parse_expr()
                self.esperar("RBRACKET")
                acessos.append(("indice", expr))
        return acessos

    def _parse_atribuicao_ou_chamada(self):
        chamada = self._parse_chamada_biblioteca_ou_none()
        if chamada is not None:
            self.esperar("NEWLINE")
            return A.ChamadaStmt(chamada, chamada.linha)

        nome_tok = self.esperar("ID")
        if self.ver("LPAREN"):
            self.avancar()
            args = []
            if not self.ver("RPAREN"):
                args.append(self._parse_expr())
                while self.ver("COMMA"):
                    self.avancar()
                    args.append(self._parse_expr())
            self.esperar("RPAREN")
            self.esperar("NEWLINE")
            return A.ChamadaStmt(A.Chamada(nome_tok.valor, args, nome_tok.linha), nome_tok.linha)

        acessos = self._parse_acessos()
        self.esperar("ATRIB")
        expr = self._parse_expr()
        self.esperar("NEWLINE")
        alvo = A.LValue(nome_tok.valor, acessos, nome_tok.linha)
        return A.Atribuicao(alvo, expr, nome_tok.linha)

    def _parse_lvalue(self):
        nome_tok = self.esperar("ID")
        acessos = self._parse_acessos()
        return A.LValue(nome_tok.valor, acessos, nome_tok.linha)

    # ---------- expressões (precedência) ----------
    def _parse_expr(self):
        # AL-18: sem isto, uma expressão fortemente aninhada (ex: muitos
        # parênteses seguidos) estourava a pilha de recursão do próprio
        # Python (RecursionError não tratado, sem número de linha nem
        # explicação) em vez de um erro de sintaxe amigável.
        self._profundidade_expr += 1
        if self._profundidade_expr > LIMITE_PROFUNDIDADE_EXPR:
            raise ErroSintatico(
                "expressão demasiado aninhada (parênteses ou operadores a mais) -- "
                "tenta simplificar, ex. dividindo em variáveis intermédias",
                self.atual().linha)
        try:
            return self._parse_ou()
        finally:
            self._profundidade_expr -= 1

    def _parse_ou(self):
        esq = self._parse_e()
        while self.ver("OU"):
            linha = self.avancar().linha
            dire = self._parse_e()
            esq = A.BinOp("ou", esq, dire, linha)
        return esq

    def _parse_e(self):
        esq = self._parse_nao()
        while self.ver("E"):
            linha = self.avancar().linha
            dire = self._parse_nao()
            esq = A.BinOp("e", esq, dire, linha)
        return esq

    def _parse_nao(self):
        if self.ver("NAO"):
            linha = self.avancar().linha
            operando = self._parse_nao()
            return A.UnOp("nao", operando, linha)
        return self._parse_relacional()

    def _parse_relacional(self):
        esq = self._parse_aditiva()
        ops = {"IGUAL": "==", "DIFERENTE": "<>", "MENOR": "<", "MAIOR": ">", "LE": "<=", "GE": ">="}
        if self.atual().tipo in ops:
            op_tok = self.avancar()
            dire = self._parse_aditiva()
            esq = A.BinOp(ops[op_tok.tipo], esq, dire, op_tok.linha)
        return esq

    def _parse_aditiva(self):
        esq = self._parse_multiplicativa()
        while self.atual().tipo in ("MAIS", "MENOS"):
            op_tok = self.avancar()
            dire = self._parse_multiplicativa()
            esq = A.BinOp(op_tok.valor, esq, dire, op_tok.linha)
        return esq

    def _parse_multiplicativa(self):
        esq = self._parse_unaria()
        while self.atual().tipo in ("VEZES", "DIVIDE", "DIV", "MOD"):
            op_tok = self.avancar()
            simbolo = {"VEZES": "*", "DIVIDE": "/", "DIV": "div", "MOD": "mod"}[op_tok.tipo]
            dire = self._parse_unaria()
            esq = A.BinOp(simbolo, esq, dire, op_tok.linha)
        return esq

    def _parse_unaria(self):
        if self.ver("MENOS"):
            linha = self.avancar().linha
            operando = self._parse_unaria()
            return A.UnOp("-", operando, linha)
        return self._parse_potencia()

    def _parse_potencia(self):
        base = self._parse_primario()
        if self.ver("POTENCIA"):
            linha = self.avancar().linha
            expoente = self._parse_unaria()
            return A.BinOp("^", base, expoente, linha)
        return base

    def _parse_primario(self):
        tok = self.atual()
        if tok.tipo == "INT":
            self.avancar()
            return A.Literal(tok.valor, "inteiro", tok.linha)
        if tok.tipo == "FLOAT":
            self.avancar()
            return A.Literal(tok.valor, "decimal", tok.linha)
        if tok.tipo == "STRING":
            self.avancar()
            return A.Literal(tok.valor, "cadeia", tok.linha)
        if tok.tipo == "CARACTER":
            self.avancar()
            return A.Literal(tok.valor, "caracter", tok.linha)
        if tok.tipo == "VERDADEIRO":
            self.avancar()
            return A.Literal(True, "booleano", tok.linha)
        if tok.tipo == "FALSO":
            self.avancar()
            return A.Literal(False, "booleano", tok.linha)
        if tok.tipo == "LPAREN":
            self.avancar()
            expr = self._parse_expr()
            self.esperar("RPAREN")
            return expr
        if tok.tipo == "ID":
            chamada = self._parse_chamada_biblioteca_ou_none()
            if chamada is not None:
                return chamada
            nome_tok = self.esperar("ID")
            if self.ver("LPAREN"):
                self.avancar()
                args = []
                if not self.ver("RPAREN"):
                    args.append(self._parse_expr())
                    while self.ver("COMMA"):
                        self.avancar()
                        args.append(self._parse_expr())
                self.esperar("RPAREN")
                return A.Chamada(nome_tok.valor, args, nome_tok.linha)
            acessos = self._parse_acessos()
            return A.LValue(nome_tok.valor, acessos, nome_tok.linha)
        raise ErroSintatico(f"expressão inesperada: {tok.tipo} ({tok.valor!r})", tok.linha)


def parse(codigo: str) -> A.Programa:
    tokens = tokenizar(codigo)
    parser = Parser(tokens)
    return parser.parse_programa()


def parse_biblioteca(codigo: str):
    """Interpreta um ficheiro incluído (via 'incluir') como uma biblioteca:
    apenas declarações globais, 'estrutura' e definições de função/
    procedimento, sem cabeçalho 'algoritmo' nem bloco 'inicio'."""
    tokens = tokenizar(codigo)
    parser = Parser(tokens)
    declaracoes = []
    funcoes = []
    estruturas = []
    while not parser.ver("EOF"):
        if parser.ver("FUNCAO") or parser.ver("PROCEDIMENTO"):
            funcoes.append(parser._parse_funcao_def())
        elif parser.ver("ESTRUTURA"):
            estruturas.append(parser._parse_estrutura_def())
        elif parser.ver("CONSTANTE"):
            declaracoes.append(parser._parse_constante())
        elif parser.ver("ID"):
            declaracoes.extend(parser._parse_declaracao_global())
        else:
            raise ErroSintatico(
                "um ficheiro incluído só pode conter declarações de variáveis, "
                f"'constante', 'estrutura', 'funcao' ou 'procedimento' "
                f"(encontrou {parser.atual().tipo})",
                parser.atual().linha)
    return declaracoes, funcoes, estruturas
