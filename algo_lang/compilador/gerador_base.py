# -*- coding: utf-8 -*-
"""Base de codegen.py.

Extraída em tempos para partilhar dispatch (mesma sequência de
isinstance por tipo de instrução/expressão) com um segundo gerador,
compilador/codegen_minimo.py, que dava suporte a um modo `compila
--minimo` sem verificação de tipos (mapeamentos diretos tipo
`afirmar`→`assert`). Esse modo e ficheiro foram removidos (commit
cc78b3d) sem fundir esta base de volta em codegen.py; hoje
`GeradorCodigo` (codegen.py) é a única subclasse de
`GeradorCodigoBase`. Alguns comentários abaixo ainda explicam
decisões em termos do modo `--minimo` que as motivou -- mantidos
porque continuam a documentar a divisão real entre o que corre
sempre (esta base) e o que só corre depois de verificar() ter
validado o programa (codegen.py), mesmo já não havendo um segundo
consumidor concreto dessa distinção."""
from __future__ import annotations

from . import ast_nodes as A

DEFAULT_POR_TIPO = {
    "inteiro": "0",
    "decimal": "0.0",
    "booleano": "False",
    "cadeia": '""',
    # Um espaço, não "" -- 'caracter' é garantidamente 1 símbolo em todo
    # o resto da linguagem (literal '...', ler()); "" quebrava essa
    # invariante para uma declaração sem valor inicial nunca lida.
    "caracter": '" "',
}


class ErroInternoCompilador(Exception):
    """ARCH-03: uma falha de invariante do PRÓPRIO gerador de código
    (distinto de propósito de ErroSemantico, que É esperado, disparado
    por um erro real no programa do estudante). Em codegen.py isto
    nunca deveria de facto acontecer, porque verificar() (semantics.py)
    já validou o programa antes de gerar_python() correr -- os sítios
    que a levantam estão marcados '# pragma: no cover' por essa razão.
    (Histórico: também usada por um extinto codegen_minimo.py, que
    saltava verificar() de propósito e por isso conseguia mesmo
    alcançar alguns destes pontos com um programa ALGO sintaticamente
    válido mas semanticamente inválido.)"""
    def __init__(self, mensagem):
        super().__init__(f"Erro interno do compilador: {mensagem}")


