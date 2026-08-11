# -*- coding: utf-8 -*-
"""Gerador de fluxogramas em formato DOT (Graphviz) a partir da AST da
linguagem ALGO."""

from ..compilador import ast_nodes as A
# ARCH-02: texto_expr vive em compilador/ast_nodes.py (não aqui), para
# não inverter a camada documentada do pipeline -- tools/ depende do
# compilador, nunca o inverso. Reexportado aqui só para não obrigar a
# mudar todos os chamadores já existentes neste ficheiro.
from ..compilador.ast_nodes import texto_expr


def _escapar(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class GeradorFluxograma:
    def __init__(self, titulo: str, nomes_rotinas=None):
        self.titulo = titulo
        self.nomes_rotinas = nomes_rotinas or set()
        self.contador = 0
        self.declaracoes_nos = []
        self.declaracoes_arestas = []

    def novo_id(self):
        self.contador += 1
        return f"n{self.contador}"

    def no(self, id_, rotulo, forma, extra=""):
        self.declaracoes_nos.append(
            f'    {id_} [label="{_escapar(rotulo)}", shape={forma}{extra}];'
        )

    def aresta(self, origem, destino, rotulo=None):
        if rotulo:
            self.declaracoes_arestas.append(
                f'    {origem} -> {destino} [label="{_escapar(rotulo)}"];'
            )
        else:
            self.declaracoes_arestas.append(f"    {origem} -> {destino};")

    # ---------- geração ----------
    def gerar(self, corpo) -> str:
        inicio = self.novo_id()
        self.no(inicio, "Início", "oval")
        fim = self.novo_id()
        self.no(fim, "Fim", "oval")

        saida = self.gerar_bloco(corpo, inicio)
        self.aresta(saida, fim)

        linhas = ["digraph Fluxograma {", f'    label="{_escapar(self.titulo)}";',
                  "    labelloc=t;", '    node [fontname="Helvetica", fontsize=11];',
                  '    edge [fontname="Helvetica", fontsize=10];', "    rankdir=TB;"]
        linhas.extend(self.declaracoes_nos)
        linhas.extend(self.declaracoes_arestas)
        linhas.append("}")
        return "\n".join(linhas)

    def gerar_bloco(self, stmts, entrada, rotulo_primeira=None):
        """Liga sequencialmente os statements a partir de 'entrada'.
        Devolve o id do último nó gerado (para continuar a ligação)."""
        atual = entrada
        rotulo = rotulo_primeira
        for stmt in stmts:
            atual = self.gerar_stmt(stmt, atual, rotulo)
            rotulo = None
        return atual

    def _eh_chamada_a_rotina(self, chamada):
        return isinstance(chamada, A.Chamada) and "." not in chamada.nome and \
            chamada.nome in self.nomes_rotinas

    def gerar_stmt(self, stmt, anterior, rotulo=None):
        if isinstance(stmt, A.Declaracao):
            if stmt.inicial is not None:
                texto = f"{stmt.nome} = {texto_expr(stmt.inicial)}"
            else:
                texto = f"declarar {stmt.nome}: {stmt.tipo}"
            id_ = self.novo_id()
            if stmt.inicial is not None and self._eh_chamada_a_rotina(stmt.inicial):
                self.no(id_, texto, "box", extra=", peripheries=2")
            else:
                self.no(id_, texto, "box")
            self.aresta(anterior, id_, rotulo)
            return id_

        if isinstance(stmt, A.Atribuicao):
            texto = f"{texto_expr(stmt.alvo)} = {texto_expr(stmt.expr)}"
            id_ = self.novo_id()
            if self._eh_chamada_a_rotina(stmt.expr):
                self.no(id_, texto, "box", extra=", peripheries=2")
            else:
                self.no(id_, texto, "box")
            self.aresta(anterior, id_, rotulo)
            return id_

        if isinstance(stmt, A.Ler):
            nomes = ", ".join(texto_expr(a) for a in stmt.alvos)
            id_ = self.novo_id()
            self.no(id_, f"ler({nomes})", "parallelogram")
            self.aresta(anterior, id_, rotulo)
            return id_

        if isinstance(stmt, A.Escrever):
            textos = ", ".join(texto_expr(e) for e in stmt.exprs)
            id_ = self.novo_id()
            self.no(id_, f"escrever({textos})", "parallelogram")
            self.aresta(anterior, id_, rotulo)
            return id_

        if isinstance(stmt, A.ChamadaStmt):
            id_ = self.novo_id()
            if self._eh_chamada_a_rotina(stmt.chamada):
                self.no(id_, texto_expr(stmt.chamada), "box", extra=", peripheries=2")
            else:
                self.no(id_, texto_expr(stmt.chamada), "box")
            self.aresta(anterior, id_, rotulo)
            return id_

        if isinstance(stmt, A.Devolver):
            id_ = self.novo_id()
            self.no(id_, f"devolver {texto_expr(stmt.expr)}", "box", extra=', peripheries=2')
            self.aresta(anterior, id_, rotulo)
            return id_

        if isinstance(stmt, A.Afirmar):
            id_ = self.novo_id()
            self.no(id_, f"afirmar {texto_expr(stmt.condicao)}", "box", extra=', style=dashed')
            self.aresta(anterior, id_, rotulo)
            return id_

        if isinstance(stmt, A.Se):
            return self._gerar_se(stmt, anterior, rotulo)

        if isinstance(stmt, A.Para):
            return self._gerar_para(stmt, anterior, rotulo)

        if isinstance(stmt, A.Enquanto):
            return self._gerar_enquanto(stmt, anterior, rotulo)

        if isinstance(stmt, A.FazEnquanto):
            return self._gerar_faz_enquanto(stmt, anterior, rotulo)

        if isinstance(stmt, A.Escolha):
            return self._gerar_escolha(stmt, anterior, rotulo)

        id_ = self.novo_id()  # pragma: no cover -- os 12 tipos de instrução da AST estão todos tratados acima
        self.no(id_, "(instrução)", "box")  # pragma: no cover
        self.aresta(anterior, id_, rotulo)  # pragma: no cover
        return id_  # pragma: no cover

    def _gerar_se(self, stmt: A.Se, anterior, rotulo):
        fim_id = self.novo_id()
        self.no(fim_id, "", "point")

        ponto_decisao_anterior = anterior
        rotulo_entrada = rotulo
        for cond, corpo in stmt.ramos:
            d = self.novo_id()
            self.no(d, texto_expr(cond), "diamond")
            self.aresta(ponto_decisao_anterior, d, rotulo_entrada)
            if corpo:
                saida_corpo = self.gerar_bloco(corpo, d, rotulo_primeira="sim")
                self.aresta(saida_corpo, fim_id)
            else:  # pragma: no cover -- o parser exige >=1 instrução em qualquer bloco
                self.aresta(d, fim_id, "sim")
            ponto_decisao_anterior = d
            rotulo_entrada = "não"

        if stmt.senao:
            saida_senao = self.gerar_bloco(stmt.senao, ponto_decisao_anterior,
                                            rotulo_primeira=rotulo_entrada)
            self.aresta(saida_senao, fim_id)
        else:
            self.aresta(ponto_decisao_anterior, fim_id, rotulo_entrada)

        return fim_id

    def _gerar_para(self, stmt: A.Para, anterior, rotulo):
        d = self.novo_id()
        passo_txt = f" passo {texto_expr(stmt.passo)}" if stmt.passo else ""
        self.no(d, f"{stmt.var} de {texto_expr(stmt.ini)} até "
                   f"{texto_expr(stmt.fim)}{passo_txt}", "diamond")
        self.aresta(anterior, d, rotulo)
        if stmt.corpo:
            saida_corpo = self.gerar_bloco(stmt.corpo, d, rotulo_primeira="sim")
            self.aresta(saida_corpo, d)
        else:  # pragma: no cover -- o parser exige >=1 instrução em qualquer bloco
            self.aresta(d, d, "sim")
        fim_id = self.novo_id()
        self.no(fim_id, "", "point")
        self.aresta(d, fim_id, "não")
        return fim_id

    def _gerar_enquanto(self, stmt: A.Enquanto, anterior, rotulo):
        d = self.novo_id()
        self.no(d, texto_expr(stmt.condicao), "diamond")
        self.aresta(anterior, d, rotulo)
        if stmt.corpo:
            saida_corpo = self.gerar_bloco(stmt.corpo, d, rotulo_primeira="sim")
            self.aresta(saida_corpo, d)
        else:  # pragma: no cover -- o parser exige >=1 instrução em qualquer bloco
            self.aresta(d, d, "sim")
        fim_id = self.novo_id()
        self.no(fim_id, "", "point")
        self.aresta(d, fim_id, "não")
        return fim_id

    def _gerar_faz_enquanto(self, stmt: A.FazEnquanto, anterior, rotulo):
        inicio_corpo = self.novo_id()
        self.no(inicio_corpo, "", "point")
        self.aresta(anterior, inicio_corpo, rotulo)
        saida_corpo = self.gerar_bloco(stmt.corpo, inicio_corpo)
        d = self.novo_id()
        self.no(d, texto_expr(stmt.condicao), "diamond")
        self.aresta(saida_corpo, d)
        self.aresta(d, inicio_corpo, "sim")
        fim_id = self.novo_id()
        self.no(fim_id, "", "point")
        self.aresta(d, fim_id, "não")
        return fim_id

    def _gerar_escolha(self, stmt: A.Escolha, anterior, rotulo):
        d = self.novo_id()
        self.no(d, f"escolher {texto_expr(stmt.expr)}", "hexagon")
        self.aresta(anterior, d, rotulo)
        fim_id = self.novo_id()
        self.no(fim_id, "", "point")
        for valores, corpo in stmt.casos:
            rotulo_caso = ", ".join(texto_expr(v) for v in valores)
            if corpo:
                saida = self.gerar_bloco(corpo, d, rotulo_primeira=rotulo_caso)
                self.aresta(saida, fim_id)
            else:  # pragma: no cover -- o parser exige >=1 instrução em qualquer bloco
                self.aresta(d, fim_id, rotulo_caso)
        if stmt.contrario:
            saida = self.gerar_bloco(stmt.contrario, d, rotulo_primeira="contrario")
            self.aresta(saida, fim_id)
        else:
            self.aresta(d, fim_id, "contrario")
        return fim_id


def gerar_dot(corpo, titulo: str, nomes_rotinas=None) -> str:
    return GeradorFluxograma(titulo, nomes_rotinas).gerar(corpo)
