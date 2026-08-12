# -*- coding: utf-8 -*-
import asyncio
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

import bd
import main
import autenticacao
import executor


@pytest.fixture
def cliente():
    with TestClient(main.app) as c:
        yield c


def _msg(codigo, nome="principal.algo"):
    """Atalho: a maioria dos testes só precisa de UM ficheiro -- monta
    a mensagem no formato multi-ficheiro que os endpoints esperam."""
    return {"ficheiros": [{"nome": nome, "conteudo": codigo}], "principal": nome}


def _resposta_llm_falsa(texto):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(
        {"choices": [{"message": {"content": texto}}]}).encode()
    return cm


# ---------- UX-11: visualizador de rasto sem dependência de CDN externo ----------

def test_visualizador_de_rasto_nao_referencia_cdn_externo(cliente):
    r = cliente.get("/estatico/visualizador/algo-trace-viewer.html")
    assert r.status_code == 200
    conteudo = r.text
    assert "unpkg.com" not in conteudo
    assert "cdn.tailwindcss.com" not in conteudo
    assert '<script src="../vendor/tracer/react.development.js"' in conteudo


def test_visualizador_de_rasto_vendor_files_acessiveis(cliente):
    for nome in ("react.development.js", "react-dom.development.js",
                 "babel.min.js", "tailwind.js"):
        r = cliente.get(f"/estatico/vendor/tracer/{nome}")
        assert r.status_code == 200, nome


# ---------- UX-12: painel do Alguem visível por omissão ----------

def test_painel_do_alguem_nao_e_escondido_ao_carregar(cliente):
    """Antes, app.js chamava alternarPainelAlguem() logo no arranque só
    para o esconder -- um estudante novo na web podia nunca descobrir
    que o tutor existe. Sem teste de browser disponível neste projeto
    (sem framework de testes JS), confirma-se ao nível do conteúdo
    servido que essa chamada de arranque já não existe."""
    r = cliente.get("/estatico/app.js")
    assert r.status_code == 200
    assert "alternarPainelAlguem(); // painel do Alguem começa escondido" not in r.text


# ---------- UX-13: indicador "a pensar..." no chat ----------

def test_app_js_tem_indicador_de_a_pensar(cliente):
    """Sem teste de browser disponível, confirma-se ao nível do
    conteúdo servido que a lógica do indicador existe e está ligada ao
    envio de mensagens e à receção de resposta/erro."""
    r = cliente.get("/estatico/app.js")
    assert r.status_code == 200
    assert "mostrarIndicadorAPensar" in r.text
    assert "esconderIndicadorAPensar" in r.text


# ---------- UX-14: input desativado + link para Definições sem credencial ----------

def test_app_js_desativa_entrada_alguem_quando_falta_credencial(cliente):
    """Antes, se faltasse credencial LLM o servidor enviava "erro" e
    fechava o socket, e depois disso escrever e submeter no chat não
    fazia absolutamente nada, sem novo aviso nem estado desativado
    visível. Sem teste de browser disponível, confirma-se ao nível do
    conteúdo servido que a entrada é desativada e que existe um link
    persistente para Definições nesse caso."""
    r = cliente.get("/estatico/app.js")
    assert r.status_code == 200
    assert "desativarEntradaAlguem" in r.text
    assert "ativarEntradaAlguem" in r.text
    assert "if (!alguemPronto) desativarEntradaAlguem();" in r.text

    editor_html = (Path(__file__).parent.parent / "paginas_privadas" / "editor.html").read_text(encoding="utf-8")
    assert 'id="aviso-credencial-alguem"' in editor_html
    assert 'id="botao-ir-definicoes"' in editor_html


# ---------- UX-15: marcador de erro no gutter do CodeMirror ----------

def test_app_js_marca_erro_de_compilacao_no_editor(cliente):
    """Antes, um erro de compilação só aparecia como texto no
    terminal, sem nenhum marcador na margem do CodeMirror nem
    "clicar para saltar para a linha". Sem teste de browser
    disponível, confirma-se ao nível do conteúdo servido que a lógica
    de marcação/salto existe e está ligada à receção de
    "erro_compilacao"."""
    r = cliente.get("/estatico/app.js")
    assert r.status_code == 200
    assert "marcarErroNoEditor" in r.text
    assert "limparMarcadorDeErro" in r.text
    assert '"gutter-erro"' in r.text
    assert "escreverErroCompilacaoNoTerminal(dados.mensagem);\n      marcarErroNoEditor(dados.mensagem);" in r.text


# ---------- UX-16: rótulos de texto na barra de ferramentas principal ----------

def test_botoes_principais_da_toolbar_tem_rotulo_de_texto():
    """Antes, Executar/Fluxograma/Rasto/Verificador eram só ícones SVG
    com 'title' como único rótulo -- pouco descobrível, e tooltips não
    aparecem de forma fiável em dispositivos táteis."""
    editor_html = (Path(__file__).parent.parent / "paginas_privadas" / "editor.html").read_text(encoding="utf-8")
    for id_botao, rotulo in [
        ("botao-executar", "Executar"),
        ("botao-fluxograma", "Fluxograma"),
        ("botao-rasto", "Rasto"),
        ("botao-linter", "Verificador"),
    ]:
        inicio = editor_html.index(f'id="{id_botao}"')
        fim = editor_html.index("</button>", inicio)
        assert f'<span class="rotulo-botao">{rotulo}</span>' in editor_html[inicio:fim]


