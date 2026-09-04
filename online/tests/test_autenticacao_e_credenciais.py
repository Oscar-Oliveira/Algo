# -*- coding: utf-8 -*-
import os

import pytest

import autenticacao
import configuracao_llm
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


# ---------- ON-10: rejeitar chaves de cifragem obviamente pouco aleatórias ----------

def test_cifragem_com_chave_pouco_aleatoria_da_erro_claro(monkeypatch):
    import base64
    chave_fraca = base64.urlsafe_b64encode(b"\x00" * 32).decode("ascii")
    monkeypatch.setenv(cifragem.VARIAVEL_AMBIENTE_CHAVE, chave_fraca)
    with pytest.raises(cifragem.ErroCifragem, match="pouco aleatória"):
        cifragem.cifrar("x")


def test_cifragem_com_chave_gerada_normalmente_nao_e_rejeitada():
    chave_boa = cifragem.gerar_chave_nova()
    assert not cifragem._chave_parece_pouco_aleatoria(chave_boa)


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


# ---------- ON-13: bloqueio de passwords comuns ----------

@pytest.mark.parametrize("password_comum", [
    "password", "PASSWORD", "12345678", "qwerty123", "iloveyou",
])
def test_registar_com_password_comum_da_erro(password_comum):
    with pytest.raises(autenticacao.ErroAutenticacao, match="comum"):
        autenticacao.registar("a@b.com", password_comum)


def test_registar_com_password_incomum_funciona():
    autenticacao.registar("a@b.com", "umaPasswordBemMenosObvia9")  # não deve levantar


# ---------- ON-11: rate limiting de login por conta ----------

def test_login_bloqueia_apos_tentativas_falhadas_repetidas():
    autenticacao.registar("a@b.com", "password123")
    for _ in range(autenticacao.LIMIAR_TENTATIVAS_LOGIN):
        with pytest.raises(autenticacao.ErroAutenticacao, match="incorretos"):
            autenticacao.autenticar("a@b.com", "password_errada")
    # mesmo com a password CORRETA, a conta está bloqueada agora
    with pytest.raises(autenticacao.ErroAutenticacao, match="Demasiadas tentativas"):
        autenticacao.autenticar("a@b.com", "password123")


def test_login_bloqueado_nao_verifica_a_password(monkeypatch):
    """Depois de bloqueada, nem sequer deve chamar bcrypt.checkpw --
    poupa ciclos numa conta já bloqueada."""
    autenticacao.registar("a@b.com", "password123")
    for _ in range(autenticacao.LIMIAR_TENTATIVAS_LOGIN):
        with pytest.raises(autenticacao.ErroAutenticacao):
            autenticacao.autenticar("a@b.com", "password_errada")

    def checkpw_que_nao_deveria_ser_chamado(*a, **kw):
        raise AssertionError("bcrypt.checkpw não devia ser chamado numa conta bloqueada")
    monkeypatch.setattr(autenticacao.bcrypt, "checkpw", checkpw_que_nao_deveria_ser_chamado)

    with pytest.raises(autenticacao.ErroAutenticacao, match="Demasiadas tentativas"):
        autenticacao.autenticar("a@b.com", "password123")


def test_login_bem_sucedido_repoe_o_contador_de_falhas():
    autenticacao.registar("a@b.com", "password123")
    for _ in range(autenticacao.LIMIAR_TENTATIVAS_LOGIN - 1):
        with pytest.raises(autenticacao.ErroAutenticacao):
            autenticacao.autenticar("a@b.com", "password_errada")
    autenticacao.autenticar("a@b.com", "password123")  # repõe o contador
    for _ in range(autenticacao.LIMIAR_TENTATIVAS_LOGIN - 1):
        with pytest.raises(autenticacao.ErroAutenticacao, match="incorretos"):
            autenticacao.autenticar("a@b.com", "password_errada")
    autenticacao.autenticar("a@b.com", "password123")  # continua a funcionar, não bloqueou


@pytest.mark.parametrize("tentativas,minimo,maximo", [
    (5, 60, 60),
    (6, 120, 120),
    (7, 240, 240),
    (20, 3600, 3600),  # nunca ultrapassa o teto
])
def test_duracao_do_bloqueio_cresce_exponencialmente_ate_um_teto(tentativas, minimo, maximo):
    duracao = autenticacao._duracao_bloqueio_segundos(tentativas)
    assert minimo <= duracao <= maximo


