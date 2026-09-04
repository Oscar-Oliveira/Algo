# -*- coding: utf-8 -*-
"""Apoio Pedagógico -- terceiro papel de LLM (ver
docs/interno/PlanoAlguemLLMInvestigacao.md, secção 11/Fase 6): sempre
da plataforma (nunca do estudante), analisa o histórico de UM
estudante (sessões do Alguem e/ou execuções de código) sob pedido do
admin e devolve uma sugestão de apoio pedagógico -- nunca gravada como
sessão, nunca visível ao estudante.

Fluxo em DOIS pedidos, com revisão humana obrigatória entre eles (nunca
um só pedido que já entrega a análise final):

1. preparar_resumo(...)  -- monta o histórico filtrado (tipos/período),
   resume-o se for grande (mecanismo automático por tamanho -- nunca
   uma escolha do admin, ver _resumir_por_tamanho), devolve o texto
   para o admin ler e, se quiser, editar.
2. gerar_analise(...)    -- só depois do admin confirmar (com o texto
   tal como ficou), envia-o ao LLM configurado, junto do prompt
   'apoio_pedagogico', e devolve a análise.
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

# Ponto a partir do qual preferimos encolher o texto (resumindo) em vez
# de arriscar um pedido demasiado grande -- não é o limite real de
# nenhum modelo (isso varia por fornecedor), só uma margem confortável
# para caber com folga em qualquer um dos suportados, com espaço de
# sobra para o prompt e a resposta.
LIMITE_CARATERES_RESUMO = 12000
# Segurança contra um ciclo teórico (resumos que nunca encolhem o
# suficiente) -- histórico de um estudante não deve precisar de mais
# que 2-3 rondas na prática.
MAX_RONDAS_RESUMO = 4


class ErroApoioPedagogico(Exception):
    pass


class ErroApoioPedagogicoIndisponivel(ErroApoioPedagogico):
    """Sem configuração global para este papel (ver
    configuracao_llm.resolver_apoio_pedagogico), ou o fornecedor
    configurado falhou ao responder."""
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


def _formatar_sessao_alguem(eventos: list[dict]) -> str:
    """Transcrição legível de uma sessão -- pergunta do estudante +
    resposta final ENTREGUE, por turno (não as tentativas rejeitadas
    pelo Guardião, que são rascunhos internos que o estudante nunca
    viu). Usa os eventos em bruto (não as métricas agregadas de
    investigacao.py) porque o apoio pedagógico precisa do conteúdo real
    das trocas, não só de números."""
    inicio = next((e for e in eventos if e.get("tipo") == "inicio_sessao"), None)
    mensagens_por_turno = {
        e["turno"]: e.get("mensagem_estudante", "")
        for e in eventos if e.get("tipo") == "tentativa_guardiao" and "turno" in e
    }
    respostas = sorted(
        (e for e in eventos if e.get("tipo") == "resposta_final"),
        key=lambda e: e.get("turno", 0))

    linhas = [
        f"--- Sessão do Alguem em {inicio.get('timestamp') if inicio else '?'} "
        f"({inicio.get('fornecedor') if inicio else '?'}/{inicio.get('modelo') if inicio else '?'}) ---"
    ]
    for r in respostas:
        pergunta = mensagens_por_turno.get(r.get("turno"))
        if pergunta:
            linhas.append(f"Estudante: {pergunta}")
        linhas.append(f"Alguem: {r.get('resposta', '')}")
    if not respostas:
        linhas.append("(sessão sem respostas registadas)")
    return "\n".join(linhas)


def _formatar_execucao_codigo(execucao: dict) -> str:
    return (
        f"--- {execucao['tipo'].capitalize()} de '{execucao['nome_ficheiro_principal']}' "
        f"em {execucao['criado_em'].isoformat()} ---\nResultado: {execucao.get('resultado', '')}"
    )


def montar_blocos_historico(estudante_id: int, email: str, *, tipos: set[str],
                             data_inicio: str | None = None, data_fim: str | None = None,
                             pasta_logs: str | None = None, dsn: str | None = None) -> list[dict]:
    """Um bloco {"timestamp", "texto"} por sessão do Alguem e/ou
    execução de código desta conta, filtrado por tipo e período,
    ordenado do mais antigo para o mais recente -- é assim que faz
    sentido ler uma evolução ao longo do tempo (ao contrário da vista
    por estudante em investigacao.py, que mostra do mais recente)."""
    _validar_tipos(tipos)
    blocos: list[dict] = []

    if "alguem" in tipos:
        pasta_logs = pasta_logs or registador.PASTA_LOGS_POR_OMISSAO
        eventos_por_sessao = metricas.carregar_eventos_por_sessao(pasta_logs)
        for eventos in eventos_por_sessao.values():
            if not eventos or eventos[0].get("id_estudante") != email:
                continue
            inicio = next((e for e in eventos if e.get("tipo") == "inicio_sessao"), None)
            timestamp = inicio.get("timestamp") if inicio else None
            if data_inicio and (not timestamp or timestamp < data_inicio):
                continue
            if data_fim and (not timestamp or timestamp > data_fim):
                continue
            blocos.append({"timestamp": timestamp or "", "texto": _formatar_sessao_alguem(eventos)})

    if "codigo" in tipos:
        execucoes = historico_codigo.listar_por_estudante(
            estudante_id, dsn, data_inicio=data_inicio, data_fim=data_fim)
        for execucao in execucoes:
            blocos.append({
                "timestamp": execucao["criado_em"].isoformat(),
                "texto": _formatar_execucao_codigo(execucao),
            })

    blocos.sort(key=lambda b: b["timestamp"])
    return blocos


def _pedir_resumo(fornecedor, texto: str) -> str:
    mensagens = [
        {"role": "system", "content": (
            "Resume o histórico de um estudante de programação abaixo, preservando "
            "os factos concretos (que dificuldades teve, que erros repetiu, que "
            "progresso mostrou) -- este resumo vai servir de base a uma análise "
            "pedagógica depois, por isso não percas detalhe relevante, só linguagem "
            "supérflua.")},
        {"role": "user", "content": texto},
    ]
    try:
        return fornecedor.responder(mensagens)
    except ErroFornecedorLLM as e:
        raise ErroApoioPedagogicoIndisponivel(f"Falha ao gerar o resumo: {e}") from e


def _resumir_por_tamanho(fornecedor, blocos: list[str], limite: int) -> str:
    """Mecanismo automático, nunca uma escolha do admin (ver secção 11
    do plano): se tudo couber num único pedido, uma só chamada resume o
    texto completo; senão, agrupa os blocos em fatias que cabem no
    limite, resume cada fatia à parte, e repete o processo sobre os
    resumos se ainda não couberem -- um bloco nunca é cortado a meio."""
    if not blocos:
        return ""
    texto_completo = "\n\n".join(blocos)
    if len(texto_completo) <= limite:
        return _pedir_resumo(fornecedor, texto_completo)

    for _ in range(MAX_RONDAS_RESUMO):
        fatias: list[list[str]] = []
        fatia_atual: list[str] = []
        tamanho_atual = 0
        for bloco in blocos:
            if fatia_atual and tamanho_atual + len(bloco) > limite:
                fatias.append(fatia_atual)
                fatia_atual, tamanho_atual = [], 0
            fatia_atual.append(bloco)
            tamanho_atual += len(bloco)
        if fatia_atual:
            fatias.append(fatia_atual)

        resumos = [_pedir_resumo(fornecedor, "\n\n".join(fatia)) for fatia in fatias]
        texto_completo = "\n\n".join(resumos)
        if len(texto_completo) <= limite or len(fatias) <= 1:
            return texto_completo
        blocos = resumos
    return texto_completo


def preparar_resumo(admin_id: int, admin_global: bool, estudante_id: int, *, tipos: set[str],
                     data_inicio: str | None = None, data_fim: str | None = None,
                     pasta_logs: str | None = None, dsn: str | None = None) -> str:
    """Primeiro passo do fluxo (ver módulo) -- não fala ainda com o LLM
    de análise, só (opcionalmente) com o de resumo, que é o mesmo
    fornecedor configurado para 'apoio_pedagogico'."""
    email = investigacao.verificar_acesso_estudante(admin_id, admin_global, estudante_id, dsn)
    blocos = montar_blocos_historico(
        estudante_id, email, tipos=tipos, data_inicio=data_inicio, data_fim=data_fim,
        pasta_logs=pasta_logs, dsn=dsn)
    if not blocos:
        return "(Sem histórico para este estudante no período/âmbito escolhido.)"
    fornecedor = _fornecedor_apoio_pedagogico()
    return _resumir_por_tamanho(fornecedor, [b["texto"] for b in blocos], LIMITE_CARATERES_RESUMO)


def gerar_analise(admin_id: int, admin_global: bool, estudante_id: int, resumo: str,
                   dsn: str | None = None) -> str:
    """Segundo passo (ver módulo) -- 'resumo' é o texto que o admin
    confirmou (o que preparar_resumo devolveu, editado ou não)."""
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
