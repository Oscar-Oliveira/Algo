# -*- coding: utf-8 -*-
"""Grupos de estudantes, geridos por um administrador. Cada
grupo tem um código de junção: alta entropia, gerado pelo servidor,
nunca escolhido pelo estudante. O código é guardado de duas formas
diferentes, para dois propósitos diferentes -- ver notes.md:
- 'codigo_hash' (SHA-256, determinístico): usado para verificar um
  código submetido no registo por lookup indexado, sem percorrer todos
  os grupos. SHA-256 (não bcrypt) porque o código já é de alta entropia
  por construção (gerado aqui, nunca escolhido por uma pessoa) -- ao
  contrário de uma password, não há risco de dicionário a mitigar com
  um hash lento.
- 'codigo_cifrado' (Fernet, reversível, ver cifragem.py): para o admin
  poder consultar o código em claro a qualquer momento no painel,
  mesma técnica já usada para as chaves de API de LLM."""
from __future__ import annotations

import csv
import hashlib
import io
import secrets

import psycopg

from bd import sessao_bd
from cifragem import cifrar, decifrar

# Alfabeto sem carateres visualmente ambíguos (0/O, 1/I/l) -- o código
# é para ser escrito num quadro ou ditado em voz alta numa sala de
# aula, não só copiado/colado.
_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TAMANHO_CODIGO = 12  # ~61 bits de entropia (log2(33**12)), impraticável de adivinhar


class ErroGrupo(Exception):
    pass


def _gerar_codigo() -> str:
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_TAMANHO_CODIGO))


def _hash_codigo(codigo: str) -> str:
    return hashlib.sha256(codigo.strip().upper().encode("utf-8")).hexdigest()


def criar_grupo(nome: str, criado_por: int | None = None, dsn: str | None = None) -> dict:
    nome = nome.strip()
    if not nome:
        raise ErroGrupo("O nome do grupo não pode estar vazio.")
    codigo = _gerar_codigo()
    try:
        with sessao_bd(dsn) as bd:
            cursor = bd.execute(
                "INSERT INTO grupo (nome, codigo_hash, codigo_cifrado, criado_por) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (nome, _hash_codigo(codigo), cifrar(codigo), criado_por),
            )
            grupo_id = cursor.fetchone()["id"]
    except psycopg.errors.UniqueViolation as e:
        raise ErroGrupo(f"Já existe um grupo chamado '{nome}'.") from e
    return {"id": grupo_id, "nome": nome, "codigo": codigo}


def editar_grupo(grupo_id: int, nome: str, dsn: str | None = None) -> None:
    nome = nome.strip()
    if not nome:
        raise ErroGrupo("O nome do grupo não pode estar vazio.")
    try:
        with sessao_bd(dsn) as bd:
            bd.execute("UPDATE grupo SET nome = %s WHERE id = %s", (nome, grupo_id))
    except psycopg.errors.UniqueViolation as e:
        raise ErroGrupo(f"Já existe um grupo chamado '{nome}'.") from e


