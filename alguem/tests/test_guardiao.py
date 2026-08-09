# -*- coding: utf-8 -*-
"""Testes do Guardião Pedagógico: a heurística (sem chamar o LLM), a
classificação pelo LLM (com um fornecedor controlável, não só o
'ecoar' do FornecedorFalso simples), e a integração completa no
Tutor -- regeneração, limite de tentativas, e a recusa segura final."""
import pytest

from alguem.nucleo.guardiao import GuardiaoPedagogico, Classificacao, CLASSIFICACOES_BLOQUEAVEIS
from alguem.nucleo.tutor import Alguem, RESPOSTA_SEGURA_POR_OMISSAO
from alguem.nucleo.politica_pedagogica import PoliticaPedagogica
from alguem.fornecedores.base import AgenteLLM


class FornecedorControlavel(AgenteLLM):
    """Fornecedor de testes que devolve, uma a uma, as respostas de
    uma lista pré-definida -- para controlar exatamente o que "o
    modelo" diz em cada chamada sucessiva (a resposta real, depois a
    classificação, depois uma nova tentativa, etc.)."""
    def __init__(self, respostas, *a, **kw):
        super().__init__(*a, **kw)
        self._respostas = list(respostas)
        self.pedidos_recebidos = []

    @property
    def nome(self):
        return "controlavel"

    def responder(self, mensagens):
        self.pedidos_recebidos.append(list(mensagens))
        return self._respostas.pop(0)


# ---------- heurística (sem chamar o LLM) ----------

def test_heuristica_deteta_bloco_de_codigo_markdown():
    guardiao = GuardiaoPedagogico(FornecedorControlavel([], modelo="x", api_key="x"))
    resultado = guardiao.classificar("Aqui está: ```algo\nescrever(1)\n```")
    assert resultado == Classificacao.CODE


def test_heuristica_deteta_linha_de_algo_sem_marcadores_markdown():
    guardiao = GuardiaoPedagogico(FornecedorControlavel([], modelo="x", api_key="x"))
    resultado = guardiao.classificar('Experimenta:\nfuncao dobro(n:inteiro):inteiro\n')
    assert resultado == Classificacao.CODE


def test_heuristica_nao_dispara_para_texto_normal():
    """A heurística não deve ter falsos positivos em prosa comum --
    isto teria de chegar à classificação por LLM (que aqui devolve
    SAFE, confirmando que a heurística não bloqueou primeiro)."""
    guardiao = GuardiaoPedagogico(FornecedorControlavel(["SAFE"], modelo="x", api_key="x"))
    resultado = guardiao.classificar(
        "Achas que precisas de guardar todos os números, ou só o maior até agora?")
    assert resultado == Classificacao.SAFE


# ---------- GOAL-01: heurística também reconhece Python, não só ALGO ----------

@pytest.mark.parametrize("resposta", [
    "def dobro(n):\n    return n * 2",
    "for i in range(10):\n    print(i)",
    "while x < 10:\n    x = x + 1",
    "import math",
    "from math import sqrt",
    "class Ponto:\n    pass",
    "print('resultado:', x)",
])
def test_heuristica_deteta_sintaxe_python_sem_marcadores_markdown(resposta):
    """Um estudante pode pedir a solução 'só em Python, não em ALGO' --
    a heurística tem de reconhecer isso tal como reconhece ALGO."""
    guardiao = GuardiaoPedagogico(FornecedorControlavel([], modelo="x", api_key="x"))
    assert guardiao.classificar(resposta) == Classificacao.CODE


# ---------- UX-07: a heurística não pode ter falsos positivos em
# dicas de nível 5 (pseudocódigo parcial), explicitamente permitidas
# pela política por omissão ----------

def test_heuristica_nao_dispara_para_exemplo_real_de_nivel_5():
    """O próprio exemplo de nível 5 documentado em escada_de_ajuda.py
    -- se a heurística o bloqueasse, estaria a impedir exatamente o
    tipo de ajuda que o sistema é suposto poder dar."""
    from alguem.nucleo.escada_de_ajuda import ESCADA_DE_AJUDA
    exemplo_nivel_5 = next(n.exemplo for n in ESCADA_DE_AJUDA if n.numero == 5)
    guardiao = GuardiaoPedagogico(FornecedorControlavel(["PARTIAL_SOLUTION"], modelo="x", api_key="x"))
    resultado = guardiao.classificar(exemplo_nivel_5)
    assert resultado == Classificacao.PARTIAL_SOLUTION  # veio do LLM, não da heurística


@pytest.mark.parametrize("dica_nivel_5", [
    "Podes começar assim:\nler primeiro valor\nmaior <- ______\ndepois "
    "percorre o resto e compara.",
    "Pensa numa estrutura destas: para cada elemento, verifica se é "
    "maior do que o atual e atualiza se for.",
    "Uma pista: precisas de uma variável para guardar o total e outra "
    "para o contador, mas ainda tens de decidir onde inicializar cada uma.",
])
def test_heuristica_nao_dispara_para_dicas_de_nivel_5_plausiveis(dica_nivel_5):
    guardiao = GuardiaoPedagogico(FornecedorControlavel(["PARTIAL_SOLUTION"], modelo="x", api_key="x"))
    resultado = guardiao.classificar(dica_nivel_5)
    assert resultado == Classificacao.PARTIAL_SOLUTION


