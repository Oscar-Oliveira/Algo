# -*- coding: utf-8 -*-
"""Verificador de tipos em tempo de compilação para a linguagem ALGO."""

import keyword

from . import ast_nodes as A
from .. import bibliotecas

NUMERICOS = {"inteiro", "decimal"}
TEXTUAIS = {"cadeia", "caracter"}
PRIMITIVOS = NUMERICOS | TEXTUAIS | {"booleano"}


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
    """Escopo aninhado (bloco, função, ou nível de topo): nomes locais
    próprios, com fallback de LEITURA para o escopo pai (Escopo ou dict).

    'raiz_funcao' marca a fronteira de uma função/procedimento (ou do
    corpo principal): é seguro sombrear para lá dela porque corresponde
    a um 'def' Python à parte, com o seu próprio namespace. Um Escopo
    de bloco comum (corpo de 'se'/'para'/'enquanto'/...) não é fronteira,
    porque em Python if/for/while NÃO criam namespace novo -- por isso
    '_registar_decl' não deixa redeclarar um nome já ativo num bloco
    aninhado dentro da mesma função, só reaproveitar o nome depois de o
    bloco onde foi declarado ter terminado."""

    def __init__(self, pai, raiz_funcao=False):
        self.pai = pai
        self.raiz_funcao = raiz_funcao
        self.locais = {}

    def __contains__(self, nome):
        return nome in self.locais or nome in self.pai

    def __getitem__(self, nome):
        if nome in self.locais:
            return self.locais[nome]
        return self.pai[nome]

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

        # nome_python_gerado (ex.: "matematica_raiz") -> "biblioteca.metodo"
        # (ex.: "matematica.raiz"), só para bibliotecas importadas -- uma
        # função/estrutura/variável do estudante com o MESMO nome que o
        # nome Python interno de uma função de biblioteca sobrepunha-se-lhe
        # silenciosamente no código gerado (a definição do estudante vem
        # depois no ficheiro), sem nenhum erro a avisar.
        self.nomes_internos_bibliotecas = {
            f"{nome_biblioteca}_{metodo}": f"{nome_biblioteca}.{metodo}"
            for nome_biblioteca, info in self.bibliotecas_importadas.items()
            for metodo in info["funcoes"]
        }

        self.funcoes = {}
        for f in programa.funcoes:
            if f.nome in self.funcoes:
                raise ErroSemantico(f"'{f.nome}' já foi definido anteriormente", f.linha)
            if f.nome in PRIMITIVOS:
                raise ErroSemantico(
                    f"'{f.nome}' é o nome de um tipo primitivo; escolhe outro "
                    f"nome para a função/procedimento", f.linha)
            if f.nome.lower() in self.bibliotecas_importadas:
                raise ErroSemantico(
                    f"'{f.nome}' já é o nome de uma biblioteca importada; "
                    f"escolhe outro nome para a função/procedimento", f.linha)
            if f.nome in self.nomes_internos_bibliotecas:
                raise ErroSemantico(
                    f"'{f.nome}' colide com o nome interno gerado para "
                    f"'{self.nomes_internos_bibliotecas[f.nome]}' (biblioteca "
                    f"importada); escolhe outro nome para a função/procedimento",
                    f.linha)
            self.funcoes[f.nome] = f

        # Nomes de topo do corpo principal (variáveis/constantes globais) --
        # calculado aqui porque as estruturas são registadas ANTES de
        # 'self.globais' existir (ver verificar(), mais abaixo), só para
        # dar uma mensagem dedicada em _validar_dims quando um campo de
        # array de 'estrutura' referencia um destes nomes.
        self._nomes_globais_top_level = {d.nome for d in programa.declaracoes}

        self.estruturas = {}   # nome_estrutura -> {campo: (tipo, dims)}
        linhas_dos_campos = {}   # (nome_estrutura, nome_campo) -> linha (só para mensagens de erro)
        for e in programa.estruturas:
            if e.nome in self.estruturas:
                raise ErroSemantico(f"a estrutura '{e.nome}' já foi definida", e.linha)
            if e.nome in self.funcoes:
                raise ErroSemantico(
                    f"'{e.nome}' já é o nome de uma função/procedimento; escolhe "
                    f"outro nome para a estrutura", e.linha)
            if e.nome in PRIMITIVOS:
                raise ErroSemantico(
                    f"'{e.nome}' é o nome de um tipo primitivo; escolhe outro "
                    f"nome para a estrutura", e.linha)
            if e.nome.lower() in self.bibliotecas_importadas:
                raise ErroSemantico(
                    f"'{e.nome}' já é o nome de uma biblioteca importada; "
                    f"escolhe outro nome para a estrutura", e.linha)
            if e.nome in self.nomes_internos_bibliotecas:
                raise ErroSemantico(
                    f"'{e.nome}' colide com o nome interno gerado para "
                    f"'{self.nomes_internos_bibliotecas[e.nome]}' (biblioteca "
                    f"importada); escolhe outro nome para a estrutura", e.linha)
            campos = {}
            for c in e.campos:
                if c.nome in campos:
                    raise ErroSemantico(
                        f"a estrutura '{e.nome}' tem o campo '{c.nome}' duplicado", c.linha)
                if c.inicial is not None:
                    raise ErroSemantico(
                        "os campos de uma estrutura não podem ter valor inicial", c.linha)
                if c.dims:
                    # AL-48/B7: _registar_decl já valida tipo/sinal de cada
                    # dimensão para variáveis normais -- o registo de campos
                    # de 'estrutura' saltava essa validação por completo,
                    # limitando-se a contar len(c.dims). Sem escopo próprio
                    # (um campo de estrutura não vê variáveis nenhumas), só
                    # expressões resolúveis sem nomes (literais/aritmética
                    # entre literais) fazem sentido aqui.
                    self._validar_dims(c.dims, {}, c.linha, contexto_campo=True)
                dims_n = 0 if c.dims is None else len(c.dims)
                campos[c.nome] = (c.tipo, dims_n)
                linhas_dos_campos[(e.nome, c.nome)] = c.linha
            self.estruturas[e.nome] = campos

        # valida os tipos dos campos só depois de todas as estruturas estarem
        # registadas, para permitir referências cruzadas entre estruturas
        # (ex: 'estrutura A' pode ter um campo do tipo 'B', definida a seguir)
        for nome_estrutura, campos in self.estruturas.items():
            for nome_campo, (tipo, _dims) in campos.items():
                if tipo not in PRIMITIVOS and tipo not in self.estruturas:
                    linha = linhas_dos_campos[(nome_estrutura, nome_campo)]
                    raise ErroSemantico(
                        f"o campo '{nome_campo}' da estrutura '{nome_estrutura}' tem tipo "
                        f"desconhecido '{tipo}'", linha)

    def _validar_tipo(self, tipo, linha):
        if tipo in PRIMITIVOS:
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
        self._pre_registar_recursivo(self.programa.corpo, self.globais, set(escopo_topo))

        for f in self.programa.funcoes:
            self._verificar_funcao(f)

        self._verificar_bloco(self.programa.corpo, escopo_topo, ctx_funcao=None)

    def _pre_registar_recursivo(self, stmts, destino, globais_previas):
        for s in stmts:
            if isinstance(s, A.Declaracao):
                dims_n = 0 if s.dims is None else len(s.dims)
                if s.nome in destino:
                    if s.nome in globais_previas:
                        # AL-82/B10: 'destino' já continha este nome ANTES
                        # de começarmos a percorrer o corpo (é uma global a
                        # sério, declarada antes de 'inicio') -- não é um
                        # conflito entre ramos irmãos descobertos agora
                        # durante esta travessia, é uma redeclaração pura e
                        # simples, tal como _registar_decl já deteta
                        # corretamente mais tarde (passo 5) quando o tipo
                        # repetido é IGUAL. Sem esta distinção, um tipo
                        # diferente fazia esta função reportar a mensagem
                        # pensada para ramos irmãos ("tipos diferentes em
                        # ramos diferentes"), em vez de "já foi declarada".
                        raise ErroSemantico(
                            f"a variável '{s.nome}' já foi declarada", s.linha)
                    # AL-54/B13: antes, uma segunda declaração do mesmo
                    # nome (ex.: em ramos 'se'/'senao' mutuamente
                    # exclusivos ao nível de topo) era silenciosamente
                    # ignorada aqui -- 'self.globais' ficava com o tipo da
                    # PRIMEIRA declaração encontrada em DFS, mesmo que o
                    # ramo que executasse de facto em runtime fosse outro,
                    # com um tipo diferente -- uma função que usasse essa
                    # global ficava a assumir um tipo estaticamente
                    # incorreto. Só é erro se o TIPO diferir -- o mesmo
                    # nome com o mesmo tipo em ramos irmãos é legítimo (o
                    # tipo estático fica correto seja qual for o ramo).
                    tipo_existente, dims_existente, _eh_const = destino[s.nome]
                    if (tipo_existente, dims_existente) != (s.tipo, dims_n):
                        raise ErroSemantico(
                            f"a variável '{s.nome}' é declarada com tipos diferentes "
                            f"em ramos diferentes ('{tipo_existente}' e '{s.tipo}') -- "
                            f"para ser visível a funções, o compilador precisa de um "
                            f"único tipo estático para '{s.nome}'", s.linha)
                else:
                    destino[s.nome] = (s.tipo, dims_n, s.eh_constante)
            for bloco in A.subblocos(s):
                self._pre_registar_recursivo(bloco, destino, globais_previas)

    # ---------- funções ----------
    def _verificar_funcao(self, f: A.FuncaoDef):
        escopo = Escopo(self.globais, raiz_funcao=True)
        for p in f.parametros:
            if p.nome in escopo.locais:
                raise ErroSemantico(f"parâmetro '{p.nome}' duplicado", f.linha)
            self._verificar_nome_disponivel(p.nome, f.linha, "o parâmetro")
            self._validar_tipo(p.tipo, f.linha)
            escopo.locais[p.nome] = (p.tipo, p.dims, False)
        if f.tipo_retorno is not None:
            self._validar_tipo(f.tipo_retorno, f.linha)

        self._verificar_bloco(f.corpo, escopo, ctx_funcao=f)

        if not f.eh_procedimento and not self._todos_caminhos_devolvem(f.corpo):
            raise ErroSemantico(
                f"a função '{f.nome}' declara devolver '{f.tipo_retorno}' mas nem "
                f"todos os caminhos terminam com 'devolver' (ex.: falta um 'senao', "
                f"ou um 'escolher' sem 'contrario') -- um caminho que chegue ao fim "
                f"sem devolver nada crasha em runtime", f.linha)

    def _todos_caminhos_devolvem(self, stmts):
        """AL-49/B8: verificação CONSERVADORA de que todos os caminhos de
        execução do bloco terminam num 'devolver' -- ao contrário do
        antigo _contem_devolver (que só verificava "existe algum
        'devolver' em qualquer lugar", mesmo dentro de um único ramo de
        um 'se' sem 'senao'). Percorre as instruções em ordem; basta UMA
        garantir sempre 'devolver' para o bloco inteiro garantir (tudo o
        que vier a seguir é código morto, já assinalado à parte pelo
        linter) -- por isso não olha só para a última instrução. Um 'se'
        conta só se tiver 'senao' e TODOS os ramos garantirem devolver
        (mesma regra para 'escolher'/'contrario'). Um 'faz...enquanto'
        conta se o corpo garantir (executa sempre pelo menos uma vez,
        antes de a condição sequer ser vista); um 'enquanto' só conta com
        condição literalmente 'verdadeiro' (o ALGO não tem instrução para
        sair de um ciclo a meio, por isso um corpo que garanta devolver
        aqui garante-o já na primeira iteração). É deliberadamente
        conservadora: pode recusar um programa correto num caso extremo
        não coberto aqui, mas nunca aceita um que tenha de facto um
        caminho sem 'devolver'."""
        for s in stmts:
            if isinstance(s, A.Devolver):
                return True
            if isinstance(s, A.Se) and s.senao is not None:
                if (all(self._todos_caminhos_devolvem(corpo) for _cond, corpo in s.ramos)
                        and self._todos_caminhos_devolvem(s.senao)):
                    return True
            elif isinstance(s, A.Escolha) and s.contrario is not None:
                if (all(self._todos_caminhos_devolvem(corpo) for _valores, corpo in s.casos)
                        and self._todos_caminhos_devolvem(s.contrario)):
                    return True
            elif isinstance(s, A.FazEnquanto) and self._todos_caminhos_devolvem(s.corpo):
                return True
            elif isinstance(s, A.Enquanto) and self._condicao_literalmente_verdadeira(s.condicao) \
                    and self._todos_caminhos_devolvem(s.corpo):
                return True
        return False

    def _condicao_literalmente_verdadeira(self, expr):
        return isinstance(expr, A.Literal) and expr.tipo == "booleano" and expr.valor is True

    # ---------- declarações ----------
    def _nome_ativo(self, escopo, nome):
        """Verifica se 'nome' já está em uso dentro do mesmo namespace
        Python (a função/procedimento atual, ou o corpo principal),
        incluindo qualquer bloco 'se'/'para'/'enquanto'/... ainda aberto
        à volta do ponto de declaração -- sem subir além dessa fronteira,
        para continuar a permitir que uma função sombreie uma global."""
        nivel = escopo
        while True:
            locais = nivel.locais if isinstance(nivel, Escopo) else nivel
            if nome in locais:
                return True
            if isinstance(nivel, Escopo) and not nivel.raiz_funcao:
                nivel = nivel.pai
                continue
            return False

    def _verificar_nome_disponivel(self, nome, linha, o_que_e):
        """Rejeita 'nome' se colidir com uma função/procedimento, estrutura,
        biblioteca importada, nome interno gerado para uma biblioteca, ou
        tipo primitivo. AL-50/B10: partilhado entre _registar_decl
        (variáveis) e _verificar_funcao (parâmetros) -- antes, só
        variáveis passavam por esta verificação; um parâmetro chamado
        'Ponto' (sombreando uma estrutura) ou 'inteiro' compilava sem
        aviso e podia gerar Python inválido/incorreto silenciosamente."""
        if nome in self.funcoes:
            raise ErroSemantico(
                f"'{nome}' já é o nome de uma função/procedimento; escolhe "
                f"outro nome para {o_que_e}", linha)
        if nome in self.estruturas:
            raise ErroSemantico(
                f"'{nome}' já é o nome de uma estrutura; escolhe outro nome "
                f"para {o_que_e}", linha)
        if nome in self.bibliotecas_importadas:
            raise ErroSemantico(
                f"'{nome}' já é o nome de uma biblioteca importada; escolhe "
                f"outro nome para {o_que_e}", linha)
        if nome in self.nomes_internos_bibliotecas:
            raise ErroSemantico(
                f"'{nome}' colide com o nome interno gerado para "
                f"'{self.nomes_internos_bibliotecas[nome]}' (biblioteca "
                f"importada); escolhe outro nome para {o_que_e}", linha)
        if nome in PRIMITIVOS:
            raise ErroSemantico(
                f"'{nome}' é o nome de um tipo primitivo; escolhe outro nome "
                f"para {o_que_e}", linha)

    def _registar_decl(self, escopo, d: A.Declaracao):
        if self._nome_ativo(escopo, d.nome):
            raise ErroSemantico(f"a variável '{d.nome}' já foi declarada", d.linha)
        self._verificar_nome_disponivel(d.nome, d.linha, "a variável")
        self._validar_tipo(d.tipo, d.linha)
        if d.eh_constante:
            if d.inicial is None:  # pragma: no cover -- o parser já exige '=' em 'constante'
                raise ErroSemantico(
                    f"a constante '{d.nome}' tem de ser inicializada com um valor", d.linha)
            if d.dims is not None:  # pragma: no cover -- 'constante' não tem sintaxe de array no parser
                raise ErroSemantico("uma constante não pode ser um array", d.linha)
        if d.dims:
            self._validar_dims(d.dims, escopo, d.linha)
        if d.inicial is not None:
            if isinstance(d.inicial, A.ArrayLiteral):
                # AL-16: o parser já não sabe se 'd' é um array -- este
                # caso (ex.: "x:inteiro = {1,2,3}") é agora genuinamente
                # possível e tem de ser apanhado aqui.
                if d.dims is None:
                    raise ErroSemantico(
                        f"'{d.nome}' não é um array; não pode ser inicializado com {{...}}",
                        d.linha)
                self._verificar_array_literal(d.inicial, d.tipo, d.dims, escopo)
            elif isinstance(d.inicial, A.EstruturaLiteral):
                if d.dims is not None:
                    if d.inicial.campos:
                        raise ErroSemantico(
                            f"'{d.nome}' é um array; usa '{{valor, valor, ...}}' para o "
                            f"inicializar, não '{{campo: valor}}'", d.linha)
                    # AL-45/B5: '{}' vazio é sintaticamente ambíguo entre
                    # "struct vazia" e "array vazio" -- o parser não sabe
                    # (nem deve saber) as dimensões do alvo neste ponto
                    # (_proximo_parece_campo_literal). Aqui já sabemos que
                    # o alvo é um array, por isso um '{}' vazio é aceite
                    # como um array literal sem elementos (ver codegen.py).
                else:
                    self._verificar_estrutura_literal(d.inicial, d.tipo, escopo)
            elif isinstance(d.inicial, A.Chamada):
                # Ramo unificado para QUALQUER chamada (com ou sem 'ref',
                # incluindo funções de biblioteca) como valor inicial --
                # chama-se _verificar_chamada diretamente em vez de passar
                # por _tipo_expr porque uma chamada com 'ref' não pode ser
                # usada "dentro de uma expressão" (_tipo_expr rejeita-a
                # explicitamente), mas aqui é a própria instrução de
                # declaração, não uma subexpressão.
                tipo_inicial = self._verificar_chamada(d.inicial, escopo)
                if tipo_inicial is None:
                    raise ErroSemantico(
                        f"'{d.inicial.nome}' é um procedimento e não devolve valor", d.linha)
                dims_n = 0 if d.dims is None else len(d.dims)
                dims_inicial = self._dims_retorno_de_chamada(d.inicial)
                if dims_inicial != dims_n:
                    # Mesmo gate "dimensões antes de tipo" usado em
                    # _verificar_chamada/'devolver' -- sem ele um array
                    # podia inicializar em silêncio uma variável escalar
                    # (ou vice-versa), partilhando o mesmo 'tipo' ignorando
                    # dims.
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' "
                        f"({self._descricao_dims(dims_n)}) com "
                        f"{self._descricao_dims(dims_inicial)}", d.linha)
                if dims_n > 0:
                    if tipo_inicial != d.tipo:
                        raise ErroSemantico(
                            f"'{d.nome}' é um array de '{d.tipo}' mas está a ser "
                            f"inicializado com um array de '{tipo_inicial}' -- arrays "
                            f"não são alargados/estreitados automaticamente, o tipo "
                            f"do elemento tem de ser exatamente igual", d.linha)
                elif not self._compativel(d.tipo, tipo_inicial):
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' (tipo '{d.tipo}') com um "
                        f"valor do tipo '{tipo_inicial}'", d.linha)
                # AL-51/B17: ao contrário do caminho normal de _tipo_expr,
                # este ramo nunca marcava _tipo_inferido --
                # codegen.py:_coagir_decimal depende dele para saber se tem
                # de gerar float(...) no valor de retorno; sem isto,
                # 'y:decimal = f(x)' com 'f' a devolver 'inteiro' ficava com
                # o inteiro cru (5 em vez de 5.0).
                d.inicial._tipo_inferido = tipo_inicial
            else:
                tipo_inicial, _ = self._tipo_expr(d.inicial, escopo)
                if not self._compativel(d.tipo, tipo_inicial):
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' (tipo '{d.tipo}') com um "
                        f"valor do tipo '{tipo_inicial}'", d.linha)
        dims_n = 0 if d.dims is None else len(d.dims)
        escopo[d.nome] = (d.tipo, dims_n, d.eh_constante)

    def _validar_dims(self, dims, escopo, linha, contexto_campo=False):
        """Valida cada expressão de dimensão de um array: tem de ser
        inteira e não pode ser um literal negativo. Partilhado entre
        declarações normais (com escopo real) e campos de 'estrutura'
        (AL-48/B7, com escopo vazio -- um campo não vê variáveis).

        'contexto_campo' (só True para o caso de 'estrutura') dá uma
        mensagem dedicada quando o nome referenciado é uma global do
        programa principal -- sem isto, a variável do 'escopo' vazio
        parecia "não declarada" (factualmente errado: está declarada, só
        não é visível aqui, porque as estruturas são registadas ANTES do
        resto do programa, incluindo constantes globais)."""
        for dim_expr in dims:
            if (contexto_campo and isinstance(dim_expr, A.LValue) and not dim_expr.acessos
                    and dim_expr.nome not in escopo and dim_expr.nome in self._nomes_globais_top_level):
                raise ErroSemantico(
                    f"'{dim_expr.nome}' é uma variável/constante do programa principal, "
                    f"mas o tamanho de um array-campo de 'estrutura' não pode "
                    f"referenciá-la -- estruturas são registadas antes do resto do "
                    f"programa, por isso nada aí é visível ainda; usa um valor literal",
                    dim_expr.linha)
            tipo, _ = self._tipo_expr(dim_expr, escopo)
            if tipo != "inteiro":
                raise ErroSemantico(
                    "o tamanho de um array tem de ser uma expressão inteira", linha)
            valor_literal = self._valor_literal_negativo(dim_expr)
            if valor_literal is not None:
                raise ErroSemantico(
                    f"o tamanho de um array não pode ser negativo (é {valor_literal})",
                    dim_expr.linha)

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
            if isinstance(expr, A.EstruturaLiteral):
                # AL-78/B8: um literal '{...}' aninhado dentro doutro literal
                # de estrutura -- o tipo esperado (tipo_campo) já é
                # conhecido pelo contexto (o campo declarado), por isso dá
                # para validar recursivamente em vez de cair em
                # _tipo_expr(), que rejeita SEMPRE um '{...}' sem tipo
                # próprio (certo para outras posições, errado aqui).
                self._verificar_estrutura_literal(expr, tipo_campo, escopo)
                continue
            tipo_valor, _ = self._tipo_expr(expr, escopo)
            if not self._compativel(tipo_campo, tipo_valor):
                raise ErroSemantico(
                    f"o campo '{nome_campo}' de '{tipo_esperado}' espera '{tipo_campo}' "
                    f"mas recebeu '{tipo_valor}'", lit.linha)

    def _tamanho_estatico(self, dim_expr):
        """AL-79/B7: devolve o tamanho declarado de uma dimensão se for um
        literal inteiro estático (o único caso em que dá para validar o
        número de elementos de um literal '{...}' em compilação); None se
        for uma expressão dinâmica (variável, chamada, etc.), caso em que
        não há como validar estaticamente."""
        if isinstance(dim_expr, A.Literal) and dim_expr.tipo == "inteiro":
            return dim_expr.valor
        return None

    def _verificar_array_literal(self, lit: A.ArrayLiteral, tipo_elemento, dims, escopo):
        # AL-16: desde que o parser deixou de saber de antemão quantas
        # dimensões esperar (_parse_literal_chaveta é genérico), estas
        # duas verificações de forma passaram a ser o único sítio que as
        # apanha -- já não são garantidas pelo parser.
        # AL-79/B7: 'dims' (lista de expressões de dimensão, não só a
        # contagem) permite validar o TAMANHO de cada nível quando é um
        # literal estático -- antes só a profundidade de aninhamento era
        # verificada, nunca o número de elementos contra o tamanho
        # declarado (ex.: 'v:inteiro[5] = {1,2,3}' compilava sem erro).
        tam_esperado = self._tamanho_estatico(dims[0])
        if tam_esperado is not None and len(lit.elementos) != tam_esperado:
            raise ErroSemantico(
                f"o array tem tamanho declarado {tam_esperado} mas o literal "
                f"'{{...}}' tem {len(lit.elementos)} elemento(s)", lit.linha)
        for elem in lit.elementos:
            if len(dims) > 1:
                if not isinstance(elem, A.ArrayLiteral):
                    raise ErroSemantico(
                        f"esperava-se uma lista aninhada {{...}} (o array tem "
                        f"{len(dims)} dimensões)", lit.linha)
                self._verificar_array_literal(elem, tipo_elemento, dims[1:], escopo)
            else:
                if isinstance(elem, A.ArrayLiteral):
                    raise ErroSemantico(
                        "demasiados níveis de aninhamento em {...} para as dimensões "
                        "declaradas", lit.linha)
                if isinstance(elem, A.EstruturaLiteral):
                    # AL-78/B8: elemento de array que é ele próprio um
                    # literal de estrutura (ex.: array de estruturas) --
                    # mesma lógica do campo aninhado, acima.
                    self._verificar_estrutura_literal(elem, tipo_elemento, escopo)
                    continue
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

    def _dims_retorno_de_chamada(self, chamada: A.Chamada):
        """Nº de dimensões do array devolvido por 'chamada' (0 para valor
        escalar, procedimento ou chamada de biblioteca -- nenhuma função de
        biblioteca devolve array hoje)."""
        if "." in chamada.nome:
            return 0
        f_def = self.funcoes.get(chamada.nome)
        if f_def is None or f_def.eh_procedimento:
            return 0
        return f_def.dims_retorno

    @staticmethod
    def _descricao_dims(dims):
        return "um valor escalar" if dims == 0 else f"um array de {dims} dimensão(ões)"

    def _verificar_stmt(self, s, escopo, ctx_funcao):
        if isinstance(s, A.Declaracao):
            self._registar_decl(escopo, s)

        elif isinstance(s, A.Atribuicao):
            self._verificar_nao_constante(s.alvo, escopo, "atribuir a")
            tipo_alvo, dims_alvo = self._tipo_lvalue(s.alvo, escopo)
            if dims_alvo > 0:
                # AL-46/B6: só _tipo_expr (lado direito) rejeitava um array
                # não indexado -- o alvo de uma atribuição nunca era
                # verificado, por isso 'v = 5' com 'v:inteiro[3]' compilava
                # e crashava em runtime com um TypeError cru do Python.
                raise ErroSemantico(
                    f"'{s.alvo.nome}' é um array; não pode ser atribuído "
                    f"diretamente (falta indexá-lo, ex: {s.alvo.nome}[i] = ...)",
                    s.linha)
            if isinstance(s.expr, A.Chamada) and self._tem_ref(s.expr):
                tipo_retorno = self._verificar_chamada(s.expr, escopo)
                if tipo_retorno is None:
                    raise ErroSemantico(
                        f"'{s.expr.nome}' é um procedimento e não devolve valor",
                        s.linha)
                # dims_alvo já é garantidamente 0 aqui (o array acima
                # rejeita reatribuição direta a um array inteiro) -- falta
                # só garantir que o LADO DIREITO também não é um array
                # (partilharia o mesmo 'tipo' que um escalar, ignorando
                # dims, se não fosse este gate).
                dims_retorno = self._dims_retorno_de_chamada(s.expr)
                if dims_retorno > 0:
                    raise ErroSemantico(
                        f"'{s.expr.nome}' devolve {self._descricao_dims(dims_retorno)} "
                        f"mas '{s.alvo.nome}' é {self._descricao_dims(dims_alvo)}",
                        s.linha)
                if not self._compativel(tipo_alvo, tipo_retorno):
                    raise ErroSemantico(
                        f"não é possível atribuir um valor do tipo '{tipo_retorno}' à "
                        f"variável '{s.alvo.nome}' (tipo '{tipo_alvo}')", s.linha)
                # AL-51/B17: mesma correção que a declaração, acima.
                s.expr._tipo_inferido = tipo_retorno
            elif isinstance(s.expr, A.EstruturaLiteral):
                # Mesma ideia que a declaração/argumento de chamada: um
                # literal de estrutura não tem tipo próprio, mas o tipo
                # esperado já é conhecido pelo contexto (o tipo já
                # declarado do alvo) -- sem este ramo, 'p = {x: 9}' falhava
                # com "não há informação suficiente" mesmo sabendo-se
                # exatamente que forma esperar.
                self._verificar_estrutura_literal(s.expr, tipo_alvo, escopo)
            else:
                tipo_expr, _ = self._tipo_expr(s.expr, escopo)
                if not self._compativel(tipo_alvo, tipo_expr):
                    raise ErroSemantico(
                        f"não é possível atribuir um valor do tipo '{tipo_expr}' à "
                        f"variável '{s.alvo.nome}' (tipo '{tipo_alvo}')", s.linha)

        elif isinstance(s, A.Ler):
            for alvo in s.alvos:
                self._verificar_nao_constante(alvo, escopo, "ler para")
                tipo_alvo, dims_alvo = self._tipo_lvalue(alvo, escopo)
                if dims_alvo > 0:
                    # AL-46/B6: mesma verificação que a atribuição, acima.
                    raise ErroSemantico(
                        f"'{alvo.nome}' é um array; não pode ser o alvo direto "
                        f"de 'ler' (falta indexá-lo, ex: ler({alvo.nome}[i]))",
                        alvo.linha)
                if tipo_alvo not in PRIMITIVOS:
                    # AL-47/B9: 'ler' só sabe preencher um valor primitivo --
                    # sem isto, 'ler(a)' com 'a' de tipo 'estrutura' compilava
                    # para 'a = _algo_ler_texto()' (o leitor de recurso),
                    # transformando 'a' silenciosamente numa string; o
                    # crash real só aparecia mais tarde, num acesso a campo,
                    # com uma mensagem enganadora (AttributeError traduzido
                    # como "valor nulo").
                    raise ErroSemantico(
                        f"'{alvo.nome}' é do tipo '{tipo_alvo}'; 'ler' só pode "
                        f"preencher um valor de tipo primitivo (inteiro, decimal, "
                        f"booleano, cadeia ou caracter) -- lê os campos "
                        f"individualmente", alvo.linha)

        elif isinstance(s, A.Escrever):
            for e in s.exprs:
                tipo, _ = self._tipo_expr(e, escopo)
                if tipo in self.estruturas:
                    # AL-55/B14: arrays já eram implicitamente rejeitados
                    # (via a verificação dims>0 de _tipo_expr), mas não
                    # havia equivalente para estruturas -- 'escrever(p)'
                    # com 'p:Ponto' imprimia algo como
                    # "<__main__.Ponto object at 0x...>", sem valor
                    # pedagógico e não determinístico na aparência.
                    raise ErroSemantico(
                        f"não é possível escrever um valor do tipo '{tipo}' "
                        f"diretamente -- escreve os campos individualmente, "
                        f"ex: '{A.texto_expr(e)}.campo'", s.linha)

        elif isinstance(s, A.Se):
            for cond, corpo in s.ramos:
                tipo, _ = self._tipo_expr(cond, escopo)
                if tipo != "booleano":
                    raise ErroSemantico(
                        f"a condição de 'se' tem de ser booleana (é '{tipo}')",
                        getattr(cond, "linha", s.linha))
                self._verificar_bloco(corpo, Escopo(escopo), ctx_funcao)
            if s.senao is not None:
                self._verificar_bloco(s.senao, Escopo(escopo), ctx_funcao)

        elif isinstance(s, A.Para):
            escopo_corpo = Escopo(escopo)
            if s.var not in escopo:
                raise ErroSemantico(
                    f"a variável de controlo '{s.var}' do ciclo 'para' não foi "
                    f"declarada -- declara-a antes do ciclo, ex.: '{s.var}:inteiro'",
                    s.linha)
            if escopo[s.var][:2] != ("inteiro", 0):
                raise ErroSemantico(
                    f"a variável de controlo '{s.var}' do ciclo 'para' tem de ser "
                    f"inteiro", s.linha)
            if escopo[s.var][2]:
                raise ErroSemantico(
                    f"'{s.var}' é uma constante; não pode ser usada como variável "
                    f"de controlo de um ciclo 'para'", s.linha)
            for expr, rotulo in ((s.ini, "inicial"), (s.fim, "final")):
                tipo, _ = self._tipo_expr(expr, escopo_corpo)
                if tipo != "inteiro":
                    raise ErroSemantico(
                        f"o valor {rotulo} do ciclo 'para' tem de ser inteiro (é "
                        f"'{tipo}')", s.linha)
            if s.passo is not None:
                tipo, _ = self._tipo_expr(s.passo, escopo_corpo)
                if tipo != "inteiro":
                    raise ErroSemantico("o 'passo' do ciclo 'para' tem de ser inteiro", s.linha)
                if isinstance(s.passo, A.Literal) and s.passo.valor == 0:
                    raise ErroSemantico(
                        "o 'passo' de um ciclo 'para' não pode ser 0 (o ciclo nunca "
                        "avançaria)", s.passo.linha)
            self._verificar_bloco(s.corpo, escopo_corpo, ctx_funcao)

        elif isinstance(s, A.Enquanto):
            tipo, _ = self._tipo_expr(s.condicao, escopo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'enquanto' tem de ser booleana (é '{tipo}')", s.linha)
            self._verificar_bloco(s.corpo, Escopo(escopo), ctx_funcao)

        elif isinstance(s, A.FazEnquanto):
            escopo_corpo = Escopo(escopo)
            self._verificar_bloco(s.corpo, escopo_corpo, ctx_funcao)
            tipo, _ = self._tipo_expr(s.condicao, escopo_corpo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'fazer...enquanto' tem de ser booleana (é "
                    f"'{tipo}')", s.linha)

        elif isinstance(s, A.Escolha):
            tipo_base, _ = self._tipo_expr(s.expr, escopo)
            valores_vistos = set()
            for valores, corpo in s.casos:
                for v in valores:
                    tipo_v, _ = self._tipo_expr(v, escopo)
                    if not self._tipos_comparaveis(tipo_base, tipo_v):
                        raise ErroSemantico(
                            f"o valor de 'caso' é do tipo '{tipo_v}', incompatível com "
                            f"'{tipo_base}' de 'escolher'", getattr(v, "linha", s.linha))
                    if isinstance(v, A.Literal):
                        # AL-56/B15: erro clássico de copy-paste -- um
                        # valor de 'caso' repetido faz o segundo ramo
                        # nunca ser alcançado (o primeiro já capturou esse
                        # valor). O linter já tinha um AVISO equivalente
                        # (não bloqueia a compilação); isto promove o caso
                        # comum (literais) a erro de compilação real.
                        # AL-83/B11: a chave normaliza por FAMÍLIA de tipo,
                        # não pelo tipo exato -- 'caso "a"' e 'caso \'a\''
                        # (cadeia vs caracter) ou 'caso 1' e 'caso 1.0'
                        # (inteiro vs decimal) são o MESMO valor em
                        # runtime (Python: "a" == 'a' e 1 == 1.0), por
                        # isso o segundo ramo é igualmente inalcançável.
                        if v.tipo in NUMERICOS:
                            chave = ("numero", v.valor)
                        elif v.tipo in TEXTUAIS:
                            chave = ("texto", v.valor)
                        else:
                            chave = (v.tipo, v.valor)
                        if chave in valores_vistos:
                            raise ErroSemantico(
                                f"o valor '{A.texto_expr(v)}' já apareceu antes neste "
                                f"'escolher' -- este ramo nunca seria alcançado",
                                v.linha)
                        valores_vistos.add(chave)
                self._verificar_bloco(corpo, Escopo(escopo), ctx_funcao)
            if s.contrario is not None:
                self._verificar_bloco(s.contrario, Escopo(escopo), ctx_funcao)

        elif isinstance(s, A.Devolver):
            if ctx_funcao is None or ctx_funcao.eh_procedimento:
                raise ErroSemantico(
                    "'devolver' só pode ser usado dentro de uma função", s.linha)
            if isinstance(s.expr, A.ArrayLiteral):
                self._verificar_array_literal(
                    s.expr, ctx_funcao.tipo_retorno, [None] * ctx_funcao.dims_retorno, escopo)
                tipo, dims = ctx_funcao.tipo_retorno, ctx_funcao.dims_retorno
            elif isinstance(s.expr, A.EstruturaLiteral):
                # Literal de estrutura devolvido diretamente -- o tipo já é
                # conhecido pelo contexto (o tipo de retorno declarado da
                # função), mesma ideia do ramo de A.ArrayLiteral acima.
                self._verificar_estrutura_literal(s.expr, ctx_funcao.tipo_retorno, escopo)
                tipo, dims = ctx_funcao.tipo_retorno, 0
            else:
                tipo, dims = self._tipo_expr(s.expr, escopo, permitir_array=True)
            if dims != ctx_funcao.dims_retorno:
                # Mesmo gate "dimensões antes de tipo" de _verificar_chamada --
                # sem ele um array podia ser devolvido em silêncio onde se
                # espera um escalar, ou vice-versa.
                raise ErroSemantico(
                    f"a função '{ctx_funcao.nome}' devolve "
                    f"{self._descricao_dims(ctx_funcao.dims_retorno)} mas está a "
                    f"devolver {self._descricao_dims(dims)}", s.linha)
            if ctx_funcao.dims_retorno > 0:
                if tipo != ctx_funcao.tipo_retorno:
                    raise ErroSemantico(
                        f"a função '{ctx_funcao.nome}' devolve um array de "
                        f"'{ctx_funcao.tipo_retorno}' mas está a devolver um array de "
                        f"'{tipo}' -- arrays não são alargados/estreitados "
                        f"automaticamente, o tipo do elemento tem de ser exatamente "
                        f"igual", s.linha)
            elif not self._compativel(ctx_funcao.tipo_retorno, tipo):
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
        # AL-53/B12: constrói o caminho textual real (ex.: "c.valores")
        # à medida que percorremos os acessos -- antes, TODAS as mensagens
        # de erro abaixo usavam sempre lv.nome (a variável base), mesmo
        # quando o problema estava num campo/índice vários níveis
        # adiante, dando mensagens factualmente erradas (ex.: "'c' é um
        # array" quando 'c' é uma estrutura e o array é 'c.valores').
        caminho = lv.nome
        for tag, valor in lv.acessos:
            if tag == "indice":
                if dims <= 0:
                    raise ErroSemantico(
                        f"'{caminho}' não é um array; não pode ser indexado", lv.linha)
                tipo_idx, _ = self._tipo_expr(valor, escopo)
                if tipo_idx != "inteiro":
                    raise ErroSemantico(
                        f"o índice de '{caminho}' tem de ser inteiro (é '{tipo_idx}')",
                        lv.linha)
                dims -= 1
                caminho = f"{caminho}[{A.texto_expr(valor)}]"
            else:  # "campo"
                if dims > 0:
                    raise ErroSemantico(
                        f"'{caminho}' é um array; falta indexá-lo antes de aceder a "
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
                caminho = f"{caminho}.{valor}"
        return tipo, dims

    def _tipo_expr(self, expr, escopo, permitir_array=False):
        """Cada 'return' de sucesso também guarda o tipo em
        expr._tipo_inferido -- codegen.py reaproveita-o para decidir onde
        inserir coerções 'inteiro' -> 'decimal' (ex.: 'x: decimal = 5' ou
        devolver um inteiro de uma função 'decimal'), sem duplicar aqui
        toda a lógica de inferência de tipos.

        'permitir_array' (por omissão False) controla se um array "nu" (não
        indexado) é aceite como valor -- só os dois sítios legítimos disso
        (argumento de chamada, expressão de 'devolver') passam True; todos
        os outros contextos (aritmética, condições, escrever(), etc.)
        continuam a rejeitar um array nu com o erro de sempre."""
        if isinstance(expr, A.Literal):
            expr._tipo_inferido = expr.tipo
            return expr.tipo, 0
        if isinstance(expr, A.LValue):
            tipo, dims = self._tipo_lvalue(expr, escopo)
            if dims > 0 and not permitir_array:
                raise ErroSemantico(
                    f"'{expr.nome}' é um array; falta indexá-lo (ex: {expr.nome}[i])",
                    expr.linha)
            expr._tipo_inferido = tipo
            return tipo, dims
        if isinstance(expr, A.BinOp):
            tipo, dims = self._tipo_binop(expr, escopo)
            expr._tipo_inferido = tipo
            return tipo, dims
        if isinstance(expr, A.UnOp):
            tipo, _ = self._tipo_expr(expr.operando, escopo)
            if expr.op == "nao":
                if tipo != "booleano":
                    raise ErroSemantico(
                        f"'nao' só se aplica a valores booleanos (é '{tipo}')", expr.linha)
                expr._tipo_inferido = "booleano"
                return "booleano", 0
            if expr.op == "-":
                if tipo not in NUMERICOS:
                    raise ErroSemantico(
                        f"'-' unário só se aplica a números (é '{tipo}')", expr.linha)
                expr._tipo_inferido = tipo
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
            dims_retorno = self._dims_retorno_de_chamada(expr)
            if dims_retorno > 0 and not permitir_array:
                raise ErroSemantico(
                    f"'{expr.nome}' devolve um array; falta indexá-lo (ex: "
                    f"{expr.nome}(...)[i])", expr.linha)
            expr._tipo_inferido = tipo_retorno
            return tipo_retorno, dims_retorno
        if isinstance(expr, (A.ArrayLiteral, A.EstruturaLiteral)):
            # AL-16: um literal '{...}' não tem um tipo próprio -- só faz
            # sentido onde o tipo/forma esperado já é conhecido pelo
            # contexto (valor inicial de uma declaração, ou argumento de
            # uma chamada com um parâmetro do tipo certo, tratados antes
            # de chegar aqui). Nas outras posições (ex.: operando de '+',
            # dentro de escrever(...)), não há informação suficiente.
            raise ErroSemantico(
                "um literal '{...}' só pode ser usado para inicializar uma variável "
                "ou como argumento de uma função/procedimento com um parâmetro do "
                "tipo certo -- aqui não há informação suficiente para saber que "
                "forma se espera", expr.linha)
        raise ErroSemantico(  # pragma: no cover -- todos os tipos de expressão da AST são tratados acima
            f"expressão não reconhecida: {type(expr).__name__}", getattr(expr, "linha", 0))

    def _expoente_estaticamente_nao_negativo(self, expr) -> bool:
        """AL-02: só reconhece os casos simples -- um literal numérico
        não-negativo é seguro; o unário '-' aplicado a algo é tratado
        como (potencialmente) negativo; qualquer outra expressão
        (variável, chamada, etc.) tem sinal desconhecido em tempo de
        compilação, por isso não é considerada não-negativa."""
        if isinstance(expr, A.UnOp) and expr.op == "-":
            return False
        if isinstance(expr, A.Literal) and expr.tipo in NUMERICOS:
            return expr.valor >= 0
        return False

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
            if "decimal" in (t_e, t_d):
                return "decimal", 0
            if op == "^" and not self._expoente_estaticamente_nao_negativo(expr.dire):
                # AL-02: '**' do Python devolve float quando a base é int e o
                # expoente é negativo -- se não conseguimos provar em
                # compilação que o expoente nunca é negativo, o resultado
                # tem de ser tipado 'decimal', não 'inteiro'.
                return "decimal", 0
            return "inteiro", 0

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
        # 'nulo' compara-se com qualquer tipo de estrutura (ex.: 'enquanto
        # no <> nulo fazer ...', o idioma de percurso de uma lista ligada).
        if (a == "nulo" and b in self.estruturas) or (b == "nulo" and a in self.estruturas):
            return True
        return a == b

    def _compativel(self, tipo_alvo, tipo_valor):
        if tipo_alvo == tipo_valor:
            return True
        if tipo_alvo == "decimal" and tipo_valor == "inteiro":
            return True
        if tipo_alvo == "cadeia" and tipo_valor == "caracter":
            return True
        # 'nulo' é aceite em qualquer sítio que espere uma estrutura (campo,
        # declaração, parâmetro, retorno) -- é o valor que representa "esta
        # referência ainda não aponta para nenhuma instância".
        if tipo_valor == "nulo" and tipo_alvo in self.estruturas:
            return True
        return False

    # ---------- chamadas ----------
    def _chave_ref_estatica(self, arg: A.LValue):
        """AL-81/B9: devolve uma chave hashable e comparável para detetar
        aliasing de 'ref' se TODOS os acessos de 'arg' forem campos
        (estaticamente conhecidos); None se algum acesso for um ÍNDICE
        (ex.: v[i] vs v[j]), que pode apontar a posições diferentes em
        runtime e por isso não é comparável em compilação."""
        for tag, _valor in arg.acessos:
            if tag == "indice":
                return None
        return (arg.nome, tuple(valor for _tag, valor in arg.acessos))

    def _verificar_chamada(self, chamada: A.Chamada, escopo):
        if "." in chamada.nome:
            biblioteca, metodo = chamada.nome.split(".", 1)
            if biblioteca not in self.bibliotecas_importadas:
                # 'p.campo(args)' (campo de estrutura chamado como se fosse
                # método) é sintaticamente indistinguível de uma chamada de
                # biblioteca -- o parser não tem informação de tipos para
                # saber a diferença. Antes de assumir "biblioteca não
                # importada" (mensagem enganadora quando 'biblioteca' é na
                # verdade uma variável declarada), verifica se é mesmo esse
                # caso e dá uma mensagem que aponta para a causa real.
                if biblioteca in escopo:
                    tipo_var = escopo[biblioteca][0]
                    if tipo_var in self.estruturas and metodo in self.estruturas[tipo_var]:
                        raise ErroSemantico(
                            f"'{metodo}' é um campo da estrutura '{tipo_var}', não uma "
                            f"função -- campos não podem ser chamados como "
                            f"'{biblioteca}.{metodo}(...)', só lidos ou atribuídos "
                            f"(ex.: '{biblioteca}.{metodo}')", chamada.linha)
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
            tipos_args = []
            for arg, categoria in zip(chamada.args, categorias):
                tipo, _ = self._tipo_expr(arg, escopo)
                tipos_args.append(tipo)
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
                if categoria == "caracter" and tipo != "caracter":
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um caracter (é '{tipo}')", chamada.linha)
                if categoria == "primitivo" and tipo not in PRIMITIVOS:
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um valor de tipo primitivo — inteiro, "
                        f"decimal, booleano, cadeia ou caracter (é '{tipo}')", chamada.linha)
            if tipo_retorno == "numeric":
                # AL-19: tipo de retorno "espelha" o do primeiro argumento
                # numérico (ex.: matematica.absoluto(inteiro) devolve inteiro,
                # não sempre decimal).
                tipo_retorno = tipos_args[0]
            return tipo_retorno

        f_def = self.funcoes.get(chamada.nome)
        if f_def is None:
            raise ErroSemantico(
                f"função ou procedimento '{chamada.nome}' não foi definido", chamada.linha)
        if len(chamada.args) != len(f_def.parametros):
            raise ErroSemantico(
                f"'{chamada.nome}' espera {len(f_def.parametros)} argumento(s), "
                f"recebeu {len(chamada.args)}", chamada.linha)
        nomes_ref_simples_usados = set()
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
                # AL-04/AL-81(B9): só apanha os casos estaticamente
                # inequívocos -- a mesma variável simples, ou o mesmo
                # CAMPO de estrutura (nome de campo é sempre uma string
                # conhecida em compilação), passados por referência a dois
                # parâmetros diferentes na mesma chamada. 'v[i]' e 'v[j]'
                # partilham o nome base 'v' mas podem apontar a posições
                # diferentes em runtime, por isso um acesso com ÍNDICE
                # nunca é comparado (ver _chave_ref_estatica).
                chave = self._chave_ref_estatica(arg)
                if chave is not None:
                    if chave in nomes_ref_simples_usados:
                        raise ErroSemantico(
                            f"'{A.texto_expr(arg)}' é passado por referência mais do "
                            f"que uma vez na mesma chamada a '{chamada.nome}'",
                            chamada.linha)
                    nomes_ref_simples_usados.add(chave)
            if isinstance(arg, A.EstruturaLiteral):
                # AL-16: um literal de estrutura não tem tipo próprio --
                # valida-se diretamente contra o tipo do parâmetro (mesma
                # lógica já usada para o valor inicial de uma declaração).
                # Um parâmetro 'por_referencia' já teria sido rejeitado
                # acima (só aceita A.LValue), por isso chegar aqui implica
                # sempre um parâmetro por valor.
                self._verificar_estrutura_literal(arg, p.tipo, escopo)
                tipo, dims = p.tipo, 0
            elif isinstance(arg, A.ArrayLiteral):
                # Mesma ideia para um literal de array ('{...}') passado
                # diretamente como argumento -- valida-se a FORMA contra as
                # dimensões do parâmetro (sem tamanho estático a verificar,
                # já que um parâmetro array aceita qualquer tamanho).
                self._verificar_array_literal(arg, p.tipo, [None] * p.dims, escopo)
                tipo, dims = p.tipo, p.dims
            else:
                tipo, dims = self._tipo_expr(arg, escopo, permitir_array=True)
            if dims != p.dims:
                # Tem de ser verificado ANTES de qualquer compatibilidade de
                # tipo: um array e um escalar podem partilhar o mesmo 'tipo'
                # (ex.: ambos "inteiro") ignorando dims -- sem este gate um
                # array inteiro seria aceite em silêncio onde se espera um
                # valor escalar, ou vice-versa.
                raise ErroSemantico(
                    f"o parâmetro '{p.nome}' de '{chamada.nome}' espera "
                    f"{self._descricao_dims(p.dims)} mas '{A.texto_expr(arg)}' é "
                    f"{self._descricao_dims(dims)}", chamada.linha)
            if p.dims > 0:
                # Parâmetro array: tipo do elemento exato, tanto por valor
                # como por referência -- uma só regra para arrays (ver
                # justificação do caso 'ref' logo abaixo; por valor segue a
                # mesma regra por simplicidade, para não haver coerção
                # elemento-a-elemento de um array inteiro).
                if tipo != p.tipo:
                    raise ErroSemantico(
                        f"o parâmetro '{p.nome}' de '{chamada.nome}' é um array de "
                        f"'{p.tipo}' mas '{A.texto_expr(arg)}' é um array de '{tipo}' "
                        f"-- arrays não são alargados/estreitados automaticamente, "
                        f"o tipo do elemento tem de ser exatamente igual",
                        chamada.linha)
            elif p.por_referencia:
                # AL-84/B12: um parâmetro 'ref' devolve o seu valor final
                # à variável do CHAMADOR (ver codegen.py:_gerar_lista_args/
                # out_vars) -- ao contrário de um parâmetro por valor,
                # aceitar aqui a mesma compatibilidade "larga" usada para
                # valor (decimal aceita inteiro, cadeia aceita caracter)
                # deixava a variável do chamador ficar com um valor de tipo
                # MAIS LARGO do que o seu tipo declarado (ex.: 'x:inteiro'
                # passado a 'ref a:decimal' ficava com 5.5 em vez de 5,
                # corrompendo silenciosamente o tipo de 'x'). 'ref' exige o
                # tipo exatamente igual, não só compatível.
                if tipo != p.tipo:
                    raise ErroSemantico(
                        f"o parâmetro '{p.nome}' de '{chamada.nome}' é por referência "
                        f"e espera exatamente '{p.tipo}', mas '{A.texto_expr(arg)}' é "
                        f"do tipo '{tipo}' -- por referência os tipos têm de ser "
                        f"exatamente iguais (não só compatíveis), porque o valor final "
                        f"é escrito de volta na variável do chamador", chamada.linha)
            elif not self._compativel(p.tipo, tipo):
                raise ErroSemantico(
                    f"o parâmetro '{p.nome}' de '{chamada.nome}' espera "
                    f"'{p.tipo}' mas recebeu '{tipo}'", chamada.linha)
        return None if f_def.eh_procedimento else f_def.tipo_retorno


def verificar(programa: A.Programa):
    verificar_nomes_python(programa)
    VerificadorTipos(programa).verificar()
