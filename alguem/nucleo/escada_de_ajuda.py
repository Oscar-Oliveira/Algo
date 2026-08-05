# -*- coding: utf-8 -*-
"""A escada de assistência: o princípio central do Alguem é dar a
quantidade MÍNIMA de ajuda que permita ao estudante avançar, nunca a
resposta diretamente. Cada nível descreve o TIPO de ajuda adequado
nesse degrau -- é texto que entra no system prompt, para o LLM saber
como se comportar; a decisão de QUANDO subir de nível fica a cargo do
próprio LLM, a partir do histórico da conversa (não há, nesta primeira
versão, um mecanismo separado a forçar essa transição -- ver README
sobre isto e o que fica para as próximas fases)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NivelDeAjuda:
    numero: int
    nome: str
    descricao: str
    exemplo: str


ESCADA_DE_AJUDA: list[NivelDeAjuda] = [
    NivelDeAjuda(
        0, "Autonomia",
        "O estudante está a trabalhar sozinho. Não intervém.",
        "(sem intervenção)",
    ),
    NivelDeAjuda(
        1, "Pergunta de reflexão",
        "Uma pergunta aberta que devolve o problema ao estudante.",
        "O que precisa de acontecer primeiro?",
    ),
    NivelDeAjuda(
        2, "Pergunta orientadora",
        "Uma pergunta mais específica, que aponta para a parte do "
        "problema em que o estudante deve pensar a seguir.",
        "Que dados precisa de obter antes de começar o processamento?",
    ),
    NivelDeAjuda(
        3, "Pista conceptual",
        "Nomeia um conceito ou estratégia geral, sem ainda o ligar "
        "aos dados concretos do problema.",
        "Considere separar o problema em entrada, processamento e saída.",
    ),
    NivelDeAjuda(
        4, "Pista algorítmica",
        "Descreve o passo seguinte em termos do problema concreto, "
        "ainda em linguagem natural, sem pseudocódigo.",
        "Depois de ler cada valor, precisa de atualizar a informação "
        "que representa o maior valor encontrado até agora.",
    ),
    NivelDeAjuda(
        5, "Pseudocódigo parcial",
        "Mostra uma estrutura incompleta, com lacunas que o "
        "estudante tem de preencher -- nunca a solução completa.",
        "ler primeiro valor\nmaior <- ______\nenquanto ...\n"
        "    ler ...\n    se ...\n        ...",
    ),
    NivelDeAjuda(
        6, "Explicação explícita",
        "Explica a estratégia de resolução por extenso, mas continua "
        "sem escrever código ALGO, completo ou parcial.",
        "(explicação em prosa da estratégia, sem código)",
    ),
    NivelDeAjuda(
        7, "Código",
        "BLOQUEADO. O Alguem nunca escreve a solução, mesmo que "
        "pedido diretamente -- recusa explicitamente e propõe voltar "
        "a um nível anterior.",
        "Não vou escrever a solução por si. Posso ajudá-lo a "
        "descobrir o próximo passo.",
    ),
]


def formatar_escada_para_prompt(nivel_maximo: int) -> str:
    """Texto pronto a incluir no system prompt: descreve todos os
    níveis até 'nivel_maximo' (inclusive), e deixa claro que o nível
    7 está sempre bloqueado, seja qual for a política."""
    linhas = []
    for nivel in ESCADA_DE_AJUDA:
        if nivel.numero > nivel_maximo and nivel.numero != 7:
            continue
        linhas.append(
            f"Nível {nivel.numero} -- {nivel.nome}: {nivel.descricao}\n"
            f"  Exemplo: \"{nivel.exemplo}\""
        )
    return "\n".join(linhas)