def ativar_grupo(grupo_id: int, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute("UPDATE grupo SET ativo = TRUE WHERE id = %s", (grupo_id,))


def desativar_grupo(grupo_id: int, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute("UPDATE grupo SET ativo = FALSE WHERE id = %s", (grupo_id,))


def ativar_alguem_grupo(grupo_id: int, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute("UPDATE grupo SET alguem_ativo = TRUE WHERE id = %s", (grupo_id,))


def desativar_alguem_grupo(grupo_id: int, dsn: str | None = None) -> None:
    with sessao_bd(dsn) as bd:
        bd.execute("UPDATE grupo SET alguem_ativo = FALSE WHERE id = %s", (grupo_id,))


def grupo_bloqueia_alguem(estudante_id: int, dsn: str | None = None) -> bool:
    """Verdadeiro se o estudante pertencer a um grupo com o Alguem
    excluído (grupo.alguem_ativo = FALSE) -- independente do interruptor
    global (definicoes.alguem_ativo), que manda por cima de tudo. Um
    estudante sem grupo, ou cujo grupo permite o Alguem, nunca é
    bloqueado por isto."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT 1 FROM estudante_grupo eg JOIN grupo ON grupo.id = eg.grupo_id "
            "WHERE eg.estudante_id = %s AND grupo.alguem_ativo = FALSE",
            (estudante_id,),
        ).fetchone()
    return linha is not None


def nome_grupo_do_estudante(estudante_id: int, dsn: str | None = None) -> str | None:
    """Nome do grupo do estudante neste momento, ou None se não
    pertencer a nenhum -- usado para denormalizar o grupo nos eventos
    do Alguem (ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção
    4/Fase 4: preserva o grupo tal como era nessa sessão, mesmo que o
    estudante mude de grupo depois)."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT grupo.nome FROM estudante_grupo eg JOIN grupo ON grupo.id = eg.grupo_id "
            "WHERE eg.estudante_id = %s LIMIT 1",
            (estudante_id,),
        ).fetchone()
    return linha["nome"] if linha else None


def apagar_grupo(grupo_id: int, dsn: str | None = None) -> None:
    """Só apaga se o grupo não tiver nenhum membro ESTUDANTE -- levanta
    ErroGrupo com uma mensagem clara caso contrário, em vez de um no-op
    silencioso (ao contrário de revogar_conta/rejeitar_conta, esta é
    uma ação destrutiva pedida explicitamente pelo admin; um "não
    aconteceu nada" sem explicação seria confuso). Um admin de grupo
    que giria este grupo não conta como "membro" -- a linha dele em
    estudante_grupo desaparece sozinha (ON DELETE CASCADE), só deixa
    de gerir este grupo, não bloqueia a eliminação."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT COUNT(*) AS n FROM estudante_grupo eg "
            "JOIN estudante ON estudante.id = eg.estudante_id "
            "WHERE eg.grupo_id = %s AND estudante.admin = FALSE",
            (grupo_id,),
        ).fetchone()
        if linha["n"] > 0:
            raise ErroGrupo("Este grupo tem membros associados -- desativa-o em vez de o eliminar.")
        cursor = bd.execute("DELETE FROM grupo WHERE id = %s", (grupo_id,))
        if cursor.rowcount == 0:
            raise ErroGrupo("Grupo não encontrado.")


def listar_grupos(dsn: str | None = None) -> list[dict]:
    """'num_membros' conta só estudantes (admin = FALSE) -- um admin de
    grupo que giria este grupo aparece em estudante_grupo mas não é um
    "membro" da turma, ver apagar_grupo."""
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT grupo.id, grupo.nome, grupo.ativo, grupo.alguem_ativo, grupo.criado_em, "
            "       COUNT(membro.id) AS num_membros "
            "FROM grupo "
            "LEFT JOIN estudante_grupo eg ON eg.grupo_id = grupo.id "
            "LEFT JOIN estudante membro ON membro.id = eg.estudante_id AND membro.admin = FALSE "
            "GROUP BY grupo.id ORDER BY grupo.nome"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def ver_codigo(grupo_id: int, dsn: str | None = None) -> str:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT codigo_cifrado FROM grupo WHERE id = %s", (grupo_id,)
        ).fetchone()
    if linha is None:
        raise ErroGrupo("Grupo não encontrado.")
    return decifrar(bytes(linha["codigo_cifrado"]))


def regenerar_codigo(grupo_id: int, dsn: str | None = None) -> str:
    """Gera um código novo e invalida o antigo -- membros já
    registados não são afetados, só passa a ser este o código exigido
    a partir de agora para novos registos neste grupo."""
    codigo = _gerar_codigo()
    with sessao_bd(dsn) as bd:
        cursor = bd.execute(
            "UPDATE grupo SET codigo_hash = %s, codigo_cifrado = %s WHERE id = %s",
            (_hash_codigo(codigo), cifrar(codigo), grupo_id),
        )
        if cursor.rowcount == 0:
            raise ErroGrupo("Grupo não encontrado.")
    return codigo


def verificar_codigo(codigo: str, dsn: str | None = None) -> int | None:
    """Devolve o id do grupo se o código corresponder a um grupo ativo,
    ou None caso contrário (código errado, inexistente, ou de um grupo
    desativado -- as três situações são indistinguíveis de propósito,
    ver autenticacao.registar)."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT id FROM grupo WHERE codigo_hash = %s AND ativo = TRUE",
            (_hash_codigo(codigo),),
        ).fetchone()
    return linha["id"] if linha else None


def reatribuir_grupo(estudante_id: int, novo_grupo_id: int | None, dsn: str | None = None) -> int | None:
    """Move um estudante para outro grupo (ou para None = sem grupo) --
    substitui SEMPRE por completo a linha existente em estudante_grupo
    (nunca acrescenta), porque uma conta não-admin só pode ter uma
    pertença. Devolve o id do grupo anterior, para quem chamar poder
    registar o evento de auditoria com o antes/depois. Levanta ErroGrupo
    se 'novo_grupo_id' não corresponder a um grupo existente e ativo, ou
    se 'estudante_id' não existir."""
    with sessao_bd(dsn) as bd:
        if novo_grupo_id is not None:
            existe = bd.execute(
                "SELECT 1 FROM grupo WHERE id = %s AND ativo = TRUE", (novo_grupo_id,)
            ).fetchone()
            if existe is None:
                raise ErroGrupo("Grupo de destino inválido ou inativo.")
        existe_estudante = bd.execute(
            "SELECT 1 FROM estudante WHERE id = %s", (estudante_id,)
        ).fetchone()
        if existe_estudante is None:
            raise ErroGrupo("Estudante não encontrado.")
        linha_anterior = bd.execute(
            "SELECT grupo_id FROM estudante_grupo WHERE estudante_id = %s LIMIT 1", (estudante_id,)
        ).fetchone()
        bd.execute("DELETE FROM estudante_grupo WHERE estudante_id = %s", (estudante_id,))
        if novo_grupo_id is not None:
            bd.execute(
                "INSERT INTO estudante_grupo (estudante_id, grupo_id) VALUES (%s, %s)",
                (estudante_id, novo_grupo_id),
            )
    return linha_anterior["grupo_id"] if linha_anterior else None


def definir_grupos_geridos(admin_id: int, grupo_ids: list[int], dsn: str | None = None) -> None:
    """Substitui por completo o conjunto de grupos geridos por um admin
    de grupo (não-global) pelos indicados em 'grupo_ids' -- mais
    simples de refletir de uma vez o que a UI escolheu do que um
    add/remove incremental. Ao contrário de reatribuir_grupo, aqui pode
    ficar mais do que uma linha (um admin pode gerir várias turmas).
    Levanta ErroGrupo se algum id não corresponder a um grupo existente."""
    grupo_ids = list(dict.fromkeys(grupo_ids))
    try:
        with sessao_bd(dsn) as bd:
            bd.execute("DELETE FROM estudante_grupo WHERE estudante_id = %s", (admin_id,))
            for grupo_id in grupo_ids:
                bd.execute(
                    "INSERT INTO estudante_grupo (estudante_id, grupo_id) VALUES (%s, %s)",
                    (admin_id, grupo_id),
                )
    except psycopg.errors.ForeignKeyViolation as e:
        raise ErroGrupo("Um dos grupos indicados não existe.") from e


def listar_grupos_geridos(admin_id: int, dsn: str | None = None) -> list[int]:
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT grupo_id FROM estudante_grupo WHERE estudante_id = %s ORDER BY grupo_id",
            (admin_id,),
        ).fetchall()
    return [linha["grupo_id"] for linha in linhas]


