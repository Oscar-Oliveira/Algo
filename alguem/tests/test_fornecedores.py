# -*- coding: utf-8 -*-
"""Testes dos fornecedores LLM. Como não há acesso de rede real neste
ambiente, toda a camada HTTP é simulada (unittest.mock) -- o que se
testa aqui é a construção correta do pedido e a leitura correta da
resposta, não a API em si (essa só se confirma com credenciais reais,
fora deste ambiente)."""
import json
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from alguem.fornecedores.base import ErroFornecedorLLM
from alguem.fornecedores.openrouter import FornecedorOpenRouter
from alguem.fornecedores.gemini import FornecedorGemini
from alguem.fornecedores import criar_fornecedor, FORNECEDORES


def _resposta_falsa(corpo: dict):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(corpo).encode("utf-8")
    return cm


# ---------- construção sem chave de API ----------

def test_falta_api_key_da_erro_claro():
    with pytest.raises(ErroFornecedorLLM, match="Falta a chave de API"):
        FornecedorOpenRouter(modelo="x", api_key="")


# ---------- OpenRouter ----------

def test_openrouter_pedido_bem_formado():
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"choices": [{"message": {"content": "ok"}}]})) as m:
        f = FornecedorOpenRouter(modelo="gpt-4o-mini", api_key="sk-teste")
        f.responder([{"role": "user", "content": "ola"}])
        pedido = m.call_args[0][0]
        assert pedido.full_url == "https://openrouter.ai/api/v1/chat/completions"
        assert pedido.get_header("Authorization") == "Bearer sk-teste"
        corpo = json.loads(pedido.data.decode())
        assert corpo["model"] == "gpt-4o-mini"
        assert corpo["messages"] == [{"role": "user", "content": "ola"}]


def test_openrouter_extrai_resposta_corretamente():
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"choices": [{"message": {"content": "Ola!"}}]})):
        f = FornecedorOpenRouter(modelo="x", api_key="sk-teste")
        assert f.responder([{"role": "user", "content": "oi"}]) == "Ola!"


def test_openrouter_erro_http_da_mensagem_amigavel():
    erro = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
    erro.read = lambda: b'{"error": "invalid api key"}'
    with patch("urllib.request.urlopen", side_effect=erro):
        f = FornecedorOpenRouter(modelo="x", api_key="sk-invalida")
        with pytest.raises(ErroFornecedorLLM, match="HTTP 401"):
            f.responder([{"role": "user", "content": "oi"}])


def test_openrouter_erro_de_rede_da_mensagem_amigavel():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sem ligação")):
        f = FornecedorOpenRouter(modelo="x", api_key="sk-teste")
        with pytest.raises(ErroFornecedorLLM, match="Não foi possível contactar"):
            f.responder([{"role": "user", "content": "oi"}])


def test_openrouter_resposta_em_formato_inesperado():
    with patch("urllib.request.urlopen", return_value=_resposta_falsa({"algo_estranho": True})):
        f = FornecedorOpenRouter(modelo="x", api_key="sk-teste")
        with pytest.raises(ErroFornecedorLLM, match="formato inesperado"):
            f.responder([{"role": "user", "content": "oi"}])


# ---------- Gemini ----------

def test_gemini_traduz_mensagens_de_sistema_e_papeis():
    f = FornecedorGemini(modelo="gemini-1.5-flash", api_key="x")
    instrucao, conteudos = f._traduzir_mensagens([
        {"role": "system", "content": "És o Alguem."},
        {"role": "system", "content": "Contexto extra."},
        {"role": "user", "content": "ola"},
        {"role": "assistant", "content": "ola, como posso ajudar?"},
        {"role": "user", "content": "não sei os ciclos"},
    ])
    assert instrucao == {"parts": [{"text": "És o Alguem.\n\nContexto extra."}]}
    assert conteudos == [
        {"role": "user", "parts": [{"text": "ola"}]},
        {"role": "model", "parts": [{"text": "ola, como posso ajudar?"}]},
        {"role": "user", "parts": [{"text": "não sei os ciclos"}]},
    ]


def test_gemini_sem_mensagens_de_sistema():
    f = FornecedorGemini(modelo="x", api_key="x")
    instrucao, conteudos = f._traduzir_mensagens([{"role": "user", "content": "ola"}])
    assert instrucao is None
    assert conteudos == [{"role": "user", "parts": [{"text": "ola"}]}]


