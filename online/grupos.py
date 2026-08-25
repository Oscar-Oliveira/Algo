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


def apagar_grupo(grupo_id: int, dsn: str | None = None) -> None:
    """Só apaga se o grupo não tiver nenhum membro -- levanta ErroGrupo
    com uma mensagem clara caso contrário, em vez de um no-op
    silencioso (ao contrário de revogar_conta/rejeitar_conta, esta é
    uma ação destrutiva pedida explicitamente pelo admin; um "não
    aconteceu nada" sem explicação seria confuso)."""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT COUNT(*) AS n FROM estudante WHERE grupo_id = %s", (grupo_id,)
        ).fetchone()
        if linha["n"] > 0:
            raise ErroGrupo("Este grupo tem membros associados -- desativa-o em vez de o eliminar.")
        cursor = bd.execute("DELETE FROM grupo WHERE id = %s", (grupo_id,))
        if cursor.rowcount == 0:
            raise ErroGrupo("Grupo não encontrado.")


def listar_grupos(dsn: str | None = None) -> list[dict]:
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            "SELECT grupo.id, grupo.nome, grupo.ativo, grupo.criado_em, "
            "       COUNT(estudante.id) AS num_membros "
            "FROM grupo LEFT JOIN estudante ON estudante.grupo_id = grupo.id "
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
    """Move um estudante para outro grupo (ou para None = sem grupo).
    Devolve o id do grupo anterior, para quem chamar poder registar o
    evento de auditoria com o antes/depois. Levanta ErroGrupo se
    'novo_grupo_id' não corresponder a um grupo existente e ativo."""
    with sessao_bd(dsn) as bd:
        if novo_grupo_id is not None:
            existe = bd.execute(
                "SELECT 1 FROM grupo WHERE id = %s AND ativo = TRUE", (novo_grupo_id,)
            ).fetchone()
            if existe is None:
                raise ErroGrupo("Grupo de destino inválido ou inativo.")
        linha_anterior = bd.execute(
            "SELECT grupo_id FROM estudante WHERE id = %s", (estudante_id,)
        ).fetchone()
        if linha_anterior is None:
            raise ErroGrupo("Estudante não encontrado.")
        bd.execute(
            "UPDATE estudante SET grupo_id = %s WHERE id = %s", (novo_grupo_id, estudante_id)
        )
    return linha_anterior["grupo_id"]


def exportar_membros_csv(grupo_id: int, dsn: str | None = None) -> str:
    with sessao_bd(dsn) as bd:
        grupo = bd.execute("SELECT nome FROM grupo WHERE id = %s", (grupo_id,)).fetchone()
        if grupo is None:
            raise ErroGrupo("Grupo não encontrado.")
        membros = bd.execute(
            "SELECT email, criado_em, aprovado, admin FROM estudante "
            "WHERE grupo_id = %s ORDER BY email",
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
