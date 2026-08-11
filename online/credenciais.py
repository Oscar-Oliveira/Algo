# -*- coding: utf-8 -*-
"""Cada estudante configura o seu próprio fornecedor de LLM (a decisão
tomada foi: cada um traz e configura a sua própria chave). Guarda-se
uma credencial por conta -- escolher um fornecedor novo substitui o
anterior, não acumula."""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

from alguem.fornecedores import FORNECEDORES
from bd import sessao_bd
from cifragem import cifrar, decifrar

# ARCH-13: antes uma segunda lista mantida à mão aqui, que podia ficar
# desatualizada em relação ao registo real -- adicionar um fornecedor
# novo em alguem/fornecedores/__init__.py não o tornava disponível na
# web até alguém lembrar de atualizar esta lista também, sem erro
# nenhum até se notar.
FORNECEDORES_VALIDOS = frozenset(FORNECEDORES)


class ErroCredencial(Exception):
    pass


def _validar_host_ollama(host: str) -> None:
    """ON-14: 'host' é escolhido pelo próprio estudante e torna-se o URL
    base de um pedido HTTP feito pelo SERVIDOR (não pelo browser do
    estudante) sempre que o tutor é usado -- sem validação, um host como
    'http://169.254.169.254' (metadata de cloud) ou 'http://127.0.0.1:
    <porta interna>' é um SSRF clássico contra a própria máquina do
    servidor ou a rede interna. Bloqueia esquemas que não sejam http/
    https e qualquer endereço (resolvido por DNS) privado, loopback,
    link-local, reservado ou multicast."""
    partes = urlparse(host)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise ErroCredencial(f"Host inválido: '{host}'.")
    try:
        enderecos = {info[4][0] for info in socket.getaddrinfo(partes.hostname, None)}
    except socket.gaierror:
        raise ErroCredencial(f"Não foi possível resolver o host '{partes.hostname}'.")
    for ip_texto in enderecos:
        ip = ipaddress.ip_address(ip_texto)
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ErroCredencial(
                f"Host '{host}' aponta para um endereço interno/privado -- não permitido."
            )


@dataclass
class CredencialLLM:
    fornecedor: str
    modelo: str
    api_key: str
    host: str | None = None


def guardar_credencial(estudante_id: int, fornecedor: str, modelo: str,
                        api_key: str, host: str | None = None,
                        caminho_bd: str | None = None) -> None:
    if fornecedor not in FORNECEDORES_VALIDOS:
        disponiveis = ", ".join(sorted(FORNECEDORES_VALIDOS))
        raise ErroCredencial(f"Fornecedor '{fornecedor}' desconhecido. Disponíveis: {disponiveis}.")
    if not modelo:
        raise ErroCredencial("Indica o modelo a usar.")
    if fornecedor != "ollama" and not api_key:
        raise ErroCredencial(f"O fornecedor '{fornecedor}' precisa de uma chave de API.")
    # ON-15: 'host' só faz sentido para o Ollama (URL do servidor local/
    # rede onde corre) -- outros fornecedores usam sempre o mesmo
    # endpoint fixo. Sem isto, um host era guardado silenciosamente para
    # qualquer fornecedor e só dava um erro confuso mais tarde, quando
    # o Alguem tentasse mesmo usar a credencial.
    if host and fornecedor != "ollama":
        raise ErroCredencial(f"O campo 'host' só é suportado pelo fornecedor 'ollama', não '{fornecedor}'.")
    if host:
        _validar_host_ollama(host)

    api_key_cifrada = cifrar(api_key) if api_key else b""
    with sessao_bd(caminho_bd) as bd:
        bd.execute(
            """INSERT INTO credencial_llm (estudante_id, fornecedor, modelo, api_key_cifrada, host, atualizado_em)
               VALUES (?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(estudante_id) DO UPDATE SET
                   fornecedor = excluded.fornecedor,
                   modelo = excluded.modelo,
                   api_key_cifrada = excluded.api_key_cifrada,
                   host = excluded.host,
                   atualizado_em = excluded.atualizado_em""",
            (estudante_id, fornecedor, modelo, api_key_cifrada, host),
        )


def obter_credencial(estudante_id: int, caminho_bd: str | None = None) -> CredencialLLM | None:
    """Devolve a credencial do estudante (com a chave já decifrada),
    ou None se ainda não configurou nenhuma."""
    with sessao_bd(caminho_bd) as bd:
        linha = bd.execute(
            "SELECT fornecedor, modelo, api_key_cifrada, host FROM credencial_llm WHERE estudante_id = ?",
            (estudante_id,),
        ).fetchone()
    if linha is None:
        return None
    return CredencialLLM(
        fornecedor=linha["fornecedor"],
        modelo=linha["modelo"],
        api_key=decifrar(linha["api_key_cifrada"]),
        host=linha["host"],
    )
