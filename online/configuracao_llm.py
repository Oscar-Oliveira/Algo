# -*- coding: utf-8 -*-
"""Configurações de LLM -- várias por conta, com etiqueta, a nível global
(admin) ou pessoal (estudante), com uma seleção ativa por papel (apoio/
guardião) em cada nível e uma regra de precedência entre elas. Substitui
o antigo modelo de "uma credencial por conta" (ver
docs/interno/PlanoAlguemLLMInvestigacao.md, Fase 2)."""
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

# O guardião nunca é escolha pessoal do estudante -- só existe seleção
# GLOBAL para ele (ver PAPEIS_PESSOAIS abaixo). É uma decisão de
# transparência: o estudante escolhe UM LLM (para conversar), que serve
# também de guardião até o admin decidir o contrário a nível global --
# nunca vê nem escolhe o guardião como um conceito à parte. Deixar o
# estudante escolher o seu próprio guardião defeitava o propósito dele
# (é uma verificação de segurança independente do estudante).
PAPEIS_GLOBAIS = frozenset({"apoio", "guardiao"})
PAPEIS_PESSOAIS = frozenset({"apoio"})


class ErroConfiguracaoLLM(Exception):
    pass


def _validar_papel_global(papel: str) -> None:
    if papel not in PAPEIS_GLOBAIS:
        raise ErroConfiguracaoLLM(f"Papel '{papel}' desconhecido. Válidos: apoio, guardiao.")


def _validar_papel_pessoal(papel: str) -> None:
    if papel not in PAPEIS_PESSOAIS:
        raise ErroConfiguracaoLLM(f"Papel '{papel}' não tem seleção pessoal. Válidos: apoio.")


def _validar_host_ollama(host: str) -> None:
    """ON-14: 'host' é escolhido por quem cria a configuração e torna-se o
    URL base de um pedido HTTP feito pelo SERVIDOR (não pelo browser)
    sempre que o tutor é usado -- sem validação, um host como
    'http://169.254.169.254' (metadata de cloud) ou 'http://127.0.0.1:
    <porta interna>' é um SSRF clássico contra a própria máquina do
    servidor ou a rede interna. Bloqueia esquemas que não sejam http/
    https e qualquer endereço (resolvido por DNS) privado, loopback,
    link-local, reservado ou multicast."""
    partes = urlparse(host)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise ErroConfiguracaoLLM(f"Host inválido: '{host}'.")
    try:
        enderecos = {info[4][0] for info in socket.getaddrinfo(partes.hostname, None)}
    except socket.gaierror:
        raise ErroConfiguracaoLLM(f"Não foi possível resolver o host '{partes.hostname}'.")
    for ip_texto in enderecos:
        ip = ipaddress.ip_address(ip_texto)
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ErroConfiguracaoLLM(
                f"Host '{host}' aponta para um endereço interno/privado -- não permitido."
            )


def _validar_campos(etiqueta: str, fornecedor: str, modelo: str, api_key: str, host: str | None) -> None:
    if not etiqueta:
        raise ErroConfiguracaoLLM("Indica uma etiqueta para identificar esta configuração.")
    if fornecedor not in FORNECEDORES_VALIDOS:
        disponiveis = ", ".join(sorted(FORNECEDORES_VALIDOS))
        raise ErroConfiguracaoLLM(f"Fornecedor '{fornecedor}' desconhecido. Disponíveis: {disponiveis}.")
    if not modelo:
        raise ErroConfiguracaoLLM("Indica o modelo a usar.")
    if fornecedor != "ollama" and not api_key:
        raise ErroConfiguracaoLLM(f"O fornecedor '{fornecedor}' precisa de uma chave de API.")
    # ON-15: 'host' só faz sentido para o Ollama -- outros fornecedores
    # usam sempre o mesmo endpoint fixo.
    if host and fornecedor != "ollama":
        raise ErroConfiguracaoLLM(f"O campo 'host' só é suportado pelo fornecedor 'ollama', não '{fornecedor}'.")
    if host:
        _validar_host_ollama(host)


@dataclass
class ConfiguracaoLLM:
    id: int
    estudante_id: int | None
    etiqueta: str
    fornecedor: str
    modelo: str
    api_key: str  # já decifrada
    host: str | None


