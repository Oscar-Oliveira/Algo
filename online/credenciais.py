# -*- coding: utf-8 -*-
"""Cada estudante configura o seu próprio fornecedor de LLM (a decisão
tomada foi: cada um traz e configura a sua própria chave). Guarda-se
uma credencial por conta -- escolher um fornecedor novo substitui o
anterior, não acumula."""
from __future__ import annotations

from dataclasses import dataclass

from bd import sessao_bd
from cifragem import cifrar, decifrar

FORNECEDORES_VALIDOS = {"openrouter", "gemini", "openai", "anthropic", "huggingface", "ollama", "opencode"}


class ErroCredencial(Exception):
    pass


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