def test_registar_email_duplicado():
    autenticacao.registar("a@b.com", "password123")
    with pytest.raises(autenticacao.ErroAutenticacao) as excinfo:
        autenticacao.registar("a@b.com", "outrapassword")
    # ON-12: a mensagem é deliberadamente genérica -- não confirma que
    # o motivo é especificamente o email já existir
    assert "Já existe" not in str(excinfo.value)


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


def test_password_nunca_fica_em_texto_simples(dsn):
    id_est = autenticacao.registar("a@b.com", "password123", dsn=dsn)
    import bd
    with bd.sessao_bd(dsn) as ligacao:
        linha = ligacao.execute("SELECT password_hash FROM estudante WHERE id=%s", (id_est,)).fetchone()
    assert b"password123" not in bytes(linha["password_hash"])


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


def test_bootstrap_tardio_ainda_e_bloqueado_por_grupo_desativado(monkeypatch):
    """Achado 3 (PlanoAuditoria.md): a promoção tardia a admin
    (ONLINE_EMAIL_ADMIN configurada DEPOIS de a conta já existir e já
    pertencer a um grupo entretanto desativado) continua bloqueada pelo
    grupo desativado -- neste momento a conta AINDA não é admin
    (admin=False até este mesmo autenticar() a promover), por isso o
    bloqueio por grupo desativado (só para não-admin, ver
    _grupo_do_estudante_esta_inativo) ainda se aplica. Contraste com
    test_login_de_admin_nao_e_bloqueado_por_grupo_desativado, onde a
    conta já é admin no momento do login."""
    import grupos
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    grupo = grupos.criar_grupo("Grupo A")
    id_est = autenticacao.registar("professor@escola.pt", "password123", codigo_grupo=grupo["codigo"])
    grupos.desativar_grupo(grupo["id"])

    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    with pytest.raises(autenticacao.ErroAutenticacao, match="grupo foi desativado"):
        autenticacao.autenticar("professor@escola.pt", "password123")


# ---------- registo com código de grupo ----------

def test_registar_sem_codigo_de_grupo_fica_sem_grupo():
    import grupos
    id_est = autenticacao.registar("a@b.com", "password123")
    todos = {c["id"]: c for c in autenticacao.listar_todos()}
    assert todos[id_est]["grupo_id"] is None


def test_registar_com_codigo_de_grupo_valido():
    import grupos
    grupo = grupos.criar_grupo("Grupo A")
    id_est = autenticacao.registar("a@b.com", "password123", codigo_grupo=grupo["codigo"])
    todos = {c["id"]: c for c in autenticacao.listar_todos()}
    assert todos[id_est]["grupo_id"] == grupo["id"]


def test_registar_com_codigo_de_grupo_invalido_da_erro():
    with pytest.raises(autenticacao.ErroCodigoGrupoInvalido, match="inválido"):
        autenticacao.registar("a@b.com", "password123", codigo_grupo="nao-existe")


def test_registar_com_codigo_de_grupo_desativado_da_erro():
    import grupos
    grupo = grupos.criar_grupo("Grupo A")
    grupos.desativar_grupo(grupo["id"])
    with pytest.raises(autenticacao.ErroCodigoGrupoInvalido, match="inválido"):
        autenticacao.registar("a@b.com", "password123", codigo_grupo=grupo["codigo"])


# ---------- grupo desativado bloqueia login (sem exceção para admin) ----------

def test_login_bloqueado_quando_grupo_esta_desativado(monkeypatch):
    import grupos
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    grupo = grupos.criar_grupo("Grupo A")
    autenticacao.registar("aluno@escola.pt", "password123", codigo_grupo=grupo["codigo"])
    grupos.desativar_grupo(grupo["id"])
    with pytest.raises(autenticacao.ErroAutenticacao, match="grupo foi desativado"):
        autenticacao.autenticar("aluno@escola.pt", "password123")


def test_login_de_admin_nao_e_bloqueado_por_grupo_desativado(monkeypatch):
    """Decisão explícita (reverte a versão anterior desta regra, de
    quando só havia um tipo de admin): um admin de grupo pode gerir
    várias turmas ao mesmo tempo -- bloquear-lhe o login só porque UMA
    delas foi desativada não faria sentido. O bloqueio por grupo
    desativado só se aplica a contas não-admin."""
    import grupos
    monkeypatch.setenv("ONLINE_EMAIL_ADMIN", "professor@escola.pt")
    grupo = grupos.criar_grupo("Grupo A")
    id_admin = autenticacao.registar("professor@escola.pt", "password123", codigo_grupo=grupo["codigo"])
    assert autenticacao.eh_admin(id_admin) is True
    grupos.desativar_grupo(grupo["id"])
    assert autenticacao.autenticar("professor@escola.pt", "password123") == id_admin


