# -*- coding: utf-8 -*-
"""Aplicação FastAPI do Algo/Alguem online. Deliberadamente sem
grandes frameworks: sem ORM (sqlite3 puro, ver bd.py), sem sistema de
templates (HTML servido tal e qual da pasta estatico/), sessão via
SessionMiddleware do próprio Starlette (cookie assinado, sem tabela de
sessões na base de dados)."""
from __future__ import annotations

import os

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from contextlib import asynccontextmanager

import bd
import autenticacao
import modo_codemirror
import cifragem
import credenciais
import executor
import alguem_ponte
from alguem.fornecedores.base import ErroFornecedorLLM

PASTA_ESTATICO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estatico")


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
app.add_middleware(SessionMiddleware, secret_key=_chave_sessao, https_only=False)

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
    Agora qualquer erro não tratado devolve sempre JSON."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno do servidor: {exc}"},
    )


# ---------- autenticação ----------

def estudante_atual(request: Request) -> int:
    """Dependência: lê o id da conta a partir da sessão (cookie
    assinado). 401 se não houver sessão válida."""
    id_estudante = request.session.get("id_estudante")
    if id_estudante is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return id_estudante


def admin_atual(id_estudante: int = Depends(estudante_atual)) -> int:
    """Dependência: como estudante_atual, mas exige também que a conta
    seja admin (ver autenticacao.eh_admin) -- 403 caso contrário."""
    if not autenticacao.eh_admin(id_estudante):
        raise HTTPException(status_code=403, detail="Só administradores podem aceder a isto.")
    return id_estudante


@app.post("/api/registar")
async def rota_registar(request: Request):
    dados = await request.json()
    try:
        id_estudante = autenticacao.registar(dados.get("email", ""), dados.get("password", ""))
    except autenticacao.ErroAutenticacao as e:
        raise HTTPException(status_code=400, detail=str(e))
    aprovado = autenticacao.esta_aprovado(id_estudante)
    if aprovado:
        request.session["id_estudante"] = id_estudante
    return {"ok": True, "pendente": not aprovado}


@app.post("/api/entrar")
async def rota_entrar(request: Request):
    dados = await request.json()
    try:
        id_estudante = autenticacao.autenticar(dados.get("email", ""), dados.get("password", ""))
    except autenticacao.ErroAutenticacao as e:
        raise HTTPException(status_code=401, detail=str(e))
    request.session["id_estudante"] = id_estudante
    return {"ok": True}


@app.post("/api/sair")
async def rota_sair(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/eu")
async def rota_eu(id_estudante: int = Depends(estudante_atual)):
    """Usado pelo frontend só para decidir se mostra a ligação para o
    painel de admin -- não devolve mais nada sobre a conta."""
    return {"admin": autenticacao.eh_admin(id_estudante)}


# ---------- administração: aprovar/rejeitar contas pendentes ----------

@app.get("/api/admin/pendentes")
async def rota_admin_pendentes(id_estudante: int = Depends(admin_atual)):
    return {"pendentes": autenticacao.listar_pendentes()}


@app.post("/api/admin/aprovar/{id_estudante_alvo}")
async def rota_admin_aprovar(id_estudante_alvo: int, id_estudante: int = Depends(admin_atual)):
    autenticacao.aprovar_conta(id_estudante_alvo)
    return {"ok": True}


@app.post("/api/admin/rejeitar/{id_estudante_alvo}")
async def rota_admin_rejeitar(id_estudante_alvo: int, id_estudante: int = Depends(admin_atual)):
    autenticacao.rejeitar_conta(id_estudante_alvo)
    return {"ok": True}


# ---------- credenciais de LLM ----------

@app.get("/api/credencial")
async def rota_obter_credencial(id_estudante: int = Depends(estudante_atual)):
    """Nunca devolve a chave de API -- só o que é seguro mostrar de
    volta ao estudante para confirmar o que já tem configurado."""
    c = credenciais.obter_credencial(id_estudante)
    if c is None:
        return {"configurado": False}
    return {"configurado": True, "fornecedor": c.fornecedor, "modelo": c.modelo, "host": c.host}


@app.post("/api/credencial")
async def rota_guardar_credencial(request: Request, id_estudante: int = Depends(estudante_atual)):
    dados = await request.json()
    try:
        credenciais.guardar_credencial(
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
    return FileResponse(os.path.join(PASTA_ESTATICO, "editor.html"))


@app.get("/admin")
async def pagina_admin(request: Request):
    id_estudante = request.session.get("id_estudante")
    if id_estudante is None or not autenticacao.eh_admin(id_estudante):
        return RedirectResponse("/editor")
    return FileResponse(os.path.join(PASTA_ESTATICO, "admin.html"))


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


@app.websocket("/ws/executar")
async def ws_executar(websocket: WebSocket):
    await websocket.accept()
    id_estudante = _id_estudante_do_websocket(websocket)
    if id_estudante is None:
        await websocket.send_json({"tipo": "erro", "mensagem": "Não autenticado."})
        await websocket.close()
        return

    pseudonimo = autenticacao.obter_id_pseudonimo(id_estudante)
    pasta_estudante = executor.preparar_pasta_estudante(pseudonimo)

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
                "mensagem": "Execução interrompida: excedeu o tempo limite.",
            })

    tarefa_leitura = None
    import asyncio
    tarefa_leitura = asyncio.create_task(ler_e_reencaminhar())

    try:
        while not execucao.terminou:
            mensagem = await websocket.receive_json()
            if mensagem.get("tipo") == "entrada":
                await execucao.enviar_entrada(mensagem.get("valor", ""))
    except WebSocketDisconnect:
        await execucao.terminar_a_forcar()
    finally:
        if tarefa_leitura is not None and not tarefa_leitura.done():
            tarefa_leitura.cancel()
        await execucao.terminar_a_forcar()


