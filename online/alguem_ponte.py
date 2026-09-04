# -*- coding: utf-8 -*-
"""Constrói um Alguem por pedido, a partir das configurações de LLM
ativas para os papéis de apoio e guardião (ver configuracao_llm.py) e
das definições/prompts editáveis pelo admin (ver definicoes.py e
prompts_configuraveis.py), em vez de um config.json local -- é a única
adaptação necessária; todo o resto do pacote alguem/ (política,
guardião, escada de ajuda, registador) é reaproveitado tal e qual, sem
alterações."""

from __future__ import annotations

import sys
import os

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

from alguem.fornecedores import criar_fornecedor, ErroFornecedorLLM
from alguem.nucleo import Alguem, GuardiaoPedagogico, PoliticaPedagogica, Registador
from alguem.nucleo.ficheiros_visiveis import LIMITE_FICHEIROS, LIMITE_BYTES_TOTAL

import definicoes
import grupos
import prompts_configuraveis
from configuracao_llm import (
    resolver_configuracao_ativa, obter_selecao_global, permissao_ativa,
    ConfiguracaoLLM, ErroConfiguracaoLLM, _validar_host_ollama,
)
from autenticacao import obter_email


class ErroAlguemIndisponivel(Exception):
    """'acionavel' diz se ir a Definições resolve o problema (falta uma
    config pessoal, ou a que está configurada deixou de ser válida) ou
    não (não há LLM nenhum disponível para esta conta -- nem global, nem
    permissão para uma pessoal -- e Definições nem sequer mostra a opção
    de criar uma). O frontend usa isto para decidir se mostra o link
    "Definições" na mensagem de aviso (ver main.py:ws_alguem e
    app.js:desativarEntradaAlguem)."""
    def __init__(self, mensagem: str, acionavel: bool = True):
        super().__init__(mensagem)
        self.acionavel = acionavel


