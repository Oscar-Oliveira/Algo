# -*- coding: utf-8 -*-
"""Testes do núcleo pedagógico: PoliticaPedagogica, escada de ajuda, e
o system prompt que os junta."""
import pytest

from alguem.nucleo.politica_pedagogica import PoliticaPedagogica
from alguem.nucleo.escada_de_ajuda import ESCADA_DE_AJUDA, formatar_escada_para_prompt
from alguem.nucleo.system_prompt import construir_system_prompt


# ---------- PoliticaPedagogica ----------

def test_politica_por_omissao_e_socratica_restritiva():
    p = PoliticaPedagogica()
    assert p.modo == "socratic"
    assert p.permite_gerar_codigo is False
    assert p.permite_solucoes_completas is False


def test_politica_a_partir_de_dict_vazio_usa_omissoes():
    p = PoliticaPedagogica.a_partir_de_dict({})
    assert p == PoliticaPedagogica()


def test_politica_a_partir_de_dict_so_muda_o_indicado():
    p = PoliticaPedagogica.a_partir_de_dict({"nivel_maximo_ajuda": 3})
    assert p.nivel_maximo_ajuda == 3
    assert p.modo == "socratic"  # o resto fica por omissão


def test_politica_campo_desconhecido_da_erro_claro():
    with pytest.raises(ValueError, match="campo.*desconhecido"):
        PoliticaPedagogica.a_partir_de_dict({"nivel_maximo_ajuda_com_erro_de_escrita": 3})


# ---------- AG-15: validação de nivel_maximo_ajuda ----------

@pytest.mark.parametrize("nivel_invalido", [-1, 8, -5, 100])
def test_politica_com_nivel_maximo_fora_do_intervalo_da_erro(nivel_invalido):
    with pytest.raises(ValueError, match="nivel_maximo_ajuda"):
        PoliticaPedagogica(nivel_maximo_ajuda=nivel_invalido)


@pytest.mark.parametrize("nivel_valido", [0, 1, 5, 7])
def test_politica_com_nivel_maximo_no_intervalo_e_aceite(nivel_valido):
    assert PoliticaPedagogica(nivel_maximo_ajuda=nivel_valido).nivel_maximo_ajuda == nivel_valido


def test_politica_a_partir_de_dict_tambem_valida_nivel_maximo():
    with pytest.raises(ValueError, match="nivel_maximo_ajuda"):
        PoliticaPedagogica.a_partir_de_dict({"nivel_maximo_ajuda": -1})


# ---------- AG-16: nível 0 nunca é excluído com um nível máximo válido
# (o próprio finding descreve como resolvido automaticamente pelo
# AG-15, já que um nivel_maximo negativo deixa de ser possível) ----------

def test_formatar_escada_inclui_sempre_o_nivel_0_com_nivel_maximo_valido():
    texto = formatar_escada_para_prompt(nivel_maximo=0)
    assert "Nível 0" in texto


# ---------- Escada de ajuda ----------

def test_escada_tem_8_niveis_0_a_7():
    assert [n.numero for n in ESCADA_DE_AJUDA] == list(range(8))


def test_nivel_7_e_sempre_bloqueado_por_texto():
    nivel_7 = ESCADA_DE_AJUDA[7]
    assert "BLOQUEADO" in nivel_7.descricao


def test_formatar_escada_respeita_o_nivel_maximo():
    texto = formatar_escada_para_prompt(nivel_maximo=2)
    assert "Nível 0" in texto
    assert "Nível 1" in texto
    assert "Nível 2" in texto
    assert "Nível 3" not in texto
    assert "Nível 5" not in texto


def test_formatar_escada_inclui_sempre_o_nivel_7_bloqueado():
    """Mesmo com nivel_maximo baixo, o nível 7 (bloqueado) tem de
    aparecer -- é o que deixa claro ao LLM que código está sempre
    fora de questão, seja qual for a política."""
    texto = formatar_escada_para_prompt(nivel_maximo=2)
    assert "Nível 7" in texto
    assert "BLOQUEADO" in texto


# ---------- system prompt ----------

def test_system_prompt_inclui_identidade_do_alguem():
    prompt = construir_system_prompt(PoliticaPedagogica())
    assert "És o Alguem" in prompt
    assert "linguagem ALGO" in prompt


def test_system_prompt_proibe_codigo_quando_politica_pede():
    prompt = construir_system_prompt(PoliticaPedagogica(permite_gerar_codigo=False))
    assert "Nunca escreves código, em ALGO, Python OU QUALQUER outra" in prompt


def test_system_prompt_nao_proibe_codigo_quando_politica_permite():
    prompt = construir_system_prompt(PoliticaPedagogica(permite_gerar_codigo=True))
    assert "Nunca escreves código, em ALGO, Python OU QUALQUER outra" not in prompt


def test_system_prompt_proibicao_e_agnostica_de_linguagem():
    """GOAL-01: a proibição de escrever código não pode ser específica
    a ALGO -- tem de mencionar explicitamente Python (a linguagem para
    que o ALGO compila, e por isso a via óbvia de contornar uma
    proibição só de ALGO)."""
    prompt = construir_system_prompt(PoliticaPedagogica())
    assert "Python" in prompt
    assert "solução funcional" in prompt


def test_system_prompt_muda_com_a_politica():
    """Duas políticas diferentes têm de produzir prompts diferentes --
    é o que permite as 'configurações experimentais' do documento de
    investigação (A/B/C) só mudando o config.json."""
    prompt_socratico = construir_system_prompt(
        PoliticaPedagogica(modo="socratic", prefere_perguntas=True))
    prompt_explicativo = construir_system_prompt(
        PoliticaPedagogica(modo="explicativo", prefere_perguntas=False))
    assert prompt_socratico != prompt_explicativo
    assert "prefere responder com uma pergunta" in prompt_socratico
    assert "prefere responder com uma pergunta" not in prompt_explicativo


def test_system_prompt_respeita_nivel_maximo_de_ajuda():
    prompt_restrito = construir_system_prompt(PoliticaPedagogica(nivel_maximo_ajuda=1))
    prompt_permissivo = construir_system_prompt(PoliticaPedagogica(nivel_maximo_ajuda=6))
    assert "Nível 5" not in prompt_restrito
    assert "Nível 5" in prompt_permissivo