class GeradorCodigoBase:
    def __init__(self, programa: A.Programa):
        self.programa = programa
        self.linhas = []
        self.tabela_tipos_globais = {}   # nome -> tipo (tudo o que é global no programa)
        self.refs_atuais = []            # nomes ref da função a gerar neste momento
        self.tipo_retorno_atual = None   # tipo de retorno da função a gerar neste momento
        self.dims_retorno_atual = 0      # nº de dimensões do vetor devolvido pela função a gerar neste momento
        self.estruturas = {}
        self.mapa_linhas = {}            # nº de linha do .py gerado -> nº de linha do .algo original
        self._linha_algo_atual = None    # linha ALGO da instrução a ser gerada neste momento
        # Contador persistente (não uma variável local): dá a CADA
        # 'fazer...enquanto' a sua própria bandeira '_algo_fazer_primeira_N',
        # que precisa de sobreviver a toda a vida do ciclo, incluindo
        # através de ciclos aninhados.
        self._contador_faz_enquanto = 0
        # Idem para as temporárias de dimensão de _construir_vetor_aninhado
        # (codegen.py) -- nomes ÚNICOS em todo o programa, não reaproveitados
        # por índice (0, 1, ...) dentro de cada chamada: uma única instrução
        # pode invocar _construir_vetor_aninhado mais do que uma vez (ex.:
        # preenchimento de várias linhas em falta num literal de vetor
        # multidimensional parcial, ver _expr_vetor_literal) antes de a
        # instrução final ser emitida -- nomes fixos colidiriam entre essas
        # chamadas irmãs.
        self._contador_dim_vetor = 0

    def emit(self, texto, nivel):
        self.linhas.append("    " * nivel + texto)
        if self._linha_algo_atual is not None:
            self.mapa_linhas[len(self.linhas)] = self._linha_algo_atual

    # -------- declarações --------
    def _valor_default(self, tipo):
        if tipo in DEFAULT_POR_TIPO:
            return DEFAULT_POR_TIPO[tipo]
        return "None"   # 'estrutura' sem literal fica 'nulo' por omissão -- ver ponto 5

    def _coagir_decimal(self, expr_py: str, tipo_alvo, expr_no) -> str:
        """'decimal' aceita um valor 'inteiro' (_compativel em semantics.py),
        mas o Python gerado não convertia sozinho -- 'x: decimal = 5'
        ficava com o inteiro 5, não 5.0. semantics.py anota cada nó de
        expressão com o seu tipo inferido (expr._tipo_inferido, ver
        VerificadorTipos._tipo_expr) durante verificar(), que corre
        sempre antes de gerar_python(); reaproveita-se esse tipo aqui em
        vez de o recalcular."""
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
            # Um literal de estrutura como valor de uma ATRIBUIÇÃO.
            # codegen.py (única subclasse) intercepta e trata este caso
            # com _expr_estrutura_literal antes de chegar aqui (ver
            # GeradorCodigo._gerar_atribuicao), por isso este ramo é
            # inatingível no compilador atual -- era o caminho usado pelo
            # extinto codegen_minimo.py.
            expr = self._expr_estrutura_literal(stmt.expr, tipo_alvo, tipos)
        elif isinstance(stmt.expr, A.VetorLiteral):
            # 'v = {1, 2, 3}' com 'v' já declarado como vetor -- ao
            # contrário de uma declaração, não há aqui o tamanho DECLARADO
            # de 'v' à mão (só o nome do tipo, em 'tipos'), por isso não
            # há tamanho-alvo para preencher em falta (dims_exprs=None,
            # ver _expr_vetor_literal) -- fica só com os elementos dados,
            # como sempre.
            expr = self._expr_vetor_literal(stmt.expr, tipo_alvo, None, tipos)
        else:
            expr = self._coagir_decimal(self._expr(stmt.expr, tipos), tipo_alvo, stmt.expr)
            # O alvo pode ser um vetor inteiro (dims > 0) desde a
            # introdução de atribuição direta entre vetores -- 'tipos' aqui
            # só guarda o NOME do tipo, por isso as dimensões vêm anotadas
            # por semantics.py em 'stmt.alvo._dims_inferido'.
            dims_alvo = getattr(stmt.alvo, "_dims_inferido", 0)
            if dims_alvo == 1:
                # O lado direito (variável ou chamada sem 'ref') só tem o
                # tamanho REAL conhecido em runtime -- tal como em
                # _gerar_declaracao, mas aqui não há 'd.dims[0]' para
                # consultar (o alvo já existia antes desta instrução).
                # 'len(alvo)' ANTES da atribuição é o próprio tamanho
                # declarado do alvo: só chega aqui depois de já ter sido
                # construído com o tamanho certo (declaração, ou uma
                # atribuição anterior que já passou por este mesmo guarda)
                # -- e o Python avalia todo o lado direito antes de
                # reatribuir 'alvo'.
                expr = f"_algo_verificar_tamanho_vetor_resultado({expr}, len({alvo}))"
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
            if primeiro:
                # 'stmt.casos' vazio -- nenhum 'if' foi emitido, por isso
                # não há nada a que um 'else:' se possa juntar. 'contrario'
                # executa sempre neste caso, sem condição nenhuma.
                self._gerar_corpo(stmt.contrario, nivel, tipos)
            else:
                self.emit("else:", nivel)
                self._gerar_corpo(stmt.contrario, nivel + 1, tipos)

    def _encontrar_funcao(self, nome):
        if "." in nome:
            # Só uma chamada 'alias.metodo(...)' (função incluída com
            # alias) corresponde a um FuncaoDef real -- 'biblioteca.metodo'
            # (biblioteca embutida) não tem, o seu código já vem pronto do
            # registo (ver GeradorCodigo.gerar()).
            prefixo, metodo = nome.split(".", 1)
            mapa = self.programa.aliases_inclusao.get(prefixo)
            if mapa is None or metodo not in mapa:
                return None
            nome = mapa[metodo]
        for f in self.programa.funcoes:
            if f.nome == nome:
                return f
        return None  # pragma: no cover -- semantics.py já garante que existe, se não tiver "."

    # -------- lvalue / expressões --------
    def _lvalue(self, lv: A.LValue, tipos):
        # '_algo_indice' rejeita índices negativos em runtime; aplicado
        # aqui para leitura E escrita, porque este é o único sítio que
        # constrói o texto Python de um acesso indexado.
        base = lv.nome
        for tag, valor in lv.acessos:
            if tag == "indice":
                base += f"[_algo_indice({self._expr(valor, tipos)})]"
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
        # AL-XX: tipo de retorno da função a gerar neste momento -- usado
        # por codegen.py para coagir 'retornar <inteiro>' de uma função
        # 'decimal'.
        self.tipo_retorno_atual = f.tipo_retorno
        self.dims_retorno_atual = f.dims_retorno

        if not f.corpo:  # pragma: no cover -- o parser exige >=1 instrução no corpo
            self.emit("pass", 1)
        for stmt in f.corpo:
            self._gerar_stmt(stmt, 1, tipos_locais)

        if f.eh_procedimento and self.refs_atuais:
            # NÃO reatribuir _linha_algo_atual = f.linha aqui -- isso faria
            # o número de linha no trace "saltar para trás" num
            # procedimento só com parâmetros 'ref'. Mantém o valor já
            # deixado pela última instrução real do corpo.
            self.emit(f"return {', '.join(self.refs_atuais)}", 1)

        self.refs_atuais = []
        self.tipo_retorno_atual = None
        self.dims_retorno_atual = 0
        self._linha_algo_atual = None
        self.linhas.append("")
