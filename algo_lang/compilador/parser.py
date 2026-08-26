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
    # Sem estas entradas, _nome_amigavel cairia no ramo genérico
    # (tipo.lower()) para estes tokens, mostrando jargão em inglês/
    # abreviaturas internas em vez de português.
    "STRING": "um texto entre aspas duplas", "INT": "um número inteiro",
    "FLOAT": "um número decimal", "CARACTER": "um caracter entre aspas simples",
    "LE": "'<='", "GE": "'>='",
}


TOKENS_COM_VALOR = {"ID", "STRING", "INT", "FLOAT", "CARACTER"}


def _nome_amigavel(tipo, valor=None):
    if valor is not None and tipo in TOKENS_COM_VALOR:
        return f"{NOMES_AMIGAVEIS[tipo]} ({valor!r})"
    if tipo in NOMES_AMIGAVEIS:
        return NOMES_AMIGAVEIS[tipo]
    if valor is not None:
        return f"{tipo.lower()} ({valor!r})"
    return tipo.lower()  # pragma: no cover -- todo token sem nome amigável tem valor


class ErroSintatico(Exception):
    def __init__(self, mensagem, linha, coluna=None):
        if coluna is not None:
            super().__init__(f"Erro de sintaxe na linha {linha}, coluna {coluna}: {mensagem}")
        else:
            super().__init__(f"Erro de sintaxe na linha {linha}: {mensagem}")
        self.linha = linha
        self.coluna = coluna


# Este limite não é aplicado automaticamente -- cada ponto de recursão
# DIRETA (uma função que se chama a si própria, não um 'while' que avança
# para o próximo nível de precedência) tem de chamar
# self._entrar_profundidade_expr() manualmente antes de recursar. Confirma
# que TODOS os pontos abaixo continuam a chamar _entrar_profundidade_expr()
# antes de qualquer novo ponto de recursão direta em expressões:
#   _parse_expr (parênteses aninhados), _parse_nao ('nao' encadeado),
#   _parse_unaria ('-' unário encadeado), _parse_potencia (expoente de
#   '^', que é ele próprio right-associative e recursa via
#   _parse_unaria). Os níveis de precedência entre estes (_parse_ou,
#   _parse_e, _parse_relacional, _parse_aditiva, _parse_multiplicativa)
#   NÃO precisam do guard -- avançam para o próximo nível via 'while',
#   não se chamam a si próprios.
LIMITE_PROFUNDIDADE_EXPR = 50
LIMITE_PROFUNDIDADE_BLOCO = 50

# Uma cadeia PLANA de operadores do MESMO nível de precedência (ex.:
# '1+1+1+...', sem parênteses) não cresce a pilha do PARSER (avança num
# 'while', não recursa -- daí não usar LIMITE_PROFUNDIDADE_EXPR acima),
# mas produz uma árvore BinOp encadeada com profundidade igual ao nº de
# operadores. codegen.py envolve CADA BinOp em parênteses Python
# literais, por isso essa profundidade vira profundidade real de
# parênteses aninhados no .py gerado -- e o próprio CPython tem um
# limite de aninhamento (~200).
#
# Guardado como atributo no PRÓPRIO nó (_algo_prof_arv), calculado
# bottom-up (1 + profundidade máxima dos filhos) em CADA sítio que
# constrói um BinOp/UnOp -- ver _criar_binop/_criar_unop/_profundidade_no
# abaixo.
LIMITE_PROFUNDIDADE_ARVORE = 150


