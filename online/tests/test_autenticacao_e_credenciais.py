# -*- coding: utf-8 -*-
import os

import pytest

import autenticacao
import credenciais
import cifragem


# ---------- cifragem ----------

def test_cifrar_decifrar_texto():
    cifrado = cifragem.cifrar("sk-teste-123")
    assert cifrado != b"sk-teste-123"
    assert cifragem.decifrar(cifrado) == "sk-teste-123"


def test_cifrar_string_vazia():
    assert cifragem.cifrar("") == b""
    assert cifragem.decifrar(b"") == ""


def test_cifragem_sem_variavel_de_ambiente_da_erro_claro(monkeypatch):
    monkeypatch.delenv(cifragem.VARIAVEL_AMBIENTE_CHAVE, raising=False)
    with pytest.raises(cifragem.ErroCifragem, match="não está definida"):
        cifragem.cifrar("x")


# ---------- autenticação ----------

def test_registar_e_autenticar():
    id1 = autenticacao.registar("estudante@exemplo.com", "password123")
    id2 = autenticacao.autenticar("estudante@exemplo.com", "password123")
    assert id1 == id2


def test_autenticar_password_errada():
    autenticacao.registar("a@b.com", "password123")
    with pytest.raises(autenticacao.ErroAutenticacao, match="incorretos"):
        autenticacao.autenticar("a@b.com", "password_errada")


def test_autenticar_email_inexistente():
    with pytest.raises(autenticacao.ErroAutenticacao, match="incorretos"):
        autenticacao.autenticar("naoexiste@exemplo.com", "qualquer")


def test_mensagem_de_erro_igual_para_email_inexistente_e_password_errada():
    """Não deve ser possível distinguir 'este email não existe' de 'a
    password está errada' pela mensagem -- evita confirmar quais
    emails têm conta."""
    autenticacao.registar("a@b.com", "password123")
    mensagem1 = mensagem2 = None
    try:
        autenticacao.autenticar("a@b.com", "errada")
    except autenticacao.ErroAutenticacao as e:
        mensagem1 = str(e)
    try:
        autenticacao.autenticar("naoexiste@b.com", "errada")
    except autenticacao.ErroAutenticacao as e:
        mensagem2 = str(e)
    assert mensagem1 is not None and mensagem1 == mensagem2


def test_registar_email_duplicado():
    autenticacao.registar("a@b.com", "password123")
    with pytest.raises(autenticacao.ErroAutenticacao, match="Já existe"):
        autenticacao.registar("a@b.com", "outrapassword")


def test_registar_email_invalido():
    with pytest.raises(autenticacao.ErroAutenticacao, match="inválido"):
        autenticacao.registar("nao-e-um-email", "password123")


def test_registar_password_curta():
    with pytest.raises(autenticacao.ErroAutenticacao, match="8 caracteres"):
        autenticacao.registar("a@b.com", "curta")


def test_email_normalizado_para_minusculas():
    autenticacao.registar("Maiuscula@Exemplo.com", "password123")
    id_login = autenticacao.autenticar("maiuscula@exemplo.com", "password123")
    assert id_login is not None


def test_password_nunca_fica_em_texto_simples(caminho_bd):
    id_est = autenticacao.registar("a@b.com", "password123", caminho_bd)
    import bd
    with bd.sessao_bd(caminho_bd) as ligacao:
        linha = ligacao.execute("SELECT password_hash FROM estudante WHERE id=?", (id_est,)).fetchone()
    assert b"password123" not in linha["password_hash"]


def test_id_pseudonimo_diferente_do_id_da_conta():
    id_est = autenticacao.registar("a@b.com", "password123")
    pseudo = autenticacao.obter_id_pseudonimo(id_est)
    assert pseudo != str(id_est)
    import uuid
    uuid.UUID(pseudo)


# ---------- aprovação de contas (admin) ----------
# ONLINE_EMAIL_ADMIN por omissão não está definida em nenhum teste
# acima -- por isso o registo continua sempre aberto (aprovado=1
# automaticamente) em todos eles, sem precisar de nenhuma alteração.
# Estes testes é que ligam o "gate", só dentro de si próprios.