def test_login_permitido_quando_grupo_e_reativado(monkeypatch):
    import grupos
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    grupo = grupos.criar_grupo("Grupo A")
    id_est = autenticacao.registar("aluno@escola.pt", "password123", codigo_grupo=grupo["codigo"])
    grupos.desativar_grupo(grupo["id"])
    grupos.ativar_grupo(grupo["id"])
    assert autenticacao.autenticar("aluno@escola.pt", "password123") == id_est


def test_login_sem_grupo_nao_e_afetado_por_nenhum_grupo(monkeypatch):
    import grupos
    monkeypatch.delenv("ONLINE_EMAIL_ADMIN", raising=False)
    grupo = grupos.criar_grupo("Grupo A")
    grupos.desativar_grupo(grupo["id"])
    id_est = autenticacao.registar("aluno@escola.pt", "password123")  # sem código
    assert autenticacao.autenticar("aluno@escola.pt", "password123") == id_est


# ---------- privilégios de admin (conceder/remover) ----------

def test_tornar_admin_concede_privilegios():
    id_est = autenticacao.registar("a@b.com", "password123")
    assert autenticacao.eh_admin(id_est) is False
    autenticacao.tornar_admin(id_est)
    assert autenticacao.eh_admin(id_est) is True


def test_remover_admin_com_mais_do_que_um_admin():
    id_admin1 = autenticacao.registar("a@b.com", "password123")
    id_admin2 = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin1)
    autenticacao.tornar_admin(id_admin2)

    alterou = autenticacao.remover_admin(id_admin2, ator_id=id_admin1)
    assert alterou is True
    assert autenticacao.eh_admin(id_admin2) is False


def test_remover_admin_nao_se_deixasse_zero_admins():
    id_admin1 = autenticacao.registar("a@b.com", "password123")
    id_outro = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin1)

    alterou = autenticacao.remover_admin(id_admin1, ator_id=id_outro)
    assert alterou is False
    assert autenticacao.eh_admin(id_admin1) is True


def test_remover_admin_do_proprio_ator_nao_muda_nada():
    id_admin1 = autenticacao.registar("a@b.com", "password123")
    id_admin2 = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin1)
    autenticacao.tornar_admin(id_admin2)

    alterou = autenticacao.remover_admin(id_admin1, ator_id=id_admin1)
    assert alterou is False
    assert autenticacao.eh_admin(id_admin1) is True


# ---------- admin global vs. admin de grupo ----------

def test_tornar_admin_fica_global_por_omissao():
    """DEFAULT TRUE na coluna admin_global (bd.py) -- decisão
    deliberada: preserva o comportamento atual (todos os admins
    equivalentes) até alguém decidir restringir um admin a um grupo."""
    id_est = autenticacao.registar("a@b.com", "password123")
    autenticacao.tornar_admin(id_est)
    assert autenticacao.eh_admin_global(id_est) is True


def test_eh_admin_global_falso_para_nao_admin():
    id_est = autenticacao.registar("a@b.com", "password123")
    assert autenticacao.eh_admin_global(id_est) is False


def test_definir_admin_global_para_false_torna_admin_de_grupo():
    id_admin1 = autenticacao.registar("a@b.com", "password123")
    id_admin2 = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin1)
    autenticacao.tornar_admin(id_admin2)

    alterou = autenticacao.definir_admin_global(id_admin2, False, ator_id=id_admin1)
    assert alterou is True
    assert autenticacao.eh_admin_global(id_admin2) is False
    assert autenticacao.eh_admin(id_admin2) is True  # continua admin, só deixa de ser global


def test_definir_admin_global_nao_se_deixasse_zero_admins_globais():
    id_admin1 = autenticacao.registar("a@b.com", "password123")
    id_admin2 = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin1)
    autenticacao.tornar_admin(id_admin2)
    autenticacao.definir_admin_global(id_admin2, False, ator_id=id_admin1)

    alterou = autenticacao.definir_admin_global(id_admin1, False, ator_id=id_admin2)
    assert alterou is False
    assert autenticacao.eh_admin_global(id_admin1) is True


