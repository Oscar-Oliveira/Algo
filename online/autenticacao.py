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
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import psycopg

import grupos
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


class ErroCodigoGrupoInvalido(ErroAutenticacao):
    """Subclasse à parte (não só ErroAutenticacao genérico) para quem
    chamar registar() poder distinguir esta falha das outras (email
    inválido, password fraca, email já em uso) e aplicar rate-limiting
    por IP só a tentativas de código de grupo errado -- ver
    limitador_registo.py."""
    pass


def _validar_email(email: str) -> str:
    email = email.strip().lower()
    if not PADRAO_EMAIL.match(email):
        raise ErroAutenticacao("Endereço de email inválido.")
    return email


# ON-13: lista curta e propositadamente pequena (não o rockyou completo
# -- só as passwords mais óbvias, que qualquer verificador rápido
# apanharia) das passwords mais comuns, para recusar os casos mais
# flagrantes ("password123", "12345678") sem impor uma política de
# complexidade pesada a estudantes.
PASSWORDS_COMUNS = {
    "password", "password1", "12345678", "123456789",
    "1234567890", "qwerty123", "qwertyuiop", "letmein123", "iloveyou",
    "admin1234", "welcome123", "abc123456", "senha1234", "senha12345",
    "12345678910", "00000000", "11111111", "asdfghjkl", "changeme123",
}


def _validar_password(password: str) -> None:
    if len(password) < 8:
        raise ErroAutenticacao("A password tem de ter pelo menos 8 caracteres.")
    if password.lower() in PASSWORDS_COMUNS:
        raise ErroAutenticacao(
            "Essa password é demasiado comum e fácil de adivinhar -- escolhe outra.")


def _emails_admin() -> set[str]:
    bruto = os.environ.get("ONLINE_EMAIL_ADMIN", "")
    return {e.strip().lower() for e in bruto.split(",") if e.strip()}


def registar(email: str, password: str, codigo_grupo: str | None = None,
             dsn: str | None = None) -> int:
    """Cria uma conta nova. Devolve o id do estudante. 'aprovado' fica
    True se ONLINE_EMAIL_ADMIN não estiver configurada, ou se este
    email for um dos admins -- caso contrário a conta fica pendente até
    um admin a aprovar. 'codigo_grupo' é sempre opcional: se indicado,
    tem de corresponder a um grupo ativo (ErroAutenticacao caso
    contrário); se omitido, a conta fica sem grupo (nenhuma linha em
    estudante_grupo) até um admin lha atribuir. Levanta ErroAutenticacao
    se os dados forem inválidos ou se o email já estiver em uso --
    ON-12: a mensagem para email já em uso é deliberadamente genérica
    (não diz "já existe conta"), para não revelar a quem regista quais
    emails já têm conta -- a mesma filosofia já aplicada em
    autenticar()."""
    email = _validar_email(email)
    _validar_password(password)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    id_pseudonimo = str(uuid.uuid4())
    emails_admin = _emails_admin()
    eh_admin = email in emails_admin
    aprovado = eh_admin or not emails_admin

    grupo_id = None
    if codigo_grupo:
        grupo_id = grupos.verificar_codigo(codigo_grupo, dsn=dsn)
        if grupo_id is None:
            raise ErroCodigoGrupoInvalido("Código de grupo inválido.")

    try:
        with sessao_bd(dsn) as bd:
            cursor = bd.execute(
                "INSERT INTO estudante (email, password_hash, id_pseudonimo, aprovado, admin) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (email, password_hash, id_pseudonimo, aprovado, eh_admin),
            )
            estudante_id = cursor.fetchone()["id"]
            if grupo_id is not None:
                bd.execute(
                    "INSERT INTO estudante_grupo (estudante_id, grupo_id) VALUES (%s, %s)",
                    (estudante_id, grupo_id),
                )
            return estudante_id
    except psycopg.errors.UniqueViolation as e:
        raise ErroAutenticacao(
            "Não foi possível concluir o registo com estes dados. Se já "
            "tens conta, tenta entrar em vez de registar."
        ) from e


def esta_aprovado(estudante_id: int, dsn: str | None = None) -> bool:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT aprovado FROM estudante WHERE id = %s", (estudante_id,)
        ).fetchone()
    return bool(linha and linha["aprovado"])


