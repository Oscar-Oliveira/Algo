# -*- coding: utf-8 -*-
"""AL-07: base partilhada entre compilador/codegen.py e
compilador/codegen_minimo.py.

Os dois geradores têm a mesma estrutura de dispatch (mesma sequência
de isinstance por tipo de instrução/expressão), mas o CÓDIGO PYTHON
QUE CADA UM EMITE é deliberadamente diferente na maior parte dos
casos: codegen.py gera código com verificações de tipo/runtime;
codegen_minimo.py gera código direto, sem rede de segurança nenhuma,
por desenho (ver CLAUDE.md). Fundir essa parte exigiria parametrizar
o comportamento de cada emissão -- um redesenho real do gerador de
código, não uma extração mecânica, com risco de introduzir uma
regressão subtil.

Esta base contém só os ~11 métodos que já eram bytes idênticos entre
os dois ficheiros antes desta extração -- percurso de lvalues,
resolução de funções, e as estruturas de controlo (se/para/escolha)
cujo código gerado não depende de nenhuma verificação de segurança
específica de um dos modos. Reduz duplicação real sem tocar em nada
que seja deliberadamente diferente entre os dois."""
from __future__ import annotations

from . import ast_nodes as A

DEFAULT_POR_TIPO = {
    "inteiro": "0",
    "decimal": "0.0",
    "booleano": "False",
    "cadeia": '""',
    "caracter": '""',
}


class ErroInternoCompilador(Exception):
    """ARCH-03: uma falha de invariante do PRÓPRIO gerador de código --
    partilhada por codegen.py e codegen_minimo.py (antes só existia em
    codegen.py; codegen_minimo.py reaproveitava ErroSemantico para o
    mesmo tipo de falha, fazendo um bug do compilador parecer um erro de
    tipos do estudante). Em codegen.py isto nunca deveria de facto
    acontecer, porque verificar() (semantics.py) já validou o programa
    antes de gerar_python() correr -- os sítios que a levantam aí estão
    marcados '# pragma: no cover' por essa razão. Em codegen_minimo.py
    (--minimo salta verificar() de propósito) alguns destes pontos SÃO
    alcançáveis por um programa ALGO sintaticamente válido mas
    semanticamente inválido; nesses, não está marcada 'no cover'.
    Distinto de propósito de ErroSemantico, que É esperado (disparado
    por um erro real no programa do estudante)."""
    def __init__(self, mensagem):
        super().__init__(f"Erro interno do compilador: {mensagem}")