def test_definir_admin_global_do_proprio_ator_nao_muda_nada():
    id_admin1 = autenticacao.registar("a@b.com", "password123")
    id_admin2 = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin1)
    autenticacao.tornar_admin(id_admin2)

    alterou = autenticacao.definir_admin_global(id_admin1, False, ator_id=id_admin1)
    assert alterou is False
    assert autenticacao.eh_admin_global(id_admin1) is True


def test_remover_admin_do_unico_admin_global_nao_muda_nada_mesmo_havendo_outro_admin():
    """Guarda extra em remover_admin (não só 'sobra pelo menos um
    admin'): remover o estatuto de admin por completo do único admin
    GLOBAL não pode deixar a aplicação sem ninguém capaz de aceder às
    abas restritas (Utilizadores, Grupos, ...), mesmo que sobre um
    admin de grupo."""
    id_admin_global = autenticacao.registar("a@b.com", "password123")
    id_admin_grupo = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin_global)
    autenticacao.tornar_admin(id_admin_grupo)
    autenticacao.definir_admin_global(id_admin_grupo, False, ator_id=id_admin_global)

    alterou = autenticacao.remover_admin(id_admin_global, ator_id=id_admin_grupo)
    assert alterou is False
    assert autenticacao.eh_admin(id_admin_global) is True


def test_listar_todos_inclui_admin_global_e_grupos_geridos():
    import grupos
    grupo = grupos.criar_grupo("Grupo A")
    id_admin_global = autenticacao.registar("a@b.com", "password123")
    id_admin_grupo = autenticacao.registar("c@d.com", "password123")
    autenticacao.tornar_admin(id_admin_global)
    autenticacao.tornar_admin(id_admin_grupo)
    autenticacao.definir_admin_global(id_admin_grupo, False, ator_id=id_admin_global)
    grupos.definir_grupos_geridos(id_admin_grupo, [grupo["id"]])

    contas = {c["id"]: c for c in autenticacao.listar_todos()}
    assert contas[id_admin_global]["admin_global"] is True
    assert contas[id_admin_global]["grupos_geridos_ids"] == []
    assert contas[id_admin_grupo]["admin_global"] is False
    assert contas[id_admin_grupo]["grupos_geridos_ids"] == [grupo["id"]]


# ---------- configuração de LLM ----------

def test_sem_configuracao_llm():
    id_est = autenticacao.registar("a@b.com", "password123")
    assert configuracao_llm.listar_configuracoes_estudante(id_est) == []


def test_criar_e_obter_configuracao():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(id_est, "Principal", "openai", "gpt-4o-mini", "sk-teste")
    c = configuracao_llm.obter_configuracao(config_id)
    assert c.etiqueta == "Principal"
    assert c.fornecedor == "openai"
    assert c.modelo == "gpt-4o-mini"
    assert c.api_key == "sk-teste"
    assert c.estudante_id == id_est


def test_criar_varias_configuracoes_ficam_independentes():
    id_est = autenticacao.registar("a@b.com", "password123")
    configuracao_llm.criar_configuracao(id_est, "Rápida", "openai", "gpt-4o-mini", "sk-1")
    # 8.8.8.8 é um IP público real (Google DNS) só para não depender de
    # resolução de DNS num ambiente de teste sem rede -- não é loopback
    # nem privado, por isso passa a validação de ON-14.
    configuracao_llm.criar_configuracao(id_est, "Local", "ollama", "llama3.2", "", host="http://8.8.8.8:11434")
    configs = configuracao_llm.listar_configuracoes_estudante(id_est)
    assert {c.etiqueta for c in configs} == {"Rápida", "Local"}


def test_editar_configuracao_substitui_campos():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(id_est, "Principal", "openai", "gpt-4o-mini", "sk-1")
    configuracao_llm.editar_configuracao(config_id, "Principal", "ollama", "llama3.2", "", host="http://8.8.8.8:11434")
    c = configuracao_llm.obter_configuracao(config_id)
    assert c.fornecedor == "ollama"
    assert c.host == "http://8.8.8.8:11434"


def test_apagar_configuracao():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(id_est, "Principal", "openai", "gpt-4o-mini", "sk-1")
    configuracao_llm.apagar_configuracao(config_id)
    assert configuracao_llm.obter_configuracao(config_id) is None


