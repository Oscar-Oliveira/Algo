# -*- coding: utf-8 -*-
"""ARCH-04: lógica de deteção de colisões de nomes partilhada por
`algo_lang.cli._resolver_lista_de_inclusoes` e
`online.executor._resolver_lista_de_inclusoes` -- cada um resolve
'incluir' de forma ligeiramente diferente à volta disto (a CLI faz
sys.exit(1) num erro; o online nunca pode, porque isso terminaria o
servidor inteiro, não só o pedido de um estudante -- ver o gotcha
documentado em CLAUDE.md), mas a REGRA do que conta como colisão -- um
nome de estrutura/função/variável global que já existe no programa --
é exatamente a mesma nos dois. Esta função só deteta e mescla; cada
chamador decide como reagir a uma colisão (imprimir e sair, ou
levantar o seu próprio tipo de erro)."""
from __future__ import annotations


class ColisaoDeInclusao(Exception):
    """Uma estrutura/função/variável global de um ficheiro incluído
    colide com um nome já existente no programa. 'tipo' é sempre
    'estrutura', 'função' ou 'variável global' -- cada chamador
    formata a sua própria mensagem final a partir destes campos, para
    preservar o texto exato que já mostrava antes desta extração."""
    def __init__(self, tipo: str, nome: str, caminho_origem: str):
        self.tipo = tipo
        self.nome = nome
        self.caminho_origem = caminho_origem
        super().__init__(f"{tipo} '{nome}' (incluído de '{caminho_origem}') colide")


def mesclar_biblioteca_no_programa(programa, caminho_origem: str,
                                    declaracoes, funcoes, estruturas) -> None:
    """Acrescenta as estruturas/funções/declarações de uma biblioteca
    incluída (já parseada por parse_biblioteca) ao 'programa',
    verificando colisões de nome contra o que já lá está -- mesma
    ordem de verificação (estrutura, depois função, depois variável)
    que os dois chamadores já usavam. Levanta ColisaoDeInclusao na
    primeira colisão encontrada; muta 'programa' em cada acrescento
    bem-sucedido, tal como o código original fazia."""
    nomes_estruturas_existentes = {e.nome for e in programa.estruturas}
    for e in estruturas:
        if e.nome in nomes_estruturas_existentes:
            raise ColisaoDeInclusao("estrutura", e.nome, caminho_origem)
        programa.estruturas.append(e)
        nomes_estruturas_existentes.add(e.nome)

    nomes_existentes = {f.nome for f in programa.funcoes}
    for f in funcoes:
        if f.nome in nomes_existentes:
            raise ColisaoDeInclusao("função", f.nome, caminho_origem)
        programa.funcoes.append(f)
        nomes_existentes.add(f.nome)

    nomes_decl_existentes = {d.nome for d in programa.declaracoes}
    for d in declaracoes:
        if d.nome in nomes_decl_existentes:
            raise ColisaoDeInclusao("variável global", d.nome, caminho_origem)
        programa.declaracoes.append(d)
        nomes_decl_existentes.add(d.nome)