def test_gemini_pedido_bem_formado():
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa(
                   {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})) as m:
        f = FornecedorGemini(modelo="gemini-1.5-flash", api_key="chave-teste")
        f.responder([{"role": "system", "content": "sys"}, {"role": "user", "content": "ola"}])
        pedido = m.call_args[0][0]
        assert pedido.full_url == (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-flash:generateContent?key=chave-teste")
        corpo = json.loads(pedido.data.decode())
        assert corpo["systemInstruction"] == {"parts": [{"text": "sys"}]}
        assert corpo["contents"] == [{"role": "user", "parts": [{"text": "ola"}]}]


def test_gemini_extrai_resposta_corretamente():
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa(
                   {"candidates": [{"content": {"parts": [{"text": "Ola da Gemini!"}]}}]})):
        f = FornecedorGemini(modelo="x", api_key="x")
        assert f.responder([{"role": "user", "content": "oi"}]) == "Ola da Gemini!"


def test_gemini_erro_http_da_mensagem_amigavel():
    erro = urllib.error.HTTPError("url", 400, "Bad Request", {}, None)
    erro.read = lambda: b'{"error": "modelo desconhecido"}'
    with patch("urllib.request.urlopen", side_effect=erro):
        f = FornecedorGemini(modelo="x", api_key="x")
        with pytest.raises(ErroFornecedorLLM, match="HTTP 400"):
            f.responder([{"role": "user", "content": "oi"}])


def test_gemini_erro_de_rede_da_mensagem_amigavel():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sem ligação")):
        f = FornecedorGemini(modelo="x", api_key="x")
        with pytest.raises(ErroFornecedorLLM, match="Não foi possível contactar"):
            f.responder([{"role": "user", "content": "oi"}])


def test_gemini_resposta_em_formato_inesperado():
    with patch("urllib.request.urlopen", return_value=_resposta_falsa({"algo_estranho": True})):
        f = FornecedorGemini(modelo="x", api_key="x")
        with pytest.raises(ErroFornecedorLLM, match="formato inesperado"):
            f.responder([{"role": "user", "content": "oi"}])


def test_gemini_texto_nulo_da_erro_em_vez_de_devolver_none():
    with patch("urllib.request.urlopen", return_value=_resposta_falsa(
            {"candidates": [{"content": {"parts": [{"text": None}]}}]})):
        f = FornecedorGemini(modelo="x", api_key="x")
        with pytest.raises(ErroFornecedorLLM, match="não devolveu texto"):
            f.responder([{"role": "user", "content": "oi"}])


def test_gemini_texto_vazio_da_erro():
    with patch("urllib.request.urlopen", return_value=_resposta_falsa(
            {"candidates": [{"content": {"parts": [{"text": ""}]}}]})):
        f = FornecedorGemini(modelo="x", api_key="x")
        with pytest.raises(ErroFornecedorLLM, match="não devolveu texto"):
            f.responder([{"role": "user", "content": "oi"}])


# ---------- fábrica de fornecedores ----------

def test_criar_fornecedor_openrouter():
    f = criar_fornecedor("openrouter", "gpt-4o-mini", "sk-teste")
    assert isinstance(f, FornecedorOpenRouter)
    assert f.nome == "openrouter"


def test_criar_fornecedor_gemini():
    f = criar_fornecedor("gemini", "gemini-1.5-flash", "chave-teste")
    assert isinstance(f, FornecedorGemini)
    assert f.nome == "gemini"


def test_criar_fornecedor_desconhecido():
    with pytest.raises(ErroFornecedorLLM, match="desconhecido"):
        criar_fornecedor("naoexiste", "modelo", "chave")


def test_todos_os_fornecedores_registados_tem_nome_unico():
    nomes = [classe(modelo="x", api_key="x").nome for classe in FORNECEDORES.values()]
    assert len(nomes) == len(set(nomes))
    assert set(nomes) == set(FORNECEDORES.keys())


# ---------- fornecedores "compatíveis com OpenAI" (parametrizado --
# OpenAI, OpenCode e HuggingFace partilham a mesma lógica de
# _base_openai_compativel.py, só muda o URL) ----------