# ---------- ON-15: 'host' só é suportado pelo fornecedor ollama ----------

def test_host_em_fornecedor_que_nao_e_ollama_da_erro():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="ollama"):
        configuracao_llm.criar_configuracao(
            id_est, "Principal", "openai", "gpt-4o-mini", "sk-teste", host="http://8.8.8.8:11434")


def test_host_em_ollama_continua_a_funcionar():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(
        id_est, "Local", "ollama", "llama3.2", "", host="http://8.8.8.8:11434")
    c = configuracao_llm.obter_configuracao(config_id)
    assert c.host == "http://8.8.8.8:11434"


def test_configuracao_fornecedor_desconhecido():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="desconhecido"):
        configuracao_llm.criar_configuracao(id_est, "X", "naoexiste", "x", "chave")


def test_fornecedores_validos_vem_do_registo_real_do_alguem():
    """ARCH-13: antes uma segunda lista mantida à mão, que podia
    desatualizar-se em relação a alguem/fornecedores/__init__.py sem
    nenhum erro até alguém notar."""
    from alguem.fornecedores import FORNECEDORES
    assert configuracao_llm.FORNECEDORES_VALIDOS == frozenset(FORNECEDORES)


def test_configuracao_sem_etiqueta_da_erro():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="etiqueta"):
        configuracao_llm.criar_configuracao(id_est, "", "openai", "gpt-4o-mini", "sk-teste")


def test_configuracao_sem_chave_quando_e_obrigatoria():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="precisa de uma chave"):
        configuracao_llm.criar_configuracao(id_est, "X", "openai", "gpt-4o-mini", "")


def test_configuracao_ollama_nao_precisa_de_chave():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(id_est, "Local", "ollama", "llama3.2", "")
    c = configuracao_llm.obter_configuracao(config_id)
    assert c.fornecedor == "ollama"


# ---------- ON-14: SSRF via host da configuração Ollama ----------

@pytest.mark.parametrize("host", [
    "http://127.0.0.1:11434",       # loopback
    "http://localhost:11434",       # loopback (por nome)
    "http://169.254.169.254/",      # link-local -- metadata de cloud (AWS/GCP/Azure)
    "http://10.0.0.5:11434",        # rede privada
    "http://192.168.1.10:11434",    # rede privada
])
def test_configuracao_ollama_com_host_interno_e_rejeitada(host):
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="interno|privado"):
        configuracao_llm.criar_configuracao(id_est, "Local", "ollama", "llama3.2", "", host=host)


def test_configuracao_ollama_com_esquema_invalido_e_rejeitada():
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="inválido"):
        configuracao_llm.criar_configuracao(id_est, "Local", "ollama", "llama3.2", "", host="file:///etc/passwd")


def test_configuracao_ollama_com_host_publico_e_aceite():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(
        id_est, "Local", "ollama", "llama3.2", "", host="http://8.8.8.8:11434")
    c = configuracao_llm.obter_configuracao(config_id)
    assert c.host == "http://8.8.8.8:11434"


def test_configuracao_fica_cifrada_em_disco(dsn):
    id_est = autenticacao.registar("a@b.com", "password123", dsn=dsn)
    config_id = configuracao_llm.criar_configuracao(
        id_est, "Principal", "openai", "gpt-4o-mini", "sk-super-secreta", dsn=dsn)
    import bd
    with bd.sessao_bd(dsn) as ligacao:
        linha = ligacao.execute(
            "SELECT api_key_cifrada FROM configuracao_llm WHERE id=%s", (config_id,)
        ).fetchone()
    assert b"sk-super-secreta" not in bytes(linha["api_key_cifrada"])


# ---------- seleção por papel e regra de precedência ----------
# (ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção 2)

def test_selecao_estudante_recusa_configuracao_de_outra_conta():
    id_a = autenticacao.registar("a@b.com", "password123")
    id_b = autenticacao.registar("b@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(id_a, "X", "openai", "gpt-4o-mini", "sk-1")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="não pertence"):
        configuracao_llm.definir_selecao_estudante(id_b, "apoio", config_id)


def test_selecao_global_recusa_configuracao_pessoal():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(id_est, "X", "openai", "gpt-4o-mini", "sk-1")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="global"):
        configuracao_llm.definir_selecao_global("apoio", config_id)


