# -*- coding: utf-8 -*-
"""Testes de online.apoio_pedagogico -- terceiro papel de LLM (ver
docs/interno/PlanoAlguemLLMInvestigacao.md, secção 11/Fase 6): monta o
histórico filtrado de um estudante, resume-o (mecanismo automático por
tamanho) e gera uma análise, sempre com o controlo de acesso por grupo
já usado pela Investigação."""
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


def test_montar_blocos_historico_so_alguem(tmp_path):
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    historico_codigo.registar_execucao(id_est, "executa", "p.algo", [], "Sucesso")

    blocos = ap.montar_blocos_historico(id_est, "a@b.com", tipos={"alguem"}, pasta_logs=str(tmp_path))
    assert len(blocos) == 1
    assert "Estudante: Como faço um ciclo?" in blocos[0]["texto"]
    assert "Alguem: Tenta pensar em repetição." in blocos[0]["texto"]


def test_montar_blocos_historico_so_codigo(tmp_path):
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    historico_codigo.registar_execucao(id_est, "executa", "p.algo", [], "Sucesso")

    blocos = ap.montar_blocos_historico(id_est, "a@b.com", tipos={"codigo"}, pasta_logs=str(tmp_path))
    assert len(blocos) == 1
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


# ---------- _resumir_por_tamanho (mecanismo automático) ----------

def test_resumir_por_tamanho_cabe_num_so_pedido():
    fornecedor = _FornecedorFalso()
    resultado = ap._resumir_por_tamanho(fornecedor, ["bloco pequeno"], limite=1000)
    assert len(fornecedor.chamadas) == 1
    assert resultado == "resumo-1"


def test_resumir_por_tamanho_sem_blocos_nao_chama_llm():
    fornecedor = _FornecedorFalso()
    assert ap._resumir_por_tamanho(fornecedor, [], limite=1000) == ""
    assert fornecedor.chamadas == []


def test_resumir_por_tamanho_map_reduce_quando_nao_cabe():
    """Quatro blocos de 30 caracteres cada (120 no total) não cabem num
    limite de 50 -- tem de agrupar em fatias, resumir cada uma (mais de
    uma chamada), e só devolver sem precisar de uma segunda ronda
    porque os resumos já cabem no limite."""
    fornecedor = _FornecedorFalso()
    blocos = ["b" * 30, "c" * 30, "d" * 30, "e" * 30]
    resultado = ap._resumir_por_tamanho(fornecedor, blocos, limite=50)
    assert len(fornecedor.chamadas) > 1
    assert resultado  # algum texto voltou


def test_resumir_por_tamanho_nunca_corta_um_bloco_a_meio():
    fornecedor = _FornecedorFalso()
    blocos = ["x" * 40, "y" * 40]
    ap._resumir_por_tamanho(fornecedor, blocos, limite=50)
    # cada bloco (40) excede metade do limite (50) -- teem de ir cada um
    # para a sua própria fatia, nunca os dois juntos (80 > 50)
    for chamada in fornecedor.chamadas:
        texto_enviado = chamada[-1]["content"]
        assert "x" * 40 not in texto_enviado or "y" * 40 not in texto_enviado


# ---------- preparar_resumo / gerar_analise (fluxo completo) ----------

def test_preparar_resumo_sem_llm_configurado_levanta_erro(tmp_path):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _sessao_com_turno(tmp_path, "a@b.com")
    with pytest.raises(ap.ErroApoioPedagogicoIndisponivel):
        ap.preparar_resumo(
            admin_id, True, id_est, tipos={"alguem"}, pasta_logs=str(tmp_path))


def test_preparar_resumo_sem_historico_nao_chama_llm(tmp_path, monkeypatch):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_llm_apoio_pedagogico(admin_id)
    fornecedor = _FornecedorFalso()
    monkeypatch.setattr(ap, "criar_fornecedor", lambda *a, **k: fornecedor)

    resumo = ap.preparar_resumo(admin_id, True, id_est, tipos={"alguem"}, pasta_logs=str(tmp_path))
    assert "Sem histórico" in resumo
    assert fornecedor.chamadas == []


def test_preparar_resumo_com_historico_chama_llm(tmp_path, monkeypatch):
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    _configurar_llm_apoio_pedagogico(admin_id)
    _sessao_com_turno(tmp_path, "a@b.com")
    fornecedor = _FornecedorFalso()
    monkeypatch.setattr(ap, "criar_fornecedor", lambda *a, **k: fornecedor)

    resumo = ap.preparar_resumo(admin_id, True, id_est, tipos={"alguem"}, pasta_logs=str(tmp_path))
    assert resumo == "resumo-1"
    assert len(fornecedor.chamadas) == 1


def test_preparar_resumo_fora_do_ambito_de_admin_de_grupo_levanta_erro(tmp_path):
    admin_id = autenticacao.registar("prof@escola.pt", "password123")
    id_est = autenticacao.registar("a@b.com", "password123")
    turma_a = grupos.criar_grupo("Turma A", criado_por=admin_id)
    grupos.definir_grupos_geridos(admin_id, [turma_a["id"]])
    with pytest.raises(inv.ErroAcessoNegado):
        ap.preparar_resumo(admin_id, False, id_est, tipos={"alguem"}, pasta_logs=str(tmp_path))


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
