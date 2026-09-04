# -*- coding: utf-8 -*-
"""Testes de online.alguem_ponte -- a única adaptação necessária para
reaproveitar alguem/ no serviço web."""
import json

import pytest

import alguem_ponte
import autenticacao
import bd
import configuracao_llm
import definicoes
import grupos
import prompts_configuraveis


def _primeiro_evento(tutor):
    with open(tutor.registador.caminho, encoding="utf-8") as f:
        return json.loads(f.readline())


# ---------- ON-26: mesmo limite de AG-28 aplicado no ponto de entrada do online ----------

def test_limitar_ficheiros_visiveis_dentro_do_limite_fica_intacto():
    ficheiros = [("a.algo", "conteudo a"), ("b.algo", "conteudo b")]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    assert resultado == ficheiros


def test_limitar_ficheiros_visiveis_corta_pelo_numero_de_ficheiros(monkeypatch):
    monkeypatch.setattr(alguem_ponte, "LIMITE_FICHEIROS", 2)
    ficheiros = [(f"f{i}.algo", f"conteudo {i}") for i in range(5)]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    assert len(resultado) == 2


def test_limitar_ficheiros_visiveis_trunca_por_bytes_totais(monkeypatch):
    monkeypatch.setattr(alguem_ponte, "LIMITE_BYTES_TOTAL", 20)
    ficheiros = [("grande.algo", "x" * 100)]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    assert len(resultado) == 1
    nome, conteudo = resultado[0]
    assert "truncado" in conteudo


def test_limitar_ficheiros_visiveis_para_de_incluir_apos_esgotar_bytes(monkeypatch):
    monkeypatch.setattr(alguem_ponte, "LIMITE_BYTES_TOTAL", 15)
    ficheiros = [("a.algo", "x" * 10), ("b.algo", "y" * 10), ("c.algo", "z" * 10)]
    resultado = alguem_ponte.limitar_ficheiros_visiveis(ficheiros)
    nomes = [n for n, _ in resultado]
    # a.algo entra inteiro (10 bytes), b.algo entra truncado (esgota o
    # orçamento de 15), c.algo não entra de todo
    assert nomes == ["a.algo", "b.algo"]
    assert "truncado" in dict(resultado)["b.algo"]


# ---------- achado 2 (PlanoAuditoria.md): revalidar o host do Ollama a cada uso ----------

def _guardar_configuracao_pessoal_ativa(estudante_id, fornecedor, modelo, api_key, host=None):
    """Cria uma configuração pessoal e torna-a a ativa para 'apoio' --
    equivalente, para efeitos destes testes, ao antigo guardar_credencial
    (que guardava uma única credencial já implicitamente 'ativa')."""
    configuracao_llm.definir_permissao("apoio", True)
    config_id = configuracao_llm.criar_configuracao(
        estudante_id, f"{fornecedor} · {modelo}", fornecedor, modelo, api_key, host=host)
    configuracao_llm.definir_selecao_estudante(estudante_id, "apoio", config_id)
    return config_id


def test_construir_alguem_rejeita_host_que_passou_a_apontar_para_interno():
    """_validar_host_ollama já corre em criar_configuracao, mas só uma
    vez, ao guardar -- um domínio com TTL baixo pode resolver para um
    IP público nesse momento e para um IP interno mais tarde (DNS
    rebinding). Aqui simula-se isso: guarda-se com um host válido,
    depois altera-se diretamente na BD para um IP interno (sem passar
    pela validação de criar_configuracao, tal como uma resolução DNS
    diferente também não passaria por ela) -- construir_alguem() tem
    de recusar, não só confiar no que já estava guardado."""
    id_est = autenticacao.registar("ollama@escola.pt", "password123")
    config_id = _guardar_configuracao_pessoal_ativa(
        id_est, "ollama", "llama3", "", host="http://exemplo.pt:11434")
    with bd.sessao_bd() as ligacao:
        ligacao.execute(
            "UPDATE configuracao_llm SET host = %s WHERE id = %s",
            ("http://127.0.0.1:11434", config_id),
        )
    with pytest.raises(alguem_ponte.ErroAlguemIndisponivel, match="deixou de ser válido"):
        alguem_ponte.construir_alguem(id_est)