def _profundidade_no(no):
    return getattr(no, "_algo_prof_arv", 1)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self._profundidade_expr = 0
        self._profundidade_bloco = 0

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
                atual.linha, atual.coluna,
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
            if corpo is not None:
                if self.ver("INICIO"):
                    raise ErroSintatico(
                        "o programa já tem um bloco 'inicio' -- só pode haver um",
                        self.atual().linha, self.atual().coluna)
                raise ErroSintatico(
                    "o bloco 'inicio' tem de ser a última coisa do programa -- "
                    f"encontrou {_nome_amigavel(self.atual().tipo, self.atual().valor)} "
                    f"depois dele",
                    self.atual().linha, self.atual().coluna)
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
                    f"'funcao', 'procedimento' ou 'inicio', encontrou "
                    f"{_nome_amigavel(self.atual().tipo, self.atual().valor)}",
                    self.atual().linha, self.atual().coluna)

        if corpo is None:
            raise ErroSintatico(
                "o programa tem de ter um bloco 'inicio'", self.atual().linha, self.atual().coluna)

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
            campos.extend(self._parse_declaracao_comum(permitir_ref=True))
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
        self.esperar(
            "COMO",
            msg="'incluir' exige sempre um alias -- usa 'incluir "
                f"{caminho_tok.valor!r} como <nome>'",
        )
        como = self.esperar("ID").valor
        self.esperar("NEWLINE")
        return A.Incluir(caminho_tok.valor, linha, como)

    def _parse_tipo(self):
        """Um 'tipo' é sintaticamente apenas um identificador -- pode ser um
        tipo primitivo (inteiro, decimal, ...) ou o nome de uma 'estrutura'.
        Propositadamente NÃO são palavras reservadas (para não colidirem com
        nomes de bibliotecas como 'cadeia'/'matematica' ou de estruturas do
        utilizador); a validade do tipo é confirmada mais tarde, em
        semantics.py, quando já sabemos que estruturas foram definidas."""
        tok = self.atual()
        if tok.tipo != "ID":
            raise ErroSintatico(
                f"esperava-se um tipo, encontrou {_nome_amigavel(tok.tipo, tok.valor)}",
                tok.linha, tok.coluna)
        self.avancar()
        return tok.valor

    # declaração global (fora de funções/procedimentos, antes de 'inicio')
    def _parse_declaracao_global(self):
        return self._parse_declaracao_comum()

    def _parse_declaracao_comum(self, permitir_ref=False):
        """Assume que o token atual é o primeiro ID de uma lista de nomes,
        seguido de ':' e do tipo. Já confirmado pelo chamador via lookahead.

        'permitir_ref' só é True vindo de _parse_estrutura_def -- um campo
        de 'estrutura' pode ser marcado 'ref' (nome:ref Tipo, aliasing em
        vez de cópia por valor, ver docs/manual/07-Estruturas.md). Fora
        desse contexto (declaração global ou local), 'ref' não é uma
        palavra-chave válida aqui -- só existe hoje como marcador de
        parâmetro (_parse_param) ou, agora, de campo."""
        linha = self.atual().linha
        coluna = self.atual().coluna
        nomes = self._parse_lista_virgulas(lambda: self.esperar("ID").valor, "COLON")
        self.esperar("COLON")
        por_referencia = False
        if self.ver("REF"):
            if not permitir_ref:
                raise ErroSintatico(
                    "'ref' só é permitido num parâmetro de função/procedimento ou "
                    "num campo de 'estrutura'", self.atual().linha, self.atual().coluna)
            self.avancar()
            por_referencia = True
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
                    "não é possível inicializar várias variáveis na mesma linha", linha, coluna)
            # '{...}' é reconhecido por _parse_primario em qualquer posição
            # de expressão (incluindo este valor inicial); se a FORMA não
            # corresponder a 'tipo'/'dims', semantics.py dá o erro claro.
            inicial = self._parse_expr()
        self.esperar("NEWLINE")
        return [A.Declaracao(tipo, nome, dims, linha, inicial, por_referencia=por_referencia)
                for nome in nomes]

    def _parse_literal_chaveta(self):
        """Um literal '{...}' -- vetor ('{v1, v2, ...}', possivelmente
        aninhado para vetores multidimensionais) ou estrutura
        ('{campo: valor, ...}'), disambiguado pela forma do conteúdo
        logo a seguir a '{'. Usado tanto no valor inicial de uma
        declaração como em qualquer posição de expressão (ex.:
        argumento de uma chamada, via _parse_primario) -- a verificação
        de que a FORMA (nº de dimensões do vetor / tipo dos campos)
        corresponde ao que é esperado no contexto é feita inteiramente
        em semantics.py, não aqui; o parser só reconhece a sintaxe,
        sem precisar de saber de antemão quantas dimensões esperar."""
        if self._proximo_parece_campo_literal():
            return self._parse_estrutura_literal()
        return self._parse_vetor_literal_generico()

    def _parse_vetor_literal_generico(self):
        linha = self.atual().linha
        self.esperar("LBRACE")
        elementos = []
        if not self.ver("RBRACE"):
            elementos = self._parse_lista_virgulas(self._parse_expr, "RBRACE")
        self.esperar("RBRACE")
        return A.VetorLiteral(elementos, linha)

    def _proximo_parece_campo_literal(self):
        """Olha para os tokens a seguir a '{' (sem consumir) para decidir se
        parece um literal de estrutura ('{campo: valor, ...}' ou '{}') em
        vez de uma lista de valores de vetor mal colocada."""
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
            campos = self._parse_lista_virgulas(self._parse_campo_literal, "RBRACE")
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
            params = self._parse_lista_virgulas(self._parse_param, "RPAREN")
        self.esperar("RPAREN")
        tipo_retorno = None
        dims_retorno = 0
        if not eh_proc:
            self.esperar("COLON")
            tipo_retorno = self._parse_tipo()
            dims_retorno = self._parse_dims_vazias()
        self.esperar("NEWLINE")
        corpo = self._parse_bloco_stmts()
        return A.FuncaoDef(nome_tok.valor, tipo_retorno, params, corpo, linha, eh_proc,
                            dims_retorno)

    def _parse_param(self):
        por_ref = False
        if self.ver("REF"):
            self.avancar()
            por_ref = True
        nome_tok = self.esperar("ID")
        self.esperar("COLON")
        tipo = self._parse_tipo()
        dims = self._parse_dims_vazias()
        return A.Parametro(nome_tok.valor, tipo, por_ref, dims, nome_tok.linha)

    def _parse_lista_virgulas(self, parse_item, fechar):
        """'item (',' item)*', com deteção dedicada de vírgula a mais antes
        do fecho (ex.: 'f(1, 2,)', '{1, 2,}') -- em vez do erro genérico
        de _parse_primario ('expressão inesperada: RPAREN'), que não
        explica a causa real. Partilhado por todos os sítios do parser que
        constroem uma lista separada por vírgulas com esta mesma forma
        (chamadas, literais de vetor, valores de 'caso'), para não haver a
        mesma verificação reimplementada em cada um deles. Não trata a
        lista vazia -- quem chama decide se '()'/'{}' vazio é aceite antes
        de invocar isto."""
        itens = [parse_item()]
        while self.ver("COMMA"):
            self.avancar()
            if self.ver(fechar):
                raise ErroSintatico(
                    f"vírgula a mais antes de {_nome_amigavel(fechar)}",
                    self.atual().linha, self.atual().coluna)
            itens.append(parse_item())
        return itens

    def _parse_dims_vazias(self):
        """Colchetes vazios '[]' (0, 1 ou mais pares), usados na sintaxe de
        parâmetros e tipos de retorno do tipo vetor: aceita vetor de
        qualquer tamanho, por isso -- ao contrário dos colchetes de uma
        declaração -- não há expressão de tamanho lá dentro."""
        dims = 0
        while self.ver("LBRACKET"):
            self.avancar()
            self.esperar(
                "RBRACKET",
                msg="um parâmetro ou tipo de retorno do tipo vetor usa colchetes "
                    "vazios, ex: 'v:inteiro[]' (sem tamanho -- aceita um vetor de "
                    "qualquer tamanho)")
            dims += 1
        return dims

    def _parse_bloco_inicio(self):
        self.esperar("INICIO")
        self.esperar("NEWLINE")
        return self._parse_bloco_stmts()

    def _parse_bloco_stmts(self):
        # Sem isto, blocos aninhados a mais estouravam a pilha de recursão
        # do próprio Python (RecursionError cru, sem número de linha); só
        # ErroLexico/ErroSintatico/ErroSemantico são apanhados em cli.py.
        self._profundidade_bloco += 1
        if self._profundidade_bloco > LIMITE_PROFUNDIDADE_BLOCO:
            raise ErroSintatico(
                "blocos aninhados a mais ('se'/'para'/'enquanto'/... uns "
                "dentro dos outros) -- tenta simplificar, ex. extraindo "
                "parte da lógica para uma função", self.atual().linha)
        try:
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
        finally:
            self._profundidade_bloco -= 1

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
        if tok.tipo == "RETORNAR":
            return self._parse_retornar()
        if tok.tipo == "SAIR":
            return self._parse_sair()
        if tok.tipo == "CONTINUAR":
            return self._parse_continuar()
        if tok.tipo == "CONSTANTE":
            return self._parse_constante()
        if tok.tipo == "AFIRMAR":
            return self._parse_afirmar()
        if tok.tipo == "ID":
            return self._parse_decl_atrib_ou_chamada()
        raise ErroSintatico(
            f"instrução inesperada: {_nome_amigavel(tok.tipo, tok.valor)}", tok.linha, tok.coluna)

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
        alvos = self._parse_lista_virgulas(self._parse_lvalue, "RPAREN")
        self.esperar("RPAREN")
        self.esperar("NEWLINE")
        return A.Ler(alvos, linha)

    def _parse_escrever(self):
        linha = self.atual().linha
        coluna = self.atual().coluna
        self.esperar("ESCREVER")
        self.esperar("LPAREN")
        if self.ver("RPAREN"):
            raise ErroSintatico("'escrever' precisa de pelo menos 1 argumento", linha, coluna)
        exprs = self._parse_lista_virgulas(self._parse_expr, "RPAREN")
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
            valores = self._parse_lista_virgulas(self._parse_expr, "NEWLINE")
            self.esperar("NEWLINE")
            corpo = self._parse_bloco_stmts()
            casos.append((valores, corpo))
        if self.ver("CONTRARIO"):
            self.avancar()
            self.esperar("NEWLINE")
            contrario = self._parse_bloco_stmts()
        self.esperar("DEDENT")
        return A.Escolha(expr, casos, contrario, linha)

    def _parse_retornar(self):
        linha = self.atual().linha
        self.esperar("RETORNAR")
        expr = None if self.ver("NEWLINE") else self._parse_expr()
        self.esperar("NEWLINE")
        return A.Retornar(expr, linha)

    def _parse_sair(self):
        linha = self.atual().linha
        self.esperar("SAIR")
        self.esperar("NEWLINE")
        return A.Sair(linha)

    def _parse_continuar(self):
        linha = self.atual().linha
        self.esperar("CONTINUAR")
        self.esperar("NEWLINE")
        return A.Continuar(linha)

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
                    args = self._parse_lista_virgulas(self._parse_expr, "RPAREN")
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
                args = self._parse_lista_virgulas(self._parse_expr, "RPAREN")
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
    def _entrar_profundidade_expr(self):
        # Sem isto, uma expressão fortemente aninhada (muitos parênteses,
        # ou cadeias de 'nao'/'-'/'^' encadeados) estourava a pilha de
        # recursão do próprio Python em vez de um erro de sintaxe
        # amigável. Partilhado por todos os pontos de recursão direta em
        # expressões -- não só _parse_expr, mas também _parse_nao/
        # _parse_unaria/_parse_potencia.
        self._profundidade_expr += 1
        if self._profundidade_expr > LIMITE_PROFUNDIDADE_EXPR:
            raise ErroSintatico(
                "expressão demasiado aninhada (parênteses ou operadores a mais) -- "
                "tenta simplificar, ex. dividindo em variáveis intermédias",
                self.atual().linha)

    def _criar_binop(self, op, esq, dire, linha):
        # Ver comentário de LIMITE_PROFUNDIDADE_ARVORE acima.
        # Chamado em TODOS os sítios que constroem um A.BinOp -- inclui os
        # 4 níveis que avançam em 'while' (_parse_ou/_parse_e/
        # _parse_aditiva/_parse_multiplicativa), que não recursam mas
        # ainda assim produzem uma árvore tão profunda quanto o nº de
        # operadores da cadeia, e os níveis que já recursam (relacional,
        # potencia), cuja profundidade de árvore também importa aqui,
        # independentemente de já estarem cobertos por
        # _entrar_profundidade_expr (essa protege a pilha do PARSER; esta
        # protege quem consome a árvore depois: semantics.py, linter.py,
        # e o Python gerado por codegen.py).
        profundidade = 1 + max(_profundidade_no(esq), _profundidade_no(dire))
        if profundidade > LIMITE_PROFUNDIDADE_ARVORE:
            raise ErroSintatico(
                "esta expressão tem operadores a mais -- tenta dividi-la em "
                "variáveis intermédias", linha)
        no = A.BinOp(op, esq, dire, linha)
        no._algo_prof_arv = profundidade
        return no

    def _criar_unop(self, op, operando, linha):
        profundidade = 1 + _profundidade_no(operando)
        if profundidade > LIMITE_PROFUNDIDADE_ARVORE:
            raise ErroSintatico(
                "esta expressão tem operadores a mais -- tenta dividi-la em "
                "variáveis intermédias", linha)
        no = A.UnOp(op, operando, linha)
        no._algo_prof_arv = profundidade
        return no

    def _parse_expr(self):
        self._entrar_profundidade_expr()
        try:
            return self._parse_ou()
        finally:
            self._profundidade_expr -= 1

    def _parse_ou(self):
        esq = self._parse_e()
        while self.ver("OU"):
            linha = self.avancar().linha
            dire = self._parse_e()
            esq = self._criar_binop("ou", esq, dire, linha)
        return esq

    def _parse_e(self):
        esq = self._parse_nao()
        while self.ver("E"):
            linha = self.avancar().linha
            dire = self._parse_nao()
            esq = self._criar_binop("e", esq, dire, linha)
        return esq

    def _parse_nao(self):
        if self.ver("NAO"):
            linha = self.avancar().linha
            self._entrar_profundidade_expr()
            try:
                operando = self._parse_nao()
            finally:
                self._profundidade_expr -= 1
            return self._criar_unop("nao", operando, linha)
        return self._parse_relacional()

    def _parse_relacional(self):
        esq = self._parse_aditiva()
        ops = {"IGUAL": "==", "DIFERENTE": "<>", "MENOR": "<", "MAIOR": ">", "LE": "<=", "GE": ">="}
        if self.atual().tipo in ops:
            op_tok = self.avancar()
            dire = self._parse_aditiva()
            esq = self._criar_binop(ops[op_tok.tipo], esq, dire, op_tok.linha)
            if self.atual().tipo in ops:
                # Deliberadamente proibido (mesma decisão da maioria das
                # linguagens): 'a < b < c' não significa "a < b e b < c",
                # significa "(a < b) < c" (comparar um booleano com 'c'),
                # quase sempre um erro do aluno -- sem esta mensagem
                # dedicada, o erro só aparecia mais tarde, genérico, no
                # sítio que esperava o fecho da expressão.
                raise ErroSintatico(
                    "operadores relacionais não podem ser encadeados (ex.: "
                    "'a < b < c') -- usa 'e' para combinar duas comparações, "
                    "ex.: 'a < b e b < c'", self.atual().linha, self.atual().coluna)
        return esq

    def _parse_aditiva(self):
        esq = self._parse_multiplicativa()
        while self.atual().tipo in ("MAIS", "MENOS"):
            op_tok = self.avancar()
            dire = self._parse_multiplicativa()
            esq = self._criar_binop(op_tok.valor, esq, dire, op_tok.linha)
        return esq

    def _parse_multiplicativa(self):
        esq = self._parse_unaria()
        while self.atual().tipo in ("VEZES", "DIVIDE", "DIV", "MOD"):
            op_tok = self.avancar()
            simbolo = {"VEZES": "*", "DIVIDE": "/", "DIV": "div", "MOD": "mod"}[op_tok.tipo]
            dire = self._parse_unaria()
            esq = self._criar_binop(simbolo, esq, dire, op_tok.linha)
        return esq

    def _parse_unaria(self):
        if self.ver("MENOS"):
            linha = self.avancar().linha
            self._entrar_profundidade_expr()
            try:
                operando = self._parse_unaria()
            finally:
                self._profundidade_expr -= 1
            return self._criar_unop("-", operando, linha)
        return self._parse_potencia()

    def _parse_potencia(self):
        base = self._parse_primario()
        if self.ver("POTENCIA"):
            linha = self.avancar().linha
            self._entrar_profundidade_expr()
            try:
                expoente = self._parse_unaria()
            finally:
                self._profundidade_expr -= 1
            return self._criar_binop("^", base, expoente, linha)
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
        if tok.tipo == "NULO":
            self.avancar()
            return A.Literal(None, "nulo", tok.linha)
        if tok.tipo == "LPAREN":
            self.avancar()
            expr = self._parse_expr()
            self.esperar("RPAREN")
            return expr
        if tok.tipo == "LBRACE":
            # Literal de vetor/estrutura como expressão geral, não só como
            # valor inicial de uma declaração (ex.: argumento de uma
            # chamada com um parâmetro do tipo certo).
            return self._parse_literal_chaveta()
        if tok.tipo == "ID":
            chamada = self._parse_chamada_biblioteca_ou_none()
            if chamada is not None:
                # 'biblioteca.metodo(...)' pode ser seguido de '[indice]'/
                # '.campo' quando o resultado é um vetor/estrutura (ex.:
                # 'cadeia.dividir(...)[0]') -- só faz sentido aqui (dentro
                # de uma expressão), não como instrução solta, por isso
                # não entra em _parse_chamada_biblioteca_ou_none em si
                # (partilhado com _parse_atribuicao_ou_chamada).
                chamada.acessos = self._parse_acessos()
                return chamada
            nome_tok = self.esperar("ID")
            if self.ver("LPAREN"):
                self.avancar()
                args = []
                if not self.ver("RPAREN"):
                    args = self._parse_lista_virgulas(self._parse_expr, "RPAREN")
                self.esperar("RPAREN")
                acessos = self._parse_acessos()
                return A.Chamada(nome_tok.valor, args, nome_tok.linha, acessos)
            acessos = self._parse_acessos()
            return A.LValue(nome_tok.valor, acessos, nome_tok.linha)
        raise ErroSintatico(
            f"expressão inesperada: {_nome_amigavel(tok.tipo, tok.valor)}", tok.linha, tok.coluna)


