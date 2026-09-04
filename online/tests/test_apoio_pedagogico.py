# -*- coding: utf-8 -*-
"""Testes de online.apoio_pedagogico -- terceiro papel de LLM (ver
docs/interno/PlanoAlguemLLMInvestigacao.md, secção 11/Fase 6): monta o
histórico filtrado de um estudante como factos compactos, encolhe-o de
forma determinística se necessário (sem LLM nenhum) e só depois gera
uma análise (o único passo que fala com um LLM), sempre com o controlo
de acesso por grupo já usado pela Investigação."""
import pytest

import apoio_pedagogico as ap
import autenticacao
import configuracao_llm
import grupos
import historico_codigo
import investigacao as inv
from alguem.nucleo.registador import Registador


def _sessao_com_turno(pasta_logs, email, pergunta="Como faço um ciclo?", resposta="Tenta pensar em repetição."):
    r = Registador(id_estudante=email, pasta_logs=str(pasta_logs))
    r.inicio_sessao("openrouter", "gpt-4o-mini", {}, [])
    turno = r.novo_turno()
    r.tentativa_guardiao(turno, 1, pergunta, resposta, "SAFE", 1, True)
    r.resposta_final(turno, resposta, 1, False)
    r.fim_sessao()


class _FornecedorFalso:
    def __init__(self):
        self.chamadas = []

    def responder(self, mensagens):
        self.chamadas.append(mensagens)
        return f"resumo-{len(self.chamadas)}"


def _configurar_llm_apoio_pedagogico(admin_id):
    config_id = configuracao_llm.criar_configuracao(
        None, "Etiqueta", "openai", "gpt-4o-mini", "sk-teste", criado_por=admin_id)
    configuracao_llm.definir_selecao_global("apoio_pedagogico", config_id)
    return config_id


# ---------- montar_blocos_historico ----------

def test_montar_blocos_historico_valida_tipos():
    with pytest.raises(ap.ErroApoioPedagogico):
        ap.montar_blocos_historico(1, "a@b.com", tipos=set())
    with pytest.raises(ap.ErroApoioPedagogico):
        ap.montar_blocos_historico(1, "a@b.com", tipos={"desconhecido"})


def test_montar_blocos_historico_so_alguem_e_um_facto_compacto_nao_a_transcricao(tmp_path):
    """Decisão revista: o bloco de uma sessão é um facto de uma linha
    (métricas), não a transcrição integral da conversa -- é o que
    permite a preparar_resumo nunca precisar de um LLM para encolher."""
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    historico_codigo.registar_execucao(id_est, "executa", "p.algo", [], "Sucesso")

    blocos = ap.montar_blocos_historico(id_est, "a@b.com", tipos={"alguem"}, pasta_logs=str(tmp_path))
    assert len(blocos) == 1
    assert blocos[0]["tipo"] == "alguem"
    texto = blocos[0]["texto"]
    assert "1 turno(s)" in texto
    assert "leakage" in texto
    # nunca o conteúdo real da conversa
    assert "Como faço um ciclo?" not in texto
    assert "Tenta pensar em repetição." not in texto


def test_montar_blocos_historico_so_codigo(tmp_path):
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    historico_codigo.registar_execucao(id_est, "executa", "p.algo", [], "Sucesso")

    blocos = ap.montar_blocos_historico(id_est, "a@b.com", tipos={"codigo"}, pasta_logs=str(tmp_path))
    assert len(blocos) == 1
    assert blocos[0]["tipo"] == "codigo"
    assert "p.algo" in blocos[0]["texto"]


def test_montar_blocos_historico_ambos_ordenados_cronologicamente(tmp_path):
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    historico_codigo.registar_execucao(id_est, "executa", "p.algo", [], "Sucesso")

    blocos = ap.montar_blocos_historico(id_est, "a@b.com", tipos={"alguem", "codigo"}, pasta_logs=str(tmp_path))
    assert len(blocos) == 2
    assert [b["timestamp"] for b in blocos] == sorted(b["timestamp"] for b in blocos)