from alguem.fornecedores.openai import FornecedorOpenAI
from alguem.fornecedores.opencode import FornecedorOpenCode
from alguem.fornecedores.huggingface import FornecedorHuggingFace

FORNECEDORES_ESTILO_OPENAI = [
    (FornecedorOpenAI, "https://api.openai.com/v1/chat/completions"),
    (FornecedorOpenCode, "https://opencode.ai/zen/go/v1/chat/completions"),
    (FornecedorHuggingFace, "https://router.huggingface.co/v1/chat/completions"),
]


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_pedido_bem_formado(classe, url_esperado):
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"choices": [{"message": {"content": "ok"}}]})) as m:
        f = classe(modelo="modelo-x", api_key="chave-teste")
        f.responder([{"role": "user", "content": "ola"}])
        pedido = m.call_args[0][0]
        assert pedido.full_url == url_esperado
        assert pedido.get_header("Authorization") == "Bearer chave-teste"
        corpo = json.loads(pedido.data.decode())
        assert corpo == {"model": "modelo-x", "messages": [{"role": "user", "content": "ola"}]}


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_extrai_resposta_corretamente(classe, url_esperado):
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"choices": [{"message": {"content": "Ola!"}}]})):
        f = classe(modelo="x", api_key="chave-teste")
        assert f.responder([{"role": "user", "content": "oi"}]) == "Ola!"


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_erro_http(classe, url_esperado):
    erro = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
    erro.read = lambda: b'{"error": "invalid api key"}'
    with patch("urllib.request.urlopen", side_effect=erro):
        f = classe(modelo="x", api_key="chave-invalida")
        with pytest.raises(ErroFornecedorLLM, match="HTTP 401"):
            f.responder([{"role": "user", "content": "oi"}])


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_erro_de_rede(classe, url_esperado):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sem ligação")):
        f = classe(modelo="x", api_key="chave-teste")
        with pytest.raises(ErroFornecedorLLM, match="Não foi possível contactar"):
            f.responder([{"role": "user", "content": "oi"}])


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_resposta_em_formato_inesperado(classe, url_esperado):
    with patch("urllib.request.urlopen", return_value=_resposta_falsa({"algo_estranho": True})):
        f = classe(modelo="x", api_key="chave-teste")
        with pytest.raises(ErroFornecedorLLM, match="formato inesperado"):
            f.responder([{"role": "user", "content": "oi"}])


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_exige_chave_de_api(classe, url_esperado):
    with pytest.raises(ErroFornecedorLLM, match="Falta a chave de API"):
        classe(modelo="x", api_key="")


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_content_nulo_da_erro_em_vez_de_devolver_none(classe, url_esperado):
    """Acontece quando o modelo decide fazer uma chamada de ferramenta
    (tool_calls) em vez de responder em texto -- 'content' vem null.
    Nunca deve devolver None como se fosse uma resposta válida."""
    with patch("urllib.request.urlopen", return_value=_resposta_falsa(
            {"choices": [{"message": {"content": None, "tool_calls": [{"id": "x"}]}}]})):
        f = classe(modelo="x", api_key="chave-teste")
        with pytest.raises(ErroFornecedorLLM, match="não devolveu texto"):
            f.responder([{"role": "user", "content": "oi"}])


@pytest.mark.parametrize("classe,url_esperado", FORNECEDORES_ESTILO_OPENAI)
def test_estilo_openai_content_vazio_da_erro(classe, url_esperado):
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"choices": [{"message": {"content": ""}}]})):
        f = classe(modelo="x", api_key="chave-teste")
        with pytest.raises(ErroFornecedorLLM, match="não devolveu texto"):
            f.responder([{"role": "user", "content": "oi"}])


def test_huggingface_aceita_modelo_com_sufixo_de_fornecedor():
    """O nome do modelo na HF costuma incluir o fornecedor de inferência
    (ex: 'deepseek-ai/DeepSeek-V4-Pro:deepinfra') -- confirma que passa
    tal e qual, sem nenhuma tentativa de o interpretar/dividir."""
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"choices": [{"message": {"content": "ok"}}]})) as m:
        f = FornecedorHuggingFace(modelo="deepseek-ai/DeepSeek-V4-Pro:deepinfra", api_key="hf_x")
        f.responder([{"role": "user", "content": "oi"}])
        corpo = json.loads(m.call_args[0][0].data.decode())
        assert corpo["model"] == "deepseek-ai/DeepSeek-V4-Pro:deepinfra"