# ---------- páginas e sessão ----------

def test_pagina_inicial_sem_sessao(cliente):
    r = cliente.get("/", follow_redirects=False)
    assert r.status_code == 200


def test_editor_sem_sessao_redireciona(cliente):
    r = cliente.get("/editor", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/"


def test_paginas_com_guarda_de_sessao_nao_sao_acessiveis_via_pasta_estatica(cliente):
    """ON-21: editor.html/ajuda.html/admin.html não podem estar na
    pasta montada publicamente (/estatico/...) -- isso contornava por
    completo a verificação de sessão das rotas /editor, /ajuda, /admin."""
    for nome in ("editor.html", "ajuda.html", "admin.html"):
        r = cliente.get(f"/estatico/{nome}")
        assert r.status_code == 404


def test_registar_da_acesso_ao_editor(cliente):
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    r = cliente.get("/editor")
    assert r.status_code == 200


def test_ajuda_sem_sessao_redireciona(cliente):
    r = cliente.get("/ajuda", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/"


def test_registar_da_acesso_a_ajuda(cliente):
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    r = cliente.get("/ajuda")
    assert r.status_code == 200


def test_ajuda_explica_os_tres_tipos_de_erro_de_compilacao(cliente):
    """UX-05: o manual tem de explicar a diferença entre erro léxico/
    sintático/semântico, para quem lê a mensagem de erro sem saber o
    que esses termos significam."""
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.get("/ajuda")
    assert r.status_code == 200
    conteudo = r.text.lower()
    assert "léxico" in conteudo
    assert "sintático" in conteudo or "sintaxe" in conteudo
    assert "semântico" in conteudo


def test_registar_email_duplicado_da_400(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "outrapass"})
    assert r.status_code == 400


def test_entrar_com_credenciais_corretas(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    cliente.post("/api/sair")
    r = cliente.post("/api/entrar", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    assert cliente.get("/editor").status_code == 200


def test_entrar_com_password_errada_da_401(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    cliente.post("/api/sair")
    r = cliente.post("/api/entrar", json={"email": "a@b.com", "password": "errada"})
    assert r.status_code == 401


def test_sair_remove_o_acesso(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    cliente.post("/api/sair")
    r = cliente.get("/editor", follow_redirects=False)
    assert r.status_code == 307


# ---------- aprovação de contas (admin) ----------
# Nenhum teste acima define ONLINE_EMAIL_ADMIN -- por isso continuam
# todos a registar+entrar exatamente como antes (gate desligado).

def test_registar_com_admin_configurado_fica_pendente_e_sem_sessao(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    r = cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["pendente"] is True
    assert cliente.get("/editor", follow_redirects=False).status_code == 307


def test_entrar_com_conta_pendente_da_403(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    r = cliente.post("/api/entrar", json={"email": "aluno@escola.pt", "password": "password123"})
    assert r.status_code == 401
    assert "pendente" in r.json()["detail"]


def test_conta_pendente_indica_a_quem_contactar(cliente, monkeypatch):
    """UX-17: antes, o estudante ficava num estado de espera sem
    nenhuma indicação de a quem contactar se demorasse."""
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    r = cliente.post("/api/entrar", json={"email": "aluno@escola.pt", "password": "password123"})
    assert "contacta o professor ou administrador responsável" in r.json()["detail"]

    entrar_js = (Path(__file__).parent.parent / "estatico" / "entrar.js").read_text(encoding="utf-8")
    assert "contacta o professor ou administrador responsável" in entrar_js


# ---------- UX-18: mensagem de timeout uniforme entre CLI e web ----------

async def _timeout_falso(execucao, callback_linha, limite_segundos=None):
    raise TimeoutError()


def test_ws_executar_timeout_nomeia_a_causa_provavel(cliente, monkeypatch):
    """Antes, a web só dizia "excedeu o tempo limite", sem nomear a
    causa provável (possível ciclo infinito), ao contrário da consola
    (algo_lang/cli.py, modo --debug/--json). Substitui-se
    correr_com_limite_de_tempo por um stub que levanta TimeoutError de
    imediato -- sem esperar por um timeout real (lento e dependeria de
    temporização exata)."""
    monkeypatch.setattr(executor, "correr_com_limite_de_tempo", _timeout_falso)
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    with cliente.websocket_connect("/ws/executar") as ws:
        ws.send_json(_msg('algoritmo "T"\ninicio\n    escrever("ola")\n'))
        assert ws.receive_json()["tipo"] == "compilado"
        m = ws.receive_json()
    assert m["tipo"] == "erro"
    assert "possível ciclo infinito" in m["mensagem"]


# ---------- FEAT-02: escolha de tema claro/escuro ----------

def test_tema_js_servido_e_ligado_nas_paginas_privadas(cliente):
    """Sem framework de testes JS/browser disponível, confirma-se ao
    nível do conteúdo servido que tema.js existe, tem a lógica
    esperada (persistência em localStorage, deteção por
    prefers-color-scheme), e que as 3 páginas privadas (editor/admin/
    ajuda) o carregam. O botão de alternância só faz sentido no editor
    -- é a única página onde o utilizador tende a passar tempo
    suficiente para querer trocar de tema."""
    r = cliente.get("/estatico/tema.js")
    assert r.status_code == 200
    assert "localStorage" in r.text
    assert "prefers-color-scheme" in r.text
    assert "obterTema" in r.text

    base = Path(__file__).parent.parent / "paginas_privadas"
    for nome in ("editor.html", "admin.html", "ajuda.html"):
        conteudo = (base / nome).read_text(encoding="utf-8")
        assert '<script src="/estatico/tema.js"></script>' in conteudo

    conteudo_editor = (base / "editor.html").read_text(encoding="utf-8")
    assert 'id="botao-tema"' in conteudo_editor
    for nome in ("admin.html", "ajuda.html"):
        conteudo = (base / nome).read_text(encoding="utf-8")
        assert 'id="botao-tema"' not in conteudo


def test_estilo_css_define_tema_claro(cliente):
    r = cliente.get("/estatico/estilo.css")
    assert r.status_code == 200
    assert ':root[data-theme="light"]' in r.text


def test_admin_pendentes_exige_admin(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    r = cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})
    assert r.status_code == 200

    r = cliente.get("/api/admin/pendentes")
    assert r.status_code == 200
    emails = [c["email"] for c in r.json()["pendentes"]]
    assert emails == ["aluno@escola.pt"]


def test_admin_pendentes_bloqueado_para_nao_admin(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})
    cliente.post("/api/sair")

    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    cliente.post("/api/registar", json={"email": "outro@escola.pt", "password": "password123"})
    r = cliente.get("/api/admin/pendentes")
    assert r.status_code == 403


def test_admin_aprova_conta_pendente(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    cliente.post("/api/sair")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})

    pendentes = cliente.get("/api/admin/pendentes").json()["pendentes"]
    id_aluno = pendentes[0]["id"]
    r = cliente.post(f"/api/admin/aprovar/{id_aluno}")
    assert r.status_code == 200

    cliente.post("/api/sair")
    r = cliente.post("/api/entrar", json={"email": "aluno@escola.pt", "password": "password123"})
    assert r.status_code == 200


def test_admin_rejeita_conta_pendente(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    cliente.post("/api/sair")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})

    pendentes = cliente.get("/api/admin/pendentes").json()["pendentes"]
    id_aluno = pendentes[0]["id"]
    r = cliente.post(f"/api/admin/rejeitar/{id_aluno}")
    assert r.status_code == 200
    assert cliente.get("/api/admin/pendentes").json()["pendentes"] == []


def test_api_eu_reflete_se_a_conta_e_admin(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})
    assert cliente.get("/api/eu").json() == {"admin": True}

    cliente.post("/api/sair")
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    cliente.post("/api/registar", json={"email": "outro@escola.pt", "password": "password123"})
    assert cliente.get("/api/eu").json() == {"admin": False}


def test_pagina_admin_redireciona_quem_nao_e_admin(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.get("/admin", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/editor"


def test_admin_utilizadores_exige_admin(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})
    cliente.post("/api/sair")

    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    cliente.post("/api/registar", json={"email": "outro@escola.pt", "password": "password123"})
    r = cliente.get("/api/admin/utilizadores")
    assert r.status_code == 403


def test_admin_utilizadores_lista_todas_as_contas(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    cliente.post("/api/sair")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})

    r = cliente.get("/api/admin/utilizadores")
    assert r.status_code == 200
    utilizadores = {u["email"]: u for u in r.json()["utilizadores"]}
    assert utilizadores["aluno@escola.pt"]["aprovado"] == 0
    assert utilizadores["professor@escola.pt"]["admin"] == 1


def test_admin_revoga_conta_aprovada(cliente, monkeypatch):
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    cliente.post("/api/registar", json={"email": "aluno@escola.pt", "password": "password123"})
    cliente.post("/api/sair")

    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})

    id_aluno = next(
        u["id"] for u in cliente.get("/api/admin/utilizadores").json()["utilizadores"]
        if u["email"] == "aluno@escola.pt"
    )
    r = cliente.post(f"/api/admin/revogar/{id_aluno}")
    assert r.status_code == 200

    cliente.post("/api/sair")
    r = cliente.post("/api/entrar", json={"email": "aluno@escola.pt", "password": "password123"})
    assert r.status_code == 401
    assert "pendente" in r.json()["detail"]