def limpar_grupos(estudante_id: int, dsn: str | None = None) -> None:
    """Remove toda e qualquer associação a grupos de uma conta -- usado
    ao remover o estatuto de admin (ver main.py): um admin de grupo
    pode gerir várias turmas ao mesmo tempo, o que deixa de ser válido
    assim que a conta volta a ser um estudante normal (no máximo uma,
    ver reatribuir_grupo)."""
    with sessao_bd(dsn) as bd:
        bd.execute("DELETE FROM estudante_grupo WHERE estudante_id = %s", (estudante_id,))


def listar_membros(grupo_id: int, dsn: str | None = None) -> list[dict]:
    """Contas estudante (não admin) deste grupo -- id + email, para
    quem precisa de operar sobre a turma inteira (ex:
    online/apoio_pedagogico.py, Apoio por Grupo). Mesmo filtro
    'admin = FALSE' que exportar_membros_csv já usa."""
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT estudante.id, estudante.email FROM estudante_grupo "
            "JOIN estudante ON estudante.id = estudante_grupo.estudante_id "
            "WHERE estudante_grupo.grupo_id = %s AND estudante.admin = FALSE "
            "ORDER BY estudante.email",
            (grupo_id,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def exportar_membros_csv(grupo_id: int, dsn: str | None = None) -> str:
    with sessao_bd(dsn) as bd:
        grupo = bd.execute("SELECT nome FROM grupo WHERE id = %s", (grupo_id,)).fetchone()
        if grupo is None:
            raise ErroGrupo("Grupo não encontrado.")
        membros = bd.execute(
            "SELECT estudante.email, estudante.criado_em, estudante.aprovado, estudante.admin "
            "FROM estudante_grupo "
            "JOIN estudante ON estudante.id = estudante_grupo.estudante_id "
            "WHERE estudante_grupo.grupo_id = %s AND estudante.admin = FALSE "
            "ORDER BY estudante.email",
            (grupo_id,),
        ).fetchall()

    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(["email", "registado_em", "aprovado", "admin"])
    for membro in membros:
        escritor.writerow([
            membro["email"], membro["criado_em"].isoformat(),
            membro["aprovado"], membro["admin"],
        ])
    return saida.getvalue()