# ---------- Ollama (formato compatível com OpenAI, mas local e sem
# chave obrigatória) ----------

from alguem.fornecedores.ollama import FornecedorOllama, HOST_POR_OMISSAO


def test_ollama_nao_exige_chave_de_api():
    f = FornecedorOllama(modelo="llama3.2")  # sem api_key nenhuma
    assert f.api_key  # fica com um valor qualquer, não vazio (convenção)


def test_ollama_url_por_omissao_e_localhost():
    f = FornecedorOllama(modelo="llama3.2")
    assert f.URL_API == f"{HOST_POR_OMISSAO}/v1/chat/completions"


def test_ollama_host_customizado():
    f = FornecedorOllama(modelo="llama3.2", host="http://192.168.1.50:11434")
    assert f.URL_API == "http://192.168.1.50:11434/v1/chat/completions"


def test_ollama_host_com_barra_final_e_normalizado():
    f = FornecedorOllama(modelo="llama3.2", host="http://localhost:11434/")
    assert f.URL_API == "http://localhost:11434/v1/chat/completions"


def test_ollama_host_none_usa_a_omissao():
    """Cobre 'host: null' no config.json (JSON válido, mas diferente de
    omitir o campo) -- não deve rebentar com AttributeError."""
    f = FornecedorOllama(modelo="llama3.2", host=None)
    assert f.URL_API == f"{HOST_POR_OMISSAO}/v1/chat/completions"


def test_ollama_host_vazio_usa_a_omissao():
    f = FornecedorOllama(modelo="llama3.2", host="")
    assert f.URL_API == f"{HOST_POR_OMISSAO}/v1/chat/completions"


def test_ollama_pedido_e_resposta():
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"choices": [{"message": {"content": "ok local"}}]})) as m:
        f = FornecedorOllama(modelo="mistral")
        r = f.responder([{"role": "user", "content": "oi"}])
        assert r == "ok local"
        assert m.call_args[0][0].full_url == f"{HOST_POR_OMISSAO}/v1/chat/completions"


def test_ollama_registado_na_fabrica_com_host_customizado():
    f = criar_fornecedor("ollama", "llama3.2", host="http://outra-maquina:11434")
    assert f.host == "http://outra-maquina:11434"


# ---------- Anthropic (formato próprio: system separado, max_tokens
# obrigatório, resposta em blocos) ----------

from alguem.fornecedores.anthropic import FornecedorAnthropic


def test_anthropic_exige_chave_de_api():
    with pytest.raises(ErroFornecedorLLM, match="Falta a chave de API"):
        FornecedorAnthropic(modelo="x", api_key="")


def test_anthropic_separa_o_system_das_mensagens():
    f = FornecedorAnthropic(modelo="claude-sonnet-5", api_key="sk-ant-teste")
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"content": [{"type": "text", "text": "ok"}]})) as m:
        f.responder([
            {"role": "system", "content": "És o Alguem."},
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "olá!"},
            {"role": "user", "content": "outra pergunta"},
        ])
        corpo = json.loads(m.call_args[0][0].data.decode())
        assert corpo["system"] == "És o Alguem."
        assert corpo["messages"] == [
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "olá!"},
            {"role": "user", "content": "outra pergunta"},
        ]


def test_anthropic_sem_mensagem_de_sistema_nao_manda_o_campo():
    f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"content": [{"type": "text", "text": "ok"}]})) as m:
        f.responder([{"role": "user", "content": "oi"}])
        corpo = json.loads(m.call_args[0][0].data.decode())
        assert "system" not in corpo


def test_anthropic_envia_max_tokens_obrigatorio():
    f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"content": [{"type": "text", "text": "ok"}]})) as m:
        f.responder([{"role": "user", "content": "oi"}])
        corpo = json.loads(m.call_args[0][0].data.decode())
        assert corpo["max_tokens"] > 0