def test_construir_alguem_aceita_host_ollama_ainda_valido():
    id_est = autenticacao.registar("ollama2@escola.pt", "password123")
    _guardar_configuracao_pessoal_ativa(
        id_est, "ollama", "llama3", "", host="http://exemplo.pt:11434")
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.fornecedor.host == "http://exemplo.pt:11434"


# ---------- mensagem de indisponibilidade distingue "podes resolver tu" de "não podes" ----------

def test_construir_alguem_sem_llm_nenhum_disponivel_nao_e_acionavel():
    """Sem configuração global e sem permissão para uma pessoal, não há
    nada que o estudante possa fazer -- a mensagem não deve mandá-lo às
    Definições (ver ErroAlguemIndisponivel.acionavel, usado por
    main.py:ws_alguem e app.js:desativarEntradaAlguem)."""
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(alguem_ponte.ErroAlguemIndisponivel) as excinfo:
        alguem_ponte.construir_alguem(id_est)
    assert "configuraste" not in str(excinfo.value)
    assert excinfo.value.acionavel is False


def test_construir_alguem_permitido_mas_sem_configuracao_pessoal_e_acionavel():
    """Com permissão ligada, falta só a configuração pessoal em si --
    isso o estudante consegue resolver sozinho em Definições."""
    id_est = autenticacao.registar("a@b.com", "password123")
    configuracao_llm.definir_permissao("apoio", True)
    with pytest.raises(alguem_ponte.ErroAlguemIndisponivel) as excinfo:
        alguem_ponte.construir_alguem(id_est)
    assert "configuraste" in str(excinfo.value)
    assert excinfo.value.acionavel is True


