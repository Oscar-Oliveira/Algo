# -*- coding: utf-8 -*-
"""Constrói um Alguem por pedido, a partir da credencial que o
estudante guardou (ver credenciais.py), em vez de um config.json local
-- é a única adaptação necessária; todo o resto do pacote alguem/
(política, guardião, escada de ajuda, registador) é reaproveitado tal
e qual, sem alterações."""

from __future__ import annotations

import sys
import os

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

from alguem.fornecedores import criar_fornecedor, ErroFornecedorLLM
from alguem.nucleo import Alguem, PoliticaPedagogica, Registador
from alguem.nucleo.ficheiros_visiveis import LIMITE_FICHEIROS, LIMITE_BYTES_TOTAL

from credenciais import obter_credencial, CredencialLLM, ErroCredencial, _validar_host_ollama
from autenticacao import obter_id_pseudonimo

# Política por omissão para todas as sessões web -- mesmos valores por
# omissão que o alguem/config.exemplo.json já usa localmente.
POLITICA_POR_OMISSAO = PoliticaPedagogica()


class ErroAlguemIndisponivel(Exception):
    pass


def limitar_ficheiros_visiveis(ficheiros: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """ON-26: aplica o MESMO limite de AG-28 (alguem/nucleo/
    ficheiros_visiveis.py) aqui, no ponto de entrada do online -- os
    ficheiros que chegam por /ws/alguem (mensagem 'tipo: ficheiro')
    vêm diretamente do browser do estudante, sem passar pela resolução
    de 'incluir' que AG-28 já protege. Sem isto, nada impedia o
    browser de enviar um número arbitrário de ficheiros, ou ficheiros
    enormes, inflando sem controlo o prompt enviado ao LLM."""
    resultado: list[tuple[str, str]] = []
    bytes_acumulados = 0
    for nome, conteudo in ficheiros:
        if len(resultado) >= LIMITE_FICHEIROS or bytes_acumulados >= LIMITE_BYTES_TOTAL:
            break
        espaco_restante = LIMITE_BYTES_TOTAL - bytes_acumulados
        conteudo_bytes = conteudo.encode("utf-8")
        if len(conteudo_bytes) > espaco_restante:
            conteudo = conteudo_bytes[:espaco_restante].decode("utf-8", errors="ignore")
            conteudo += "\n\n[... ficheiro truncado, excede o limite de tamanho total permitido ...]"
        bytes_acumulados += len(conteudo.encode("utf-8"))
        resultado.append((nome, conteudo))
    return resultado


def construir_alguem(
    estudante_id: int,
    ficheiros_visiveis: list[tuple[str, str]] | None = None,
    dsn: str | None = None,
    pasta_logs: str | None = None,
) -> Alguem:
    """Lê a credencial do estudante e constrói um Alguem pronto a
    conversar. Levanta ErroAlguemIndisponivel (com mensagem amigável)
    se o estudante ainda não configurou nenhum fornecedor. Os logs
    usam o id_pseudonimo da conta, nunca o id nem o email diretamente.
    'pasta_logs' existe só para os testes conseguirem isolar os logs
    sem variáveis de ambiente (mesma técnica já usada em alguem/)."""
    credencial: CredencialLLM | None = obter_credencial(estudante_id, dsn)
    if credencial is None:
        raise ErroAlguemIndisponivel(
            "Ainda não configuraste nenhum fornecedor de LLM -- "
            "define um em Definições antes de chamares Alguem."
        )

    extras = {}
    if credencial.host:
        # Achado 2 (PlanoAuditoria.md): _validar_host_ollama já corre em
        # credenciais.guardar_credencial, mas só uma vez, ao guardar --
        # um domínio com TTL baixo pode resolver para um IP público
        # nesse momento e para um IP interno mais tarde (DNS rebinding),
        # contornando essa validação por completo. Repeti-la aqui, mesmo
        # sem a poder fixar (pinning) no pedido HTTP em si -- isso vive
        # em alguem/fornecedores/, fora do âmbito desta auditoria --,
        # encurta bastante a janela: passa a validar-se de novo em cada
        # conversa nova, não só uma vez ao guardar a credencial.
        try:
            _validar_host_ollama(credencial.host)
        except ErroCredencial as e:
            raise ErroAlguemIndisponivel(
                f"O host configurado para o Ollama deixou de ser válido: {e} "
                f"Reconfigura o fornecedor em Definições."
            ) from e
        extras["host"] = credencial.host

    try:
        fornecedor = criar_fornecedor(
            credencial.fornecedor, credencial.modelo, credencial.api_key, **extras
        )
    except ErroFornecedorLLM as e:
        raise ErroAlguemIndisponivel(str(e)) from e

    kwargs_registador = {"id_estudante": obter_id_pseudonimo(estudante_id, dsn)}
    if pasta_logs is not None:
        kwargs_registador["pasta_logs"] = pasta_logs
    registador = Registador(**kwargs_registador)
    return Alguem(
        fornecedor,
        POLITICA_POR_OMISSAO,
        ficheiros_visiveis=ficheiros_visiveis,
        registador=registador,
    )
