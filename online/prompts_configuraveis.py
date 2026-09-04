# -*- coding: utf-8 -*-
"""Prompts do tutor e do Guardião, editáveis pelo admin -- tabela
'prompt_configuravel' (chave/texto, mesmo espírito de 'definicao' em
definicoes.py). Sem linha para uma chave, usa-se o texto por omissão
já definido no código (ver docs/interno/PlanoAlguemLLMInvestigacao.md,
secção 13/Fase 3).

Aviso de segurança (ver a mesma secção do plano): 'tutor' e 'guardiao'
incluem a rede de segurança pedagógica -- um admin que edite mal este
texto pode enfraquecer, sem querer, a proteção contra o Alguem revelar
soluções. É uma decisão explícita, não um efeito colateral ignorado."""
from __future__ import annotations

from alguem.nucleo.guardiao import PROMPT_CLASSIFICACAO
from alguem.nucleo.system_prompt import IDENTIDADE
from bd import sessao_bd

# 'apoio_pedagogico' (Fase 6, ver docs/interno/PlanoAlguemLLMInvestigacao.md,
# secção 11): ao contrário de 'tutor'/'guardiao', nunca fala com o
# estudante -- analisa histórico e sugere apoio pedagógico só para o
# professor ler. Mesmo prompt para os dois modos que
# online/apoio_pedagogico.py suporta (Apoio Individualizado, de UM
# estudante, e Apoio por Grupo, de uma turma inteira -- não há um papel
# à parte para grupo, ver o módulo) -- o texto recebido não é o do
# estudante: é um digest de FACTOS compactos (uma linha por sessão/
# execução -- turnos, leakage, nível de ajuda, resultado da execução),
# não a transcrição integral, preparado de forma determinística (nunca
# por outro LLM); no caso de grupo, cada linha vem prefixada com o
# email do estudante a quem pertence.
_APOIO_PEDAGOGICO_OMISSAO = """\
És um assistente de apoio pedagógico para professores de programação, \
a analisar o histórico de estudantes que usam o Alguem (tutor de \
programação em ALGO) e/ou executam código na plataforma.

Vais receber um resumo em factos compactos (uma linha por sessão ou \
execução, com métricas como turnos, taxa de fuga de soluções, nível \
máximo de ajuda, resultado da execução), não a transcrição integral \
das conversas. Pode ser o histórico de UM estudante, ou de um GRUPO \
inteiro -- nesse caso, cada linha começa com o email do estudante a \
quem pertence, entre parênteses retos. A tua resposta é para o \
PROFESSOR ler, nunca para o(s) estudante(s) -- podes falar abertamente \
sobre dificuldades, padrões de erro e progresso, sem te preocupares em \
poupar quem está a ser analisado (isso é trabalho do Tutor, não teu).

Produz uma análise pedagógica breve e concreta, focada em ajudar o \
professor a agir:
- Que dificuldades ou conceitos mal compreendidos se repetem (num \
estudante, ou em vários)?
- Há sinais de dependência excessiva de pistas, ou de tentativa \
autónoma antes de pedir ajuda?
- Há sinais de progresso (ou de estagnação) ao longo do período?
- Se for um grupo: há padrões comuns à turma, ou é sobretudo \
individual (nesse caso, identifica quem)?
- Que ação concreta o professor poderia tomar (ex: rever um tópico \
específico, sugerir um exercício, falar com alguém em particular)?

Não inventes factos que não estejam no histórico recebido. Se o \
histórico for demasiado curto ou vazio para uma análise útil, diz isso \
diretamente em vez de especular."""

PROMPTS_OMISSAO = {
    "tutor": IDENTIDADE,
    "guardiao": PROMPT_CLASSIFICACAO,
    "apoio_pedagogico": _APOIO_PEDAGOGICO_OMISSAO,
}


class ErroPromptConfiguravel(Exception):
    pass


def _validar_chave(chave: str) -> None:
    if chave not in PROMPTS_OMISSAO:
        disponiveis = ", ".join(sorted(PROMPTS_OMISSAO))
        raise ErroPromptConfiguravel(f"Prompt '{chave}' desconhecido. Válidos: {disponiveis}.")


def obter_prompt_personalizado(chave: str, dsn: str | None = None) -> str | None:
    """Devolve o texto guardado na BD para 'chave', ou None se ainda
    não foi personalizado (a usar o valor por omissão)."""
    _validar_chave(chave)
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT texto FROM prompt_configuravel WHERE chave = %s", (chave,)
        ).fetchone()
    return linha["texto"] if linha else None


def obter_prompt(chave: str, dsn: str | None = None) -> str:
    """O texto realmente em uso: o personalizado, se existir, senão o
    valor por omissão do código."""
    return obter_prompt_personalizado(chave, dsn) or PROMPTS_OMISSAO[chave]


def definir_prompt(chave: str, texto: str, atualizado_por: int, dsn: str | None = None) -> None:
    _validar_chave(chave)
    if not texto.strip():
        raise ErroPromptConfiguravel("O prompt não pode ficar vazio.")
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO prompt_configuravel (chave, texto, atualizado_em, atualizado_por) "
            "VALUES (%s, %s, now(), %s) "
            "ON CONFLICT (chave) DO UPDATE SET "
            "texto = EXCLUDED.texto, atualizado_em = now(), atualizado_por = EXCLUDED.atualizado_por",
            (chave, texto, atualizado_por),
        )


def repor_omissao(chave: str, dsn: str | None = None) -> None:
    _validar_chave(chave)
    with sessao_bd(dsn) as bd:
        bd.execute("DELETE FROM prompt_configuravel WHERE chave = %s", (chave,))