# ---------- classificação por LLM ----------

@pytest.mark.parametrize("resposta_llm,esperado", [
    ("SAFE", Classificacao.SAFE),
    ("HINT", Classificacao.HINT),
    ("PARTIAL_SOLUTION", Classificacao.PARTIAL_SOLUTION),
    ("FULL_SOLUTION", Classificacao.FULL_SOLUTION),
    ("  safe  ", Classificacao.SAFE),  # tolera espaços e minúsculas
])
def test_classificacao_por_llm_reconhece_cada_categoria(resposta_llm, esperado):
    guardiao = GuardiaoPedagogico(FornecedorControlavel([resposta_llm], modelo="x", api_key="x"))
    assert guardiao.classificar("uma resposta qualquer sem código") == esperado


def test_classificacao_por_llm_sem_categoria_reconhecida_falha_para_o_lado_seguro():
    """Se o LLM responder algo que não bate com nenhuma categoria
    conhecida, o Guardião trata como se tivesse revelado demasiado --
    nunca assume que está tudo bem por omissão."""
    guardiao = GuardiaoPedagogico(FornecedorControlavel(["não sei responder a isto"], modelo="x", api_key="x"))
    assert guardiao.classificar("resposta qualquer") == Classificacao.FULL_SOLUTION


def test_classificacoes_bloqueaveis_sao_exatamente_code_e_full_solution():
    assert CLASSIFICACOES_BLOQUEAVEIS == {Classificacao.CODE, Classificacao.FULL_SOLUTION}


# ---------- integração no Tutor: regeneração ----------

