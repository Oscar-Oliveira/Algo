# -*- coding: utf-8 -*-
"""Apoio Pedagógico -- terceiro papel de LLM (ver
docs/interno/PlanoAlguemLLMInvestigacao.md, secção 11/Fase 6): sempre
da plataforma (nunca do estudante), analisa o histórico de UM
estudante (sessões do Alguem e/ou execuções de código) sob pedido do
admin e devolve uma sugestão de apoio pedagógico -- nunca gravada como
sessão, nunca visível ao estudante.

Fluxo em DOIS pedidos, com revisão humana obrigatória entre eles (nunca
um só pedido que já entrega a análise final):

1. preparar_resumo(...)  -- monta o histórico como FACTOS compactos
   (não a transcrição/resultado integral, ver _formatar_sessao_alguem/
   _formatar_execucao_codigo) e, se ainda assim não couber num limite
   de tamanho, encolhe-o de forma DETERMINÍSTICA (_truncar_por_tamanho)
   -- nenhum LLM é chamado neste passo, nem é preciso ter algum
   configurado. Devolve o texto para o admin ler e, se quiser, editar.
2. gerar_analise(...)    -- só depois do admin confirmar (com o texto
   tal como ficou), envia-o ao LLM configurado, junto do prompt
   'apoio_pedagogico', e devolve a análise. Este é o único passo que
   fala com um LLM.
"""
from __future__ import annotations

from alguem.fornecedores import criar_fornecedor, ErroFornecedorLLM
from alguem.nucleo import registador
from alguem.scripts import metricas

import configuracao_llm
import historico_codigo
import investigacao
import prompts_configuraveis

TIPOS_VALIDOS = frozenset({"alguem", "codigo"})

# Ponto a partir do qual _truncar_por_tamanho começa a cortar o meio do
# histórico -- não é o limite real de nenhum modelo (isso varia por
# fornecedor), só uma margem confortável para caber com folga no
# pedido de análise final, com espaço de sobra para o prompt e a
# resposta. Ao contrário de uma versão anterior deste módulo, nada
# aqui chama um LLM para encolher o texto -- ver módulo.
LIMITE_CARATERES_HISTORICO = 12000


class ErroApoioPedagogico(Exception):
    pass


class ErroApoioPedagogicoIndisponivel(ErroApoioPedagogico):
    """Sem configuração global para este papel (ver
    configuracao_llm.resolver_apoio_pedagogico), ou o fornecedor
    configurado falhou ao responder. Só pode acontecer em
    gerar_analise -- preparar_resumo nunca fala com nenhum LLM."""
    pass


def _fornecedor_apoio_pedagogico():
    credencial = configuracao_llm.resolver_apoio_pedagogico()
    if credencial is None:
        raise ErroApoioPedagogicoIndisponivel(
            "Ainda não há nenhum LLM configurado para Apoio Pedagógico -- "
            "define um na aba \"LLM\"."
        )
    extras = {"host": credencial.host} if credencial.host else {}
    try:
        return criar_fornecedor(credencial.fornecedor, credencial.modelo, credencial.api_key, **extras)
    except ErroFornecedorLLM as e:
        raise ErroApoioPedagogicoIndisponivel(str(e)) from e


def _validar_tipos(tipos: set[str]) -> None:
    if not tipos or not tipos <= TIPOS_VALIDOS:
        raise ErroApoioPedagogico("Indica pelo menos um tipo de histórico válido: 'alguem', 'codigo'.")


def _formatar_sessao_alguem(m: dict) -> str:
    """Um FACTO compacto por sessão (uma linha), não a transcrição
    integral -- 'm' são as métricas já calculadas por
    metricas.calcular_metricas_da_sessao (as mesmas que
    investigacao.py usa no relatório), reaproveitadas em vez de
    recalculadas. O objetivo é um digest pequeno o suficiente para
    normalmente nem precisar de _truncar_por_tamanho, não uma leitura
    narrativa da conversa."""
    leakage = f"{m['solution_leakage_rate']:.0%}" if m["solution_leakage_rate"] is not None else "-"
    nivel = m["hint_escalation_maxima"] if m["hint_escalation_maxima"] is not None else "-"
    return (
        f"Sessão do Alguem em {m['timestamp_inicio'] or '?'} ({m['fornecedor'] or '?'}/{m['modelo'] or '?'}): "
        f"{m['num_turnos']} turno(s), leakage {leakage}, nível máx. de ajuda {nivel}, "
        f"{m['num_recusas_seguras']} recusa(s) segura(s)."
    )


def _formatar_execucao_codigo(execucao: dict) -> str:
    return (
        f"{execucao['criado_em'].isoformat()} -- {execucao['tipo'].capitalize()} de "
        f"'{execucao['nome_ficheiro_principal']}': {execucao.get('resultado', '')}"
    )


