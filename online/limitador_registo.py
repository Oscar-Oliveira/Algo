# -*- coding: utf-8 -*-
"""Rate limiting por IP para tentativas de registo com código de grupo
errado -- defesa adicional além da alta entropia do próprio código
(ver grupos.py). Por IP, não por conta (a conta nem chega a existir
quando isto é acionado) -- o IP nunca é guardado em claro, só o seu
hash SHA-256, coerente com a pseudonimização já usada no resto do
projeto (id_pseudonimo, alguem/nucleo/identidade.py).

Limiar propositadamente mais generoso do que o do login por conta
(ver autenticacao.LIMIAR_TENTATIVAS_LOGIN): uma sala de aula inteira
pode partilhar o mesmo IP público (NAT), e alguns erros de transcrição
do código não devem bloquear o grupo todo."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from bd import sessao_bd

LIMIAR_TENTATIVAS = 15
DURACAO_BASE_BLOQUEIO_SEGUNDOS = 60
DURACAO_MAXIMA_BLOQUEIO_SEGUNDOS = 3600


class ErroLimiteRegisto(Exception):
    pass


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def _duracao_bloqueio_segundos(tentativas: int) -> int:
    excesso = max(0, tentativas - LIMIAR_TENTATIVAS)
    return min(DURACAO_BASE_BLOQUEIO_SEGUNDOS * (2 ** excesso), DURACAO_MAXIMA_BLOQUEIO_SEGUNDOS)


def verificar_bloqueado(ip_hash: str, dsn: str | None = None) -> None:
    """Levanta ErroLimiteRegisto se este IP estiver temporariamente
    bloqueado -- chamar ANTES de verificar o código de grupo."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT bloqueado_ate FROM tentativa_registo WHERE ip_hash = %s", (ip_hash,)
        ).fetchone()
    if linha is None or linha["bloqueado_ate"] is None:
        return
    agora = datetime.now(timezone.utc)
    if agora < linha["bloqueado_ate"]:
        minutos_restantes = max(1, int((linha["bloqueado_ate"] - agora).total_seconds() // 60))
        raise ErroLimiteRegisto(
            f"Demasiadas tentativas de registo com código inválido a partir deste "
            f"IP. Tenta novamente daqui a {minutos_restantes} minuto(s)."
        )


def registar_falha(ip_hash: str, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT tentativas FROM tentativa_registo WHERE ip_hash = %s", (ip_hash,)
        ).fetchone()
        tentativas = (linha["tentativas"] if linha else 0) + 1
        bloqueado_ate = None
        if tentativas >= LIMIAR_TENTATIVAS:
            duracao = _duracao_bloqueio_segundos(tentativas)
            bloqueado_ate = datetime.now(timezone.utc) + timedelta(seconds=duracao)
        bd.execute(
            "INSERT INTO tentativa_registo (ip_hash, tentativas, bloqueado_ate, atualizado_em) "
            "VALUES (%s, %s, %s, now()) "
            "ON CONFLICT (ip_hash) DO UPDATE SET "
            "    tentativas = excluded.tentativas, "
            "    bloqueado_ate = excluded.bloqueado_ate, "
            "    atualizado_em = excluded.atualizado_em",
            (ip_hash, tentativas, bloqueado_ate),
        )


def limpar(ip_hash: str, dsn: str | None = None) -> None:
    """Chamar quando um registo tem sucesso a partir deste IP -- repõe
    o contador, para não penalizar tentativas futuras por erros
    antigos já corrigidos."""
    with sessao_bd(dsn) as bd:
        bd.execute("DELETE FROM tentativa_registo WHERE ip_hash = %s", (ip_hash,))