def test_resolver_sem_nada_configurado_devolve_none():
    id_est = autenticacao.registar("a@b.com", "password123")
    assert configuracao_llm.resolver_configuracao_ativa(id_est, "apoio") is None


def test_resolver_usa_global_mesmo_com_permissao_desligada():
    admin_id = autenticacao.registar("admin@b.com", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    global_id = configuracao_llm.criar_configuracao(
        None, "Global", "openai", "gpt-4o-mini", "sk-global", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("apoio", global_id)
    c = configuracao_llm.resolver_configuracao_ativa(id_est, "apoio")
    assert c.id == global_id


def test_resolver_usa_pessoal_quando_permissao_ligada_e_sem_global():
    id_est = autenticacao.registar("a@b.com", "password123")
    configuracao_llm.definir_permissao("apoio", True)
    pessoal_id = configuracao_llm.criar_configuracao(id_est, "Minha", "openai", "gpt-4o-mini", "sk-pessoal")
    configuracao_llm.definir_selecao_estudante(id_est, "apoio", pessoal_id)
    c = configuracao_llm.resolver_configuracao_ativa(id_est, "apoio")
    assert c.id == pessoal_id


def test_resolver_ignora_pessoal_quando_permissao_desligada():
    id_est = autenticacao.registar("a@b.com", "password123")
    configuracao_llm.definir_permissao("apoio", False)
    pessoal_id = configuracao_llm.criar_configuracao(id_est, "Minha", "openai", "gpt-4o-mini", "sk-pessoal")
    configuracao_llm.definir_selecao_estudante(id_est, "apoio", pessoal_id)
    assert configuracao_llm.resolver_configuracao_ativa(id_est, "apoio") is None


def test_resolver_global_manda_sobre_pessoal():
    admin_id = autenticacao.registar("admin@b.com", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    configuracao_llm.definir_permissao("apoio", True)
    pessoal_id = configuracao_llm.criar_configuracao(id_est, "Minha", "openai", "gpt-4o-mini", "sk-pessoal")
    configuracao_llm.definir_selecao_estudante(id_est, "apoio", pessoal_id)
    global_id = configuracao_llm.criar_configuracao(
        None, "Global", "openai", "gpt-4o-mini", "sk-global", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("apoio", global_id)
    c = configuracao_llm.resolver_configuracao_ativa(id_est, "apoio")
    assert c.id == global_id


def test_apagar_configuracao_global_selecionada_limpa_a_selecao():
    admin_id = autenticacao.registar("admin@b.com", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    global_id = configuracao_llm.criar_configuracao(
        None, "Global", "openai", "gpt-4o-mini", "sk-global", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("apoio", global_id)
    configuracao_llm.apagar_configuracao(global_id)
    assert configuracao_llm.obter_selecao_global("apoio") is None
    assert configuracao_llm.resolver_configuracao_ativa(id_est, "apoio") is None


# ---------- guardião nunca é escolha pessoal do estudante (transparente para ele) ----------

def test_selecao_estudante_recusa_papel_guardiao():
    id_est = autenticacao.registar("a@b.com", "password123")
    config_id = configuracao_llm.criar_configuracao(id_est, "X", "openai", "gpt-4o-mini", "sk-1")
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="não tem seleção pessoal"):
        configuracao_llm.definir_selecao_estudante(id_est, "guardiao", config_id)


def test_permissao_recusa_papel_guardiao():
    with pytest.raises(configuracao_llm.ErroConfiguracaoLLM, match="não tem seleção pessoal"):
        configuracao_llm.definir_permissao("guardiao", True)


def test_resolver_guardiao_ignora_a_bd_mesmo_que_alguem_tenha_forcado_uma_selecao_pessoal():
    """Só por garantia extra (não devia ser possível chegar aqui por via
    normal, ver os dois testes acima): mesmo que a linha em
    selecao_llm_estudante exista na BD, resolver_configuracao_ativa nunca
    usa seleção pessoal para 'guardiao' -- só a global."""
    id_est = autenticacao.registar("a@b.com", "password123")
    assert configuracao_llm.resolver_configuracao_ativa(id_est, "guardiao") is None
    admin_id = autenticacao.registar("admin@b.com", "password123")
    global_id = configuracao_llm.criar_configuracao(
        None, "Global", "openai", "gpt-4o-mini", "sk-global", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("guardiao", global_id)
    c = configuracao_llm.resolver_configuracao_ativa(id_est, "guardiao")
    assert c.id == global_id


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
