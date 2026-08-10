# -*- coding: utf-8 -*-
"""Cifra/decifra as chaves de API dos fornecedores de LLM antes de as
guardar na base de dados. Nunca ficam em texto simples em disco.

A chave de cifragem em si NUNCA fica na base de dados nem no código --
vem sempre da variável de ambiente ONLINE_CHAVE_CIFRAGEM. Sem essa
variável definida, a aplicação recusa-se a arrancar (ver main.py) em
vez de gerar uma chave nova sozinha, o que faria com que todas as
credenciais já guardadas ficassem ilegíveis na próxima vez que o
servidor reiniciasse."""
from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken

VARIAVEL_AMBIENTE_CHAVE = "ONLINE_CHAVE_CIFRAGEM"

# ON-10: não é uma análise de entropia a sério (isso exigiria mais do
# que só contar valores de byte distintos) -- é só uma rede de
# segurança contra os casos mais flagrantes (ex: a chave toda a
# zeros, ou um padrão curto repetido), que quase de certeza não vieram
# de Fernet.generate_key() (ver gerar_chave_nova()). Uma chave gerada
# corretamente tem, na prática, quase sempre perto de 32 valores de
# byte distintos nos seus 32 bytes.
_MINIMO_BYTES_DISTINTOS = 8


def _chave_parece_pouco_aleatoria(chave: str) -> bool:
    try:
        bruto = base64.urlsafe_b64decode(chave.encode("ascii"))
    except Exception:
        return False  # formato inválido -- Fernet(...) já rejeita isto à parte
    return len(set(bruto)) < _MINIMO_BYTES_DISTINTOS


class ErroCifragem(Exception):
    pass


def gerar_chave_nova() -> str:
    """Gera uma chave de cifragem nova, para copiares para
    ONLINE_CHAVE_CIFRAGEM na primeira vez que configurares o servidor.
    Chamar isto sozinho, uma vez -- nunca gerar automaticamente dentro
    da aplicação (ver o aviso no docstring do módulo)."""
    return Fernet.generate_key().decode("ascii")


def _obter_fernet() -> Fernet:
    chave = os.environ.get(VARIAVEL_AMBIENTE_CHAVE)
    if not chave:
        raise ErroCifragem(
            f"A variável de ambiente {VARIAVEL_AMBIENTE_CHAVE} não está definida. "
            f"Gera uma com gerar_chave_nova() e define-a antes de arrancar o servidor."
        )
    try:
        fernet = Fernet(chave.encode("ascii"))
    except ValueError as e:
        raise ErroCifragem(f"{VARIAVEL_AMBIENTE_CHAVE} não é uma chave Fernet válida.") from e
    if _chave_parece_pouco_aleatoria(chave):
        raise ErroCifragem(
            f"{VARIAVEL_AMBIENTE_CHAVE} parece pouco aleatória (poucos valores de "
            f"byte distintos) -- gera sempre com gerar_chave_nova(), nunca escrita à mão."
        )
    return fernet


def validar_chave_configurada() -> None:
    """Confirma que ONLINE_CHAVE_CIFRAGEM está definida e é uma chave
    Fernet válida -- pensada para ser chamada uma vez, ao arrancar o
    servidor, para o erro aparecer logo ali (claro, no arranque) em
    vez de mais tarde, como um 500 confuso na primeira tentativa de
    guardar uma credencial. Levanta ErroCifragem se algo estiver mal;
    não faz mais nada (não cifra nada a sério)."""
    _obter_fernet()


def cifrar(texto_simples: str) -> bytes:
    if not texto_simples:
        return b""
    return _obter_fernet().encrypt(texto_simples.encode("utf-8"))


def decifrar(texto_cifrado: bytes) -> str:
    if not texto_cifrado:
        return ""
    try:
        return _obter_fernet().decrypt(texto_cifrado).decode("utf-8")
    except InvalidToken as e:
        raise ErroCifragem(
            "Não foi possível decifrar a credencial -- a chave de cifragem do "
            "servidor pode ter mudado desde que foi guardada."
        ) from e