def limitar_ficheiros_visiveis(ficheiros: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """ON-26: aplica o MESMO limite de AG-28 (alguem/nucleo/
    ficheiros_visiveis.py) aqui, no ponto de entrada do online -- os
    ficheiros que chegam por /ws/alguem (mensagem 'tipo: ficheiro')
    vêm diretamente do browser do estudante, sem passar pela resolução
    de 'incluir' que AG-28 já protege. Sem isto, nada impedia o
    browser de enviar um número arbitrário de ficheiros, ou ficheiros
    enormes, inflando sem controlo o prompt enviado ao LLM."""
    resultado: list[tuple[str, str]] = []
    bytes_acumulados = 0
    for nome, conteudo in ficheiros:
        if len(resultado) >= LIMITE_FICHEIROS or bytes_acumulados >= LIMITE_BYTES_TOTAL:
            break
        espaco_restante = LIMITE_BYTES_TOTAL - bytes_acumulados
        conteudo_bytes = conteudo.encode("utf-8")
        if len(conteudo_bytes) > espaco_restante:
            conteudo = conteudo_bytes[:espaco_restante].decode("utf-8", errors="ignore")
            conteudo += "\n\n[... ficheiro truncado, excede o limite de tamanho total permitido ...]"
        bytes_acumulados += len(conteudo.encode("utf-8"))
        resultado.append((nome, conteudo))
    return resultado


def construir_alguem(
    estudante_id: int,
    ficheiros_visiveis: list[tuple[str, str]] | None = None,
    dsn: str | None = None,
    pasta_logs: str | None = None,
) -> Alguem:
    """Lê a credencial do estudante e constrói um Alguem pronto a
    conversar. Levanta ErroAlguemIndisponivel (com mensagem amigável) se
    não há nenhum LLM de apoio disponível para esta conta -- distingue
    duas causas bem diferentes (ver regra de precedência em
    configuracao_llm.resolver_configuracao_ativa): se o estudante tem
    permissão para configurar o seu próprio mas ainda não o fez, a culpa
    é dele e a mensagem manda-o às Definições; mas se não há configuração
    global NEM permissão para uma pessoal, não há nada que o estudante
    possa fazer sozinho -- dizer-lhe para "definir um em Definições"
    seria enganador, porque essa opção nem sequer lhe aparece lá. Os logs
    identificam o estudante diretamente pelo email (ver
    docs/interno/PlanoAlguemLLMInvestigacao.md, secção 4/Fase 4 --
    reverte a pseudonimização usada até à Fase 3).
    'pasta_logs' existe só para os testes conseguirem isolar os logs
    sem variáveis de ambiente (mesma técnica já usada em alguem/)."""
    credencial: ConfiguracaoLLM | None = resolver_configuracao_ativa(estudante_id, "apoio", dsn)
    if credencial is None:
        pode_configurar_o_proprio = permissao_ativa("apoio", dsn)
        if obter_selecao_global("apoio", dsn) is None and not pode_configurar_o_proprio:
            raise ErroAlguemIndisponivel(
                "O Alguem ainda não está disponível -- a plataforma ainda não "
                "configurou nenhum fornecedor de LLM. Fala com o teu professor "
                "ou administrador.",
                acionavel=False,
            )
        raise ErroAlguemIndisponivel(
            "Ainda não configuraste nenhum fornecedor de LLM -- "
            "define um em Definições antes de chamares Alguem."
        )
    fornecedor = _criar_fornecedor_de(credencial)
    # Fase 4: "global" ou "pessoal" -- resolver_configuracao_ativa só
    # devolve uma configuração pessoal quando estudante_id está
    # preenchido nela (as globais têm sempre estudante_id NULL).
    apoio_escopo = "global" if credencial.estudante_id is None else "pessoal"

    # Fase 3: o guardião tem o seu próprio fornecedor, resolvido à parte
    # do de apoio (só seleção GLOBAL, nunca pessoal -- ver
    # configuracao_llm.PAPEIS_PESSOAIS) -- nunca deixamos o
    # 'elif politica.usar_guardiao' de Alguem.__init__ construí-lo
    # sozinho a partir do fornecedor do tutor, por isso 'guardiao' é
    # sempre passado explicitamente (objeto ou None) e 'usar_guardiao'
    # na política espelha exatamente se esse objeto existe. Um
    # guardião global configurado mas indisponível (erro do fornecedor)
    # falha alto, tal como o de apoio -- é um erro de configuração do
    # admin, não o caso "sem guardião configurado" (ponto 1 das
    # decisões validadas), que continua a resultar em guardiao=None.
    guardiao = None
    guardiao_fornecedor_nome = None
    guardiao_modelo = None
    if definicoes.usar_guardiao(dsn):
        credencial_guardiao = resolver_configuracao_ativa(estudante_id, "guardiao", dsn)
        if credencial_guardiao is not None:
            fornecedor_guardiao = _criar_fornecedor_de(credencial_guardiao)
            guardiao = GuardiaoPedagogico(
                fornecedor_guardiao,
                prompt_classificacao=prompts_configuraveis.obter_prompt("guardiao", dsn),
            )
            guardiao_fornecedor_nome = credencial_guardiao.fornecedor
            guardiao_modelo = credencial_guardiao.modelo
    # Fase 4: nunca "pessoal" -- o guardião só tem seleção global (ver
    # PAPEIS_PESSOAIS acima), por isso só há dois estados possíveis.
    guardiao_escopo = "global" if guardiao is not None else "indisponivel"

    politica = PoliticaPedagogica(
        nivel_maximo_ajuda=definicoes.nivel_maximo_ajuda(dsn),
        usar_guardiao=guardiao is not None,
    )

    kwargs_registador = {"id_estudante": obter_email(estudante_id, dsn)}
    if pasta_logs is not None:
        kwargs_registador["pasta_logs"] = pasta_logs
    registador = Registador(**kwargs_registador)
    return Alguem(
        fornecedor,
        politica,
        ficheiros_visiveis=ficheiros_visiveis,
        guardiao=guardiao,
        registador=registador,
        identidade_tutor=prompts_configuraveis.obter_prompt("tutor", dsn),
        apoio_escopo=apoio_escopo,
        guardiao_escopo=guardiao_escopo,
        guardiao_fornecedor=guardiao_fornecedor_nome,
        guardiao_modelo=guardiao_modelo,
        grupo=grupos.nome_grupo_do_estudante(estudante_id, dsn),
    )


def _criar_fornecedor_de(credencial: ConfiguracaoLLM):
    """Partilhado entre apoio e guardião -- inclui a revalidação do
    host do Ollama contra DNS rebinding (achado 2, PlanoAuditoria.md;
    ver comentário original em construir_alguem, agora aplicado aos
    dois papéis)."""
    extras = {}
    if credencial.host:
        try:
            _validar_host_ollama(credencial.host)
        except ErroConfiguracaoLLM as e:
            raise ErroAlguemIndisponivel(
                f"O host configurado para o Ollama deixou de ser válido: {e} "
                f"Reconfigura o fornecedor em Definições."
            ) from e
        extras["host"] = credencial.host

    try:
        return criar_fornecedor(credencial.fornecedor, credencial.modelo, credencial.api_key, **extras)
    except ErroFornecedorLLM as e:
        raise ErroAlguemIndisponivel(str(e)) from e
