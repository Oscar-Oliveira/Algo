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
import grupos
import limitador_registo
import modo_codemirror
import cifragem
import credenciais
import executor
import projeto
import relatorios
import alguem_ponte
from alguem.fornecedores.base import ErroFornecedorLLM
from alguem.scripts import metricas
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

# exemplos/ vive na raiz do repositório (irmã de algo_lang/, alguem/,
# online/), não dentro de online/ -- por isso não pode ser montada como
# PASTA_ESTATICO. A rota /api/exemplos lê-a diretamente do disco a cada
# pedido (tal como /modo-algo.js lê o lexer a cada pedido), para nunca
# divergir do conteúdo real da pasta.
PASTA_EXEMPLOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exemplos")

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
async def rota_admin_pendentes(id_estudante: int = Depends(admin_atual)):
    return {"pendentes": await run_in_threadpool(autenticacao.listar_pendentes)}


@app.post("/api/admin/aprovar/{id_estudante_alvo}")
async def rota_admin_aprovar(id_estudante_alvo: int, id_estudante: int = Depends(admin_atual)):
    await run_in_threadpool(autenticacao.aprovar_conta, id_estudante_alvo)
    await run_in_threadpool(atividade.registar_evento, "conta_aprovada", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/rejeitar/{id_estudante_alvo}")
async def rota_admin_rejeitar(id_estudante_alvo: int, id_estudante: int = Depends(admin_atual)):
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
async def rota_admin_utilizadores(id_estudante: int = Depends(admin_atual)):
    return {"utilizadores": await run_in_threadpool(autenticacao.listar_todos)}


@app.post("/api/admin/revogar/{id_estudante_alvo}")
async def rota_admin_revogar(id_estudante_alvo: int, id_estudante: int = Depends(admin_atual)):
    if id_estudante_alvo == id_estudante:
        raise HTTPException(status_code=400, detail="Não podes revogar a tua própria conta.")
    await run_in_threadpool(autenticacao.revogar_conta, id_estudante_alvo)
    await run_in_threadpool(atividade.registar_evento, "conta_revogada", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/tornar_admin/{id_estudante_alvo}")
async def rota_admin_tornar_admin(id_estudante_alvo: int, id_estudante: int = Depends(admin_atual)):
    await run_in_threadpool(autenticacao.tornar_admin, id_estudante_alvo)
    await run_in_threadpool(atividade.registar_evento, "admin_concedido", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/remover_admin/{id_estudante_alvo}")
async def rota_admin_remover_admin(id_estudante_alvo: int, id_estudante: int = Depends(admin_atual)):
    if id_estudante_alvo == id_estudante:
        raise HTTPException(status_code=400, detail="Não podes remover os teus próprios privilégios de admin.")
    alterou = await run_in_threadpool(autenticacao.remover_admin, id_estudante_alvo, id_estudante)
    if not alterou:
        raise HTTPException(
            status_code=400,
            detail="Não é possível remover: teria de sobrar pelo menos um administrador ativo.",
        )
    await run_in_threadpool(atividade.registar_evento, "admin_revogado", id_estudante, id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/utilizadores/{id_estudante_alvo}/grupo")
async def rota_admin_reatribuir_grupo(id_estudante_alvo: int, request: Request,
                                       id_estudante: int = Depends(admin_atual)):
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
async def rota_admin_listar_grupos(id_estudante: int = Depends(admin_atual)):
    return {"grupos": await run_in_threadpool(grupos.listar_grupos)}


@app.post("/api/admin/grupos")
async def rota_admin_criar_grupo(request: Request, id_estudante: int = Depends(admin_atual)):
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
async def rota_admin_editar_grupo(grupo_id: int, request: Request, id_estudante: int = Depends(admin_atual)):
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
async def rota_admin_ativar_grupo(grupo_id: int, id_estudante: int = Depends(admin_atual)):
    await run_in_threadpool(grupos.ativar_grupo, grupo_id)
    await run_in_threadpool(atividade.registar_evento, "grupo_ativado", id_estudante, None, grupo_id)
    return {"ok": True}


@app.post("/api/admin/grupos/{grupo_id}/desativar")
async def rota_admin_desativar_grupo(grupo_id: int, id_estudante: int = Depends(admin_atual)):
    await run_in_threadpool(grupos.desativar_grupo, grupo_id)
    await run_in_threadpool(atividade.registar_evento, "grupo_desativado", id_estudante, None, grupo_id)
    return {"ok": True}


@app.post("/api/admin/grupos/{grupo_id}/apagar")
async def rota_admin_apagar_grupo(grupo_id: int, id_estudante: int = Depends(admin_atual)):
    try:
        await run_in_threadpool(grupos.apagar_grupo, grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=400, detail=str(e))
    await run_in_threadpool(atividade.registar_evento, "grupo_eliminado", id_estudante, None, grupo_id)
    return {"ok": True}


@app.get("/api/admin/grupos/{grupo_id}/codigo")
async def rota_admin_ver_codigo_grupo(grupo_id: int, id_estudante: int = Depends(admin_atual)):
    try:
        codigo = await run_in_threadpool(grupos.ver_codigo, grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"codigo": codigo}


@app.post("/api/admin/grupos/{grupo_id}/regenerar_codigo")
async def rota_admin_regenerar_codigo_grupo(grupo_id: int, id_estudante: int = Depends(admin_atual)):
    try:
        codigo = await run_in_threadpool(grupos.regenerar_codigo, grupo_id)
    except grupos.ErroGrupo as e:
        raise HTTPException(status_code=404, detail=str(e))
    await run_in_threadpool(atividade.registar_evento, "grupo_editado", id_estudante, None, grupo_id,
                             {"acao": "codigo_regenerado"})
    return {"codigo": codigo}


@app.get("/api/admin/grupos/{grupo_id}/membros.csv")
async def rota_admin_exportar_membros_csv(grupo_id: int, id_estudante: int = Depends(admin_atual)):
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
async def rota_admin_listar_log(id_estudante: int = Depends(admin_atual),
                                 estudante_id: int | None = None, grupo_id: int | None = None,
                                 tipo: str | None = None, data_inicio: str | None = None,
                                 data_fim: str | None = None, pagina: int = 1):
    return await run_in_threadpool(
        atividade.listar_eventos, estudante_id, grupo_id, tipo, data_inicio, data_fim, pagina)


@app.post("/api/admin/log/apagar")
async def rota_admin_apagar_log(request: Request, id_estudante: int = Depends(admin_atual)):
    dados = await corpo_json(request)
    ids = dados.get("ids", [])
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise HTTPException(status_code=400, detail="'ids' tem de ser uma lista de inteiros.")
    apagados = await run_in_threadpool(atividade.apagar_eventos, ids)
    return {"ok": True, "apagados": apagados}


@app.get("/api/admin/log.csv")
async def rota_admin_exportar_log_csv(id_estudante: int = Depends(admin_atual),
                                       estudante_id: int | None = None, grupo_id: int | None = None,
                                       tipo: str | None = None, data_inicio: str | None = None,
                                       data_fim: str | None = None):
    csv_texto = await run_in_threadpool(
        atividade.exportar_csv, estudante_id, grupo_id, tipo, data_inicio, data_fim)
    return Response(
        content=csv_texto, media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="atividade.csv"'},
    )


# ---------- administração: atividade/métricas dos logs do Alguem ----------

@app.get("/api/admin/atividade")
async def rota_admin_atividade(id_estudante: int = Depends(admin_atual)):
    # Lê a pasta de logs do módulo registador, não a constante (idêntica
    # em produção) do próprio metricas -- é aquele módulo que o
    # alguem_ponte usa de facto para escrever os logs, e os testes já
    # isolam esse caminho com monkeypatch (ver tests/conftest.py).
    return metricas.gerar_relatorio(registador_alguem.PASTA_LOGS_POR_OMISSAO)


# ---------- administração: relatórios de problemas enviados por estudantes ----------

@app.get("/api/admin/relatorios")
async def rota_admin_relatorios(id_estudante: int = Depends(admin_atual)):
    return {"relatorios": await run_in_threadpool(relatorios.listar_relatorios)}


@app.post("/api/admin/relatorios/apagar/{id_relatorio}")
async def rota_admin_apagar_relatorio(id_relatorio: int, id_estudante: int = Depends(admin_atual)):
    await run_in_threadpool(relatorios.apagar_relatorio, id_relatorio)
    return {"ok": True}


# ---------- administração: descarregar a base de dados para backup ----------

@app.get("/api/admin/bd")
async def rota_admin_descarregar_bd(tarefas: BackgroundTasks, id_estudante: int = Depends(admin_atual)):
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
    nome_ficheiro = f"algo-online-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.sql"
    return FileResponse(
        caminho_copia,
        media_type="application/sql",
        filename=nome_ficheiro,
        background=tarefas,
    )


# ---------- credenciais de LLM ----------

@app.get("/api/credencial")
async def rota_obter_credencial(id_estudante: int = Depends(estudante_atual)):
    """Nunca devolve a chave de API -- só o que é seguro mostrar de
    volta ao estudante para confirmar o que já tem configurado."""
    c = await run_in_threadpool(credenciais.obter_credencial, id_estudante)
    if c is None:
        return {"configurado": False}
    return {"configurado": True, "fornecedor": c.fornecedor, "modelo": c.modelo, "host": c.host}


@app.post("/api/credencial")
async def rota_guardar_credencial(request: Request, id_estudante: int = Depends(estudante_atual)):
    dados = await corpo_json(request)
    try:
        await run_in_threadpool(
            credenciais.guardar_credencial,
            id_estudante,
            dados.get("fornecedor", ""),
            dados.get("modelo", ""),
            dados.get("api_key", ""),
            host=dados.get("host") or None,
        )
    except credenciais.ErroCredencial as e:
        raise HTTPException(status_code=400, detail=str(e))
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

# TEMP: alguem desativado enquanto se corrige o editor -- reativar
# trocando para True (o frontend também tem de reativar ALGUEM_ATIVO
# em online/estatico/app.js).
ALGUEM_ATIVO = False


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
        await websocket.send_json({"tipo": "erro_compilacao", "mensagem": str(e)})
        await websocket.close()
        return

    await _adquirir_vaga_de_execucao(websocket)
    try:
        await websocket.send_json({"tipo": "compilado"})
        execucao = executor.ExecucaoInterativa(caminho_py, pasta_estudante)
        await execucao.iniciar()

        async def enviar_linha(linha: str):
            await websocket.send_json({"tipo": "saida", "texto": linha})

        async def ler_e_reencaminhar():
            try:
                await executor.correr_com_limite_de_tempo(execucao, enviar_linha)
                await websocket.send_json({"tipo": "fim", "codigo_saida": execucao.codigo_saida})
            except TimeoutError:
                await websocket.send_json({
                    "tipo": "erro",
                    # UX-18: uniformizado com o aviso equivalente da consola
                    # (cli.py, modo --debug/--json), que já nomeia esta causa provável.
                    "mensagem": "Execução interrompida: excedeu o tempo limite (possível ciclo infinito).",
                })
            except executor.SaidaExcessiva:
                await websocket.send_json({
                    "tipo": "erro",
                    "mensagem": "Execução interrompida: produziu uma linha de saída demasiado longa.",
                })

        tarefa_leitura = asyncio.create_task(ler_e_reencaminhar())

        try:
            while not execucao.terminou:
                mensagem = await websocket.receive_json()
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


# ---------- WebSocket: conversa com o Alguem ----------

@app.websocket("/ws/alguem")
async def ws_alguem(websocket: WebSocket):
    await websocket.accept()
    if not ALGUEM_ATIVO:
        await websocket.send_json({"tipo": "erro", "mensagem": "O Alguem está temporariamente desativado."})
        await websocket.close()
        return
    id_estudante = _id_estudante_do_websocket(websocket)
    if id_estudante is None:
        await websocket.send_json({"tipo": "erro", "mensagem": "Não autenticado."})
        await websocket.close()
        return

    try:
        tutor = await run_in_threadpool(alguem_ponte.construir_alguem, id_estudante)
    except alguem_ponte.ErroAlguemIndisponivel as e:
        await websocket.send_json({"tipo": "erro", "mensagem": str(e)})
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