def test_construir_alguem_com_config_global_ignora_falta_de_permissao():
    """Havendo uma configuração global de apoio, o estudante nem precisa
    de permissão pessoal nem de nada configurado -- deve simplesmente
    funcionar (regra de precedência, ver configuracao_llm.
    resolver_configuracao_ativa)."""
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    global_id = configuracao_llm.criar_configuracao(
        None, "Global", "openai", "gpt-4o-mini", "sk-global", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("apoio", global_id)
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.fornecedor.modelo == "gpt-4o-mini"


# ---------- Fase 3: guardião com fornecedor próprio ----------

def _configurar_apoio_global(admin_id, modelo="gpt-4o-mini"):
    global_id = configuracao_llm.criar_configuracao(
        None, "Apoio global", "openai", modelo, "sk-apoio", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("apoio", global_id)


def test_construir_alguem_sem_guardiao_global_fica_sem_guardiao():
    """usar_guardiao continua ligado por omissão (definicoes.
    usar_guardiao), mas sem NENHUMA configuração global para 'guardiao'
    (não há seleção pessoal possível, ver PAPEIS_PESSOAIS) a conversa
    continua sem guardião -- não deve, de forma nenhuma, reaproveitar o
    fornecedor de apoio (ver o 'elif' antigo em tutor.py, que este
    caminho tem de evitar explicitamente)."""
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_apoio_global(admin_id)
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.guardiao is None
    assert tutor.politica.usar_guardiao is False


def test_construir_alguem_com_guardiao_global_usa_fornecedor_proprio():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_apoio_global(admin_id, modelo="gpt-4o-mini")
    guardiao_id = configuracao_llm.criar_configuracao(
        None, "Guardião global", "anthropic", "claude-3-haiku", "sk-guardiao", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("guardiao", guardiao_id)
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.guardiao is not None
    assert tutor.guardiao.fornecedor.modelo == "claude-3-haiku"
    assert tutor.fornecedor.modelo == "gpt-4o-mini"
    assert tutor.politica.usar_guardiao is True


def test_construir_alguem_usar_guardiao_desligado_ignora_config_guardiao():
    """O interruptor admin 'usar_guardiao' manda por cima de qualquer
    configuração global existente para o papel -- desligado, o
    guardião nunca é construído, mesmo com uma configuração válida."""
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_apoio_global(admin_id)
    guardiao_id = configuracao_llm.criar_configuracao(
        None, "Guardião global", "anthropic", "claude-3-haiku", "sk-guardiao", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("guardiao", guardiao_id)
    definicoes.definir_usar_guardiao(False)
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.guardiao is None


# ---------- Fase 3: nível máximo de ajuda e prompts editáveis pelo admin ----------

def test_construir_alguem_usa_nivel_maximo_ajuda_do_admin():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_apoio_global(admin_id)
    definicoes.definir_nivel_maximo_ajuda(2)
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.politica.nivel_maximo_ajuda == 2


def test_construir_alguem_usa_prompt_tutor_personalizado():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_apoio_global(admin_id)
    prompts_configuraveis.definir_prompt("tutor", "Sou um tutor de teste.", admin_id)
    tutor = alguem_ponte.construir_alguem(id_est)
    assert "Sou um tutor de teste." in tutor.historico[0]["content"]


# ---------- Fase 4: identificação direta (email) e campos novos em inicio_sessao ----------

def test_construir_alguem_identifica_a_sessao_pelo_email_nao_pelo_pseudonimo():
    """Ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção 4/Fase 4 --
    reverte a pseudonimização usada até à Fase 3."""
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_apoio_global(admin_id)
    tutor = alguem_ponte.construir_alguem(id_est)
    assert tutor.registador.id_estudante == "a@b.com"
    pseudonimo = autenticacao.obter_id_pseudonimo(id_est)
    evento = _primeiro_evento(tutor)
    assert evento["id_estudante"] == "a@b.com"
    assert evento["id_estudante"] != pseudonimo


def test_construir_alguem_regista_apoio_escopo_global():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_global = autenticacao.registar("global@escola.pt", "password123")
    _configurar_apoio_global(admin_id)
    tutor_global = alguem_ponte.construir_alguem(id_global)
    assert _primeiro_evento(tutor_global)["apoio_escopo"] == "global"


def test_construir_alguem_regista_apoio_escopo_pessoal():
    """Sem NENHUMA configuração global de apoio -- só assim a pessoal
    chega a ser usada (regra de precedência, ver
    configuracao_llm.resolver_configuracao_ativa)."""
    id_pessoal = autenticacao.registar("pessoal@escola.pt", "password123")
    _guardar_configuracao_pessoal_ativa(id_pessoal, "openai", "gpt-4o-mini", "sk-pessoal")
    tutor_pessoal = alguem_ponte.construir_alguem(id_pessoal)
    assert _primeiro_evento(tutor_pessoal)["apoio_escopo"] == "pessoal"


def test_construir_alguem_regista_guardiao_escopo_e_fornecedor():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_apoio_global(admin_id)

    # sem guardião global -- "indisponivel", nunca "pessoal"
    tutor_sem = alguem_ponte.construir_alguem(id_est)
    evento_sem = _primeiro_evento(tutor_sem)
    assert evento_sem["guardiao_escopo"] == "indisponivel"
    assert evento_sem["guardiao_fornecedor"] is None

    guardiao_id = configuracao_llm.criar_configuracao(
        None, "Guardião global", "anthropic", "claude-3-haiku", "sk-guardiao", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("guardiao", guardiao_id)
    tutor_com = alguem_ponte.construir_alguem(id_est)
    evento_com = _primeiro_evento(tutor_com)
    assert evento_com["guardiao_escopo"] == "global"
    assert evento_com["guardiao_fornecedor"] == "anthropic"
    assert evento_com["guardiao_modelo"] == "claude-3-haiku"


def test_construir_alguem_regista_o_grupo_do_estudante():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    _configurar_apoio_global(admin_id)

    id_com_grupo = autenticacao.registar("turma@escola.pt", "password123")
    grupo = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.reatribuir_grupo(id_com_grupo, grupo["id"])
    tutor_com_grupo = alguem_ponte.construir_alguem(id_com_grupo)
    assert _primeiro_evento(tutor_com_grupo)["grupo"] == "Turma A"

    id_sem_grupo = autenticacao.registar("solo@escola.pt", "password123")
    tutor_sem_grupo = alguem_ponte.construir_alguem(id_sem_grupo)
    assert _primeiro_evento(tutor_sem_grupo)["grupo"] is None
