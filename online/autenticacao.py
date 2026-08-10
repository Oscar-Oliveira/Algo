# -*- coding: utf-8 -*-
"""Autenticação de estudantes: hash de password com bcrypt (nunca
texto simples, nunca reversível -- ao contrário da cifragem das
chaves de LLM, que TEM de ser reversível para poder ser usada).

Aprovação de contas por administrador: a variável de ambiente opcional
ONLINE_EMAIL_ADMIN (lista de emails separados por vírgula) controla
tudo -- se ficar por preencher, o registo continua completamente
aberto (comportamento de sempre, sem gate nenhum). Só quando está
preenchida é que contas novas (que não sejam de um admin) ficam
'pendentes' até um admin as aprovar em /admin. Lida em cada chamada
(nunca cacheada), para os testes poderem usar monkeypatch.setenv por
teste sem se preocuparem com ordem de importação."""
from __future__ import annotations

import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt

from bd import sessao_bd

PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ON-11: rate limiting de login por CONTA (não por IP -- não penaliza
# uma rede escolar/institucional partilhada). Backoff progressivo: a
# duração do bloqueio dobra a cada tentativa falhada a mais, a partir
# de LIMIAR_TENTATIVAS_LOGIN, até um teto -- nunca bloqueia uma conta
# indefinidamente por um esquecimento de password.
LIMIAR_TENTATIVAS_LOGIN = 5
DURACAO_BASE_BLOQUEIO_SEGUNDOS = 60
DURACAO_MAXIMA_BLOQUEIO_SEGUNDOS = 3600


def _duracao_bloqueio_segundos(tentativas: int) -> int:
    excesso = max(0, tentativas - LIMIAR_TENTATIVAS_LOGIN)
    return min(DURACAO_BASE_BLOQUEIO_SEGUNDOS * (2 ** excesso), DURACAO_MAXIMA_BLOQUEIO_SEGUNDOS)


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


def _emails_admin() -> set[str]:
    bruto = os.environ.get("ONLINE_EMAIL_ADMIN", "")
    return {e.strip().lower() for e in bruto.split(",") if e.strip()}


def registar(email: str, password: str, caminho_bd: str | None = None) -> int:
    """Cria uma conta nova. Devolve o id do estudante -- mesma
    assinatura de sempre, mesmo agora que a conta pode ficar
    'pendente' (ver esta_aprovado()), para não obrigar todos os
    chamadores existentes a mudar. 'aprovado' fica True se
    ONLINE_EMAIL_ADMIN não estiver configurada, ou se este email for
    um dos admins -- caso contrário a conta fica pendente até um admin
    a aprovar. Levanta ErroAutenticacao se o email já estiver em uso
    ou os dados forem inválidos."""
    email = _validar_email(email)
    _validar_password(password)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    id_pseudonimo = str(uuid.uuid4())
    emails_admin = _emails_admin()
    eh_admin = email in emails_admin
    aprovado = eh_admin or not emails_admin
    try:
        with sessao_bd(caminho_bd) as bd:
            cursor = bd.execute(
                "INSERT INTO estudante (email, password_hash, id_pseudonimo, aprovado, admin) "
                "VALUES (?, ?, ?, ?, ?)",
                (email, password_hash, id_pseudonimo, int(aprovado), int(eh_admin)),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        raise ErroAutenticacao("Já existe uma conta com este email.") from e


def esta_aprovado(estudante_id: int, caminho_bd: str | None = None) -> bool:
    with sessao_bd(caminho_bd) as bd:
        linha = bd.execute(
            "SELECT aprovado FROM estudante WHERE id = ?", (estudante_id,)
        ).fetchone()
    return bool(linha and linha["aprovado"])


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
    para não revelar quais emails têm conta (a mensagem de 'conta
    pendente' já é diferente de propósito -- só é mostrada depois de a
    password já ter sido confirmada como correta, por isso não revela
    nada que o próprio estudante não soubesse já).

    ON-11: depois de LIMIAR_TENTATIVAS_LOGIN falhas seguidas, a conta
    fica bloqueada por um período que cresce a cada falha a mais (ver
    _duracao_bloqueio_segundos) -- verificado ANTES de comparar a
    password, para não gastar ciclos de bcrypt numa conta já bloqueada."""
    email = email.strip().lower()
    with sessao_bd(caminho_bd) as bd:
        linha = bd.execute(
            "SELECT id, password_hash, aprovado, admin, tentativas_login_falhadas, bloqueado_ate "
            "FROM estudante WHERE email = ?", (email,)
        ).fetchone()
    erro = ErroAutenticacao("Email ou password incorretos.")
    if linha is None:
        raise erro

    agora = datetime.now(timezone.utc)
    if linha["bloqueado_ate"]:
        bloqueado_ate = datetime.fromisoformat(linha["bloqueado_ate"])
        if agora < bloqueado_ate:
            minutos_restantes = max(1, int((bloqueado_ate - agora).total_seconds() // 60))
            raise ErroAutenticacao(
                f"Demasiadas tentativas falhadas. Tenta novamente daqui a "
                f"{minutos_restantes} minuto(s)."
            )

    if not bcrypt.checkpw(password.encode("utf-8"), linha["password_hash"]):
        tentativas = linha["tentativas_login_falhadas"] + 1
        bloqueado_ate_novo = None
        if tentativas >= LIMIAR_TENTATIVAS_LOGIN:
            duracao = _duracao_bloqueio_segundos(tentativas)
            bloqueado_ate_novo = (agora + timedelta(seconds=duracao)).isoformat()
        with sessao_bd(caminho_bd) as bd:
            bd.execute(
                "UPDATE estudante SET tentativas_login_falhadas = ?, bloqueado_ate = ? WHERE id = ?",
                (tentativas, bloqueado_ate_novo, linha["id"]),
            )
        raise erro

    # password correta -- repõe o contador de falhas
    if linha["tentativas_login_falhadas"] or linha["bloqueado_ate"]:
        with sessao_bd(caminho_bd) as bd:
            bd.execute(
                "UPDATE estudante SET tentativas_login_falhadas = 0, bloqueado_ate = NULL WHERE id = ?",
                (linha["id"],),
            )

    # bootstrap tardio: se o email só se tornou admin DEPOIS de a conta
    # já existir (ONLINE_EMAIL_ADMIN configurada mais tarde), atualiza-a
    # aqui em vez de deixar o estudante bloqueado para sempre.
    if email in _emails_admin() and not (linha["admin"] and linha["aprovado"]):
        with sessao_bd(caminho_bd) as bd:
            bd.execute(
                "UPDATE estudante SET admin = 1, aprovado = 1 WHERE id = ?", (linha["id"],)
            )
        return linha["id"]

    if not linha["aprovado"]:
        raise ErroAutenticacao("A tua conta está pendente de aprovação por um administrador.")
    return linha["id"]


def eh_admin(estudante_id: int, caminho_bd: str | None = None) -> bool:
    with sessao_bd(caminho_bd) as bd:
        linha = bd.execute(
            "SELECT admin FROM estudante WHERE id = ?", (estudante_id,)
        ).fetchone()
    return bool(linha and linha["admin"])


def listar_pendentes(caminho_bd: str | None = None) -> list[dict]:
    """Contas ainda não aprovadas, mais antigas primeiro."""
    with sessao_bd(caminho_bd) as bd:
        linhas = bd.execute(
            "SELECT id, email, criado_em FROM estudante WHERE aprovado = 0 ORDER BY criado_em"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def aprovar_conta(estudante_id: int, caminho_bd: str | None = None) -> None:
    with sessao_bd(caminho_bd) as bd:
        bd.execute("UPDATE estudante SET aprovado = 1 WHERE id = ?", (estudante_id,))


def rejeitar_conta(estudante_id: int, caminho_bd: str | None = None) -> None:
    """Remove uma conta ainda pendente -- nunca uma já aprovada (o
    WHERE aprovado = 0 é a salvaguarda), para 'rejeitar' não poder ser
    usado por engano para apagar uma conta ativa."""
    with sessao_bd(caminho_bd) as bd:
        bd.execute("DELETE FROM estudante WHERE id = ? AND aprovado = 0", (estudante_id,))


def listar_todos(caminho_bd: str | None = None) -> list[dict]:
    """Todas as contas (pendentes, aprovadas e admin), mais antigas
    primeiro -- para a tabela de utilizadores do painel de admin."""
    with sessao_bd(caminho_bd) as bd:
        linhas = bd.execute(
            "SELECT id, email, criado_em, aprovado, admin FROM estudante ORDER BY criado_em"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def revogar_conta(estudante_id: int, caminho_bd: str | None = None) -> None:
    """Bloqueia o login de uma conta já aprovada (põe aprovado=0),
    revertendo aprovar_conta -- nunca uma conta admin (o WHERE admin = 0
    é a salvaguarda, simétrica à de rejeitar_conta), para não ser
    possível bloquear um admin por engano a partir desta ação."""
    with sessao_bd(caminho_bd) as bd:
        bd.execute(
            "UPDATE estudante SET aprovado = 0 WHERE id = ? AND aprovado = 1 AND admin = 0",
            (estudante_id,),
        )