def test_admin_nao_pode_revogar_a_propria_conta(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})
    id_proprio = cliente.get("/api/admin/utilizadores").json()["utilizadores"][0]["id"]

    r = cliente.post(f"/api/admin/revogar/{id_proprio}")
    assert r.status_code == 400


def test_admin_atividade_exige_admin(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})
    cliente.post("/api/sair")

    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    cliente.post("/api/registar", json={"email": "outro@escola.pt", "password": "password123"})
    r = cliente.get("/api/admin/atividade")
    assert r.status_code == 403


def test_admin_atividade_sem_logs_devolve_relatorio_vazio(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "a@b.com")
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})

    r = cliente.get("/api/admin/atividade")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["por_sessao"] == []
    assert corpo["globais"]["num_sessoes"] == 0


def test_admin_bd_exige_admin(cliente, monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    cliente.post("/api/registar", json={"email": "professor@escola.pt", "password": "password123"})
    cliente.post("/api/sair")

    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    cliente.post("/api/registar", json={"email": "outro@escola.pt", "password": "password123"})
    r = cliente.get("/api/admin/bd")
    assert r.status_code == 403


def test_admin_bd_devolve_copia_sqlite_valida(cliente, monkeypatch, tmp_path):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "a@b.com")
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})

    r = cliente.get("/api/admin/bd")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/vnd.sqlite3"

    caminho_copia = tmp_path / "copia.db"
    caminho_copia.write_bytes(r.content)
    ligacao = bd.obter_ligacao(str(caminho_copia))
    try:
        emails = [linha["email"] for linha in ligacao.execute("SELECT email FROM estudante")]
    finally:
        ligacao.close()
    assert emails == ["a@b.com"]