def obter_email(estudante_id: int, dsn: str | None = None) -> str:
    """Ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção 4/Fase 4:
    os eventos do Alguem passam a identificar o estudante pelo email
    diretamente, não pelo id_pseudonimo (ver obter_id_pseudonimo
    abaixo, que continua a existir só para o isolamento de pasta de
    execução em executor.py, sem relação com isto)."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT email FROM estudante WHERE id = %s", (estudante_id,)
        ).fetchone()
    if linha is None:
        raise ErroAutenticacao("Conta não encontrada.")
    return linha["email"]


def obter_id_pseudonimo(estudante_id: int, dsn: str | None = None) -> str:
    """O identificador usado nos logs do Alguem -- nunca o id da conta
    nem o email diretamente, para as conversas registadas não ficarem
    trivialmente ligadas à identidade real do estudante."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT id_pseudonimo FROM estudante WHERE id = %s", (estudante_id,)
        ).fetchone()
    if linha is None:
        raise ErroAutenticacao("Conta não encontrada.")
    return linha["id_pseudonimo"]


def _grupo_do_estudante_esta_inativo(estudante_id: int, dsn: str | None = None) -> bool:
    """Só usado para o bloqueio de login por grupo desativado (ver
    autenticar) -- só se aplica a contas não-admin, por isso só olha
    para uma linha (uma conta não-admin tem no máximo uma em
    estudante_grupo, ver grupos.reatribuir_grupo)."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT grupo.ativo FROM estudante_grupo "
            "JOIN grupo ON grupo.id = estudante_grupo.grupo_id "
            "WHERE estudante_grupo.estudante_id = %s LIMIT 1",
            (estudante_id,),
        ).fetchone()
    return linha is not None and not linha["ativo"]


def autenticar(email: str, password: str, dsn: str | None = None) -> int:
    """Confirma email+password. Devolve o id do estudante se
    corretos. Levanta ErroAutenticacao caso contrário -- a mensagem é
    deliberadamente igual para 'email não existe' e 'password errada',
    para não revelar quais emails têm conta (a mensagem de 'conta
    pendente'/'grupo desativado' já é diferente de propósito -- só é
    mostrada depois de a password já ter sido confirmada como correta,
    por isso não revela nada que o próprio estudante não soubesse já).

    ON-11: depois de LIMIAR_TENTATIVAS_LOGIN falhas seguidas, a conta
    fica bloqueada por um período que cresce a cada falha a mais (ver
    _duracao_bloqueio_segundos) -- verificado ANTES de comparar a
    password, para não gastar ciclos de bcrypt numa conta já bloqueada.

    Um grupo desativado bloqueia o login dos seus membros -- só
    estudantes (contas não-admin). Um admin de grupo pode gerir várias
    turmas ao mesmo tempo; bloquear-lhe o login só porque UMA delas foi
    desativada não faria sentido -- decisão explícita (reverte a versão
    anterior desta regra, de quando só havia um tipo de admin), ver
    docs/interno/PlanoAlguemLLMInvestigacao.md."""
    email = email.strip().lower()
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT id, password_hash, aprovado, admin, "
            "       tentativas_login_falhadas, bloqueado_ate "
            "FROM estudante WHERE email = %s", (email,)
        ).fetchone()
    erro = ErroAutenticacao("Email ou password incorretos.")
    if linha is None:
        raise erro

    agora = datetime.now(timezone.utc)
    if linha["bloqueado_ate"]:
        bloqueado_ate = linha["bloqueado_ate"]
        if agora < bloqueado_ate:
            minutos_restantes = max(1, int((bloqueado_ate - agora).total_seconds() // 60))
            raise ErroAutenticacao(
                f"Demasiadas tentativas falhadas. Tenta novamente daqui a "
                f"{minutos_restantes} minuto(s)."
            )

    if not bcrypt.checkpw(password.encode("utf-8"), bytes(linha["password_hash"])):
        tentativas = linha["tentativas_login_falhadas"] + 1
        bloqueado_ate_novo = None
        if tentativas >= LIMIAR_TENTATIVAS_LOGIN:
            duracao = _duracao_bloqueio_segundos(tentativas)
            bloqueado_ate_novo = agora + timedelta(seconds=duracao)
        with sessao_bd(dsn) as bd:
            bd.execute(
                "UPDATE estudante SET tentativas_login_falhadas = %s, bloqueado_ate = %s WHERE id = %s",
                (tentativas, bloqueado_ate_novo, linha["id"]),
            )
        raise erro

    # password correta -- repõe o contador de falhas
    if linha["tentativas_login_falhadas"] or linha["bloqueado_ate"]:
        with sessao_bd(dsn) as bd:
            bd.execute(
                "UPDATE estudante SET tentativas_login_falhadas = 0, bloqueado_ate = NULL WHERE id = %s",
                (linha["id"],),
            )

    # bootstrap tardio: se o email só se tornou admin DEPOIS de a conta
    # já existir (ONLINE_EMAIL_ADMIN configurada mais tarde), atualiza-a
    # aqui em vez de deixar o estudante bloqueado para sempre. Nesta
    # altura a conta ainda NÃO é admin (linha["admin"] é False) -- por
    # isso o bloqueio por grupo desativado ainda se aplica, verificado
    # ANTES de promover/devolver.
    if email in _emails_admin() and not (linha["admin"] and linha["aprovado"]):
        if _grupo_do_estudante_esta_inativo(linha["id"], dsn):
            raise ErroAutenticacao(
                "O teu grupo foi desativado. Contacta o administrador responsável por este grupo."
            )
        with sessao_bd(dsn) as bd:
            bd.execute(
                "UPDATE estudante SET admin = TRUE, aprovado = TRUE WHERE id = %s", (linha["id"],)
            )
        return linha["id"]

    if not linha["aprovado"]:
        raise ErroAutenticacao(
            "A tua conta está pendente de aprovação por um administrador -- "
            "não precisas de te registar outra vez. Se demorar mais do que "
            "esperavas, contacta o professor ou administrador responsável por este grupo."
        )

    if not linha["admin"] and _grupo_do_estudante_esta_inativo(linha["id"], dsn):
        raise ErroAutenticacao(
            "O teu grupo foi desativado. Contacta o administrador responsável por este grupo."
        )

    return linha["id"]


def eh_admin(estudante_id: int, dsn: str | None = None) -> bool:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT admin FROM estudante WHERE id = %s", (estudante_id,)
        ).fetchone()
    return bool(linha and linha["admin"])


def eh_admin_global(estudante_id: int, dsn: str | None = None) -> bool:
    """Admin GLOBAL (por oposição a admin de grupo): vê e gere tudo --
    Utilizadores, Grupos, Problemas Reportados, Registo de Atividade,
    Definições. Um admin de grupo não passa aqui (403), só acede à
    futura aba de Investigação, filtrada aos seus grupos."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT admin AND admin_global AS admin_global FROM estudante WHERE id = %s",
            (estudante_id,),
        ).fetchone()
    return bool(linha and linha["admin_global"])