class GeradorCodigoBase:
    def __init__(self, programa: A.Programa):
        self.programa = programa
        self.linhas = []
        self.tabela_tipos_globais = {}   # nome -> tipo (tudo o que é global no programa)
        self.refs_atuais = []            # nomes ref da função a gerar neste momento
        self.tipo_retorno_atual = None   # tipo de retorno da função a gerar neste momento
        self.estruturas = {}
        self.mapa_linhas = {}            # nº de linha do .py gerado -> nº de linha do .algo original
        self._linha_algo_atual = None    # linha ALGO da instrução a ser gerada neste momento

    def emit(self, texto, nivel):
        self.linhas.append("    " * nivel + texto)
        if self._linha_algo_atual is not None:
            self.mapa_linhas[len(self.linhas)] = self._linha_algo_atual

    # -------- declarações --------
    def _valor_default(self, tipo):
        if tipo in DEFAULT_POR_TIPO:
            return DEFAULT_POR_TIPO[tipo]
        return f"{tipo}()"   # instância por omissão de uma estrutura

    def _estruturas_recursivas(self):
        """Nomes de estrutura que são (direta ou mutuamente) recursivas --
        ex.: 'No' com um campo 'seguinte: No' (lista ligada), ou duas
        estruturas com campos cruzados. self._valor_default(tipo) para
        um desses nomes nunca termina (o valor por omissão de um campo
        do próprio tipo seria outra instância, com outro campo do
        próprio tipo, ad infinitum) -- por isso os SEUS campos desse
        tipo têm de ficar 'None' (nulo) em vez de construídos eagerly;
        ver o uso em _gerar_estrutura (codegen.py / codegen_minimo.py).
        Percorre só campos escalares (dims_n == 0); um campo array
        nunca recursa porque começa vazio (o elemento nunca chega a ser
        construído em compilação nem em runtime)."""
        grafo = {
            nome: [tipo for tipo, dims_n in campos.values()
                   if dims_n == 0 and tipo in self.estruturas]
            for nome, campos in self.estruturas.items()
        }
        recursivas = set()
        for origem in grafo:
            pilha = list(grafo[origem])
            vistos = set()
            while pilha:
                atual = pilha.pop()
                if atual == origem:
                    recursivas.add(origem)
                    break
                if atual in vistos:
                    continue
                vistos.add(atual)
                pilha.extend(grafo.get(atual, []))
        return recursivas

    def _coagir_decimal(self, expr_py: str, tipo_alvo, expr_no) -> str:
        """'decimal' aceita um valor 'inteiro' (_compativel em semantics.py),
        mas o Python gerado não convertia sozinho -- 'x: decimal = 5'
        ficava com o inteiro 5, não 5.0. semantics.py anota cada nó de
        expressão com o seu tipo inferido (expr._tipo_inferido, ver
        VerificadorTipos._tipo_expr) durante verificar(), que corre
        sempre antes de gerar_python(); reaproveita-se esse tipo aqui em
        vez de o recalcular. Partilhado, mas inofensivo para
        codegen_minimo.py: --minimo salta verificar() de propósito, por
        isso os nós nunca têm '_tipo_inferido' nesse caminho e isto
        nunca coage nada, consistente com --minimo não ter rede de
        segurança nenhuma."""
        if tipo_alvo == "decimal" and getattr(expr_no, "_tipo_inferido", None) == "inteiro":
            return f"float({expr_py})"
        return expr_py

    # -------- statements --------
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
        tipo_alvo = self._tipo_final_lvalue(stmt.alvo, tipos)
        if isinstance(stmt.expr, A.EstruturaLiteral):
            # AL-90/B17: um literal de estrutura como valor de uma
            # ATRIBUIÇÃO (não só de uma declaração). semantics.py já
            # permite este caso também em modo normal (propaga o tipo já
            # declarado do alvo para o literal), mas codegen.py sobrepõe
            # este método e trata o caso ali com _expr_estrutura_literal
            # (coerção decimal, literais aninhados) antes de chegar aqui --
            # este ramo simplificado só é mesmo alcançado a partir de
            # codegen_minimo.py (--minimo, que salta verificar() de
            # propósito e não tem o mesmo cuidado). Sem este caso especial,
            # _expr() não tem nenhum ramo para EstruturaLiteral e o PRÓPRIO
            # COMPILADOR rebentava ("expressão não suportada"), em vez de
            # gerar Python válido -- aqui é sempre possível, porque
            # 'tipo_alvo' já dá o nome do construtor a usar.
            kwargs = ", ".join(
                f"{nome}={self._expr(valor, tipos)}" for nome, valor in stmt.expr.campos)
            expr = f"{tipo_alvo}({kwargs})"
        else:
            expr = self._coagir_decimal(self._expr(stmt.expr, tipos), tipo_alvo, stmt.expr)
        self.emit(f"{alvo} = {expr}", nivel)

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
        if stmt.passo:
            # AL-XX: 'passo' entra no range() duas vezes (direção e step) --
            # se for avaliado inline nas duas, uma expressão com efeito
            # lateral (chamada de função) corre duas vezes por iteração do
            # range, dando um step efetivo errado. Avalia-se uma única vez
            # para uma variável temporária antes do 'for'.
            self.emit(f"_algo_passo = {self._expr(stmt.passo, tipos)}", nivel)
            passo = "_algo_passo"
        else:
            passo = "1"
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
        # AL-XX: tipo de retorno da função a gerar neste momento -- só
        # codegen.py o consulta (para coagir 'devolver <inteiro>' de uma
        # função 'decimal'); irrelevante para codegen_minimo.py.
        self.tipo_retorno_atual = f.tipo_retorno

        if not f.corpo:  # pragma: no cover -- o parser exige >=1 instrução no corpo
            self.emit("pass", 1)
        for stmt in f.corpo:
            self._gerar_stmt(stmt, 1, tipos_locais)

        if f.eh_procedimento and self.refs_atuais:
            # AL-68/B28: NÃO reatribuir _linha_algo_atual = f.linha aqui --
            # isso mapeava este 'return' sintético para a linha da
            # ASSINATURA do procedimento (mais cedo no ficheiro do que a
            # última instrução real gerada), fazendo o número de linha no
            # trace "saltar para trás" num procedimento só com parâmetros
            # 'ref' (ex.: 3, 4, 5, 2). Mantém o valor já deixado pela
            # última instrução real do corpo, gerada no laço acima.
            self.emit(f"return {', '.join(self.refs_atuais)}", 1)

        self.refs_atuais = []
        self.tipo_retorno_atual = None
        self._linha_algo_atual = None
        self.linhas.append("")
