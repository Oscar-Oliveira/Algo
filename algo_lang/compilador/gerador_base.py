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


class GeradorCodigoBase:
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

    # -------- declarações --------
    def _valor_default(self, tipo):
        if tipo in DEFAULT_POR_TIPO:
            return DEFAULT_POR_TIPO[tipo]
        return f"{tipo}()"   # instância por omissão de uma estrutura

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
        expr = self._expr(stmt.expr, tipos)
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