def listar_pendentes(dsn: str | None = None) -> list[dict]:
    """Contas ainda não aprovadas, mais antigas primeiro."""
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT id, email, criado_em FROM estudante WHERE aprovado = FALSE ORDER BY criado_em"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def aprovar_conta(estudante_id: int, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute("UPDATE estudante SET aprovado = TRUE WHERE id = %s", (estudante_id,))


def rejeitar_conta(estudante_id: int, dsn: str | None = None) -> str | None:
    """Remove uma conta ainda pendente -- nunca uma já aprovada (o
    WHERE aprovado = FALSE é a salvaguarda), para 'rejeitar' não poder
    ser usado por engano para apagar uma conta ativa. Devolve o email
    da conta apagada (ou None se não havia nenhuma pendente com este
    id) -- como a linha deixa de existir, é este o único registo que
    sobra para quem quiser deixar um rasto de auditoria da rejeição
    (ver main.py: log_atividade.alvo_id não pode apontar para um id
    já removido)."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "DELETE FROM estudante WHERE id = %s AND aprovado = FALSE RETURNING email",
            (estudante_id,),
        ).fetchone()
    return linha["email"] if linha else None


def listar_todos(dsn: str | None = None) -> list[dict]:
    """Todas as contas (pendentes, aprovadas e admin), mais antigas
    primeiro -- para a tabela de utilizadores do painel de admin.
    'grupo_id'/'grupo_nome' (pertença, só relevante para uma conta
    não-admin) e 'grupos_geridos_ids' (âmbito de gestão, só relevante
    para um admin de grupo) vêm todos da mesma relação
    (estudante_grupo, ver grupos.py) -- por subqueries em vez de
    JOIN+GROUP BY, para não obrigar a listar todas as colunas no GROUP
    BY. 'grupo_id'/'grupo_nome' assumem no máximo uma linha (LIMIT 1),
    o que só é garantido para contas não-admin."""
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT estudante.id, estudante.email, estudante.criado_em, estudante.aprovado, "
            "       estudante.admin, estudante.admin_global, "
            "       (SELECT eg.grupo_id FROM estudante_grupo eg "
            "        WHERE eg.estudante_id = estudante.id LIMIT 1) AS grupo_id, "
            "       (SELECT grupo.nome FROM estudante_grupo eg JOIN grupo ON grupo.id = eg.grupo_id "
            "        WHERE eg.estudante_id = estudante.id LIMIT 1) AS grupo_nome, "
            "       COALESCE("
            "         (SELECT array_agg(eg.grupo_id ORDER BY eg.grupo_id) "
            "          FROM estudante_grupo eg WHERE eg.estudante_id = estudante.id), "
            "         '{}') AS grupos_geridos_ids "
            "FROM estudante ORDER BY estudante.criado_em"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def revogar_conta(estudante_id: int, dsn: str | None = None) -> None:
    """Bloqueia o login de uma conta já aprovada (põe aprovado=FALSE),
    revertendo aprovar_conta -- nunca uma conta admin (o WHERE admin =
    FALSE é a salvaguarda, simétrica à de rejeitar_conta), para não ser
    possível bloquear um admin por engano a partir desta ação."""
    with sessao_bd(dsn) as bd:
        bd.execute(
            "UPDATE estudante SET aprovado = FALSE WHERE id = %s AND aprovado = TRUE AND admin = FALSE",
            (estudante_id,),
        )


def tornar_admin(estudante_id: int, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute("UPDATE estudante SET admin = TRUE WHERE id = %s", (estudante_id,))


def remover_admin(estudante_id: int, ator_id: int, dsn: str | None = None) -> bool:
    """Remove o estatuto de admin de 'estudante_id' -- nunca do próprio
    ator (guarda também embutida na query, além da verificação feita
    pela rota), e nunca se isso deixasse a aplicação sem nenhum admin
    ativo (subquery COUNT no próprio WHERE, para a condição ser
    avaliada atomicamente com o UPDATE e não deixar uma janela de
    corrida entre "contar admins" e "remover admin" em dois pedidos
    concorrentes). A mesma lógica aplica-se a admins globais: se
    'estudante_id' for o único admin global ativo, a remoção também é
    bloqueada -- caso contrário ninguém ficaria capaz de aceder às abas
    restritas a admin global (Utilizadores, Grupos, ...). Devolve True
    se a conta foi mesmo alterada -- False significa que uma das
    guardas impediu a ação (quem chamar pode então mostrar uma mensagem
    clara em vez de um sucesso silencioso que não fez nada)."""
    with sessao_bd(dsn) as bd:
        cursor = bd.execute(
            "UPDATE estudante SET admin = FALSE "
            "WHERE id = %s AND id != %s AND admin = TRUE "
            "AND (SELECT COUNT(*) FROM estudante WHERE admin = TRUE AND aprovado = TRUE) > 1 "
            "AND (NOT admin_global OR (SELECT COUNT(*) FROM estudante "
            "     WHERE admin = TRUE AND admin_global = TRUE AND aprovado = TRUE) > 1)",
            (estudante_id, ator_id),
        )
        return cursor.rowcount > 0


def definir_admin_global(estudante_id: int, admin_global: bool, ator_id: int,
                          dsn: str | None = None) -> bool:
    """Muda o estatuto de admin global de 'estudante_id' (só se aplica a
    contas já admin -- promover diretamente a admin global uma conta
    não-admin não faz sentido). Ao RETIRAR o estatuto global, aplica as
    mesmas guardas de remover_admin: nunca à própria conta do ator, e
    nunca se isso deixasse a aplicação sem nenhum admin global ativo.
    Devolve True se a conta foi mesmo alterada."""
    with sessao_bd(dsn) as bd:
        if admin_global:
            cursor = bd.execute(
                "UPDATE estudante SET admin_global = TRUE WHERE id = %s AND admin = TRUE",
                (estudante_id,),
            )
        else:
            cursor = bd.execute(
                "UPDATE estudante SET admin_global = FALSE "
                "WHERE id = %s AND id != %s AND admin = TRUE AND admin_global = TRUE "
                "AND (SELECT COUNT(*) FROM estudante "
                "     WHERE admin = TRUE AND admin_global = TRUE AND aprovado = TRUE) > 1",
                (estudante_id, ator_id),
            )
        return cursor.rowcount > 0