def test_sem_admin_configurado_conta_fica_logo_aprovada(monkeypatch):
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    id_est = autenticacao.registar("a@b.com", "password123")
    assert autenticacao.esta_aprovado(id_est) is True
    assert autenticacao.autenticar("a@b.com", "password123") == id_est


def test_email_admin_fica_logo_aprovado_e_e_admin(monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    id_est = autenticacao.registar("professor@escola.pt", "password123")
    assert autenticacao.esta_aprovado(id_est) is True
    assert autenticacao.eh_admin(id_est) is True
    assert autenticacao.autenticar("professor@escola.pt", "password123") == id_est


def test_conta_normal_fica_pendente_quando_ha_admin_configurado(monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    id_est = autenticacao.registar("aluno@escola.pt", "password123")
    assert autenticacao.esta_aprovado(id_est) is False
    assert autenticacao.eh_admin(id_est) is False
    with pytest.raises(autenticacao.ErroAutenticacao, match="pendente"):
        autenticacao.autenticar("aluno@escola.pt", "password123")


def test_aprovar_conta_permite_entrar(monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    id_est = autenticacao.registar("aluno@escola.pt", "password123")
    autenticacao.aprovar_conta(id_est)
    assert autenticacao.autenticar("aluno@escola.pt", "password123") == id_est


def test_rejeitar_conta_remove_a_conta_pendente(monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    id_est = autenticacao.registar("aluno@escola.pt", "password123")
    autenticacao.rejeitar_conta(id_est)
    assert autenticacao.listar_pendentes() == []
    with pytest.raises(autenticacao.ErroAutenticacao, match="incorretos"):
        autenticacao.autenticar("aluno@escola.pt", "password123")


def test_rejeitar_conta_nao_apaga_conta_ja_aprovada(monkeypatch):
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    id_est = autenticacao.registar("a@b.com", "password123")
    autenticacao.rejeitar_conta(id_est)  # já aprovada -- rejeitar não faz nada
    assert autenticacao.autenticar("a@b.com", "password123") == id_est


def test_listar_pendentes_so_mostra_contas_por_aprovar(monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    autenticacao.registar("professor@escola.pt", "password123")
    id_pendente = autenticacao.registar("aluno@escola.pt", "password123")
    pendentes = autenticacao.listar_pendentes()
    assert [p["id"] for p in pendentes] == [id_pendente]
    assert pendentes[0]["email"] == "aluno@escola.pt"


def test_revogar_conta_bloqueia_entrada_de_conta_aprovada(monkeypatch):
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    id_est = autenticacao.registar("a@b.com", "password123")
    autenticacao.revogar_conta(id_est)
    assert autenticacao.esta_aprovado(id_est) is False
    with pytest.raises(autenticacao.ErroAutenticacao, match="pendente"):
        autenticacao.autenticar("a@b.com", "password123")


def test_revogar_conta_nao_afeta_conta_admin(monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    id_est = autenticacao.registar("professor@escola.pt", "password123")
    autenticacao.revogar_conta(id_est)  # é admin -- revogar não faz nada
    assert autenticacao.autenticar("professor@escola.pt", "password123") == id_est


def test_listar_todos_inclui_pendentes_aprovados_e_admin(monkeypatch):
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    id_admin = autenticacao.registar("professor@escola.pt", "password123")
    id_pendente = autenticacao.registar("aluno@escola.pt", "password123")
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    id_aprovado = autenticacao.registar("outro@escola.pt", "password123")

    todos = {c["id"]: c for c in autenticacao.listar_todos()}
    assert set(todos) == {id_admin, id_pendente, id_aprovado}
    assert todos[id_admin]["admin"] == 1 and todos[id_admin]["aprovado"] == 1
    assert todos[id_pendente]["aprovado"] == 0
    assert todos[id_aprovado]["aprovado"] == 1 and todos[id_aprovado]["admin"] == 0


def test_admin_configurado_depois_da_conta_ja_existir(monkeypatch):
    """Bootstrap tardio: a conta do professor foi criada ANTES de
    ONLINE_EMAIL_ADMIN estar configurada -- autenticar() tem de a
    promover a admin/aprovada na primeira vez que entra, não deixá-la
    bloqueada para sempre."""
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    id_est = autenticacao.registar("professor@escola.pt", "password123")
    assert autenticacao.eh_admin(id_est) is False

    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    assert autenticacao.autenticar("professor@escola.pt", "password123") == id_est
    assert autenticacao.eh_admin(id_est) is True


# ---------- credenciais ----------

def test_sem_credencial_configurada():
    id_est = autenticacao.registar("a@b.com", "password123")
    assert credenciais.obter_credencial(id_est) is None


def test_guardar_e_ler_credencial():
    id_est = autenticacao.registar("a@b.com", "password123")
    credenciais.guardar_credencial(id_est, "openai", "gpt-4o-mini", "sk-teste")
    c = credenciais.obter_credencial(id_est)
    assert c.fornecedor == "openai"
    assert c.modelo == "gpt-4o-mini"
    assert c.api_key == "sk-teste"


def test_guardar_credencial_substitui_a_anterior():
    id_est = autenticacao.registar("a@b.com", "password123")
    credenciais.guardar_credencial(id_est, "openai", "gpt-4o-mini", "sk-1")
    credenciais.guardar_credencial(id_est, "ollama", "llama3.2", "", host="http://localhost:11434")
    c = credenciais.obter_credencial(id_est)
    assert c.fornecedor == "ollama"
    assert c.host == "http://localhost:11434"


def test_credencial_fornecedor_desconhecido():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(credenciais.ErroCredencial, match="desconhecido"):
        credenciais.guardar_credencial(id_est, "naoexiste", "x", "chave")


def test_credencial_sem_chave_quando_e_obrigatoria():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(credenciais.ErroCredencial, match="precisa de uma chave"):
        credenciais.guardar_credencial(id_est, "openai", "gpt-4o-mini", "")


def test_credencial_ollama_nao_precisa_de_chave():
    id_est = autenticacao.registar("a@b.com", "password123")
    credenciais.guardar_credencial(id_est, "ollama", "llama3.2", "")
    c = credenciais.obter_credencial(id_est)
    assert c.fornecedor == "ollama"


def test_credencial_fica_cifrada_em_disco(caminho_bd):
    id_est = autenticacao.registar("a@b.com", "password123", caminho_bd)
    credenciais.guardar_credencial(id_est, "openai", "gpt-4o-mini", "sk-super-secreta", caminho_bd=caminho_bd)
    import bd
    with bd.sessao_bd(caminho_bd) as ligacao:
        linha = ligacao.execute(
            "SELECT api_key_cifrada FROM credencial_llm WHERE estudante_id=?", (id_est,)
        ).fetchone()
    assert b"sk-super-secreta" not in linha["api_key_cifrada"]


# ---------- arranque do servidor: validação cedo das chaves ----------

def test_servidor_recusa_arrancar_sem_chave_de_cifragem(monkeypatch):
    """Reproduz o bug real reportado: sem esta validação, o erro só
    aparecia mais tarde, como um 500 confuso, ao tentar guardar a
    primeira credencial -- não no arranque do servidor."""
    import sys
    monkeypatch.delenv(cifragem.VARIAVEL_AMBIENTE_CHAVE, raising=False)
    monkeypatch.setenv("ONLINE_CHAVE_SESSAO", "x" * 32)
    for nome_modulo in list(sys.modules):
        if nome_modulo == "main":
            del sys.modules[nome_modulo]
    with pytest.raises(RuntimeError, match="ONLINE_CHAVE_CIFRAGEM"):
        import main


def test_servidor_recusa_arrancar_com_chave_de_cifragem_invalida(monkeypatch):
    import sys
    monkeypatch.setenv(cifragem.VARIAVEL_AMBIENTE_CHAVE, "isto-nao-e-uma-chave-fernet")
    monkeypatch.setenv("ONLINE_CHAVE_SESSAO", "x" * 32)
    for nome_modulo in list(sys.modules):
        if nome_modulo == "main":
            del sys.modules[nome_modulo]
    with pytest.raises(RuntimeError, match="não é uma chave Fernet válida"):
        import main
