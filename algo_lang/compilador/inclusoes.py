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
    'estrutura', 'função' ou 'variável global' -- a categoria do item
    INCLUÍDO -- cada chamador formata a sua própria mensagem final a
    partir destes campos, para preservar o texto exato que já mostrava
    antes desta extração. 'tipo_existente' (a categoria do nome já
    existente no programa, que pode ser DIFERENTE de 'tipo' -- ex.:
    uma função incluída chamada 'Ponto' colide com uma 'estrutura'
    'Ponto' já definida) tem por omissão o mesmo valor de 'tipo', para
    o caso mais comum (mesma categoria) continuar exatamente como
    antes desta extração."""
    def __init__(self, tipo: str, nome: str, caminho_origem: str, tipo_existente: str = None):
        self.tipo = tipo
        self.nome = nome
        self.caminho_origem = caminho_origem
        self.tipo_existente = tipo_existente if tipo_existente is not None else tipo
        super().__init__(f"{tipo} '{nome}' (incluído de '{caminho_origem}') colide")


def mesclar_biblioteca_no_programa(programa, caminho_origem: str,
                                    declaracoes, funcoes, estruturas) -> None:
    """Acrescenta as estruturas/funções/declarações de uma biblioteca
    incluída (já parseada por parse_biblioteca) ao 'programa',
    verificando colisões de nome contra o que já lá está -- mesma
    ordem de verificação (estrutura, depois função, depois variável)
    que os dois chamadores já usavam, agora também ENTRE categorias
    diferentes (ex.: uma função incluída com o mesmo nome de uma
    estrutura já definida) -- antes só a mesma categoria era
    verificada aqui, e uma colisão cruzada só era apanhada mais tarde,
    de forma genérica, em semantics.py, sem indicar que veio de um
    ficheiro incluído. Levanta ColisaoDeInclusao na primeira colisão
    encontrada; muta 'programa' em cada acrescento bem-sucedido, tal
    como o código original fazia."""
    nomes_por_categoria = {
        "estrutura": {e.nome for e in programa.estruturas},
        "função": {f.nome for f in programa.funcoes},
        "variável global": {d.nome for d in programa.declaracoes},
    }

    def _verificar_colisao(tipo: str, nome: str) -> None:
        for tipo_existente, nomes in nomes_por_categoria.items():
            if nome in nomes:
                raise ColisaoDeInclusao(tipo, nome, caminho_origem, tipo_existente)

    for e in estruturas:
        _verificar_colisao("estrutura", e.nome)
        programa.estruturas.append(e)
        nomes_por_categoria["estrutura"].add(e.nome)

    for f in funcoes:
        _verificar_colisao("função", f.nome)
        programa.funcoes.append(f)
        nomes_por_categoria["função"].add(f.nome)

    for d in declaracoes:
        _verificar_colisao("variável global", d.nome)
        programa.declaracoes.append(d)
        nomes_por_categoria["variável global"].add(d.nome)