def montar_blocos_historico(estudante_id: int, email: str, *, tipos: set[str],
                             data_inicio: str | None = None, data_fim: str | None = None,
                             pasta_logs: str | None = None, dsn: str | None = None) -> list[dict]:
    """Um bloco {"timestamp", "texto", "tipo"} por sessão do Alguem e/ou
    execução de código desta conta -- um facto compacto cada, não a
    transcrição/resultado integral (ver _formatar_*) -- filtrado por
    tipo e período, ordenado do mais antigo para o mais recente (é
    assim que faz sentido ler uma evolução ao longo do tempo, ao
    contrário da vista por estudante em investigacao.py, que mostra do
    mais recente)."""
    _validar_tipos(tipos)
    blocos: list[dict] = []

    if "alguem" in tipos:
        pasta_logs = pasta_logs or registador.PASTA_LOGS_POR_OMISSAO
        eventos_por_sessao = metricas.carregar_eventos_por_sessao(pasta_logs)
        for eventos in eventos_por_sessao.values():
            if not eventos:
                continue
            m = metricas.calcular_metricas_da_sessao(eventos)
            if m["id_estudante"] != email:
                continue
            timestamp = m["timestamp_inicio"]
            if data_inicio and (not timestamp or timestamp < data_inicio):
                continue
            if data_fim and (not timestamp or timestamp > data_fim):
                continue
            blocos.append({"timestamp": timestamp or "", "texto": _formatar_sessao_alguem(m), "tipo": "alguem"})

    if "codigo" in tipos:
        execucoes = historico_codigo.listar_por_estudante(
            estudante_id, dsn, data_inicio=data_inicio, data_fim=data_fim)
        for execucao in execucoes:
            blocos.append({
                "timestamp": execucao["criado_em"].isoformat(),
                "texto": _formatar_execucao_codigo(execucao),
                "tipo": "codigo",
            })

    blocos.sort(key=lambda b: b["timestamp"])
    return blocos


def contar_historico(admin_id: int, admin_global: bool, estudante_id: int, *, tipos: set[str],
                      data_inicio: str | None = None, data_fim: str | None = None,
                      pasta_logs: str | None = None, dsn: str | None = None) -> dict:
    """Pré-visualização SEM chamar nenhum LLM (nem sequer exige um
    configurado) -- só conta quanto histórico existe para os filtros
    escolhidos, para o admin ver a quantidade de trabalho ANTES de
    pedir o resumo. Mesmo controlo de acesso que preparar_resumo/
    gerar_analise (secção 15)."""
    email = investigacao.verificar_acesso_estudante(admin_id, admin_global, estudante_id, dsn)
    blocos = montar_blocos_historico(
        estudante_id, email, tipos=tipos, data_inicio=data_inicio, data_fim=data_fim,
        pasta_logs=pasta_logs, dsn=dsn)
    return {
        "total": len(blocos),
        "alguem": sum(1 for b in blocos if b["tipo"] == "alguem"),
        "codigo": sum(1 for b in blocos if b["tipo"] == "codigo"),
    }


def _cabe(blocos: list[str], limite: int) -> bool:
    return len("\n".join(blocos)) <= limite


def _truncar_por_tamanho(blocos: list[str], limite: int) -> str:
    """Determinístico, sem LLM nenhum: se tudo couber, devolve tal
    qual. Senão, mantém o mais antigo e o mais recente (metade do
    orçamento de carateres cada), para preservar sinal de progressão ao
    longo do tempo em vez de só recência -- e assinala quantos itens do
    meio ficaram de fora. Um bloco nunca é cortado a meio."""
    if not blocos:
        return ""
    if _cabe(blocos, limite):
        return "\n".join(blocos)

    orcamento_cada = limite // 2
    fim_inicio = 0
    while fim_inicio < len(blocos) and _cabe(blocos[:fim_inicio + 1], orcamento_cada):
        fim_inicio += 1
    inicio_fim = len(blocos)
    while inicio_fim > fim_inicio and _cabe(blocos[inicio_fim - 1:], orcamento_cada):
        inicio_fim -= 1

    omitidos = inicio_fim - fim_inicio
    partes = blocos[:fim_inicio]
    if omitidos > 0:
        partes = partes + [f"[... {omitidos} item(ns) de histórico omitido(s) por limite de tamanho ...]"]
    partes = partes + blocos[inicio_fim:]
    return "\n".join(partes)


def preparar_resumo(admin_id: int, admin_global: bool, estudante_id: int, *, tipos: set[str],
                     data_inicio: str | None = None, data_fim: str | None = None,
                     pasta_logs: str | None = None, dsn: str | None = None) -> str:
    """Primeiro passo do fluxo (ver módulo) -- puramente determinístico,
    nunca fala com nenhum LLM (não precisa de nenhum configurado)."""
    email = investigacao.verificar_acesso_estudante(admin_id, admin_global, estudante_id, dsn)
    blocos = montar_blocos_historico(
        estudante_id, email, tipos=tipos, data_inicio=data_inicio, data_fim=data_fim,
        pasta_logs=pasta_logs, dsn=dsn)
    if not blocos:
        return "(Sem histórico para este estudante no período/âmbito escolhido.)"
    return _truncar_por_tamanho([b["texto"] for b in blocos], LIMITE_CARATERES_HISTORICO)


def gerar_analise(admin_id: int, admin_global: bool, estudante_id: int, resumo: str,
                   dsn: str | None = None) -> str:
    """Segundo passo (ver módulo) -- 'resumo' é o texto que o admin
    confirmou (o que preparar_resumo devolveu, editado ou não). Único
    passo do fluxo que fala com um LLM."""
    investigacao.verificar_acesso_estudante(admin_id, admin_global, estudante_id, dsn)
    if not resumo or not resumo.strip():
        raise ErroApoioPedagogico("O resumo está vazio -- gera ou escreve algo antes de pedir a análise.")
    fornecedor = _fornecedor_apoio_pedagogico()
    prompt = prompts_configuraveis.obter_prompt("apoio_pedagogico", dsn)
    mensagens = [{"role": "system", "content": prompt}, {"role": "user", "content": resumo}]
    try:
        return fornecedor.responder(mensagens)
    except ErroFornecedorLLM as e:
        raise ErroApoioPedagogicoIndisponivel(f"Falha ao gerar a análise: {e}") from e
