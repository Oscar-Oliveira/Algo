# -*- coding: utf-8 -*-
"""Autenticação de estudantes: hash de password com bcrypt (nunca
texto simples, nunca reversível -- ao contrário da cifragem das
chaves de LLM, que TEM de ser reversível para poder ser usada)."""
from __future__ import annotations

import re
import sqlite3
import uuid

import bcrypt

from bd import sessao_bd

PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ErroAutenticacao(Exception):
    pass


def _validar_email(email: str) -> str:
    email = email.strip().lower()
    if not PADRAO_EMAIL.match(email):
        raise ErroAutenticacao("Endereço de email inválido.")
    return email


def _validar_password(password: str) -> None:
    if len(password) < 8:
        raise ErroAutenticacao("A password tem de ter pelo menos 8 caracteres.")


def registar(email: str, password: str, caminho_bd: str | None = None) -> int:
    """Cria uma conta nova. Devolve o id do estudante. Levanta
    ErroAutenticacao se o email já estiver em uso ou os dados forem
    inválidos."""
    email = _validar_email(email)
    _validar_password(password)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    id_pseudonimo = str(uuid.uuid4())
    try:
        with sessao_bd(caminho_bd) as bd:
            cursor = bd.execute(
                "INSERT INTO estudante (email, password_hash, id_pseudonimo) VALUES (?, ?, ?)",
                (email, password_hash, id_pseudonimo),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        raise ErroAutenticacao("Já existe uma conta com este email.") from e


def obter_id_pseudonimo(estudante_id: int, caminho_bd: str | None = None) -> str:
    """O identificador usado nos logs do Alguem -- nunca o id da conta
    nem o email diretamente, para as conversas registadas não ficarem
    trivialmente ligadas à identidade real do estudante."""
    with sessao_bd(caminho_bd) as bd:
        linha = bd.execute(
            "SELECT id_pseudonimo FROM estudante WHERE id = ?", (estudante_id,)
        ).fetchone()
    if linha is None:
        raise ErroAutenticacao("Conta não encontrada.")
    return linha["id_pseudonimo"]


def autenticar(email: str, password: str, caminho_bd: str | None = None) -> int:
    """Confirma email+password. Devolve o id do estudante se
    corretos. Levanta ErroAutenticacao caso contrário -- a mensagem é
    deliberadamente igual para 'email não existe' e 'password errada',
    para não revelar quais emails têm conta."""
    email = email.strip().lower()
    with sessao_bd(caminho_bd) as bd:
        linha = bd.execute(
            "SELECT id, password_hash FROM estudante WHERE email = ?", (email,)
        ).fetchone()
    erro = ErroAutenticacao("Email ou password incorretos.")
    if linha is None:
        raise erro
    if not bcrypt.checkpw(password.encode("utf-8"), linha["password_hash"]):
        raise erro
    return linha["id"]
