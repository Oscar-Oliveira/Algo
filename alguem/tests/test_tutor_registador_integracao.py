# -*- coding: utf-8 -*-
"""Testes de integração entre o Tutor (Alguem) e o Registador -- que os
eventos certos ficam mesmo escritos no ficheiro .jsonl da sessão
durante uma conversa real, incluindo as tentativas rejeitadas pelo
guardião."""
import json

import pytest

from alguem.nucleo.tutor import Alguem
from alguem.nucleo.politica_pedagogica import PoliticaPedagogica
from alguem.nucleo.registador import Registador
from alguem.fornecedores.base import AgenteLLM


class FornecedorControlavel(AgenteLLM):
    def __init__(self, respostas, *a, **kw):
        super().__init__(*a, **kw)
        self._respostas = list(respostas)

    @property
    def nome(self):
        return "controlavel"

    def responder(self, mensagens):
        return self._respostas.pop(0)


class FornecedorQueFalha(AgenteLLM):
    """Simula uma falha de rede/API na chamada ao fornecedor (AG-21/AG-22)."""
    @property
    def nome(self):
        return "falha"

    def responder(self, mensagens):
        raise ConnectionError("falha de rede simulada")


def _ler_eventos(caminho):
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def test_construir_alguem_regista_inicio_de_sessao(tmp_path):
    fornecedor = FornecedorControlavel([], modelo="modelo-x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    eventos = _ler_eventos(registador.caminho)
    assert eventos[0]["tipo"] == "inicio_sessao"
    assert eventos[0]["fornecedor"] == "controlavel"
    assert eventos[0]["modelo"] == "modelo-x"


def test_ficheiros_visiveis_no_construtor_ficam_no_evento_de_inicio(tmp_path):
    fornecedor = FornecedorControlavel([], modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    Alguem(fornecedor, PoliticaPedagogica(),
           ficheiros_visiveis=[("exercicio.algo", "conteudo")],
           registador=registador)
    eventos = _ler_eventos(registador.caminho)
    assert eventos[0]["ficheiros_iniciais"] == ["exercicio.algo"]


def test_conversar_regista_a_resposta_final_aceite_logo_na_primeira(tmp_path):
    fornecedor = FornecedorControlavel(["Boa pergunta!", "SAFE"], modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    alguem = Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    alguem.conversar("não sei por onde começar")

    eventos = _ler_eventos(registador.caminho)
    tipos = [e["tipo"] for e in eventos]
    assert tipos.count("tentativa_guardiao") == 1
    assert tipos.count("resposta_final") == 1

    resposta_final = [e for e in eventos if e["tipo"] == "resposta_final"][0]
    assert resposta_final["resposta"] == "Boa pergunta!"
    assert resposta_final["num_tentativas"] == 1
    assert resposta_final["veio_de_recusa_segura"] is False


def test_conversar_regista_a_tentativa_rejeitada_e_a_regeneracao(tmp_path):
    fornecedor = FornecedorControlavel([
        "```algo\nescrever(1)\n```", "Uma pista melhor.", "SAFE",
    ], modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    alguem = Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    alguem.conversar("dá-me o código")

    eventos = _ler_eventos(registador.caminho)
    tentativas = [e for e in eventos if e["tipo"] == "tentativa_guardiao"]
    assert len(tentativas) == 2
    assert tentativas[0]["classificacao"] == "CODE"
    assert tentativas[0]["aceitavel"] is False
    # o conteúdo revelador fica no log, mesmo nunca tendo sido mostrado
    assert "```" in tentativas[0]["resposta_proposta"]
    assert tentativas[1]["classificacao"] == "SAFE"
    assert tentativas[1]["aceitavel"] is True

    resposta_final = [e for e in eventos if e["tipo"] == "resposta_final"][0]
    assert resposta_final["resposta"] == "Uma pista melhor."
    assert resposta_final["num_tentativas"] == 2


def test_esgotar_tentativas_regista_veio_de_recusa_segura(tmp_path):
    fornecedor = FornecedorControlavel([
        "```algo\nescrever(1)\n```", "```algo\nescrever(2)\n```",
    ], modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    alguem = Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    alguem.conversar("dá-me o código")

    eventos = _ler_eventos(registador.caminho)
    resposta_final = [e for e in eventos if e["tipo"] == "resposta_final"][0]
    assert resposta_final["veio_de_recusa_segura"] is True
    assert resposta_final["num_tentativas"] == 2


def test_turnos_incrementam_a_cada_conversar(tmp_path):
    fornecedor = FornecedorControlavel(
        ["r1", "SAFE", "r2", "SAFE"], modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    alguem = Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    alguem.conversar("primeira")
    alguem.conversar("segunda")

    eventos = _ler_eventos(registador.caminho)
    respostas_finais = [e for e in eventos if e["tipo"] == "resposta_final"]
    assert respostas_finais[0]["turno"] == 1
    assert respostas_finais[1]["turno"] == 2


def test_fechar_sessao_escreve_o_evento_fim_sessao(tmp_path):
    fornecedor = FornecedorControlavel([], modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    alguem = Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    alguem.fechar_sessao()

    eventos = _ler_eventos(registador.caminho)
    assert eventos[-1]["tipo"] == "fim_sessao"


def test_considerar_ficheiros_a_meio_da_conversa_regista_evento(tmp_path):
    fornecedor = FornecedorControlavel([], modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    alguem = Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    alguem.considerar_ficheiros([("outro.algo", "conteudo")])

    eventos = _ler_eventos(registador.caminho)
    eventos_ficheiros = [e for e in eventos if e["tipo"] == "ficheiros_atualizados"]
    assert eventos_ficheiros[-1]["ficheiros"] == ["outro.algo"]


# ---------- AG-21 + AG-22: falha do fornecedor a meio de um turno ----------

def test_falha_do_fornecedor_regista_evento_falha_turno_e_nao_deixa_mensagem_pendurada(tmp_path):
    from alguem.nucleo.tutor import RESPOSTA_ERRO_FORNECEDOR
    fornecedor = FornecedorQueFalha(modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    alguem = Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    resposta = alguem.conversar("uma pergunta")

    assert resposta == RESPOSTA_ERRO_FORNECEDOR
    # a mensagem do estudante não fica no histórico sem resposta
    # correspondente -- quebraria a alternância estrita user/assistant
    # exigida por alguns fornecedores (ex. Anthropic) no turno seguinte
    assert len(alguem.historico) == 1

    eventos = _ler_eventos(registador.caminho)
    falhas = [e for e in eventos if e["tipo"] == "falha_turno"]
    assert len(falhas) == 1
    assert falhas[0]["turno"] == 1
    assert falhas[0]["mensagem_estudante"] == "uma pergunta"
    assert "falha de rede simulada" in falhas[0]["motivo"]
    # o turno falhado não pode aparecer como se tivesse tido uma
    # resposta final normal -- distorceria as métricas de investigação
    assert not any(e["tipo"] == "resposta_final" for e in eventos)


def test_falha_do_fornecedor_sem_guardiao_tambem_regista_e_nao_deixa_pendurado(tmp_path):
    from alguem.nucleo.tutor import RESPOSTA_ERRO_FORNECEDOR
    fornecedor = FornecedorQueFalha(modelo="x", api_key="x")
    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    politica = PoliticaPedagogica(usar_guardiao=False)
    alguem = Alguem(fornecedor, politica, registador=registador)
    resposta = alguem.conversar("uma pergunta")

    assert resposta == RESPOSTA_ERRO_FORNECEDOR
    assert len(alguem.historico) == 1
    eventos = _ler_eventos(registador.caminho)
    assert any(e["tipo"] == "falha_turno" for e in eventos)


# ---------- AG-26: fechar o Registador se o construtor falhar depois de o criar ----------

def test_construtor_fecha_o_registador_criado_internamente_se_falhar_depois(monkeypatch):
    """Se o construtor falhar DEPOIS de já ter criado o Registador (ex:
    inicio_sessao levanta), o ficheiro de log já aberto tem de ser
    fechado -- não pode ficar pendurado."""
    import alguem.nucleo.tutor as tutor_mod

    fechado = []

    class RegistadorFalsoQueFalha:
        def __init__(self, id_estudante):
            self.id_estudante = id_estudante

        def inicio_sessao(self, **kwargs):
            raise RuntimeError("falha simulada a meio do construtor")

        def fechar(self):
            fechado.append(True)

    monkeypatch.setattr(tutor_mod, "Registador", RegistadorFalsoQueFalha)

    fornecedor = FornecedorControlavel([], modelo="x", api_key="x")
    with pytest.raises(RuntimeError, match="falha simulada"):
        Alguem(fornecedor, PoliticaPedagogica())
    assert fechado == [True]


def test_registador_explicito_nao_e_fechado_pelo_construtor_se_falhar(tmp_path):
    """Um Registador passado explicitamente é do CALLER -- se o
    construtor falhar depois, não deve fechá-lo, já que o caller pode
    continuar a precisar dele."""
    from alguem.fornecedores.base import AgenteLLM as _AgenteLLM

    class FornecedorComNomeQuebrado(_AgenteLLM):
        @property
        def nome(self):
            raise RuntimeError("nome indisponível")

        def responder(self, mensagens):
            return "x"

    registador = Registador(id_estudante="est-1", pasta_logs=str(tmp_path))
    fornecedor = FornecedorComNomeQuebrado(modelo="x", api_key="x")
    with pytest.raises(RuntimeError, match="nome indisponível"):
        Alguem(fornecedor, PoliticaPedagogica(), registador=registador)
    registador.fim_sessao()  # não levanta -- o ficheiro continua aberto


def test_sem_registador_explicito_usa_um_por_omissao_isolado_pelo_conftest(tmp_path):
    """Confirma que o Alguem funciona mesmo sem passar um Registador --
    cria um por omissão (o conftest.py desta suite já garante que isso
    não escreve na pasta real do pacote)."""
    fornecedor = FornecedorControlavel([], modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    assert alguem.registador is not None
    assert alguem.registador.id_estudante  # tem algum valor, gerado automaticamente