def _linha_para_configuracao(linha: dict) -> ConfiguracaoLLM:
    return ConfiguracaoLLM(
        id=linha["id"],
        estudante_id=linha["estudante_id"],
        etiqueta=linha["etiqueta"],
        fornecedor=linha["fornecedor"],
        modelo=linha["modelo"],
        api_key=decifrar(bytes(linha["api_key_cifrada"]) if linha["api_key_cifrada"] else b""),
        host=linha["host"],
    )


_CAMPOS = "id, estudante_id, etiqueta, fornecedor, modelo, api_key_cifrada, host"


def criar_configuracao(estudante_id: int | None, etiqueta: str, fornecedor: str, modelo: str,
                        api_key: str, host: str | None = None, criado_por: int | None = None,
                        dsn: str | None = None) -> int:
    _validar_campos(etiqueta, fornecedor, modelo, api_key, host)
    if estudante_id is None and criado_por is None:
        raise ErroConfiguracaoLLM("Uma configuração global precisa de 'criado_por'.")
    api_key_cifrada = cifrar(api_key) if api_key else b""
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            """INSERT INTO configuracao_llm (estudante_id, etiqueta, fornecedor, modelo, api_key_cifrada, host, criado_por)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (estudante_id, etiqueta, fornecedor, modelo, api_key_cifrada, host, criado_por or estudante_id),
        ).fetchone()
    return linha["id"]


def editar_configuracao(config_id: int, etiqueta: str, fornecedor: str, modelo: str,
                         api_key: str, host: str | None = None, dsn: str | None = None) -> None:
    _validar_campos(etiqueta, fornecedor, modelo, api_key, host)
    api_key_cifrada = cifrar(api_key) if api_key else b""
    with sessao_bd(dsn) as bd:
        bd.execute(
            """UPDATE configuracao_llm SET etiqueta = %s, fornecedor = %s, modelo = %s,
               api_key_cifrada = %s, host = %s, atualizado_em = now() WHERE id = %s""",
            (etiqueta, fornecedor, modelo, api_key_cifrada, host, config_id),
        )


def apagar_configuracao(config_id: int, dsn: str | None = None) -> None:
    """selecao_llm_estudante limpa-se sozinha (ON DELETE SET NULL), mas as
    chaves globais em 'definicao' não são uma FK real -- uma config global
    apagada enquanto ainda selecionada para um papel ficaria "fantasma"
    (resolvida silenciosamente para None só na próxima leitura) se não se
    limpasse aqui."""
    with sessao_bd(dsn) as bd:
        for papel in PAPEIS_GLOBAIS:
            chave = f"llm_global_{papel}_id"
            bd.execute(
                "DELETE FROM definicao WHERE chave = %s AND valor = %s",
                (chave, str(config_id)),
            )
        bd.execute("DELETE FROM configuracao_llm WHERE id = %s", (config_id,))


def listar_configuracoes_globais(dsn: str | None = None) -> list[ConfiguracaoLLM]:
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            f"SELECT {_CAMPOS} FROM configuracao_llm WHERE estudante_id IS NULL ORDER BY etiqueta"
        ).fetchall()
    return [_linha_para_configuracao(l) for l in linhas]


def listar_configuracoes_estudante(estudante_id: int, dsn: str | None = None) -> list[ConfiguracaoLLM]:
    with sessao_bd(dsn) as bd:
        linhas = bd.execute(
            f"SELECT {_CAMPOS} FROM configuracao_llm WHERE estudante_id = %s ORDER BY etiqueta",
            (estudante_id,),
        ).fetchall()
    return [_linha_para_configuracao(l) for l in linhas]


def obter_configuracao(config_id: int, dsn: str | None = None) -> ConfiguracaoLLM | None:
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            f"SELECT {_CAMPOS} FROM configuracao_llm WHERE id = %s", (config_id,)
        ).fetchone()
    return _linha_para_configuracao(linha) if linha else None


def definir_selecao_estudante(estudante_id: int, papel: str, config_id: int | None,
                               dsn: str | None = None) -> None:
    """'papel' só aceita 'apoio' -- não existe seleção pessoal de
    guardião (ver PAPEIS_PESSOAIS)."""
    _validar_papel_pessoal(papel)
    coluna = f"{papel}_config_id"
    with sessao_bd(dsn) as bd:
        if config_id is not None:
            dona = bd.execute(
                "SELECT estudante_id FROM configuracao_llm WHERE id = %s", (config_id,)
            ).fetchone()
            if dona is None or dona["estudante_id"] != estudante_id:
                raise ErroConfiguracaoLLM("Essa configuração não pertence a esta conta.")
        bd.execute(
            f"""INSERT INTO selecao_llm_estudante (estudante_id, {coluna}) VALUES (%s, %s)
                ON CONFLICT (estudante_id) DO UPDATE SET {coluna} = excluded.{coluna}""",
            (estudante_id, config_id),
        )


def obter_selecao_estudante(estudante_id: int, papel: str, dsn: str | None = None) -> int | None:
    _validar_papel_pessoal(papel)
    coluna = f"{papel}_config_id"
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            f"SELECT {coluna} FROM selecao_llm_estudante WHERE estudante_id = %s", (estudante_id,)
        ).fetchone()
    return linha[coluna] if linha else None


def definir_selecao_global(papel: str, config_id: int | None, dsn: str | None = None) -> None:
    _validar_papel_global(papel)
    chave = f"llm_global_{papel}_id"
    with sessao_bd(dsn) as bd:
        if config_id is not None:
            dona = bd.execute(
                "SELECT estudante_id FROM configuracao_llm WHERE id = %s", (config_id,)
            ).fetchone()
            if dona is None or dona["estudante_id"] is not None:
                raise ErroConfiguracaoLLM("Essa configuração não é uma configuração global.")
        if config_id is None:
            bd.execute("DELETE FROM definicao WHERE chave = %s", (chave,))
        else:
            bd.execute(
                "INSERT INTO definicao (chave, valor) VALUES (%s, %s) "
                "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
                (chave, str(config_id)),
            )


def obter_selecao_global(papel: str, dsn: str | None = None) -> int | None:
    _validar_papel_global(papel)
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT valor FROM definicao WHERE chave = %s", (f"llm_global_{papel}_id",)
        ).fetchone()
    return int(linha["valor"]) if linha else None


def definir_permissao(papel: str, ativa: bool, dsn: str | None = None) -> None:
    """'papel' só aceita 'apoio' -- não existe permissão de guardião
    pessoal (ver PAPEIS_PESSOAIS)."""
    _validar_papel_pessoal(papel)
    with sessao_bd(dsn) as bd:
        bd.execute(
            "INSERT INTO definicao (chave, valor) VALUES (%s, %s) "
            "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
            (f"estudantes_podem_llm_{papel}", "true" if ativa else "false"),
        )


def permissao_ativa(papel: str, dsn: str | None = None) -> bool:
    _validar_papel_pessoal(papel)
    with sessao_bd(dsn) as bd:
        linha = bd.execute(
            "SELECT valor FROM definicao WHERE chave = %s", (f"estudantes_podem_llm_{papel}",)
        ).fetchone()
    return linha["valor"] == "true" if linha else False


def resolver_configuracao_ativa(estudante_id: int, papel: str, dsn: str | None = None) -> ConfiguracaoLLM | None:
    """Regra de precedência (ver docs/interno/PlanoAlguemLLMInvestigacao.md,
    secção 2): configuração global (se existir) manda sempre; senão, só se
    'papel' tiver seleção pessoal (só 'apoio' -- ver PAPEIS_PESSOAIS) e a
    permissão estiver ligada, usa-se a escolha pessoal do estudante, se
    existir; caso contrário não há LLM para este papel. Para 'guardiao'
    isto significa: só a configuração global, nunca uma pessoal -- o
    estudante nem tem como escolher o seu próprio guardião."""
    global_id = obter_selecao_global(papel, dsn)
    if global_id is not None:
        return obter_configuracao(global_id, dsn)
    if papel not in PAPEIS_PESSOAIS or not permissao_ativa(papel, dsn):
        return None
    pessoal_id = obter_selecao_estudante(estudante_id, papel, dsn)
    if pessoal_id is None:
        return None
    return obter_configuracao(pessoal_id, dsn)
