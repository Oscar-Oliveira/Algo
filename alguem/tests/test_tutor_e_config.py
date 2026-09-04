# -*- coding: utf-8 -*-
"""Testes do Tutor (Alguem) e do carregamento do config.json."""
import json
import os

import pytest

from alguem.nucleo.tutor import Alguem
from alguem.nucleo.politica_pedagogica import PoliticaPedagogica
from alguem.fornecedores.base import AgenteLLM
from alguem.config import carregar_config, criar_alguem, ErroConfiguracao


class FornecedorFalso(AgenteLLM):
    """Fornecedor de testes: devolve sempre a última mensagem do
    utilizador, formatada -- para confirmar que o histórico chega
    corretamente ao fornecedor, sem depender de nenhuma rede real.
    Reconhece um pedido de classificação do guardião (é a mesma
    interface AgenteLLM que serve os dois) e responde sempre "SAFE",
    para os testes que não são sobre o guardião em si não terem de se
    preocupar com isso -- ver test_guardiao.py para testes dedicados
    a cada categoria."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.mensagens_recebidas = []

    @property
    def nome(self):
        return "falso"

    def responder(self, mensagens):
        self.mensagens_recebidas.append(list(mensagens))
        ultima = [m for m in mensagens if m["role"] == "user"][-1]["content"]
        if "Categoria (uma palavra só, maiúsculas):" in ultima:
            return "SAFE"
        return f"(resposta a: {ultima})"


# ---------- Alguem / Tutor ----------

def test_alguem_comeca_com_o_system_prompt():
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    assert len(alguem.historico) == 1
    assert alguem.historico[0]["role"] == "system"
    assert "Alguem" in alguem.historico[0]["content"]


def test_alguem_com_ficheiros_visiveis_acrescenta_mensagem_extra():
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica(),
                     ficheiros_visiveis=[("exercicio.algo", "calcular a média")])
    assert len(alguem.historico) == 2
    assert "calcular a média" in alguem.historico[1]["content"]


def test_alguem_ficheiros_visiveis_inclui_o_nome_no_prompt():
    """O pedido explícito era exatamente este: o ficheiro tem de ser
    identificável PELO NOME no que é enviado ao LLM, não só o
    conteúdo solto."""
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica(),
                     ficheiros_visiveis=[("exercicio.algo", "conteudo aqui")])
    assert "exercicio.algo" in alguem.historico[1]["content"]


def test_alguem_aceita_identidade_tutor_personalizada():
    """Fase 3: alguem_ponte.py passa o texto guardado em
    prompt_configuravel (chave 'tutor'), se existir -- None (o
    omisso) continua a usar o texto por omissão do código."""
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica(), identidade_tutor="Sou um tutor de teste.")
    assert "Sou um tutor de teste." in alguem.historico[0]["content"]
    assert "És o Alguem" not in alguem.historico[0]["content"]


def test_alguem_com_varios_ficheiros_visiveis_inclui_todos_os_nomes():
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica(), ficheiros_visiveis=[
        ("principal.algo", "codigo principal"),
        ("biblioteca.algo", "codigo da biblioteca"),
    ])
    conteudo = alguem.historico[1]["content"]
    assert "principal.algo" in conteudo
    assert "biblioteca.algo" in conteudo
    assert "codigo principal" in conteudo
    assert "codigo da biblioteca" in conteudo
    assert alguem.nomes_ficheiros_visiveis == ["principal.algo", "biblioteca.algo"]


def test_considerar_ficheiros_acrescenta_nova_mensagem_sem_apagar_a_conversa():
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica(),
                     ficheiros_visiveis=[("primeiro.algo", "conteudo 1")])
    alguem.conversar("uma pergunta qualquer")
    tamanho_antes = len(alguem.historico)

    alguem.considerar_ficheiros([("segundo.algo", "conteudo 2")])

    assert len(alguem.historico) == tamanho_antes + 1
    assert alguem.nomes_ficheiros_visiveis == ["segundo.algo"]
    # a pergunta anterior continua no histórico -- não foi apagada
    assert any(m["content"] == "uma pergunta qualquer" for m in alguem.historico)


def test_ficheiros_visiveis_usa_delimitador_aleatorio_por_chamada():
    """AG-23: o conteúdo dos ficheiros do estudante é delimitado com
    um token aleatório (mesma técnica de AG-14), diferente a cada
    chamada -- não um delimitador fixo que o próprio código do
    estudante pudesse imitar para tentar injetar instruções."""
    import re
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica(),
                     ficheiros_visiveis=[("a.algo", "conteudo a")])
    alguem.considerar_ficheiros([("b.algo", "conteudo b")])
    conteudo_1 = alguem.historico[1]["content"]
    conteudo_2 = alguem.historico[2]["content"]
    delimitador_1 = re.search(r"====[0-9a-f]{16}====", conteudo_1).group()
    delimitador_2 = re.search(r"====[0-9a-f]{16}====", conteudo_2).group()
    assert delimitador_1 != delimitador_2
    assert conteudo_1.count(delimitador_1) >= 2  # abre e fecha o conteúdo do ficheiro


def test_alguem_sem_contexto_nao_acrescenta_mensagem_extra():
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    assert len(alguem.historico) == 1
    assert alguem.nomes_ficheiros_visiveis == []


def test_conversar_acumula_historico_dos_dois_lados():
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    alguem.conversar("primeira pergunta")
    alguem.conversar("segunda pergunta")
    papeis = [m["role"] for m in alguem.historico]
    assert papeis == ["system", "user", "assistant", "user", "assistant"]


def test_conversar_devolve_a_resposta_do_fornecedor():
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica())
    resposta = alguem.conversar("como calculo a média?")
    assert resposta == "(resposta a: como calculo a média?)"


def test_conversar_passa_o_historico_completo_ao_fornecedor():
    """Confirma que a segunda chamada ao fornecedor já leva a primeira
    pergunta E resposta no histórico -- é o que dá à conversa memória
    dentro da sessão. Guardião desligado de propósito -- este teste é
    sobre acumulação de histórico, não sobre o guardião (que tem os
    seus próprios testes em test_guardiao.py)."""
    fornecedor = FornecedorFalso(modelo="x", api_key="x")
    alguem = Alguem(fornecedor, PoliticaPedagogica(usar_guardiao=False))
    alguem.conversar("primeira")
    alguem.conversar("segunda")
    segunda_chamada = fornecedor.mensagens_recebidas[1]
    conteudos = [m["content"] for m in segunda_chamada]
    assert "primeira" in conteudos
    assert "(resposta a: primeira)" in conteudos
    assert "segunda" in conteudos


# ---------- config.py ----------

def _escrever_config(tmp_path, dados):
    caminho = tmp_path / "config.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return str(caminho)


def test_carregar_config_ficheiro_em_falta(tmp_path):
    with pytest.raises(ErroConfiguracao, match="Não encontrei"):
        carregar_config(str(tmp_path / "nao_existe.json"))


def test_carregar_config_json_invalido(tmp_path):
    caminho = tmp_path / "config.json"
    caminho.write_text("{ isto nao e json valido", encoding="utf-8")
    with pytest.raises(ErroConfiguracao, match="não é um JSON válido"):
        carregar_config(str(caminho))


def test_carregar_config_valido(tmp_path):
    caminho = _escrever_config(tmp_path, {"fornecedor": "openrouter", "modelo": "x"})
    dados = carregar_config(caminho)
    assert dados["fornecedor"] == "openrouter"


def test_criar_alguem_sem_fornecedor_da_erro(tmp_path):
    caminho = _escrever_config(tmp_path, {"modelo": "x"})
    with pytest.raises(ErroConfiguracao, match="fornecedor"):
        criar_alguem(caminho)


def test_criar_alguem_sem_credenciais_para_o_fornecedor_escolhido(tmp_path):
    caminho = _escrever_config(tmp_path, {"fornecedor": "openrouter", "modelo": "x"})
    with pytest.raises(ErroConfiguracao, match="chave de API"):
        criar_alguem(caminho)


def test_criar_alguem_credenciais_como_lista_da_erro_claro(tmp_path):
    """'credenciais' tem de ser um objeto -- um erro de digitação
    plausível (ex: '[]' em vez de '{}') não pode dar um AttributeError
    cru."""
    caminho = _escrever_config(tmp_path, {
        "fornecedor": "openai", "modelo": "x", "credenciais": [],
    })
    with pytest.raises(ErroConfiguracao, match="tem de ser um objeto"):
        criar_alguem(caminho)


def test_criar_alguem_credenciais_do_fornecedor_como_string_da_erro_claro(tmp_path):
    """Um erro comum: pôr a chave diretamente como string
    ('credenciais.openai: "sk-..."') em vez de dentro de um objeto com
    'api_key'."""
    caminho = _escrever_config(tmp_path, {
        "fornecedor": "openai", "modelo": "x",
        "credenciais": {"openai": "sk-direta-sem-objeto"},
    })
    with pytest.raises(ErroConfiguracao, match="tem de ser um objeto"):
        criar_alguem(caminho)


def test_criar_alguem_api_key_nula_e_tratada_como_em_falta(tmp_path):
    """'api_key: null' é JSON válido, mas diferente de omitir o campo
    -- tem de dar o mesmo erro amigável, não um TypeError/AttributeError
    mais tarde na construção do fornecedor."""
    caminho = _escrever_config(tmp_path, {
        "fornecedor": "openai", "modelo": "x",
        "credenciais": {"openai": {"api_key": None}},
    })
    with pytest.raises(ErroConfiguracao, match="chave de API"):
        criar_alguem(caminho)


def test_criar_alguem_fornecedor_desconhecido(tmp_path):
    caminho = _escrever_config(tmp_path, {
        "fornecedor": "naoexiste", "modelo": "x",
        "credenciais": {"naoexiste": {"api_key": "chave"}},
    })
    with pytest.raises(ErroConfiguracao, match="desconhecido"):
        criar_alguem(caminho)


def test_criar_alguem_politica_invalida(tmp_path):
    caminho = _escrever_config(tmp_path, {
        "fornecedor": "openrouter", "modelo": "x",
        "credenciais": {"openrouter": {"api_key": "chave"}},
        "politica_pedagogica": {"campo_que_nao_existe": True},
    })
    with pytest.raises(ErroConfiguracao, match="desconhecido"):
        criar_alguem(caminho)


def test_criar_alguem_de_ponta_a_ponta(tmp_path):
    caminho = _escrever_config(tmp_path, {
        "fornecedor": "openrouter", "modelo": "gpt-4o-mini",
        "credenciais": {"openrouter": {"api_key": "sk-teste"}},
        "politica_pedagogica": {"nivel_maximo_ajuda": 3},
    })
    alguem = criar_alguem(caminho, ficheiros_visiveis=[("exercicio.algo", "um exercício qualquer")])
    assert alguem.fornecedor.nome == "openrouter"
    assert alguem.fornecedor.modelo == "gpt-4o-mini"
    assert alguem.politica.nivel_maximo_ajuda == 3
    assert len(alguem.historico) == 2  # system + ficheiros visíveis


def test_ficheiro_config_exemplo_e_json_valido_e_tem_os_campos_certos():
    """O config.exemplo.json distribuído tem de ser, ele próprio, um
    JSON válido com a estrutura certa -- para servir mesmo de modelo."""
    caminho = os.path.join(os.path.dirname(__file__), "..", "config.exemplo.json")
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    assert "fornecedor" in dados
    assert "modelo" in dados
    assert "credenciais" in dados
    assert "politica_pedagogica" in dados
    # confirma que a política do próprio exemplo é válida
    PoliticaPedagogica.a_partir_de_dict(dados["politica_pedagogica"])