def parse(codigo: str) -> A.Programa:
    tokens = tokenizar(codigo)
    parser = Parser(tokens)
    return parser.parse_programa()


def parse_biblioteca(codigo: str):
    """Interpreta um ficheiro incluído (via 'incluir') como uma biblioteca:
    apenas declarações globais, 'estrutura', definições de função/
    procedimento e, para suportar 'incluir' transitivo (uma biblioteca
    incluir outra), também 'incluir' -- sem cabeçalho
    'algoritmo' nem bloco 'inicio'. Devolve (declaracoes, funcoes,
    estruturas, inclusoes); quem chama é responsável por resolver as
    inclusões recursivamente (ver cli.py/online/executor.py)."""
    tokens = tokenizar(codigo)
    parser = Parser(tokens)
    declaracoes = []
    funcoes = []
    estruturas = []
    inclusoes = []
    while not parser.ver("EOF"):
        if parser.ver("FUNCAO") or parser.ver("PROCEDIMENTO"):
            funcoes.append(parser._parse_funcao_def())
        elif parser.ver("ESTRUTURA"):
            estruturas.append(parser._parse_estrutura_def())
        elif parser.ver("CONSTANTE"):
            declaracoes.append(parser._parse_constante())
        elif parser.ver("INCLUIR"):
            inclusoes.append(parser._parse_incluir())
        elif parser.ver("ID"):
            declaracoes.extend(parser._parse_declaracao_global())
        else:
            raise ErroSintatico(
                "um ficheiro incluído só pode conter declarações de variáveis, "
                f"'constante', 'estrutura', 'funcao', 'procedimento' ou 'incluir' "
                f"(encontrou {_nome_amigavel(parser.atual().tipo, parser.atual().valor)})",
                parser.atual().linha, parser.atual().coluna)
    return declaracoes, funcoes, estruturas, inclusoes
