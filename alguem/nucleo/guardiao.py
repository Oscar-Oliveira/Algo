# -*- coding: utf-8 -*-
"""O Guardião Pedagógico: um segundo passo de verificação, depois do
Alguem responder e antes de a resposta chegar ao estudante. O motivo
de existir, apesar de já haver instruções no system prompt: um prompt
não garante que o modelo respeite sempre as restrições -- o Guardião é
uma rede de segurança independente disso.

Tem duas camadas, por esta ordem:
1. Uma verificação heurística, barata e determinística (deteta blocos
   de código óbvios sem precisar de chamar o LLM outra vez).
2. Se a heurística não encontrar nada, uma classificação pelo próprio
   LLM, nas 5 categorias descritas na investigação (SAFE, HINT,
   PARTIAL_SOLUTION, FULL_SOLUTION, CODE)."""
from __future__ import annotations

import re
from enum import Enum

from ..fornecedores.base import AgenteLLM

# Blocos de código markdown (```...```), ou uma linha que já parece
# claramente ALGO/Python real (não prosa) -- inclui palavras-chave do
# ALGO seguidas de estrutura de código, para apanhar mesmo sem vir
# dentro de ```.
_PADRAO_BLOCO_CODIGO = re.compile(r"```")
_PADRAO_LINHA_CODIGO_ALGO = re.compile(
    r"^\s*(algoritmo\s+\"|funcao\s+\w+\(|procedimento\s+\w+\(|"
    r"para\s+\w+\s+de\s+.+\s+fazer\s*$|enquanto\s+.+\s+fazer\s*$|"
    r"se\s+.+\s+entao\s*$)",
    re.MULTILINE,
)


class Classificacao(Enum):
    SAFE = "SAFE"
    HINT = "HINT"
    PARTIAL_SOLUTION = "PARTIAL_SOLUTION"
    FULL_SOLUTION = "FULL_SOLUTION"
    CODE = "CODE"


# As duas categorias que o Guardião pode rejeitar -- as outras três
# (SAFE/HINT/PARTIAL_SOLUTION) correspondem aos níveis 0-5 da escada,
# já governados por 'nivel_maximo_ajuda' no próprio system prompt.
CLASSIFICACOES_BLOQUEAVEIS = {Classificacao.FULL_SOLUTION, Classificacao.CODE}

# Aproximação do nível da escada (0-7) a partir da categoria do
# guardião -- não é uma classificação dedicada (isso pediria mais uma
# chamada ao LLM por resposta, decisão explícita de não fazer nesta
# fase). É só uma correspondência aproximada, para dar uma métrica de
# "Hint Escalation" sem custo extra -- não distingue, por exemplo,
# entre o nível 1 (pergunta de reflexão) e o nível 2 (pergunta
# orientadora), já que o guardião só tem 5 categorias, não 8.
NIVEL_APROXIMADO_POR_CLASSIFICACAO = {
    Classificacao.SAFE: 1,
    Classificacao.HINT: 3,
    Classificacao.PARTIAL_SOLUTION: 5,
    Classificacao.FULL_SOLUTION: 6,
    Classificacao.CODE: 7,
}


PROMPT_CLASSIFICACAO = """\
Vais avaliar se uma resposta de um tutor de algoritmia revela \
demasiado sobre a solução de um exercício, para um estudante \
iniciante que está a aprender a linguagem ALGO.

Classifica a resposta numa destas categorias EXATAS, e responde \
APENAS com a palavra da categoria, em maiúsculas, sem mais nada à \
volta:

SAFE -- não revela nada da solução: é uma pergunta, uma explicação \
de conceito genérico, ou não relacionado com a solução em si.
HINT -- dá uma pista específica sobre o próximo passo, em linguagem \
natural, sem descrever a solução toda nem usar pseudocódigo.
PARTIAL_SOLUTION -- mostra uma estrutura ou pseudocódigo incompleto \
com lacunas para o estudante preencher, ou descreve mais do que uma \
pista mas ainda não a solução toda.
FULL_SOLUTION -- descreve a solução completa em linguagem natural, \
passo a passo, de forma detalhada e sequencial que o estudante só \
precisa de traduzir diretamente para código, sem mais raciocínio.
CODE -- contém código de qualquer linguagem (ALGO, Python, ou \
pseudocódigo já muito próximo de código), mesmo que incompleto ou \
apresentado como "exemplo".

Resposta a avaliar:
---
{resposta}
---

Categoria (uma palavra só, maiúsculas):"""


class GuardiaoPedagogico:
    def __init__(self, fornecedor: AgenteLLM):
        self.fornecedor = fornecedor

    def classificar(self, resposta: str) -> Classificacao:
        """Classifica uma resposta proposta pelo Alguem. Primeiro tenta
        a heurística (barata, sem chamar o LLM); só chama o LLM se a
        heurística não encontrar nada suspeito."""
        classificacao_heuristica = self._classificar_por_heuristica(resposta)
        if classificacao_heuristica is not None:
            return classificacao_heuristica
        return self._classificar_por_llm(resposta)

    def _classificar_por_heuristica(self, resposta: str) -> Classificacao | None:
        if _PADRAO_BLOCO_CODIGO.search(resposta):
            return Classificacao.CODE
        if _PADRAO_LINHA_CODIGO_ALGO.search(resposta):
            return Classificacao.CODE
        return None

    def _classificar_por_llm(self, resposta: str) -> Classificacao:
        pedido = [{"role": "user", "content": PROMPT_CLASSIFICACAO.format(resposta=resposta)}]
        texto = self.fornecedor.responder(pedido).strip().upper()
        for classificacao in Classificacao:
            if classificacao.value in texto:
                return classificacao
        # resposta do LLM não bateu com nenhuma categoria conhecida --
        # falha para o lado seguro (trata como se tivesse revelado
        # demasiado, em vez de assumir que está tudo bem)
        return Classificacao.FULL_SOLUTION