def test_anthropic_cabecalhos_corretos():
    f = FornecedorAnthropic(modelo="x", api_key="sk-ant-teste")
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"content": [{"type": "text", "text": "ok"}]})) as m:
        f.responder([{"role": "user", "content": "oi"}])
        pedido = m.call_args[0][0]
        assert pedido.get_header("X-api-key") == "sk-ant-teste"
        assert pedido.get_header("Anthropic-version") == "2023-06-01"


def test_anthropic_concatena_varios_blocos_de_texto():
    f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
    with patch("urllib.request.urlopen", return_value=_resposta_falsa(
            {"content": [{"type": "text", "text": "parte 1. "},
                         {"type": "text", "text": "parte 2."}]})):
        assert f.responder([{"role": "user", "content": "oi"}]) == "parte 1. parte 2."


def test_anthropic_ignora_blocos_que_nao_sao_texto():
    f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
    with patch("urllib.request.urlopen", return_value=_resposta_falsa(
            {"content": [{"type": "tool_use", "id": "x"}, {"type": "text", "text": "resposta"}]})):
        assert f.responder([{"role": "user", "content": "oi"}]) == "resposta"


def test_anthropic_sem_blocos_de_texto_da_erro():
    f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"content": [{"type": "tool_use"}]})):
        with pytest.raises(ErroFornecedorLLM, match="formato inesperado"):
            f.responder([{"role": "user", "content": "oi"}])


def test_anthropic_bloco_de_texto_com_valor_nulo_da_erro():
    """Um bloco com type='text' mas text=None (não devia acontecer na
    prática, mas defensivamente) tem de dar erro claro, não rebentar
    com um TypeError cru dentro do ''.join(...)."""
    f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
    with patch("urllib.request.urlopen",
               return_value=_resposta_falsa({"content": [{"type": "text", "text": None}]})):
        with pytest.raises(ErroFornecedorLLM, match="formato inesperado"):
            f.responder([{"role": "user", "content": "oi"}])


def test_anthropic_erro_http():
    erro = urllib.error.HTTPError("url", 400, "Bad Request", {}, None)
    erro.read = lambda: b'{"error": "modelo desconhecido"}'
    with patch("urllib.request.urlopen", side_effect=erro):
        f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
        with pytest.raises(ErroFornecedorLLM, match="HTTP 400"):
            f.responder([{"role": "user", "content": "oi"}])


def test_anthropic_erro_de_rede():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sem ligação")):
        f = FornecedorAnthropic(modelo="x", api_key="sk-teste")
        with pytest.raises(ErroFornecedorLLM, match="Não foi possível contactar"):
            f.responder([{"role": "user", "content": "oi"}])


# ---------- fábrica: os 5 novos fornecedores ----------

def test_criar_fornecedor_openai():
    f = criar_fornecedor("openai", "gpt-4o-mini", "sk-teste")
    assert isinstance(f, FornecedorOpenAI)


def test_criar_fornecedor_opencode():
    f = criar_fornecedor("opencode", "deepseek-v4", "sk-teste")
    assert isinstance(f, FornecedorOpenCode)


def test_criar_fornecedor_huggingface():
    f = criar_fornecedor("huggingface", "modelo:provider", "hf_teste")
    assert isinstance(f, FornecedorHuggingFace)


def test_criar_fornecedor_ollama_sem_chave():
    f = criar_fornecedor("ollama", "llama3.2")
    assert isinstance(f, FornecedorOllama)


def test_criar_fornecedor_anthropic():
    f = criar_fornecedor("anthropic", "claude-sonnet-5", "sk-ant-teste")
    assert isinstance(f, FornecedorAnthropic)


def test_criar_fornecedor_campo_extra_nao_suportado_da_erro_amigavel():
    """Um campo em credenciais.<fornecedor> que o construtor não
    conhece (ex: pôr 'host' num fornecedor que não é a Ollama) deve dar
    um erro claro, não um TypeError cru."""
    with pytest.raises(ErroFornecedorLLM, match="Configuração inválida"):
        criar_fornecedor("openai", "gpt-4o-mini", "sk-teste", campo_que_nao_existe="x")


def test_fabrica_tem_7_fornecedores_registados():
    assert len(FORNECEDORES) == 7
    assert set(FORNECEDORES) == {
        "openrouter", "gemini", "openai", "anthropic", "huggingface", "ollama", "opencode",
    }
