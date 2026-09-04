# -*- coding: utf-8 -*-
"""Aplicação FastAPI do Algo/Alguem online. Deliberadamente sem
grandes frameworks: sem ORM (sqlite3 puro, ver bd.py), sem sistema de
templates (HTML servido tal e qual da pasta estatico/), sessão via
SessionMiddleware do próprio Starlette (cookie assinado, sem tabela de
sessões na base de dados)."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile

from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, FastAPI, File, Request, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from contextlib import asynccontextmanager

import bd
import autenticacao
import atividade
import definicoes
import grupos
import limitador_registo
import modo_codemirror
import cifragem
import configuracao_llm
import historico_codigo
import investigacao
import prompts_configuraveis
import executor
import projeto
import relatorios
import alguem_ponte
from alguem.fornecedores import criar_fornecedor
from alguem.fornecedores.base import ErroFornecedorLLM
from alguem.nucleo.escada_de_ajuda import ESCADA_DE_AJUDA
from alguem.nucleo.conhecimento_algo import REFERENCIA_SINTAXE
from alguem.nucleo import registador as registador_alguem

PASTA_ESTATICO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estatico")

# ON-21: editor.html/ajuda.html/admin.html NÃO vivem em PASTA_ESTATICO --
# essa pasta é montada publicamente via StaticFiles mais abaixo, o que
# tornava estas páginas acessíveis diretamente em /estatico/editor.html
# (etc.), contornando por completo a verificação de sessão feita pelas
# rotas /editor, /ajuda e /admin. Os recursos que estas páginas usam
# (CSS/JS/CodeMirror) continuam em PASTA_ESTATICO, com caminhos
# absolutos ("/estatico/...") -- servir o HTML de outra pasta não
# quebra isso, já que o browser resolve os recursos a partir do URL do
# pedido (/editor), não da localização física do ficheiro.
PASTA_PAGINAS_PRIVADAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paginas_privadas")

# docs/exemplos/ vive em docs/, não dentro de online/ -- por isso não
# pode ser montada como PASTA_ESTATICO. A rota /api/exemplos lê-a
# diretamente do disco a cada pedido (tal como /modo-algo.js lê o
# lexer a cada pedido), para nunca divergir do conteúdo real da pasta.
PASTA_EXEMPLOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "exemplos")

_logger = logging.getLogger("online")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    bd.preparar_bd()
    os.makedirs(executor.PASTA_EXECUCOES_POR_OMISSAO, exist_ok=True)
    yield


app = FastAPI(title="Algo Online", lifespan=ciclo_de_vida)

_chave_sessao = os.environ.get("ONLINE_CHAVE_SESSAO")
if not _chave_sessao:
    raise RuntimeError(
        "A variável de ambiente ONLINE_CHAVE_SESSAO não está definida -- "
        "gera uma (ex: python3 -c \"import secrets; print(secrets.token_hex(32))\") "
        "e define-a antes de arrancar o servidor."
    )
# ON-25: sem isto, a sessão usava o default implícito do Starlette
# (nunca expira, dura até o browser fechar/o cookie ser apagado) --
# agora explícito e configurável (segundos; omissão: 14 dias).
SESSAO_MAX_AGE_SEGUNDOS = int(os.environ.get("ONLINE_SESSAO_MAX_AGE_SEGUNDOS", str(14 * 24 * 3600)))
# ON-35: 'False' por omissão para não partir o desenvolvimento local
# sem TLS -- em produção, atrás de HTTPS, definir ONLINE_HTTPS_ONLY=1
# para o cookie de sessão nunca ser enviado em texto simples.
_HTTPS_ONLY = os.environ.get("ONLINE_HTTPS_ONLY", "").strip().lower() in ("1", "true", "yes")
app.add_middleware(
    SessionMiddleware, secret_key=_chave_sessao,
    max_age=SESSAO_MAX_AGE_SEGUNDOS, https_only=_HTTPS_ONLY,
)

# ON-22: sem isto, um pedido HTTP com um corpo enorme (ex. um
# "ficheiro" de várias centenas de MB no JSON de /api/fluxograma) era
# lido inteiro para memória antes de qualquer validação.
LIMITE_TAMANHO_CORPO_BYTES = 2_000_000


@app.middleware("http")
async def limitar_tamanho_do_corpo(request: Request, call_next):
    """Rejeita cedo com base no cabeçalho Content-Length -- não cobre
    transferência chunked sem esse cabeçalho (raro nos clientes deste
    projeto: o próprio frontend usa fetch() com um corpo JSON simples,
    que o browser define sempre), mas é a defesa de baixo esforço que
    cobre o caso real, sem precisar de um middleware de terceiros."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            tamanho = int(content_length)
        except ValueError:
            tamanho = None
        if tamanho is not None and tamanho > LIMITE_TAMANHO_CORPO_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Pedido excede o tamanho máximo permitido."},
            )
    return await call_next(request)


# ON-23: defesa mínima contra CSRF nas rotas de mutação de estado -- a
# sessão já usa cookies SameSite=Lax por omissão (Starlette), que já
# impede o browser de enviar o cookie num POST cross-site na maioria
# dos casos modernos; isto é uma segunda camada explícita, não
# dependente só desse comportamento implícito de SameSite.
METODOS_MUTAVEIS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def verificar_origem(request: Request, call_next):
    """Compara o Origin (ou o Referer, se Origin não vier) com o Host
    do próprio pedido -- só bloqueia se um dos dois estiver presente e
    não corresponder. Um pedido sem nenhum dos dois (ex: um cliente
    não-browser a chamar a API diretamente) não é bloqueado só por
    isso -- o objetivo é travar um browser a ser instruído por OUTRO
    site a submeter aqui, não policiar todos os clientes possíveis."""
    if request.method in METODOS_MUTAVEIS:
        candidato = request.headers.get("origin") or request.headers.get("referer")
        if candidato:
            host_candidato = urlsplit(candidato).netloc
            if host_candidato and host_candidato != request.headers.get("host", ""):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origem do pedido não autorizada."},
                )
    return await call_next(request)


# Confirma logo ao arrancar que ONLINE_CHAVE_CIFRAGEM está definida E é
# uma chave Fernet válida -- sem isto, o erro só aparecia mais tarde,
# ao tentar guardar a primeira credencial, como um 500 confuso em vez
# de uma mensagem clara no arranque do servidor.
try:
    cifragem.validar_chave_configurada()
except cifragem.ErroCifragem as e:
    raise RuntimeError(str(e)) from e


@app.exception_handler(Exception)
async def tratador_de_erros_inesperados(request: Request, exc: Exception):
    """Rede de segurança: sem isto, um erro não previsto (como o de
    ONLINE_CHAVE_CIFRAGEM em falta, antes desta correção) devolvia uma
    página de erro em texto simples -- o frontend tenta sempre fazer
    resposta.json(), e isso falhava com uma mensagem confusa
    ("Unexpected token 'I', "Internal S"...") em vez do erro real.
    Agora qualquer erro não tratado devolve sempre JSON.

    ON-19: a mensagem da exceção em si NÃO vai para o cliente -- podia
    revelar detalhes internos (caminhos do servidor, nomes de tabelas
    SQL, etc.). Fica só no log do servidor, com traceback completo."""
    _logger.error(
        "Erro não tratado em %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tenta outra vez daqui a pouco."},
    )


# ---------- autenticação ----------

def estudante_atual(request: Request) -> int:
    """Dependência: lê o id da conta a partir da sessão (cookie
    assinado). 401 se não houver sessão válida."""
    id_estudante = request.session.get("id_estudante")
    if id_estudante is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return id_estudante


async def corpo_json(request: Request) -> dict:
    """ON-20: um corpo malformado (JSON inválido, ou JSON válido mas
    não um objeto -- ex. uma lista ou uma string solta) fazia
    request.json() levantar, ou o '.get()' seguinte rebentar com
    AttributeError -- ambos caíam no handler global de exceções como
    500, em vez de um 400 claro. Usado em vez de 'await request.json()'
    diretamente em todas as rotas que esperam um corpo JSON objeto."""
    try:
        dados = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Corpo do pedido tem de ser JSON válido.")
    if not isinstance(dados, dict):
        raise HTTPException(status_code=400, detail="Corpo do pedido tem de ser um objeto JSON.")
    return dados


async def admin_atual(id_estudante: int = Depends(estudante_atual)) -> int:
    """Dependência: como estudante_atual, mas exige também que a conta
    seja admin (ver autenticacao.eh_admin) -- 403 caso contrário."""
    if not await run_in_threadpool(autenticacao.eh_admin, id_estudante):
        raise HTTPException(status_code=403, detail="Só administradores podem aceder a isto.")
    return id_estudante


