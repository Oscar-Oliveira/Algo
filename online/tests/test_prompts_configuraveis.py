# -*- coding: utf-8 -*-
"""Testes de online.prompts_configuraveis -- prompts do tutor/guardião
editáveis pelo admin, com fallback para o texto por omissão do código
(ver docs/interno/PlanoAlguemLLMInvestigacao.md, secção 13/Fase 3)."""
import pytest

import autenticacao
import prompts_configuraveis as pc


def test_obter_prompt_sem_personalizacao_devolve_omissao():
    assert pc.obter_prompt("tutor") == pc.PROMPTS_OMISSAO["tutor"]
    assert pc.obter_prompt("guardiao") == pc.PROMPTS_OMISSAO["guardiao"]


def test_obter_prompt_personalizado_sem_linha_devolve_none():
    assert pc.obter_prompt_personalizado("tutor") is None


def test_definir_prompt_e_ler_de_volta():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    pc.definir_prompt("tutor", "Texto novo do tutor.", admin_id)
    assert pc.obter_prompt("tutor") == "Texto novo do tutor."
    assert pc.obter_prompt_personalizado("tutor") == "Texto novo do tutor."
    # o outro prompt não é afetado
    assert pc.obter_prompt("guardiao") == pc.PROMPTS_OMISSAO["guardiao"]


def test_definir_prompt_rejeita_texto_vazio():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    with pytest.raises(pc.ErroPromptConfiguravel):
        pc.definir_prompt("tutor", "   ", admin_id)


def test_definir_prompt_rejeita_chave_desconhecida():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    with pytest.raises(pc.ErroPromptConfiguravel):
        pc.definir_prompt("apoio_pedagogico", "texto", admin_id)


def test_repor_omissao_remove_personalizacao():
    admin_id = autenticacao.registar("admin@escola.pt", "password123")
    pc.definir_prompt("guardiao", "Critério novo.", admin_id)
    assert pc.obter_prompt("guardiao") == "Critério novo."
    pc.repor_omissao("guardiao")
    assert pc.obter_prompt("guardiao") == pc.PROMPTS_OMISSAO["guardiao"]
    assert pc.obter_prompt_personalizado("guardiao") is None