# ---------- WebSocket: conversa com o Alguem ----------

@app.websocket("/ws/alguem")
async def ws_alguem(websocket: WebSocket):
    await websocket.accept()
    id_estudante = _id_estudante_do_websocket(websocket)
    if id_estudante is None:
        await websocket.send_json({"tipo": "erro", "mensagem": "Não autenticado."})
        await websocket.close()
        return

    try:
        tutor = alguem_ponte.construir_alguem(id_estudante)
    except alguem_ponte.ErroAlguemIndisponivel as e:
        await websocket.send_json({"tipo": "erro", "mensagem": str(e)})
        await websocket.close()
        return

    await websocket.send_json({
        "tipo": "pronto",
        "mensagem": "Olá! Sou o Alguem, o teu tutor de algoritmia. Em que posso ajudar-te?",
    })

    try:
        while True:
            dados = await websocket.receive_json()
            if dados.get("tipo") == "ficheiro":
                ficheiros_recebidos = dados.get("ficheiros", [])
                tutor.considerar_ficheiros(
                    [(f["nome"], f["conteudo"]) for f in ficheiros_recebidos])
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
        tutor.fechar_sessao()


# ---------- fluxograma e rasto (execução não-interativa, entradas antecipadas) ----------

@app.post("/api/fluxograma")
async def rota_fluxograma(request: Request, id_estudante: int = Depends(estudante_atual)):
    dados = await request.json()
    pseudonimo = autenticacao.obter_id_pseudonimo(id_estudante)
    pasta_estudante = executor.preparar_pasta_estudante(pseudonimo)
    try:
        resultado = executor.gerar_fluxograma_svg(
            dados.get("ficheiros", []), dados.get("principal", ""), pasta_estudante,
            nome_rotina=dados.get("rotina"))
    except executor.ErroCompilacao as e:
        raise HTTPException(status_code=400, detail=str(e))
    except executor.ErroFluxograma as e:
        raise HTTPException(status_code=503, detail=str(e))
    return resultado


@app.post("/api/rasto")
async def rota_rasto(request: Request, id_estudante: int = Depends(estudante_atual)):
    dados = await request.json()
    pseudonimo = autenticacao.obter_id_pseudonimo(id_estudante)
    pasta_estudante = executor.preparar_pasta_estudante(pseudonimo)
    try:
        rasto = executor.gerar_rasto(
            dados.get("ficheiros", []), dados.get("principal", ""),
            dados.get("entradas", []), pasta_estudante)
    except executor.ErroCompilacao as e:
        raise HTTPException(status_code=400, detail=str(e))
    except executor.ErroRasto as e:
        raise HTTPException(status_code=500, detail=str(e))
    return rasto