async def admin_global_atual(id_estudante: int = Depends(admin_atual)) -> int:
    """Como admin_atual, mas exige também que a conta seja admin
    GLOBAL (ver autenticacao.eh_admin_global) -- 403 caso contrário.
    Usado nas rotas que um admin de grupo não deve poder tocar:
    Utilizadores, Grupos, Problemas Reportados, Registo de Atividade e
    Definições (ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção
    15). As rotas de investigação (ex: rota_admin_atividade) continuam
    a usar admin_atual -- um admin de grupo acede-lhes, filtradas aos
    seus grupos, a partir da Fase 5."""
    if not await run_in_threadpool(autenticacao.eh_admin_global, id_estudante):
        raise HTTPException(status_code=403, detail="Só administradores globais podem aceder a isto.")
    return id_estudante


async def pasta_execucao_atual(id_estudante: int = Depends(estudante_atual)) -> str:
    """Dependência partilhada (ARCH-12): "resolver pseudónimo → preparar
    pasta de execução" estava repetido de forma idêntica nas rotas
    HTTP que tocam código do estudante. O WebSocket /ws/executar não
    usa esta dependência porque precisa de aceitar a ligação e
    responder com um erro JSON próprio antes de fechar quando não há
    sessão -- replica a mesma lógica manualmente, com o mesmo
    resultado."""
    pseudonimo = await run_in_threadpool(autenticacao.obter_id_pseudonimo, id_estudante)
    return executor.preparar_pasta_execucao(pseudonimo)