def test_montar_blocos_historico_filtra_por_outra_conta(tmp_path):
    id_est = autenticacao.registar("a@b.com", "password123")
    autenticacao.registar("b@c.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    _sessao_com_turno(tmp_path, "b@c.com")

    blocos = ap.montar_blocos_historico(id_est, "a@b.com", tipos={"alguem"}, pasta_logs=str(tmp_path))
    assert len(blocos) == 1


def test_montar_blocos_historico_filtra_por_periodo(tmp_path):
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    blocos = ap.montar_blocos_historico(
        id_est, "a@b.com", tipos={"alguem"}, data_inicio="2999-01-01", pasta_logs=str(tmp_path))
    assert blocos == []


# ---------- _truncar_por_tamanho (determinístico, sem LLM) ----------

def test_truncar_por_tamanho_cabe_devolve_tal_qual():
    resultado = ap._truncar_por_tamanho(["bloco pequeno"], limite=1000)
    assert resultado == "bloco pequeno"


def test_truncar_por_tamanho_sem_blocos():
    assert ap._truncar_por_tamanho([], limite=1000) == ""


def test_truncar_por_tamanho_mantem_inicio_e_fim_quando_nao_cabe():
    """Seis blocos de 10 caracteres, limite pequeno -- tem de manter
    alguns do início e alguns do fim (nunca só recência), com uma marca
    de quantos ficaram de fora pelo meio."""
    blocos = [f"bloco{i:02d} " for i in range(6)]  # 8 caracteres cada
    resultado = ap._truncar_por_tamanho(blocos, limite=20)
    assert blocos[0].strip() in resultado
    assert blocos[-1].strip() in resultado
    assert "omitido" in resultado


def test_truncar_por_tamanho_nunca_corta_um_bloco_a_meio():
    blocos = ["x" * 40, "y" * 40]
    resultado = ap._truncar_por_tamanho(blocos, limite=50)
    # cada bloco (40) excede metade do limite (50) -- não podem os dois
    # inteiros aparecer juntos sem cortar nenhum a meio
    assert not ("x" * 40 in resultado and "y" * 40 in resultado)


# ---------- contar_historico (pré-visualização, sem LLM) ----------

def test_contar_historico_conta_por_tipo(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    historico_codigo.registar_execucao(id_est, "executa", "p.algo", [], "Sucesso")
    historico_codigo.registar_execucao(id_est, "executa", "q.algo", [], "Sucesso")

    contagem = ap.contar_historico(admin_id, True, id_est, tipos={"alguem", "codigo"}, pasta_logs=str(tmp_path))
    assert contagem == {"total": 3, "alguem": 1, "codigo": 2}


def test_contar_historico_nao_precisa_de_llm_configurado(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    contagem = ap.contar_historico(admin_id, True, id_est, tipos={"alguem"}, pasta_logs=str(tmp_path))
    assert contagem == {"total": 1, "alguem": 1, "codigo": 0}


def test_contar_historico_fora_do_ambito_de_admin_de_grupo_levanta_erro():
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    with pytest.raises(inv.ErroAcessoNegado):
        ap.contar_historico(admin_id, False, id_est, tipos={"alguem"})


# ---------- preparar_resumo (determinístico, sem LLM nenhum) ----------

def test_preparar_resumo_nao_precisa_de_llm_configurado(tmp_path):
    """Decisão revista: preparar_resumo nunca fala com um LLM -- deve
    funcionar mesmo sem NENHUMA configuração de 'apoio_pedagogico'."""
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    resumo = ap.preparar_resumo(admin_id, True, id_est, tipos={"alguem"}, pasta_logs=str(tmp_path))
    assert "turno(s)" in resumo


def test_preparar_resumo_sem_historico():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    resumo = ap.preparar_resumo(admin_id, True, id_est, tipos={"alguem"}, pasta_logs=None)
    assert "Sem histórico" in resumo


def test_preparar_resumo_fora_do_ambito_de_admin_de_grupo_levanta_erro(tmp_path):
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    with pytest.raises(inv.ErroAcessoNegado):
        ap.preparar_resumo(admin_id, False, id_est, tipos={"alguem"}, pasta_logs=str(tmp_path))


# ---------- gerar_analise (o único passo que fala com um LLM) ----------

def test_gerar_analise_usa_o_prompt_configurado(monkeypatch):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_llm_apoio_pedagogico(admin_id)
    fornecedor = _FornecedorFalso()
    monkeypatch.setattr(ap, "criar_fornecedor", lambda *a, **k: fornecedor)

    analise = ap.gerar_analise(admin_id, True, id_est, "Resumo confirmado pelo admin.")
    assert analise == "resumo-1"
    mensagens = fornecedor.chamadas[0]
    assert mensagens[0]["role"] == "system"
    assert "apoio pedagógico" in mensagens[0]["content"].lower()
    assert mensagens[1] == {"role": "user", "content": "Resumo confirmado pelo admin."}


def test_gerar_analise_sem_llm_configurado_levanta_erro():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    with pytest.raises(ap.ErroApoioPedagogicoIndisponivel):
        ap.gerar_analise(admin_id, True, id_est, "Resumo qualquer.")


def test_gerar_analise_rejeita_resumo_vazio():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_llm_apoio_pedagogico(admin_id)
    with pytest.raises(ap.ErroApoioPedagogico):
        ap.gerar_analise(admin_id, True, id_est, "   ")


def test_gerar_analise_fora_do_ambito_de_admin_de_grupo_levanta_erro():
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    with pytest.raises(inv.ErroAcessoNegado):
        ap.gerar_analise(admin_id, False, id_est, "resumo qualquer")