# ---------- credenciais ----------

def test_credencial_exige_autenticacao(cliente):
    r = cliente.get("/api/credencial")
    assert r.status_code == 401


def test_credencial_fluxo_completo(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.get("/api/credencial")
    assert r.json() == {"configurado": False}

    r = cliente.post("/api/credencial", json={
        "fornecedor": "openai", "modelo": "gpt-4o-mini", "api_key": "sk-teste"})
    assert r.status_code == 200

    r = cliente.get("/api/credencial")
    dados = r.json()
    assert dados["configurado"] is True
    assert dados["fornecedor"] == "openai"
    assert "api_key" not in dados  # nunca devolvida


def test_credencial_invalida_da_400(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/credencial", json={"fornecedor": "naoexiste", "modelo": "x", "api_key": "y"})
    assert r.status_code == 400


# ---------- WebSocket: execução ----------

def test_ws_executar_sem_autenticacao(cliente):
    with cliente.websocket_connect("/ws/executar") as ws:
        m = ws.receive_json()
        assert m["tipo"] == "erro"


def test_ws_executar_programa_simples(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    with cliente.websocket_connect("/ws/executar") as ws:
        ws.send_json(_msg('algoritmo "T"\ninicio\n    escrever("ola")\n'))
        mensagens = []
        while True:
            m = ws.receive_json()
            mensagens.append(m)
            if m["tipo"] in ("fim", "erro", "erro_compilacao"):
                break
    tipos = [m["tipo"] for m in mensagens]
    assert tipos == ["compilado", "saida", "fim"]
    assert mensagens[1]["texto"] == "ola"
    assert mensagens[2]["codigo_saida"] == 0


def test_ws_executar_erro_de_compilacao(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    with cliente.websocket_connect("/ws/executar") as ws:
        ws.send_json(_msg("algoritmo sem aspas\ninicio\n    escrever(1)\n"))
        m = ws.receive_json()
        assert m["tipo"] == "erro_compilacao"
        assert "sintaxe" in m["mensagem"]


def test_ws_executar_com_entrada_interativa(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    codigo = (
        'algoritmo "Soma"\ninicio\n'
        '    a:inteiro\n    b:inteiro\n    ler(a)\n    ler(b)\n'
        '    escrever("Soma: ", a + b)\n'
    )
    with cliente.websocket_connect("/ws/executar") as ws:
        ws.send_json(_msg(codigo))
        assert ws.receive_json()["tipo"] == "compilado"
        ws.send_json({"tipo": "entrada", "valor": "3"})
        ws.send_json({"tipo": "entrada", "valor": "4"})
        mensagens = []
        while True:
            m = ws.receive_json()
            mensagens.append(m)
            if m["tipo"] == "fim":
                break
    saidas = [m["texto"] for m in mensagens if m["tipo"] == "saida"]
    assert saidas == ["Soma: 7"]


def test_adquirir_vaga_de_execucao_espera_e_avisa_quando_saturado(monkeypatch):
    """ON-03: testa _adquirir_vaga_de_execucao diretamente (não através
    de duas ligações WebSocket concorrentes no mesmo TestClient -- esse
    cliente de testes não suporta bem duas ligações WebSocket
    genuinamente simultâneas). Com o limite reduzido a 1: a segunda
    chamada tem de bloquear e avisar antes de conseguir a vaga; só
    depois de a primeira libertar é que a segunda avança."""
    monkeypatch.setattr(main, "_semaforo_execucoes", asyncio.Semaphore(1))

    class WebSocketFalso:
        def __init__(self):
            self.mensagens = []

        async def send_json(self, dados):
            self.mensagens.append(dados)

    async def cenario():
        ws1, ws2 = WebSocketFalso(), WebSocketFalso()

        await main._adquirir_vaga_de_execucao(ws1)
        assert ws1.mensagens == []  # vaga livre -- sem aviso de espera

        tarefa2 = asyncio.create_task(main._adquirir_vaga_de_execucao(ws2))
        await asyncio.sleep(0.2)
        assert not tarefa2.done()
        assert ws2.mensagens and ws2.mensagens[0]["tipo"] == "info"
        assert "ocupado" in ws2.mensagens[0]["mensagem"]

        main._semaforo_execucoes.release()  # ws1 "termina" a sua execução
        await asyncio.wait_for(tarefa2, timeout=1)

        main._semaforo_execucoes.release()  # limpeza
    asyncio.run(cenario())


def test_ws_executar_isola_estudantes_diferentes(cliente):
    """Dois estudantes diferentes, dois clientes diferentes -- as
    pastas de execução não se podem cruzar."""
    cliente.post("/api/registar", json={"email": "um@b.com", "password": "password123"})
    with cliente.websocket_connect("/ws/executar") as ws:
        ws.send_json(_msg('algoritmo "T"\ninicio\n    escrever("estudante um")\n'))
        mensagens_um = []
        while True:
            m = ws.receive_json()
            mensagens_um.append(m)
            if m["tipo"] == "fim":
                break

    with TestClient(main.app) as cliente2:
        cliente2.post("/api/registar", json={"email": "dois@b.com", "password": "password123"})
        with cliente2.websocket_connect("/ws/executar") as ws:
            ws.send_json(_msg('algoritmo "T"\ninicio\n    escrever("estudante dois")\n'))
            mensagens_dois = []
            while True:
                m = ws.receive_json()
                mensagens_dois.append(m)
                if m["tipo"] == "fim":
                    break

    saida_um = [m["texto"] for m in mensagens_um if m["tipo"] == "saida"][0]
    saida_dois = [m["texto"] for m in mensagens_dois if m["tipo"] == "saida"][0]
    assert saida_um == "estudante um"
    assert saida_dois == "estudante dois"


# ---------- WebSocket: Alguem ----------

def test_ws_alguem_sem_autenticacao(cliente):
    with cliente.websocket_connect("/ws/alguem") as ws:
        m = ws.receive_json()
        assert m["tipo"] == "erro"


def test_ws_alguem_sem_credencial_configurada(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    with cliente.websocket_connect("/ws/alguem") as ws:
        m = ws.receive_json()
        assert m["tipo"] == "erro"
        assert "configuraste" in m["mensagem"]


def test_ws_alguem_conversa_completa(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    cliente.post("/api/credencial", json={"fornecedor": "openai", "modelo": "gpt-4o-mini", "api_key": "sk-teste"})

    respostas = iter([
        json.dumps({"choices": [{"message": {"content": "Boa pergunta! O que sabes já?"}}]}),
        json.dumps({"choices": [{"message": {"content": "SAFE"}}]}),
    ])

    def urlopen_falso(pedido, timeout=None):
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = next(respostas).encode()
        return cm

    with patch("urllib.request.urlopen", side_effect=urlopen_falso):
        with cliente.websocket_connect("/ws/alguem") as ws:
            m = ws.receive_json()
            assert m["tipo"] == "pronto"
            ws.send_json({"texto": "não sei por onde começar"})
            m = ws.receive_json()
            assert m["tipo"] == "resposta"
            assert m["texto"] == "Boa pergunta! O que sabes já?"


class _TutorFalsoQueRebenta:
    """AG-21-style: simula um erro inesperado (não WebSocketDisconnect)
    a meio da conversa -- ARCH-09 exige que fechar_sessao() corra na
    mesma."""
    def __init__(self):
        self.fechado = False

    def considerar_ficheiros(self, ficheiros_visiveis):
        pass

    def conversar(self, mensagem):
        raise RuntimeError("falha inesperada simulada")

    def fechar_sessao(self):
        self.fechado = True


def test_ws_alguem_fecha_sessao_mesmo_com_excecao_inesperada(cliente, monkeypatch):
    """ARCH-09: antes, fechar_sessao() só corria dentro do 'except
    WebSocketDisconnect' -- qualquer outra exceção no loop deixava o
    ficheiro de log aberto e nunca escrevia o evento fim_sessao."""
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    cliente.post("/api/credencial", json={"fornecedor": "openai", "modelo": "gpt-4o-mini", "api_key": "sk-teste"})

    tutor_falso = _TutorFalsoQueRebenta()
    monkeypatch.setattr(main.alguem_ponte, "construir_alguem", lambda id_estudante: tutor_falso)

    with pytest.raises(Exception):
        with cliente.websocket_connect("/ws/alguem") as ws:
            ws.receive_json()  # "pronto"
            ws.send_json({"texto": "algo"})
            ws.receive_json()

    assert tutor_falso.fechado is True


def test_ws_alguem_logs_usam_pseudonimo_nao_email(cliente, tmp_path):
    cliente.post("/api/registar", json={"email": "privacidade@b.com", "password": "password123"})
    cliente.post("/api/credencial", json={"fornecedor": "openai", "modelo": "gpt-4o-mini", "api_key": "sk-teste"})

    with patch("urllib.request.urlopen", return_value=_resposta_llm_falsa("SAFE")):
        with cliente.websocket_connect("/ws/alguem") as ws:
            ws.receive_json()

    from alguem.nucleo.registador import PASTA_LOGS_POR_OMISSAO
    import glob
    ficheiros = glob.glob(f"{PASTA_LOGS_POR_OMISSAO}/*.jsonl")
    assert len(ficheiros) == 1
    with open(ficheiros[0], encoding="utf-8") as f:
        conteudo = f.read()
    assert "privacidade@b.com" not in conteudo


# ---------- fluxograma ----------

def test_fluxograma_exige_autenticacao(cliente):
    r = cliente.post("/api/fluxograma", json=_msg('algoritmo "T"\ninicio\n    escrever(1)\n'))
    assert r.status_code == 401


def test_fluxograma_gera_svg(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/fluxograma", json=_msg('algoritmo "T"\ninicio\n    escrever("ola")\n'))
    assert r.status_code == 200
    assert "<svg" in r.json()["svg"]


def test_fluxograma_erro_de_compilacao(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/fluxograma", json=_msg("algoritmo sem aspas\n"))
    assert r.status_code == 400
    assert "sintaxe" in r.json()["detail"]


# ---------- rasto ----------

def test_rasto_exige_autenticacao(cliente):
    r = cliente.post("/api/rasto", json={**_msg('algoritmo "T"\ninicio\n    escrever(1)\n'), "entradas": []})
    assert r.status_code == 401


def test_rasto_com_entradas_antecipadas(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/rasto", json={**_msg('algoritmo "T"\ninicio\n    a:inteiro\n    ler(a)\n    escrever(a*2)\n'), "entradas": ["5"]})
    assert r.status_code == 200
    dados = r.json()
    assert dados["consolaFinal"] == "10\n"
    assert dados["erro"] is None
    assert len(dados["passos"]) > 0
    # o visualizador (visualizador/algo-trace-viewer.html) exige estas
    # três chaves no ficheiro descarregado -- ver executor.gerar_rasto
    assert dados["titulo"] == "T"
    assert dados["ficheiro"] == "principal.algo"
    assert dados["codigoFonte"] == ['algoritmo "T"', "inicio", "    a:inteiro", "    ler(a)", "    escrever(a*2)"]


def test_rasto_erro_de_compilacao(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/rasto", json={**_msg("algoritmo sem aspas\n"), "entradas": []})
    assert r.status_code == 400


def test_rasto_sem_entradas_suficientes_nao_bloqueia(cliente):
    """Confirma que o pedido HTTP termina (não fica pendurado à espera
    de entrada que nunca vai chegar) -- o rasto devolve um erro
    'EOF...' em vez de ficar bloqueado."""
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/rasto", json={**_msg('algoritmo "T"\ninicio\n    a:inteiro\n    ler(a)\n    escrever(a)\n'), "entradas": []})
    assert r.status_code == 200
    assert r.json()["erro"] is not None


# ---------- projeto: descarregar/abrir como .zip (sem persistência em BD) ----------

def test_projeto_download_exige_autenticacao(cliente):
    r = cliente.post("/api/projeto/download", json=_msg('algoritmo "T"\ninicio\nfim\n'))
    assert r.status_code == 401


def test_projeto_download_devolve_zip_com_os_ficheiros(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    corpo = {
        "ficheiros": [
            {"nome": "principal.algo", "conteudo": 'algoritmo "T"\ninicio\nfim\n'},
            {"nome": "biblioteca.algo", "conteudo": "funcao dobro(x: inteiro): inteiro\n"},
        ],
        "principal": "principal.algo",
    }
    r = cliente.post("/api/projeto/download", json=corpo)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert zf.namelist() == ["principal.algo", "biblioteca.algo"]
    assert zf.read("principal.algo").decode("utf-8") == corpo["ficheiros"][0]["conteudo"]


def test_projeto_download_sem_ficheiros_da_erro(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/projeto/download", json={"ficheiros": [], "principal": ""})
    assert r.status_code == 400


def test_projeto_upload_exige_autenticacao(cliente):
    r = cliente.post("/api/projeto/upload", files={"ficheiro": ("projeto.zip", b"nao interessa", "application/zip")})
    assert r.status_code == 401


def test_projeto_upload_devolve_os_ficheiros(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as zf:
        zf.writestr("principal.algo", 'algoritmo "T"\ninicio\nfim\n')
        zf.writestr("biblioteca.algo", "funcao dobro(x: inteiro): inteiro\n")
    r = cliente.post("/api/projeto/upload", files={"ficheiro": ("projeto.zip", memoria.getvalue(), "application/zip")})
    assert r.status_code == 200
    assert r.json()["ficheiros"] == [
        {"nome": "principal.algo", "conteudo": 'algoritmo "T"\ninicio\nfim\n'},
        {"nome": "biblioteca.algo", "conteudo": "funcao dobro(x: inteiro): inteiro\n"},
    ]


def test_projeto_upload_rejeita_zip_invalido(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/projeto/upload", files={"ficheiro": ("projeto.zip", b"nao e um zip", "application/zip")})
    assert r.status_code == 400


def test_projeto_download_e_upload_fazem_ida_e_volta(cliente):
    """O ponto central deste teste: descarregar e depois voltar a abrir
    o mesmo projeto devolve exatamente os mesmos ficheiros, pela mesma
    ordem -- é essa ida-e-volta que faz o .zip funcionar como "guardar"
    sem precisar de nenhuma tabela na base de dados."""
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    corpo = {
        "ficheiros": [
            {"nome": "principal.algo", "conteudo": 'algoritmo "T"\ninicio\n    incluir "biblioteca.algo"\nfim\n'},
            {"nome": "biblioteca.algo", "conteudo": "funcao dobro(x: inteiro): inteiro\n"},
        ],
        "principal": "principal.algo",
    }
    r_download = cliente.post("/api/projeto/download", json=corpo)
    assert r_download.status_code == 200
    r_upload = cliente.post(
        "/api/projeto/upload",
        files={"ficheiro": ("projeto.zip", r_download.content, "application/zip")},
    )
    assert r_upload.status_code == 200
    assert r_upload.json()["ficheiros"] == corpo["ficheiros"]


# ---------- incluir (bibliotecas próprias), de ponta a ponta ----------

def test_ws_executar_com_incluir(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(21))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"
    with cliente.websocket_connect("/ws/executar") as ws:
        ws.send_json({
            "ficheiros": [
                {"nome": "principal.algo", "conteudo": principal},
                {"nome": "lib.algo", "conteudo": biblioteca},
            ],
            "principal": "principal.algo",
        })
        mensagens = []
        while True:
            m = ws.receive_json()
            mensagens.append(m)
            if m["tipo"] in ("fim", "erro", "erro_compilacao"):
                break
    saidas = [m["texto"] for m in mensagens if m["tipo"] == "saida"]
    assert saidas == ["42"]


def test_ws_executar_incluir_ficheiro_em_falta(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    principal = 'algoritmo "T"\nincluir "nao_existe.algo"\ninicio\n    escrever(1)\n'
    with cliente.websocket_connect("/ws/executar") as ws:
        ws.send_json({"ficheiros": [{"nome": "principal.algo", "conteudo": principal}],
                       "principal": "principal.algo"})
        m = ws.receive_json()
        assert m["tipo"] == "erro_compilacao"
        assert "não encontrado" in m["mensagem"]


def test_ws_alguem_recebe_varios_ficheiros(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    cliente.post("/api/credencial", json={"fornecedor": "openai", "modelo": "gpt-4o-mini", "api_key": "sk-teste"})

    capturado = {}

    def urlopen_falso(pedido, timeout=None):
        import json as json_mod
        corpo = json_mod.loads(pedido.data.decode())
        eh_classificacao = any(
            "Categoria (uma palavra só, maiúsculas):" in m.get("content", "")
            for m in corpo["messages"])
        if eh_classificacao:
            return _resposta_llm_falsa("SAFE")
        capturado["corpo"] = corpo
        return _resposta_llm_falsa("ok")

    with patch("urllib.request.urlopen", side_effect=urlopen_falso):
        with cliente.websocket_connect("/ws/alguem") as ws:
            ws.receive_json()  # "pronto"
            ws.send_json({"tipo": "ficheiro", "ficheiros": [
                {"nome": "principal.algo", "conteudo": "conteudo do principal"},
                {"nome": "lib.algo", "conteudo": "conteudo da biblioteca"},
            ]})
            ws.send_json({"texto": "o que faz este código?"})
            ws.receive_json()

    textos = [m["content"] for m in capturado["corpo"]["messages"]]
    assert any("principal.algo" in t and "conteudo do principal" in t for t in textos)
    assert any("lib.algo" in t and "conteudo da biblioteca" in t for t in textos)


def test_fluxograma_com_incluir(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    r = cliente.post("/api/fluxograma", json={
        "ficheiros": [
            {"nome": "principal.algo", "conteudo": 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(3))\n'},
            {"nome": "lib.algo", "conteudo": "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"},
        ],
        "principal": "principal.algo",
    })
    assert r.status_code == 200
    assert "<svg" in r.json()["svg"]


def test_fluxograma_lista_rotinas_e_permite_escolher_uma_de_biblioteca(cliente):
    cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    corpo_pedido = {
        "ficheiros": [
            {"nome": "principal.algo", "conteudo": 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(3))\n'},
            {"nome": "lib.algo", "conteudo": "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"},
        ],
        "principal": "principal.algo",
    }
    r = cliente.post("/api/fluxograma", json=corpo_pedido)
    dados = r.json()
    assert dados["rotinas"] == ["Principal", "dobro"]
    assert dados["rotina_atual"] == "Principal"

    r2 = cliente.post("/api/fluxograma", json={**corpo_pedido, "rotina": "dobro"})
    dados2 = r2.json()
    assert dados2["rotina_atual"] == "dobro"
    assert "<svg" in dados2["svg"]


# ---------- rede de segurança: erro inesperado nunca devolve texto simples ----------

def test_erro_inesperado_devolve_sempre_json():
    """Reproduz o sintoma real reportado: 'Unexpected token... is not
    valid JSON' -- acontecia quando um erro não tratado devolvia uma
    página de erro em texto simples, que o frontend tenta sempre
    fazer resposta.json(). Precisa de um TestClient próprio, com
    raise_server_exceptions=False -- por omissão, o TestClient torna a
    levantar a exceção no teste, mesmo já havendo um tratador
    registado (só o servidor uvicorn real usa sempre o tratador; isto
    é só uma particularidade do TestClient em modo de depuração)."""
    with TestClient(main.app, raise_server_exceptions=False) as cliente:
        cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
        with patch("credenciais.guardar_credencial", side_effect=RuntimeError("algo inesperado")):
            r = cliente.post("/api/credencial", json={
                "fornecedor": "openai", "modelo": "x", "api_key": "sk-teste"})
    assert r.status_code == 500
    corpo = r.json()  # nunca deve levantar exceção -- tem de ser sempre JSON válido
    assert "detail" in corpo


def test_erro_inesperado_nao_revela_a_mensagem_da_excecao_ao_cliente(caplog):
    """ON-19: a mensagem da exceção (podia conter caminhos internos,
    nomes de tabelas SQL, etc.) só pode ir para o log do servidor --
    nunca para a resposta JSON devolvida ao cliente."""
    with TestClient(main.app, raise_server_exceptions=False) as cliente:
        cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
        with patch("credenciais.guardar_credencial", side_effect=RuntimeError("segredo interno")):
            with caplog.at_level("ERROR", logger="online"):
                r = cliente.post("/api/credencial", json={
                    "fornecedor": "openai", "modelo": "x", "api_key": "sk-teste"})
    corpo = r.json()
    assert "segredo interno" not in corpo["detail"]
    assert corpo["detail"] == "Erro interno do servidor. Tenta outra vez daqui a pouco."
    # mas fica registado no log do servidor, para diagnóstico
    assert "segredo interno" in caplog.text


# ---------- ON-20: corpo JSON malformado devolve 400, não 500 ----------

@pytest.mark.parametrize("rota", ["/api/registar", "/api/entrar"])
def test_corpo_nao_json_devolve_400(cliente, rota):
    r = cliente.post(rota, content=b"isto nao e json valido {{{",
                      headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert "JSON" in r.json()["detail"]


def test_corpo_json_que_nao_e_objeto_devolve_400(cliente):
    """JSON sintaticamente válido (uma lista), mas não o objeto que a
    rota espera -- antes rebentava com AttributeError ao tentar
    '.get()' numa lista, e caía no handler global como 500."""
    r = cliente.post("/api/registar", json=["nao", "e", "um", "objeto"])
    assert r.status_code == 400
    assert "objeto" in r.json()["detail"]


def test_corpo_json_valido_continua_a_funcionar(cliente):
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200


# ---------- ON-22: limite de tamanho do corpo do pedido ----------

def test_pedido_com_corpo_demasiado_grande_e_rejeitado(cliente, monkeypatch):
    monkeypatch.setattr(main, "LIMITE_TAMANHO_CORPO_BYTES", 100)
    corpo_grande = json.dumps({"email": "a@b.com", "password": "x" * 500})
    r = cliente.post("/api/registar", content=corpo_grande,
                      headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_pedido_dentro_do_limite_nao_e_afetado(cliente, monkeypatch):
    monkeypatch.setattr(main, "LIMITE_TAMANHO_CORPO_BYTES", 100)
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200


# ---------- ON-23: verificação de Origin/Referer contra CSRF ----------

def test_post_com_origin_de_outro_site_e_rejeitado(cliente):
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"},
                      headers={"Origin": "https://site-malicioso.example"})
    assert r.status_code == 403


def test_post_com_referer_de_outro_site_e_rejeitado(cliente):
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"},
                      headers={"Referer": "https://site-malicioso.example/pagina"})
    assert r.status_code == 403


def test_post_sem_origin_nem_referer_nao_e_bloqueado(cliente):
    """Um cliente não-browser (ex: chamada direta à API) não envia
    Origin/Referer -- não deve ser bloqueado só por isso."""
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200


def test_post_com_origin_do_proprio_site_nao_e_bloqueado(cliente):
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"},
                      headers={"Origin": "http://testserver"})
    assert r.status_code == 200


def test_get_nunca_e_bloqueado_pela_verificacao_de_origem(cliente):
    """A verificação só se aplica a métodos que mutam estado -- GET
    tem de continuar a funcionar independentemente do Origin."""
    r = cliente.get("/", headers={"Origin": "https://site-malicioso.example"})
    assert r.status_code == 200


# ---------- ON-25 + ON-35: max_age explícito e https_only configurável ----------

def test_cookie_de_sessao_tem_max_age_explicito(cliente):
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    set_cookie = r.headers.get("set-cookie", "")
    assert "max-age=" in set_cookie.lower()
    assert main.SESSAO_MAX_AGE_SEGUNDOS == 14 * 24 * 3600


def test_https_only_desligado_por_omissao_para_dev_local(cliente):
    """Omissão desligada (para não partir o desenvolvimento local sem
    TLS) -- o cookie não deve ter o atributo Secure por omissão."""
    r = cliente.post("/api/registar", json={"email": "a@b.com", "password": "password123"})
    set_cookie = r.headers.get("set-cookie", "")
    assert "secure" not in set_cookie.lower()


# ---------- ON-17: bcrypt lento não pode bloquear o servidor inteiro ----------

def test_login_lento_nao_bloqueia_pedido_concorrente_nao_relacionado(cliente, monkeypatch):
    """bcrypt.checkpw é deliberadamente lento -- antes de
    run_in_threadpool, isso bloqueava o event loop inteiro, travando
    até um pedido completamente não relacionado (a página inicial)
    enquanto um login estava a decorrer."""
    import asyncio
    import time

    import httpx

    cliente.post("/api/registar", json={"email": "lento@b.com", "password": "password123"})

    checkpw_original = autenticacao.bcrypt.checkpw

    def checkpw_lento(*args, **kwargs):
        time.sleep(1.0)
        return checkpw_original(*args, **kwargs)

    monkeypatch.setattr(autenticacao.bcrypt, "checkpw", checkpw_lento)

    async def cenario():
        transporte = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://test") as ac:
            tarefa_login = asyncio.create_task(
                ac.post("/api/entrar", json={"email": "lento@b.com", "password": "password123"}))
            await asyncio.sleep(0.1)  # dá tempo ao login para começar a bloquear a thread
            inicio = time.monotonic()
            resposta_rapida = await ac.get("/")
            duracao_pedido_rapido = time.monotonic() - inicio
            resposta_login = await tarefa_login
            return duracao_pedido_rapido, resposta_rapida.status_code, resposta_login.status_code

    duracao, estado_rapido, estado_login = asyncio.run(cenario())
    assert estado_rapido == 200
    assert estado_login == 200
    # a página inicial não devia esperar pelo bcrypt lento (1s) do login
    # concorrente -- generoso para não ficar frágil em CI lento
    assert duracao < 0.5