def _ip_do_pedido(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


@app.post("/api/registar")
async def rota_registar(request: Request):
    dados = await corpo_json(request)
    codigo_grupo = (dados.get("codigo_grupo") or "").strip() or None
    ip_hash = limitador_registo.hash_ip(_ip_do_pedido(request))

    if codigo_grupo:
        try:
            await run_in_threadpool(limitador_registo.verificar_bloqueado, ip_hash)
        except limitador_registo.ErroLimiteRegisto as e:
            raise HTTPException(status_code=429, detail=str(e))

    try:
        id_estudante = await run_in_threadpool(
            autenticacao.registar, dados.get("email", ""), dados.get("password", ""), codigo_grupo)
    except autenticacao.ErroCodigoGrupoInvalido as e:
        if codigo_grupo:
            await run_in_threadpool(limitador_registo.registar_falha, ip_hash)
        raise HTTPException(status_code=400, detail=str(e))
    except autenticacao.ErroAutenticacao as e:
        raise HTTPException(status_code=400, detail=str(e))

    if codigo_grupo:
        await run_in_threadpool(limitador_registo.limpar, ip_hash)
        grupo_id = await run_in_threadpool(grupos.verificar_codigo, codigo_grupo)
    else:
        grupo_id = None

    aprovado = await run_in_threadpool(autenticacao.esta_aprovado, id_estudante)
    if aprovado:
        request.session["id_estudante"] = id_estudante
    await run_in_threadpool(
        atividade.registar_evento, "registo", id_estudante, id_estudante, grupo_id)
    return {"ok": True, "pendente": not aprovado}


@app.post("/api/entrar")
async def rota_entrar(request: Request):
    dados = await corpo_json(request)
    email = dados.get("email", "")
    try:
        id_estudante = await run_in_threadpool(autenticacao.autenticar, email, dados.get("password", ""))
    except autenticacao.ErroAutenticacao as e:
        await run_in_threadpool(
            atividade.registar_evento, "login_falhado", None, None, None, {"email": email})
        raise HTTPException(status_code=401, detail=str(e))
    request.session["id_estudante"] = id_estudante
    await run_in_threadpool(atividade.registar_evento, "login", id_estudante, id_estudante)
    return {"ok": True}


@app.post("/api/sair")
async def rota_sair(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/eu")
async def rota_eu(id_estudante: int = Depends(estudante_atual)):
    """Usado pelo frontend para decidir se mostra a ligação para o
    painel de admin, e (o 'id') para o painel de admin conseguir
    identificar a própria conta na tabela de utilizadores -- ex: para
    nunca mostrar um botão de "remover admin" na própria linha."""
    return {
        "id": id_estudante,
        "admin": await run_in_threadpool(autenticacao.eh_admin, id_estudante),
        "admin_global": await run_in_threadpool(autenticacao.eh_admin_global, id_estudante),
        "alguem_ativo": (
            await run_in_threadpool(definicoes.alguem_ativo)
            and not await run_in_threadpool(grupos.grupo_bloqueia_alguem, id_estudante)
        ),
        # Gate das Definições do LLM do próprio estudante (ver
        # botao-definicoes-alguem em app.js): só fazem sentido se a
        # plataforma permitir escolher um LLM pessoal -- sem isto, o
        # painel só mostrava configurações que nunca podem ficar ativas.
        "llm_pessoal_permitido": await run_in_threadpool(configuracao_llm.permissao_ativa, "apoio"),
    }


@app.post("/api/relatorios")
async def rota_criar_relatorio(request: Request, id_estudante: int = Depends(estudante_atual)):
    dados = await corpo_json(request)
    descricao = dados.get("descricao", "")
    if not isinstance(descricao, str) or not descricao.strip():
        raise HTTPException(status_code=400, detail="Descrição não pode estar vazia.")
    await run_in_threadpool(relatorios.criar_relatorio, id_estudante, descricao)
    return {"ok": True}


# ---------- administração: aprovar/rejeitar contas pendentes ----------

@app.get("/api/admin/pendentes")
async def rota_admin_pendentes(id_estudante: int = Depends(admin_global_atual)):
    return {"pendentes": await run_in_threadpool(autenticacao.listar_pendentes)}


@app.post("/api/admin/aprovar/{id_estudante_alvo}")
async def rota_admin_aprovar(id_estudante_alvo: int, id_estudante: int = Depends(admin_global_atual)):
    await run_in_threadpool(autenticacao.aprovar_conta, id_estudante_alvo)
    await run_in_threadpool(atividade.registar_evento, "conta_aprovada", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/rejeitar/{id_estudante_alvo}")
async def rota_admin_rejeitar(id_estudante_alvo: int, id_estudante: int = Depends(admin_global_atual)):
    # rejeitar_conta APAGA a conta -- por isso o evento não pode
    # referenciar id_estudante_alvo em alvo_id (deixaria de existir na
    # tabela estudante); regista-se antes o email como snapshot.
    email_apagado = await run_in_threadpool(autenticacao.rejeitar_conta, id_estudante_alvo)
    if email_apagado is not None:
        await run_in_threadpool(
            atividade.registar_evento, "conta_rejeitada", id_estudante, None, None,
            {"email": email_apagado, "id_original": id_estudante_alvo})
    return {"ok": True}


# ---------- administração: todos os utilizadores, revogação e privilégios ----------

@app.get("/api/admin/utilizadores")
async def rota_admin_utilizadores(id_estudante: int = Depends(admin_global_atual)):
    return {"utilizadores": await run_in_threadpool(autenticacao.listar_todos)}


@app.post("/api/admin/revogar/{id_estudante_alvo}")
async def rota_admin_revogar(id_estudante_alvo: int, id_estudante: int = Depends(admin_global_atual)):
    if id_estudante_alvo == id_estudante:
        raise HTTPException(status_code=400, detail="Não podes revogar a tua própria conta.")
    await run_in_threadpool(autenticacao.revogar_conta, id_estudante_alvo)
    await run_in_threadpool(atividade.registar_evento, "conta_revogada", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/tornar_admin/{id_estudante_alvo}")
async def rota_admin_tornar_admin(id_estudante_alvo: int, id_estudante: int = Depends(admin_global_atual)):
    await run_in_threadpool(autenticacao.tornar_admin, id_estudante_alvo)
    await run_in_threadpool(atividade.registar_evento, "admin_concedido", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/remover_admin/{id_estudante_alvo}")
async def rota_admin_remover_admin(id_estudante_alvo: int, id_estudante: int = Depends(admin_global_atual)):
    if id_estudante_alvo == id_estudante:
        raise HTTPException(status_code=400, detail="Não podes remover os teus próprios privilégios de admin.")
    alterou = await run_in_threadpool(autenticacao.remover_admin, id_estudante_alvo, id_estudante)
    if not alterou:
        raise HTTPException(
            status_code=400,
            detail="Não é possível remover: teria de sobrar pelo menos um administrador ativo.",
        )
    # Um admin de grupo pode gerir várias turmas -- deixa de ser válido
    # assim que a conta volta a ser um estudante normal (no máximo uma,
    # ver grupos.reatribuir_grupo), por isso limpa-se aqui.
    await run_in_threadpool(grupos.limpar_grupos, id_estudante_alvo)
    await run_in_threadpool(atividade.registar_evento, "admin_revogado", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/utilizadores/{id_estudante_alvo}/admin_global")
async def rota_admin_definir_admin_global(id_estudante_alvo: int, request: Request,
                                           id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    admin_global = bool(dados.get("admin_global"))
    if not admin_global and id_estudante_alvo == id_estudante:
        raise HTTPException(
            status_code=400, detail="Não podes retirar a ti próprio o estatuto de admin global.")
    alterou = await run_in_threadpool(
        autenticacao.definir_admin_global, id_estudante_alvo, admin_global, id_estudante)
    if not alterou:
        detail = ("Não é possível remover: teria de sobrar pelo menos um administrador global ativo."
                   if not admin_global else "Não foi possível concluir a ação -- a conta tem de ser admin primeiro.")
        raise HTTPException(status_code=400, detail=detail)
    await run_in_threadpool(
        atividade.registar_evento, "admin_global_alterado", id_estudante, id_estudante_alvo, None,
        {"admin_global": admin_global})
    return {"ok": True}


@app.post("/api/admin/utilizadores/{id_estudante_alvo}/grupos_geridos")
async def rota_admin_definir_grupos_geridos(id_estudante_alvo: int, request: Request,
                                             id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    grupo_ids = dados.get("grupo_ids", [])
    if not isinstance(grupo_ids, list) or not all(isinstance(i, int) for i in grupo_ids):
        raise HTTPException(status_code=400, detail="'grupo_ids' tem de ser uma lista de inteiros.")
    try:
        await run_in_threadpool(grupos.definir_grupos_geridos, id_estudante_alvo, grupo_ids)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "grupos_geridos_alterados", id_estudante, id_estudante_alvo, None,
        {"grupo_ids": grupo_ids})
    return {"ok": True}


@app.post("/api/admin/utilizadores/{id_estudante_alvo}/grupo")
async def rota_admin_reatribuir_grupo(id_estudante_alvo: int, request: Request,
                                       id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    novo_grupo_id = dados.get("grupo_id")
    if novo_grupo_id is not None and not isinstance(novo_grupo_id, int):
        raise HTTPException(status_code=400, detail="'grupo_id' tem de ser um inteiro ou null.")
    try:
        grupo_anterior_id = await run_in_threadpool(
            grupos.reatribuir_grupo, id_estudante_alvo, novo_grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "grupo_reatribuido", id_estudante, id_estudante_alvo, novo_grupo_id,
        {"grupo_anterior_id": grupo_anterior_id, "grupo_novo_id": novo_grupo_id})
    return {"ok": True}


# ---------- administração: grupos ----------

@app.get("/api/admin/grupos")
async def rota_admin_listar_grupos(id_estudante: int = Depends(admin_global_atual)):
    return {"grupos": await run_in_threadpool(grupos.listar_grupos)}


@app.post("/api/admin/grupos")
async def rota_admin_criar_grupo(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    try:
        resultado = await run_in_threadpool(grupos.criar_grupo, dados.get("nome", ""), id_estudante)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "grupo_criado", id_estudante, None, resultado["id"],
        {"nome": resultado["nome"]})
    return resultado


@app.post("/api/admin/grupos/{grupo_id}/editar")
async def rota_admin_editar_grupo(grupo_id: int, request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    try:
        await run_in_threadpool(grupos.editar_grupo, grupo_id, dados.get("nome", ""))
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "grupo_editado", id_estudante, None, grupo_id,
        {"nome_novo": dados.get("nome", "")})
    return {"ok": True}


@app.post("/api/admin/grupos/{grupo_id}/ativar")
async def rota_admin_ativar_grupo(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    await run_in_threadpool(grupos.ativar_grupo, grupo_id)
    await run_in_threadpool(atividade.registar_evento, "grupo_ativado", id_estudante, None, grupo_id)
    return {"ok": True}


@app.post("/api/admin/grupos/{grupo_id}/desativar")
async def rota_admin_desativar_grupo(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    await run_in_threadpool(grupos.desativar_grupo, grupo_id)
    await run_in_threadpool(atividade.registar_evento, "grupo_desativado", id_estudante, None, grupo_id)
    return {"ok": True}


@app.post("/api/admin/grupos/{grupo_id}/ativar_alguem")
async def rota_admin_ativar_alguem_grupo(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    await run_in_threadpool(grupos.ativar_alguem_grupo, grupo_id)
    await run_in_threadpool(atividade.registar_evento, "grupo_alguem_ativado", id_estudante, None, grupo_id)
    return {"ok": True}


@app.post("/api/admin/grupos/{grupo_id}/desativar_alguem")
async def rota_admin_desativar_alguem_grupo(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    await run_in_threadpool(grupos.desativar_alguem_grupo, grupo_id)
    await run_in_threadpool(atividade.registar_evento, "grupo_alguem_desativado", id_estudante, None, grupo_id)
    return {"ok": True}


@app.post("/api/admin/grupos/{grupo_id}/apagar")
async def rota_admin_apagar_grupo(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    try:
        await run_in_threadpool(grupos.apagar_grupo, grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 'grupo_id' NÃO pode ir no parâmetro grupo_id do evento (FK para
    # grupo.id) -- apagar_grupo já eliminou a linha, por isso vai antes
    # como detalhe (mesmo padrão de conta_rejeitada, que também apaga a
    # linha referenciada e por isso guarda o id/email como snapshot em
    # vez de referência).
    await run_in_threadpool(
        atividade.registar_evento, "grupo_eliminado", id_estudante, None, None, {"grupo_id": grupo_id})
    return {"ok": True}


@app.get("/api/admin/grupos/{grupo_id}/codigo")
async def rota_admin_ver_codigo_grupo(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    try:
        codigo = await run_in_threadpool(grupos.ver_codigo, grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"codigo": codigo}


@app.post("/api/admin/grupos/{grupo_id}/regenerar_codigo")
async def rota_admin_regenerar_codigo_grupo(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    try:
        codigo = await run_in_threadpool(grupos.regenerar_codigo, grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=404, detail=str(e))
    await run_in_threadpool(atividade.registar_evento, "grupo_editado", id_estudante, None, grupo_id,
                             {"acao": "codigo_regenerado"})
    return {"codigo": codigo}


@app.get("/api/admin/grupos/{grupo_id}/membros.csv")
async def rota_admin_exportar_membros_csv(grupo_id: int, id_estudante: int = Depends(admin_global_atual)):
    try:
        csv_texto = await run_in_threadpool(grupos.exportar_membros_csv, grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(
        content=csv_texto, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="grupo-{grupo_id}-membros.csv"'},
    )


# ---------- administração: registo geral de atividade ----------

@app.get("/api/admin/log")
async def rota_admin_listar_log(id_estudante: int = Depends(admin_global_atual),
                                 estudante_id: int | None = None, grupo_id: int | None = None,
                                 tipo: str | None = None, data_inicio: str | None = None,
                                 data_fim: str | None = None, pagina: int = 1):
    return await run_in_threadpool(
        atividade.listar_eventos, estudante_id, grupo_id, tipo, data_inicio, data_fim, pagina)


@app.post("/api/admin/log/apagar")
async def rota_admin_apagar_log(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    ids = dados.get("ids", [])
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise HTTPException(status_code=400, detail="'ids' tem de ser uma lista de inteiros.")
    apagados = await run_in_threadpool(atividade.apagar_eventos, ids)
    await run_in_threadpool(
        atividade.registar_evento, "log_apagado", id_estudante, None, None,
        {"ids": ids, "apagados": apagados})
    return {"ok": True, "apagados": apagados}


@app.get("/api/admin/log.csv")
async def rota_admin_exportar_log_csv(id_estudante: int = Depends(admin_global_atual),
                                       estudante_id: int | None = None, grupo_id: int | None = None,
                                       tipo: str | None = None, data_inicio: str | None = None,
                                       data_fim: str | None = None):
    csv_texto = await run_in_threadpool(
        atividade.exportar_csv, estudante_id, grupo_id, tipo, data_inicio, data_fim)
    return Response(
        content=csv_texto, media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="atividade.csv"'},
    )


# ---------- administração: Investigação (dashboard/relatório/exportação/vista por estudante) ----------
#
# Ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção 6/10/15, Fase
# 5. Todas usam admin_atual (não admin_global_atual) -- um admin de
# grupo acede-lhes, mas só vê estudantes cuja pertença ATUAL aponte
# para um dos grupos que gere (online/investigacao.py aplica isto).

def _pasta_logs_alguem() -> str:
    # Lê a pasta de logs do módulo registador, não a constante (idêntica
    # em produção) do próprio metricas -- é aquele módulo que o
    # alguem_ponte usa de facto para escrever os logs, e os testes já
    # isolam esse caminho com monkeypatch (ver tests/conftest.py).
    return registador_alguem.PASTA_LOGS_POR_OMISSAO


async def _sessoes_no_ambito_filtradas(
        id_estudante: int, grupo: str | None, data_inicio: str | None, data_fim: str | None,
        fornecedor: str | None, apoio_escopo: str | None, guardiao_escopo: str | None,
) -> tuple[list[dict], list[dict]]:
    """Devolve (sessões filtradas, sessões no âmbito sem filtro nenhum)
    -- a segunda serve para online/investigacao.opcoes_de_filtro."""
    admin_global = await run_in_threadpool(autenticacao.eh_admin_global, id_estudante)
    no_ambito = await run_in_threadpool(
        investigacao.listar_sessoes_no_ambito, id_estudante, admin_global, _pasta_logs_alguem())
    sessoes = investigacao.filtrar_sessoes(
        no_ambito, grupo=grupo, data_inicio=data_inicio, data_fim=data_fim,
        fornecedor=fornecedor, apoio_escopo=apoio_escopo, guardiao_escopo=guardiao_escopo)
    return sessoes, no_ambito


@app.get("/api/admin/investigacao/filtros")
async def rota_investigacao_filtros(id_estudante: int = Depends(admin_atual)):
    admin_global = await run_in_threadpool(autenticacao.eh_admin_global, id_estudante)
    no_ambito = await run_in_threadpool(
        investigacao.listar_sessoes_no_ambito, id_estudante, admin_global, _pasta_logs_alguem())
    return investigacao.opcoes_de_filtro(no_ambito)


@app.get("/api/admin/investigacao/relatorio")
async def rota_investigacao_relatorio(
        id_estudante: int = Depends(admin_atual),
        grupo: str | None = None, data_inicio: str | None = None, data_fim: str | None = None,
        fornecedor: str | None = None, apoio_escopo: str | None = None, guardiao_escopo: str | None = None):
    sessoes, _ = await _sessoes_no_ambito_filtradas(
        id_estudante, grupo, data_inicio, data_fim, fornecedor, apoio_escopo, guardiao_escopo)
    return {"sessoes": sessoes}


@app.get("/api/admin/investigacao/dashboard")
async def rota_investigacao_dashboard(
        id_estudante: int = Depends(admin_atual),
        grupo: str | None = None, data_inicio: str | None = None, data_fim: str | None = None,
        fornecedor: str | None = None, apoio_escopo: str | None = None, guardiao_escopo: str | None = None):
    sessoes, _ = await _sessoes_no_ambito_filtradas(
        id_estudante, grupo, data_inicio, data_fim, fornecedor, apoio_escopo, guardiao_escopo)
    return investigacao.gerar_dashboard(sessoes)


@app.get("/api/admin/investigacao/exportar.csv")
async def rota_investigacao_exportar_csv(
        id_estudante: int = Depends(admin_atual),
        grupo: str | None = None, data_inicio: str | None = None, data_fim: str | None = None,
        fornecedor: str | None = None, apoio_escopo: str | None = None, guardiao_escopo: str | None = None):
    sessoes, _ = await _sessoes_no_ambito_filtradas(
        id_estudante, grupo, data_inicio, data_fim, fornecedor, apoio_escopo, guardiao_escopo)
    return Response(
        content=investigacao.exportar_csv(sessoes), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="investigacao.csv"'},
    )


@app.get("/api/admin/investigacao/exportar.json")
async def rota_investigacao_exportar_json(
        id_estudante: int = Depends(admin_atual),
        grupo: str | None = None, data_inicio: str | None = None, data_fim: str | None = None,
        fornecedor: str | None = None, apoio_escopo: str | None = None, guardiao_escopo: str | None = None):
    sessoes, _ = await _sessoes_no_ambito_filtradas(
        id_estudante, grupo, data_inicio, data_fim, fornecedor, apoio_escopo, guardiao_escopo)
    return Response(
        content=investigacao.exportar_json(sessoes), media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="investigacao.json"'},
    )


@app.get("/api/admin/investigacao/estudante/{estudante_id}")
async def rota_investigacao_estudante(estudante_id: int, id_estudante: int = Depends(admin_atual)):
    admin_global = await run_in_threadpool(autenticacao.eh_admin_global, id_estudante)
    try:
        vista = await run_in_threadpool(
            investigacao.vista_estudante, id_estudante, admin_global, estudante_id, _pasta_logs_alguem())
    except investigacao.ErroAcessoNegado as e:
        raise HTTPException(status_code=403, detail=str(e))
    # Decisão validada, ponto 8: dados deixaram de estar pseudonimizados
    # (Fase 4) -- este acesso é sensível, fica auditado como qualquer
    # outro evento de log_atividade.
    await run_in_threadpool(
        atividade.registar_evento, "investigacao_estudante_visto", id_estudante, estudante_id)
    return vista


# ---------- administração: relatórios de problemas enviados por estudantes ----------

@app.get("/api/admin/relatorios")
async def rota_admin_relatorios(id_estudante: int = Depends(admin_global_atual)):
    lista = await run_in_threadpool(relatorios.listar_relatorios)
    await run_in_threadpool(relatorios.marcar_todos_vistos)
    return {"relatorios": lista}


@app.get("/api/admin/relatorios/nao_vistos")
async def rota_admin_relatorios_nao_vistos(id_estudante: int = Depends(admin_global_atual)):
    return {"nao_vistos": await run_in_threadpool(relatorios.contar_nao_vistos)}


@app.post("/api/admin/relatorios/apagar/{id_relatorio}")
async def rota_admin_apagar_relatorio(id_relatorio: int, id_estudante: int = Depends(admin_global_atual)):
    await run_in_threadpool(relatorios.apagar_relatorio, id_relatorio)
    await run_in_threadpool(
        atividade.registar_evento, "relatorio_apagado", id_estudante, None, None,
        {"relatorio_id": id_relatorio})
    return {"ok": True}


# ---------- administração: definições globais ----------

@app.get("/api/admin/definicoes")
async def rota_admin_obter_definicoes(id_estudante: int = Depends(admin_global_atual)):
    return {
        "alguem_ativo": await run_in_threadpool(definicoes.alguem_ativo),
        "nivel_maximo_ajuda": await run_in_threadpool(definicoes.nivel_maximo_ajuda),
        "usar_guardiao": await run_in_threadpool(definicoes.usar_guardiao),
        # Nível 7 (Código) fica de fora -- ver comentário em
        # definicoes.definir_nivel_maximo_ajuda: fica sempre bloqueado
        # à parte, oferecê-lo aqui seria uma opção sem efeito.
        "escada_ajuda": [
            {"numero": n.numero, "nome": n.nome, "descricao": n.descricao}
            for n in ESCADA_DE_AJUDA if n.numero <= 6
        ],
    }


@app.post("/api/admin/definicoes/alguem")
async def rota_admin_definir_alguem_ativo(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    ativo = bool(dados.get("ativo"))
    await run_in_threadpool(definicoes.definir_alguem_ativo, ativo)
    await run_in_threadpool(
        atividade.registar_evento, "definicao_alterada", id_estudante, None, None,
        {"chave": "alguem_ativo", "valor": ativo})
    return {"ok": True}


@app.post("/api/admin/definicoes/guardiao")
async def rota_admin_definir_usar_guardiao(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    ativo = bool(dados.get("ativo"))
    await run_in_threadpool(definicoes.definir_usar_guardiao, ativo)
    await run_in_threadpool(
        atividade.registar_evento, "definicao_alterada", id_estudante, None, None,
        {"chave": "usar_guardiao", "valor": ativo})
    return {"ok": True}


@app.post("/api/admin/definicoes/nivel-ajuda")
async def rota_admin_definir_nivel_maximo_ajuda(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    try:
        nivel = int(dados.get("nivel"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Nível inválido.")
    try:
        await run_in_threadpool(definicoes.definir_nivel_maximo_ajuda, nivel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "definicao_alterada", id_estudante, None, None,
        {"chave": "nivel_maximo_ajuda", "valor": nivel})
    return {"ok": True}


# ---------- administração: referência da sintaxe ALGO enviada ao Tutor ----------

@app.get("/api/admin/referencia-algo")
async def rota_admin_obter_referencia_algo(id_estudante: int = Depends(admin_global_atual)):
    return {"texto": REFERENCIA_SINTAXE}


# ---------- administração: prompts editáveis (tutor, guardião) ----------

@app.get("/api/admin/prompts")
async def rota_admin_obter_prompts(id_estudante: int = Depends(admin_global_atual)):
    resultado = {}
    for chave, omissao in prompts_configuraveis.PROMPTS_OMISSAO.items():
        personalizado = await run_in_threadpool(prompts_configuraveis.obter_prompt_personalizado, chave)
        resultado[chave] = {
            "texto": personalizado if personalizado is not None else omissao,
            "omissao": omissao,
            "personalizado": personalizado is not None,
        }
    return resultado


@app.put("/api/admin/prompts/{chave}")
async def rota_admin_definir_prompt(chave: str, request: Request,
                                     id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    try:
        await run_in_threadpool(
            prompts_configuraveis.definir_prompt, chave, dados.get("texto", ""), id_estudante)
    except prompts_configuraveis.ErroPromptConfiguravel as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "prompt_alterado", id_estudante, None, None, {"chave": chave})
    return {"ok": True}


@app.delete("/api/admin/prompts/{chave}")
async def rota_admin_repor_prompt_omissao(chave: str, id_estudante: int = Depends(admin_global_atual)):
    try:
        await run_in_threadpool(prompts_configuraveis.repor_omissao, chave)
    except prompts_configuraveis.ErroPromptConfiguravel as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "prompt_reposto_omissao", id_estudante, None, None, {"chave": chave})
    return {"ok": True}


# ---------- administração: eliminação do histórico de código executado ----------
#
# Só o histórico de código (secção 14/Fase 4) tem esta ferramenta --
# nem as sessões do Alguem (logs/*.jsonl), nem configurações de LLM
# antigas (decisão validada, ponto 11). Três modos, sem soft-delete
# nem papelaria (decisão explícita de simplicidade, ver secção 14):
# por período, por seleção manual, ou tudo.

@app.post("/api/admin/execucoes/apagar")
async def rota_admin_apagar_execucoes(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    ids = dados.get("ids", [])
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise HTTPException(status_code=400, detail="'ids' tem de ser uma lista de inteiros.")
    apagados = await run_in_threadpool(historico_codigo.apagar_por_ids, ids)
    await run_in_threadpool(
        atividade.registar_evento, "execucoes_apagadas", id_estudante, None, None,
        {"modo": "selecao", "ids": ids, "apagados": apagados})
    return {"ok": True, "apagados": apagados}


@app.post("/api/admin/execucoes/apagar-por-periodo")
async def rota_admin_apagar_execucoes_por_periodo(request: Request,
                                                    id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    try:
        dias = int(dados.get("dias"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'dias' tem de ser um inteiro.")
    if dias < 0:
        raise HTTPException(status_code=400, detail="'dias' não pode ser negativo.")
    apagados = await run_in_threadpool(historico_codigo.apagar_por_periodo, dias)
    await run_in_threadpool(
        atividade.registar_evento, "execucoes_apagadas", id_estudante, None, None,
        {"modo": "periodo", "dias": dias, "apagados": apagados})
    return {"ok": True, "apagados": apagados}


@app.post("/api/admin/execucoes/apagar-tudo")
async def rota_admin_apagar_todas_as_execucoes(request: Request,
                                                id_estudante: int = Depends(admin_global_atual)):
    # Ação destrutiva e irreversível sobre TODO o histórico -- exige um
    # sinal explícito no corpo do pedido, não só o método POST, para
    # não ficar acionável por engano.
    dados = await corpo_json(request)
    if dados.get("confirmar") is not True:
        raise HTTPException(status_code=400, detail="Confirmação em falta ('confirmar': true).")
    apagados = await run_in_threadpool(historico_codigo.apagar_tudo)
    await run_in_threadpool(
        atividade.registar_evento, "execucoes_apagadas", id_estudante, None, None,
        {"modo": "tudo", "apagados": apagados})
    return {"ok": True, "apagados": apagados}


# ---------- administração: descarregar a base de dados para backup ----------

@app.get("/api/admin/bd")
async def rota_admin_descarregar_bd(tarefas: BackgroundTasks, id_estudante: int = Depends(admin_global_atual)):
    """Devolve um dump .sql da base de dados inteira (via pg_dump), para
    o admin guardar como backup ou analisar offline -- ver
    bd.gerar_backup_sql."""
    descritor, caminho_copia = tempfile.mkstemp(suffix=".sql")
    os.close(descritor)
    try:
        await bd.gerar_backup_sql(caminho_copia)
    except bd.ErroBackup as e:
        os.remove(caminho_copia)
        _logger.error("pg_dump falhou ao gerar backup: %s", e)
        raise HTTPException(status_code=500, detail="Não foi possível gerar o backup.")
    tarefas.add_task(os.remove, caminho_copia)
    await run_in_threadpool(atividade.registar_evento, "bd_descarregada", id_estudante)
    nome_ficheiro = f"algo-online-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.sql"
    return FileResponse(
        caminho_copia,
        media_type="application/sql",
        filename=nome_ficheiro,
        background=tarefas,
    )


# ---------- configurações de LLM ----------

def _configuracao_para_json(c: configuracao_llm.ConfiguracaoLLM) -> dict:
    """Nunca inclui a chave de API -- só o que é seguro mostrar de volta
    para confirmar o que já está configurado."""
    return {"id": c.id, "etiqueta": c.etiqueta, "fornecedor": c.fornecedor, "modelo": c.modelo, "host": c.host}


@app.get("/api/llm/configuracoes")
async def rota_llm_listar_configuracoes(id_estudante: int = Depends(estudante_atual)):
    """O guardião é sempre transparente para o estudante -- só existe
    seleção pessoal para 'apoio' (ver configuracao_llm.PAPEIS_PESSOAIS),
    por isso esta resposta nem tem noção de 'papel': o estudante escolhe
    um único LLM."""
    configuracoes = await run_in_threadpool(configuracao_llm.listar_configuracoes_estudante, id_estudante)
    return {
        "configuracoes": [_configuracao_para_json(c) for c in configuracoes],
        "configuracao_ativa_id": await run_in_threadpool(
            configuracao_llm.obter_selecao_estudante, id_estudante, "apoio"),
        "llm_pessoal_permitido": await run_in_threadpool(configuracao_llm.permissao_ativa, "apoio"),
        "definido_pela_plataforma": (
            await run_in_threadpool(configuracao_llm.obter_selecao_global, "apoio")) is not None,
    }


@app.post("/api/llm/configuracoes")
async def rota_llm_criar_configuracao(request: Request, id_estudante: int = Depends(estudante_atual)):
    dados = await corpo_json(request)
    try:
        novo_id = await run_in_threadpool(
            configuracao_llm.criar_configuracao,
            id_estudante,
            dados.get("etiqueta", ""),
            dados.get("fornecedor", ""),
            dados.get("modelo", ""),
            dados.get("api_key", ""),
            host=dados.get("host") or None,
        )
    except configuracao_llm.ErroConfiguracaoLLM as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "id": novo_id}


async def _exigir_configuracao_do_estudante(config_id: int, id_estudante: int) -> None:
    c = await run_in_threadpool(configuracao_llm.obter_configuracao, config_id)
    if c is None or c.estudante_id != id_estudante:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")


@app.put("/api/llm/configuracoes/{config_id}")
async def rota_llm_editar_configuracao(config_id: int, request: Request,
                                        id_estudante: int = Depends(estudante_atual)):
    await _exigir_configuracao_do_estudante(config_id, id_estudante)
    dados = await corpo_json(request)
    try:
        await run_in_threadpool(
            configuracao_llm.editar_configuracao,
            config_id,
            dados.get("etiqueta", ""),
            dados.get("fornecedor", ""),
            dados.get("modelo", ""),
            dados.get("api_key", ""),
            host=dados.get("host") or None,
        )
    except configuracao_llm.ErroConfiguracaoLLM as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.delete("/api/llm/configuracoes/{config_id}")
async def rota_llm_apagar_configuracao(config_id: int, id_estudante: int = Depends(estudante_atual)):
    await _exigir_configuracao_do_estudante(config_id, id_estudante)
    await run_in_threadpool(configuracao_llm.apagar_configuracao, config_id)
    return {"ok": True}


@app.post("/api/llm/selecao")
async def rota_llm_definir_selecao(request: Request, id_estudante: int = Depends(estudante_atual)):
    """Só escolhe o LLM de apoio -- não existe seleção pessoal de
    guardião (ver configuracao_llm.PAPEIS_PESSOAIS)."""
    dados = await corpo_json(request)
    if not await run_in_threadpool(configuracao_llm.permissao_ativa, "apoio"):
        raise HTTPException(status_code=403, detail="A plataforma não permite escolher o próprio LLM.")
    try:
        await run_in_threadpool(
            configuracao_llm.definir_selecao_estudante, id_estudante, "apoio", dados.get("configuracao_id"))
    except configuracao_llm.ErroConfiguracaoLLM as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


# ---------- administração: configurações globais de LLM ----------

@app.get("/api/admin/llm")
async def rota_admin_llm_listar(id_estudante: int = Depends(admin_global_atual)):
    configuracoes = await run_in_threadpool(configuracao_llm.listar_configuracoes_globais)
    selecao_global, permissoes = {}, {}
    for papel in configuracao_llm.PAPEIS_GLOBAIS:
        selecao_global[papel] = await run_in_threadpool(configuracao_llm.obter_selecao_global, papel)
    for papel in configuracao_llm.PAPEIS_PESSOAIS:
        permissoes[papel] = await run_in_threadpool(configuracao_llm.permissao_ativa, papel)
    return {
        "configuracoes": [_configuracao_para_json(c) for c in configuracoes],
        "selecao_global": selecao_global,
        "permissoes": permissoes,
    }


@app.post("/api/admin/llm/configuracoes")
async def rota_admin_llm_criar_configuracao(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    try:
        novo_id = await run_in_threadpool(
            configuracao_llm.criar_configuracao,
            None,
            dados.get("etiqueta", ""),
            dados.get("fornecedor", ""),
            dados.get("modelo", ""),
            dados.get("api_key", ""),
            host=dados.get("host") or None,
            criado_por=id_estudante,
        )
    except configuracao_llm.ErroConfiguracaoLLM as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "llm_configuracao_criada", id_estudante, None, None,
        {"id": novo_id, "etiqueta": dados.get("etiqueta", "")})
    return {"ok": True, "id": novo_id}


async def _exigir_configuracao_global(config_id: int) -> None:
    c = await run_in_threadpool(configuracao_llm.obter_configuracao, config_id)
    if c is None or c.estudante_id is not None:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")


@app.put("/api/admin/llm/configuracoes/{config_id}")
async def rota_admin_llm_editar_configuracao(config_id: int, request: Request,
                                              id_estudante: int = Depends(admin_global_atual)):
    await _exigir_configuracao_global(config_id)
    dados = await corpo_json(request)
    try:
        await run_in_threadpool(
            configuracao_llm.editar_configuracao,
            config_id,
            dados.get("etiqueta", ""),
            dados.get("fornecedor", ""),
            dados.get("modelo", ""),
            dados.get("api_key", ""),
            host=dados.get("host") or None,
        )
    except configuracao_llm.ErroConfiguracaoLLM as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "llm_configuracao_editada", id_estudante, None, None, {"id": config_id})
    return {"ok": True}


@app.delete("/api/admin/llm/configuracoes/{config_id}")
async def rota_admin_llm_apagar_configuracao(config_id: int, id_estudante: int = Depends(admin_global_atual)):
    await _exigir_configuracao_global(config_id)
    await run_in_threadpool(configuracao_llm.apagar_configuracao, config_id)
    await run_in_threadpool(
        atividade.registar_evento, "llm_configuracao_apagada", id_estudante, None, None, {"id": config_id})
    return {"ok": True}


@app.post("/api/admin/llm/selecao")
async def rota_admin_llm_definir_selecao(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    papel = dados.get("papel", "")
    if papel not in configuracao_llm.PAPEIS_GLOBAIS:
        raise HTTPException(status_code=400, detail="Papel inválido.")
    try:
        await run_in_threadpool(
            configuracao_llm.definir_selecao_global, papel, dados.get("configuracao_id"))
    except configuracao_llm.ErroConfiguracaoLLM as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(
        atividade.registar_evento, "llm_selecao_alterada", id_estudante, None, None,
        {"papel": papel, "configuracao_id": dados.get("configuracao_id")})
    return {"ok": True}


@app.post("/api/admin/llm/permissao")
async def rota_admin_llm_definir_permissao(request: Request, id_estudante: int = Depends(admin_global_atual)):
    dados = await corpo_json(request)
    papel = dados.get("papel", "")
    if papel not in configuracao_llm.PAPEIS_PESSOAIS:
        raise HTTPException(status_code=400, detail="Papel inválido.")
    ativa = bool(dados.get("ativa"))
    await run_in_threadpool(configuracao_llm.definir_permissao, papel, ativa)
    await run_in_threadpool(
        atividade.registar_evento, "llm_permissao_alterada", id_estudante, None, None,
        {"papel": papel, "ativa": ativa})
    return {"ok": True}


@app.post("/api/admin/llm/configuracoes/{config_id}/testar")
async def rota_admin_llm_testar_configuracao(config_id: int, id_estudante: int = Depends(admin_global_atual)):
    """Pedido mínimo real ao fornecedor, só para confirmar que a
    configuração (chave de API, modelo, host) funciona -- não guarda
    nem mostra a resposta do modelo, só se houve erro ou não."""
    c = await run_in_threadpool(configuracao_llm.obter_configuracao, config_id)
    if c is None or c.estudante_id is not None:
        raise HTTPException(status_code=404, detail="Configuração não encontrada.")
    extras = {"host": c.host} if c.host else {}
    try:
        agente = criar_fornecedor(c.fornecedor, c.modelo, c.api_key, **extras)
        await run_in_threadpool(agente.responder, [{"role": "user", "content": "Responde só 'ok'."}])
    except ErroFornecedorLLM as e:
        return {"ok": False, "detail": str(e)}
    return {"ok": True}


# ---------- páginas ----------

@app.get("/")
async def pagina_inicial(request: Request):
    if request.session.get("id_estudante") is not None:
        return RedirectResponse("/editor")
    return FileResponse(os.path.join(PASTA_ESTATICO, "entrar.html"))


@app.get("/editor")
async def pagina_editor(request: Request):
    if request.session.get("id_estudante") is None:
        return RedirectResponse("/")
    return FileResponse(os.path.join(PASTA_PAGINAS_PRIVADAS, "editor.html"))


@app.get("/ajuda")
async def pagina_ajuda(request: Request):
    if request.session.get("id_estudante") is None:
        return RedirectResponse("/")
    return FileResponse(os.path.join(PASTA_PAGINAS_PRIVADAS, "ajuda.html"))


def _analisar_enunciado(texto: str, nomes_ficheiros_validos: list[str]) -> tuple[str, list[dict]]:
    """Corta um enunciado.md em (intro, blocos) -- um bloco por
    cabeçalho '## ...', na ordem em que aparecem. Um cabeçalho pode
    estar partido em mais do que uma linha física no ficheiro fonte
    (quebra "suave", não markdown ATX estrito -- ver
    exemplos/09_ficheiros_incluir/enunciado.md) -- linhas não vazias
    logo a seguir ao '##' são juntadas ao título até à primeira linha
    em branco, antes de se procurarem os nomes de ficheiro entre
    crases. Qualquer ficheiro de 'nomes_ficheiros_validos' que nenhum
    bloco referencie ganha um bloco próprio no fim, sem descrição, para
    nunca desaparecer da UI."""
    linhas = texto.splitlines()
    if linhas and linhas[0].strip().startswith("# "):
        linhas = linhas[1:]  # já usado para o 'titulo' da pasta, fora desta função

    secoes: list[tuple[str | None, list[str]]] = []
    titulo_atual = None
    corpo_atual: list[str] = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if linha.strip().startswith("## "):
            secoes.append((titulo_atual, corpo_atual))
            partes_titulo = [linha.strip()[3:].strip()]
            i += 1
            while i < len(linhas) and linhas[i].strip() != "":
                partes_titulo.append(linhas[i].strip())
                i += 1
            titulo_atual = " ".join(partes_titulo)
            corpo_atual = []
            continue
        corpo_atual.append(linha)
        i += 1
    secoes.append((titulo_atual, corpo_atual))

    intro = "\n".join(secoes[0][1]).strip()
    blocos = []
    cobertos = set()
    for titulo_bloco, linhas_corpo in secoes[1:]:
        ficheiros_bloco = [
            nome for nome in re.findall(r"`([^`]+\.algo)`", titulo_bloco)
            if nome in nomes_ficheiros_validos
        ]
        cobertos.update(ficheiros_bloco)
        blocos.append({
            "titulo": titulo_bloco,
            "ficheiros": ficheiros_bloco,
            "descricao": "\n".join(linhas_corpo).strip(),
        })

    for nome in nomes_ficheiros_validos:
        if nome not in cobertos:
            blocos.append({"titulo": nome, "ficheiros": [nome], "descricao": ""})

    return intro, blocos


def _listar_exemplos() -> list[dict]:
    """Lê exemplos/ do disco: uma entrada por subpasta numerada, com o
    enunciado (se existir, já cortado em intro+blocos por
    _analisar_enunciado) e o código de cada ficheiro .algo, por ordem
    alfabética. Nenhum caminho vem do pedido -- só se lê dentro da
    própria pasta exemplos/, sem risco de traversal."""
    pastas = []
    if not os.path.isdir(PASTA_EXEMPLOS):
        return pastas
    for nome_pasta in sorted(os.listdir(PASTA_EXEMPLOS)):
        caminho_pasta = os.path.join(PASTA_EXEMPLOS, nome_pasta)
        if not os.path.isdir(caminho_pasta):
            continue
        enunciado = None
        caminho_enunciado = os.path.join(caminho_pasta, "enunciado.md")
        if os.path.isfile(caminho_enunciado):
            with open(caminho_enunciado, "r", encoding="utf-8") as f:
                enunciado = f.read()
        ficheiros = []
        for nome_ficheiro in sorted(os.listdir(caminho_pasta)):
            if not nome_ficheiro.endswith(".algo"):
                continue
            with open(os.path.join(caminho_pasta, nome_ficheiro), "r", encoding="utf-8") as f:
                codigo = f.read()
            ficheiros.append({"nome": nome_ficheiro, "codigo": codigo})
        if not ficheiros:
            continue
        titulo = nome_pasta
        intro = ""
        blocos: list[dict] = []
        if enunciado:
            primeira_linha = enunciado.splitlines()[0].strip()
            if primeira_linha.startswith("#"):
                titulo = primeira_linha.lstrip("#").strip()
            intro, blocos = _analisar_enunciado(enunciado, [f["nome"] for f in ficheiros])
        pastas.append({
            "pasta": nome_pasta,
            "titulo": titulo,
            "intro": intro,
            "blocos": blocos,
            "ficheiros": ficheiros,
        })
    return pastas


@app.get("/api/exemplos")
async def rota_exemplos(id_estudante: int = Depends(estudante_atual)):
    return await run_in_threadpool(_listar_exemplos)


@app.get("/admin")
async def pagina_admin(request: Request):
    id_estudante = request.session.get("id_estudante")
    if id_estudante is None or not await run_in_threadpool(autenticacao.eh_admin, id_estudante):
        return RedirectResponse("/editor")
    return FileResponse(os.path.join(PASTA_PAGINAS_PRIVADAS, "admin.html"))


@app.get("/modo-algo.js")
async def rota_modo_algo():
    """Gerado a partir das palavras-chave reais do compilador a cada
    pedido -- nunca fica desatualizado, mesmo sem reiniciar o
    servidor depois de o ALGO mudar (o próprio processo já teria de
    reiniciar para apanhar um compilador novo, mas isto evita ter uma
    CÓPIA escrita à mão que possa divergir por engano)."""
    return Response(content=modo_codemirror.gerar_js_modo(), media_type="application/javascript")


app.mount("/estatico", StaticFiles(directory=PASTA_ESTATICO), name="estatico")


# ---------- WebSocket: execução interativa ----------

def _id_estudante_do_websocket(websocket: WebSocket) -> int | None:
    return websocket.session.get("id_estudante")


# ON-03: sem isto, N estudantes a executar código em simultâneo podiam
# esgotar CPU/memória do servidor para todos -- limite configurável
# (variável de ambiente, para não obrigar a mexer no código consoante
# o tamanho da máquina onde o servidor corre).
LIMITE_EXECUCOES_CONCORRENTES = int(os.environ.get("ONLINE_LIMITE_EXECUCOES_CONCORRENTES", "10"))
_semaforo_execucoes = asyncio.Semaphore(LIMITE_EXECUCOES_CONCORRENTES)


async def _adquirir_vaga_de_execucao(websocket: WebSocket) -> None:
    """Espera por uma vaga no semáforo de execuções concorrentes. Se
    não há vaga livre logo (servidor saturado), avisa o estudante antes
    de ficar à espera -- sem isto, um pedido bloqueado no semáforo
    pareceria simplesmente "pendurado", sem nenhuma explicação."""
    try:
        await asyncio.wait_for(_semaforo_execucoes.acquire(), timeout=0.05)
        return
    except TimeoutError:
        pass
    await websocket.send_json({
        "tipo": "info",
        "mensagem": "O servidor está ocupado -- a tua execução vai começar assim que houver um lugar livre.",
    })
    await _semaforo_execucoes.acquire()


async def _registar_execucao_com_seguranca(id_estudante: int, tipo: str, nome_principal: str,
                                            ficheiros: list[dict], resultado: str) -> None:
    """Grava o histórico de execução/debug (secção 9/Fase 4). Chamada
    sempre DEPOIS de o estudante já ter recebido o resultado da sua
    execução (o 'fim'/'erro'/'erro_compilacao' já foi enviado antes) --
    não atrasa nada que o estudante perceba, só o momento em que este
    pedido HTTP/WebSocket termina de vez do lado do servidor. Falhas
    ficam só em log: perder um registo de histórico não pode derrubar
    uma execução que já correu bem para o estudante."""
    try:
        await run_in_threadpool(
            historico_codigo.registar_execucao, id_estudante, tipo, nome_principal, ficheiros, resultado)
    except Exception:
        _logger.exception("Falha ao gravar histórico de execução de código.")


@app.websocket("/ws/executar")
async def ws_executar(websocket: WebSocket):
    await websocket.accept()
    id_estudante = _id_estudante_do_websocket(websocket)
    if id_estudante is None:
        await websocket.send_json({"tipo": "erro", "mensagem": "Não autenticado."})
        await websocket.close()
        return

    pseudonimo = await run_in_threadpool(autenticacao.obter_id_pseudonimo, id_estudante)
    pasta_estudante = executor.preparar_pasta_execucao(pseudonimo)

    try:
        mensagem_inicial = await websocket.receive_json()
    except WebSocketDisconnect:
        return

    ficheiros = mensagem_inicial.get("ficheiros", [])
    nome_principal = mensagem_inicial.get("principal", "")
    try:
        caminho_py = executor.compilar_codigo(ficheiros, nome_principal, pasta_estudante)
    except executor.ErroCompilacao as e:
        await _registar_execucao_com_seguranca(
            id_estudante, "executa", nome_principal, ficheiros, f"Erro de compilação: {e}")
        await websocket.send_json({"tipo": "erro_compilacao", "mensagem": str(e)})
        await websocket.close()
        return

    # Valor por omissão -- cobre as saídas que nunca chegam a um "fim"/
    # "erro" claro (ligação perdida a meio, tarefa cancelada); os ramos
    # dentro de ler_e_reencaminhar substituem-no pelo resultado real.
    resultado_execucao = "Ligação terminada antes da execução acabar"

    await _adquirir_vaga_de_execucao(websocket)
    try:
        await websocket.send_json({"tipo": "compilado"})
        execucao = executor.ExecucaoInterativa(caminho_py, pasta_estudante)
        await execucao.iniciar()

        async def enviar_linha(linha: str):
            await websocket.send_json({"tipo": "saida", "texto": linha})

        async def ler_e_reencaminhar():
            nonlocal resultado_execucao
            try:
                await executor.correr_com_limite_de_tempo(execucao, enviar_linha)
                await websocket.send_json({"tipo": "fim", "codigo_saida": execucao.codigo_saida})
                resultado_execucao = (
                    "Sucesso" if execucao.codigo_saida == 0
                    else f"Terminou com código de saída {execucao.codigo_saida}"
                )
            except TimeoutError:
                resultado_execucao = "Interrompida: excedeu o tempo limite (possível ciclo infinito)"
                await websocket.send_json({
                    "tipo": "erro",
                    # UX-18: uniformizado com o aviso equivalente da consola
                    # (cli.py, modo --debug/--json), que já nomeia esta causa provável.
                    "mensagem": "Execução interrompida: excedeu o tempo limite (possível ciclo infinito).",
                })
            except executor.SaidaExcessiva:
                resultado_execucao = "Interrompida: linha de saída demasiado longa"
                await websocket.send_json({
                    "tipo": "erro",
                    "mensagem": "Execução interrompida: produziu uma linha de saída demasiado longa.",
                })

        tarefa_leitura = asyncio.create_task(ler_e_reencaminhar())

        # Um programa sem nenhum ler() nunca manda o browser escrever nada
        # neste WebSocket -- 'await websocket.receive_json()' sozinho ficaria
        # bloqueado para sempre depois do "fim"/"erro". Isso prendia esta
        # ligação -- e a vaga que ocupa em _semaforo_execucoes -- até o
        # browser a fechar por conta própria no PRÓXIMO clique em
        # Executar/Debug, esgotando aos poucos o semáforo partilhado.
        # Corrida entre receber e a tarefa de leitura acabar, para sair
        # assim que a execução terminar mesmo sem entrada.
        #
        # A condição do while é 'not tarefa_leitura.done()', NÃO
        # 'not execucao.terminou' -- um programa muito rápido (ex.: um
        # único 'escrever()') pode marcar execucao.terminou=True antes
        # mesmo desta função chegar a correr o corpo do while uma única
        # vez. Com 'execucao.terminou' como condição, esse caso saltava o
        # while por completo e cancelava tarefa_leitura no finally ANTES
        # dela ter sequer arrancado -- perdendo o "saida"/"fim" que ainda
        # estava para ser reencaminhado (o browser via "compilado" e
        # nada mais, para sempre). tarefa_leitura.done() só fica True
        # depois de ela já ter mandado esse último evento ao websocket.
        try:
            while not tarefa_leitura.done():
                tarefa_receber = asyncio.create_task(websocket.receive_json())
                concluidas, _ = await asyncio.wait(
                    {tarefa_receber, tarefa_leitura}, return_when=asyncio.FIRST_COMPLETED)
                if tarefa_receber not in concluidas:
                    tarefa_receber.cancel()
                    break
                mensagem = tarefa_receber.result()
                if mensagem.get("tipo") == "entrada":
                    await execucao.enviar_entrada(mensagem.get("valor", ""))
        except WebSocketDisconnect:
            await execucao.terminar_a_forcar()
        finally:
            if not tarefa_leitura.done():
                tarefa_leitura.cancel()
            await execucao.terminar_a_forcar()
    finally:
        _semaforo_execucoes.release()
        await _registar_execucao_com_seguranca(
            id_estudante, "executa", nome_principal, ficheiros, resultado_execucao)


# ---------- WebSocket: rasto ao vivo (--debug interativo) ----------
#
# Peça isolada de propósito -- ver a nota no topo de
# online/executor.py:ExecucaoComDebugAoVivo. Reaproveita o mesmo
# _semaforo_execucoes que /ws/executar (mesmo orçamento de execuções
# concorrentes, não um limite paralelo à parte), mas não toca em mais
# nada de /ws/executar.

@app.websocket("/ws/debug")
async def ws_debug(websocket: WebSocket):
    await websocket.accept()
    id_estudante = _id_estudante_do_websocket(websocket)
    if id_estudante is None:
        await websocket.send_json({"tipo": "erro", "mensagem": "Não autenticado."})
        await websocket.close()
        return

    pseudonimo = await run_in_threadpool(autenticacao.obter_id_pseudonimo, id_estudante)
    pasta_estudante = executor.preparar_pasta_execucao(pseudonimo)

    try:
        mensagem_inicial = await websocket.receive_json()
    except WebSocketDisconnect:
        return

    ficheiros = mensagem_inicial.get("ficheiros", [])
    nome_principal = mensagem_inicial.get("principal", "")
    try:
        dados_compilados = executor.preparar_debug_ao_vivo(ficheiros, nome_principal, pasta_estudante)
    except executor.ErroCompilacao as e:
        await _registar_execucao_com_seguranca(
            id_estudante, "debug", nome_principal, ficheiros, f"Erro de compilação: {e}")
        await websocket.send_json({"tipo": "erro_compilacao", "mensagem": str(e)})
        await websocket.close()
        return

    # Ver o mesmo comentário em ws_executar -- valor por omissão para
    # as saídas que nunca chegam a um evento "fim"/"erro" claro.
    resultado_execucao = "Ligação terminada antes da execução acabar"

    await _adquirir_vaga_de_execucao(websocket)
    try:
        await websocket.send_json({"tipo": "compilado"})
        execucao = executor.ExecucaoComDebugAoVivo(dados_compilados, pasta_estudante)
        execucao.iniciar()

        async def ler_e_reencaminhar():
            nonlocal resultado_execucao
            while True:
                evento = await execucao.proximo_evento()
                await websocket.send_json(evento)
                if evento.get("tipo") == "fim":
                    resultado_execucao = "Sucesso"
                    break
                if evento.get("tipo") == "erro":
                    resultado_execucao = f"Erro em execução: {evento.get('mensagem', '')}"
                    break

        tarefa_leitura = asyncio.create_task(ler_e_reencaminhar())

        # Ver o mesmo comentário em ws_executar acima -- idêntico aqui: sem
        # a corrida entre receber e a tarefa de leitura, um programa sem
        # ler() prendia esta ligação (e a vaga que ocupa) para sempre depois
        # do "fim"/"erro". E a condição tem de ser 'not tarefa_leitura.done()',
        # não 'not execucao.terminou' -- um programa muito rápido marca
        # execucao.terminou=True antes desta função sequer chegar a correr,
        # o que cancelava tarefa_leitura no finally SEM ela ter mandado
        # "saida"/"fim" nenhum (o browser ficava preso em "compilado").
        try:
            while not tarefa_leitura.done():
                tarefa_receber = asyncio.create_task(websocket.receive_json())
                concluidas, _ = await asyncio.wait(
                    {tarefa_receber, tarefa_leitura}, return_when=asyncio.FIRST_COMPLETED)
                if tarefa_receber not in concluidas:
                    tarefa_receber.cancel()
                    break
                mensagem = tarefa_receber.result()
                if mensagem.get("tipo") == "entrada":
                    execucao.enviar_entrada(mensagem.get("valor", ""))
        except WebSocketDisconnect:
            execucao.terminar_a_forcar()
        finally:
            if not tarefa_leitura.done():
                tarefa_leitura.cancel()
            execucao.terminar_a_forcar()
    finally:
        _semaforo_execucoes.release()
        await _registar_execucao_com_seguranca(
            id_estudante, "debug", nome_principal, ficheiros, resultado_execucao)


# ---------- WebSocket: conversa com o Alguem ----------

@app.websocket("/ws/alguem")
async def ws_alguem(websocket: WebSocket):
    await websocket.accept()
    if not await run_in_threadpool(definicoes.alguem_ativo):
        await websocket.send_json({
            "tipo": "erro", "mensagem": "O Alguem está temporariamente desativado.", "acionavel": False})
        await websocket.close()
        return
    id_estudante = _id_estudante_do_websocket(websocket)
    if id_estudante is None:
        await websocket.send_json({"tipo": "erro", "mensagem": "Não autenticado.", "acionavel": False})
        await websocket.close()
        return
    if await run_in_threadpool(grupos.grupo_bloqueia_alguem, id_estudante):
        await websocket.send_json({
            "tipo": "erro", "mensagem": "O Alguem está desativado para o teu grupo.", "acionavel": False})
        await websocket.close()
        return

    try:
        tutor = await run_in_threadpool(alguem_ponte.construir_alguem, id_estudante)
    except alguem_ponte.ErroAlguemIndisponivel as e:
        await websocket.send_json({"tipo": "erro", "mensagem": str(e), "acionavel": e.acionavel})
        await websocket.close()
        return

    await websocket.send_json({
        "tipo": "pronto",
        "mensagem": "Olá! Sou o Alguem, o teu tutor de algoritmia. Em que posso ajudar-te?",
    })

    # ARCH-09: fechar_sessao() tem de correr para QUALQUER saída deste
    # bloco, não só WebSocketDisconnect -- caso contrário uma exceção
    # inesperada (ex: JSON malformado em receive_json) deixa o ficheiro
    # de log aberto e nunca escreve o evento fim_sessao, ao contrário
    # do que algo_lang/cli.py já faz com try/finally.
    try:
        while True:
            dados = await websocket.receive_json()
            if dados.get("tipo") == "ficheiro":
                ficheiros_recebidos = dados.get("ficheiros", [])
                ficheiros_visiveis = alguem_ponte.limitar_ficheiros_visiveis(
                    [(f["nome"], f["conteudo"]) for f in ficheiros_recebidos])
                tutor.considerar_ficheiros(ficheiros_visiveis)
                continue
            mensagem_estudante = dados.get("texto", "")
            if not mensagem_estudante:
                continue
            try:
                resposta = tutor.conversar(mensagem_estudante)
                await websocket.send_json({"tipo": "resposta", "texto": resposta})
            except ErroFornecedorLLM as e:
                await websocket.send_json({"tipo": "erro", "mensagem": str(e)})
    except WebSocketDisconnect:
        pass
    finally:
        tutor.fechar_sessao()


# ---------- fluxograma e rasto (execução não-interativa, entradas antecipadas) ----------

@app.post("/api/fluxograma")
async def rota_fluxograma(request: Request, pasta_estudante: str = Depends(pasta_execucao_atual)):
    dados = await corpo_json(request)
    try:
        # ON-08: gerar_fluxograma_svg chama o binário 'dot' (graphviz) de
        # forma síncrona e bloqueante -- sem isto, travava o event loop
        # (e por extensão o servidor inteiro) durante a chamada.
        resultado = await run_in_threadpool(
            executor.gerar_fluxograma_svg,
            dados.get("ficheiros", []), dados.get("principal", ""), pasta_estudante,
            nome_rotina=dados.get("rotina"))
    except executor.ErroCompilacao as e:
        raise HTTPException(status_code=400, detail=str(e))
    except executor.ErroFluxograma as e:
        raise HTTPException(status_code=503, detail=str(e))
    return resultado


@app.post("/api/linter")
async def rota_linter(request: Request, pasta_estudante: str = Depends(pasta_execucao_atual)):
    dados = await corpo_json(request)
    try:
        avisos = executor.analisar_linter(
            dados.get("ficheiros", []), dados.get("principal", ""), pasta_estudante)
    except executor.ErroCompilacao as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"avisos": avisos}


@app.post("/api/rasto")
async def rota_rasto(request: Request, pasta_estudante: str = Depends(pasta_execucao_atual)):
    dados = await corpo_json(request)
    try:
        rasto = executor.gerar_rasto(
            dados.get("ficheiros", []), dados.get("principal", ""),
            dados.get("entradas", []), pasta_estudante)
    except executor.ErroCompilacao as e:
        raise HTTPException(status_code=400, detail=str(e))
    except executor.ErroRasto as e:
        raise HTTPException(status_code=500, detail=str(e))
    return rasto


# ---------- projeto: descarregar/abrir como .zip (sem persistência em BD) ----------

@app.post("/api/projeto/download")
async def rota_descarregar_projeto(request: Request, id_estudante: int = Depends(estudante_atual)):
    dados = await corpo_json(request)
    try:
        conteudo_zip = await run_in_threadpool(projeto.construir_zip_do_projeto, dados.get("ficheiros", []))
    except projeto.ErroProjeto as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(
        content=conteudo_zip,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="projeto.zip"'},
    )


@app.post("/api/projeto/upload")
async def rota_abrir_projeto(ficheiro: UploadFile = File(...), id_estudante: int = Depends(estudante_atual)):
    conteudo_zip = await ficheiro.read()
    try:
        ficheiros = await run_in_threadpool(projeto.extrair_zip_do_projeto, conteudo_zip)
    except projeto.ErroProjeto as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ficheiros": ficheiros}