def test_resposta_safe_passa_direto_sem_regenerar():
    fornecedor = FornecedorControlavel(["Boa pergunta! O que sabes já?", "SAFE"], modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    resposta = alguem.conversar("não sei por onde começar")
    assert resposta == "Boa pergunta! O que sabes já?"
    assert len(fornecedor.pedidos_recebidos) == 2  # resposta + 1 classificação


def test_resposta_com_codigo_e_rejeitada_e_regenerada():
    fornecedor = FornecedorControlavel([
        "```algo\nescrever(x)\n```",  # 1ª tentativa: tem código (heurística já apanha)
        "Pensa nisto: o que precisas de somar a cada passo?",  # 2ª tentativa: segura
        "SAFE",  # classificação da 2ª tentativa
    ], modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    resposta = alguem.conversar("como faço isto?")
    assert resposta == "Pensa nisto: o que precisas de somar a cada passo?"
    # a 1ª tentativa (com código) nunca chega a ser devolvida nem fica no histórico
    assert not any("```" in m.get("content", "") for m in alguem.historico)


def test_esgota_tentativas_cai_para_resposta_segura_fixa():
    fornecedor = FornecedorControlavel([
        "```algo\nescrever(1)\n```",  # 1ª tentativa: código
        "```algo\nescrever(2)\n```",  # 2ª tentativa: código outra vez (esgota MAX_TENTATIVAS=2)
    ], modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    resposta = alguem.conversar("dá-me o código")
    assert resposta == RESPOSTA_SEGURA_POR_OMISSAO
    # nenhuma das tentativas com código fica no histórico -- só a recusa segura
    assert not any("```" in m.get("content", "") for m in alguem.historico)
    assert alguem.historico[-1]["content"] == RESPOSTA_SEGURA_POR_OMISSAO


def test_registo_guardiao_regista_cada_tentativa():
    fornecedor = FornecedorControlavel([
        "```algo\nescrever(1)\n```",
        "Uma pista melhor.",
        "SAFE",
    ], modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    alguem.conversar("ajuda")
    assert len(alguem.registo_guardiao) == 2
    assert alguem.registo_guardiao[0]["classificacao"] == "CODE"
    assert alguem.registo_guardiao[0]["aceitavel"] is False
    assert alguem.registo_guardiao[1]["classificacao"] == "SAFE"
    assert alguem.registo_guardiao[1]["aceitavel"] is True


# ---------- política ----------

def test_permite_gerar_codigo_deixa_passar_classificacao_code():
    fornecedor = FornecedorControlavel(["```algo\nescrever(1)\n```"], modelo="x", api_key="x")
    politica = PoliticaPedagogica(permite_gerar_codigo=True)
    alguem = Alguem(fornecedor, politica)
    resposta = alguem.conversar("mostra-me código")
    assert "```" in resposta  # passou direto, sem regenerar


def test_permite_solucoes_completas_deixa_passar_classificacao_full_solution():
    fornecedor = FornecedorControlavel(["a solução completa em prosa", "FULL_SOLUTION"], modelo="x", api_key="x")
    politica = PoliticaPedagogica(permite_solucoes_completas=True)
    alguem = Alguem(fornecedor, politica)
    resposta = alguem.conversar("dá-me a solução")
    assert resposta == "a solução completa em prosa"


def test_usar_guardiao_falso_salta_a_classificacao_por_completo():
    fornecedor = FornecedorControlavel(["```algo\nescrever(1)\n```"], modelo="x", api_key="x")
    politica = PoliticaPedagogica(usar_guardiao=False)
    alguem = Alguem(fornecedor, politica)
    resposta = alguem.conversar("mostra-me código")
    assert "```" in resposta
    assert len(fornecedor.pedidos_recebidos) == 1  # nenhuma chamada extra de classificação
    assert alguem.registo_guardiao == []


def test_guardiao_explicito_no_construtor_tem_prioridade_sobre_a_politica():
    fornecedor_resposta = FornecedorControlavel(["```algo\nescrever(1)\n```"], modelo="x", api_key="x")
    fornecedor_guardiao = FornecedorControlavel(["CODE", "SAFE"], modelo="x", api_key="x")
    # a política pede guardião, mas passamos um já pronto, com o SEU
    # PRÓPRIO fornecedor (útil para usar um modelo diferente/mais
    # barato só para classificar)
    guardiao_customizado = GuardiaoPedagogico(fornecedor_guardiao)
    politica = PoliticaPedagogica(usar_guardiao=True)
    alguem = Alguem(fornecedor_resposta, politica, guardiao=guardiao_customizado)
    assert alguem.guardiao is guardiao_customizado


# ---------- guardião com fornecedores de formato próprio (Anthropic,
# Gemini) -- o guardião usa o MESMO fornecedor da conversa principal
# por omissão, e esses dois têm tradução de mensagens própria; nunca
# tinha sido testada esta combinação especificamente ----------

def test_guardiao_funciona_com_anthropic_como_fornecedor(monkeypatch):
    import json
    from unittest.mock import patch, MagicMock
    from alguem.fornecedores.anthropic import FornecedorAnthropic

    respostas = iter([
        json.dumps({"content": [{"type": "text", "text": "Boa pergunta! O que sabes já?"}]}),
        json.dumps({"content": [{"type": "text", "text": "SAFE"}]}),
    ])

    def urlopen_falso(pedido, timeout=None):
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = next(respostas).encode()
        return cm

    with patch("urllib.request.urlopen", side_effect=urlopen_falso):
        fornecedor = FornecedorAnthropic(modelo="claude-sonnet-5", api_key="sk-teste")
        alguem = Alguem(fornecedor, PoliticaPedagogica())
        resposta = alguem.conversar("não sei por onde começar")
    assert resposta == "Boa pergunta! O que sabes já?"
    assert alguem.guardiao.fornecedor is fornecedor


def test_guardiao_funciona_com_gemini_como_fornecedor():
    import json
    from unittest.mock import patch, MagicMock
    from alguem.fornecedores.gemini import FornecedorGemini

    respostas = iter([
        json.dumps({"candidates": [{"content": {"parts": [{"text": "O que precisas de saber primeiro?"}]}}]}),
        json.dumps({"candidates": [{"content": {"parts": [{"text": "SAFE"}]}}]}),
    ])

    def urlopen_falso(pedido, timeout=None):
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = next(respostas).encode()
        return cm

    with patch("urllib.request.urlopen", side_effect=urlopen_falso):
        fornecedor = FornecedorGemini(modelo="gemini-1.5-flash", api_key="chave-teste")
        alguem = Alguem(fornecedor, PoliticaPedagogica())
        resposta = alguem.conversar("olá")
    assert resposta == "O que precisas de saber primeiro?"


def test_guardiao_regenera_corretamente_com_anthropic():
    """O caminho mais complexo (regeneração após rejeição) combinado
    com um fornecedor de formato próprio."""
    import json
    from unittest.mock import patch, MagicMock
    from alguem.fornecedores.anthropic import FornecedorAnthropic

    respostas = iter([
        json.dumps({"content": [{"type": "text", "text": "```algo\nescrever(x)\n```"}]}),
        json.dumps({"content": [{"type": "text", "text": "Pensa nisto: o que precisas de somar?"}]}),
        json.dumps({"content": [{"type": "text", "text": "SAFE"}]}),
    ])

    def urlopen_falso(pedido, timeout=None):
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = next(respostas).encode()
        return cm

    with patch("urllib.request.urlopen", side_effect=urlopen_falso):
        fornecedor = FornecedorAnthropic(modelo="x", api_key="sk-teste")
        alguem = Alguem(fornecedor, PoliticaPedagogica())
        resposta = alguem.conversar("dá-me o código")
    assert "```" not in resposta
    assert resposta == "Pensa nisto: o que precisas de somar?"
    assert not any("```" in m.get("content", "") for m in alguem.historico)
