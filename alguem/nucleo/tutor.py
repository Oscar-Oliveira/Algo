# -*- coding: utf-8 -*-
"""O Alguem em si: mantém a conversa com o estudante, aplica a política
pedagógica (via system prompt) e delega a geração de texto ao
fornecedor de LLM configurado. Não sabe nada sobre qual fornecedor
concreto está a usar -- só fala com a interface AgenteLLM."""
from __future__ import annotations

from ..fornecedores.base import AgenteLLM
from .politica_pedagogica import PoliticaPedagogica
from .system_prompt import construir_system_prompt
from .guardiao import (
    GuardiaoPedagogico, Classificacao, CLASSIFICACOES_BLOQUEAVEIS,
    NIVEL_APROXIMADO_POR_CLASSIFICACAO,
)
from .registador import Registador
from .identidade import obter_id_estudante

MAX_TENTATIVAS = 2

RESPOSTA_SEGURA_POR_OMISSAO = (
    "Não vou escrever a solução por si. Posso ajudá-lo a descobrir o "
    "próximo passo -- o que já tentou até agora?"
)

PEDIDO_DE_REGENERACAO = (
    "A tua resposta anterior revelou demasiado da solução (código ou "
    "solução completa). Responde outra vez à mesma pergunta, mas com "
    "uma pista mais pequena -- uma pergunta ou uma pista conceptual, "
    "nunca código nem a solução passo a passo."
)


class Alguem:
    def __init__(self, fornecedor: AgenteLLM, politica: PoliticaPedagogica,
                 ficheiros_visiveis: list[tuple[str, str]] | None = None,
                 guardiao: GuardiaoPedagogico | None = None,
                 registador: Registador | None = None):
        self.fornecedor = fornecedor
        self.politica = politica
        self.historico: list[dict] = [
            {"role": "system", "content": construir_system_prompt(politica)},
        ]
        self.nomes_ficheiros_visiveis: list[str] = []

        # o guardião só é criado por omissão se a política o pedir --
        # permite comparar experimentalmente "com" e "sem" guardião
        # (RQ5 da investigação: será que o system prompt sozinho chega?)
        if guardiao is not None:
            self.guardiao = guardiao
        elif politica.usar_guardiao:
            self.guardiao = GuardiaoPedagogico(fornecedor)
        else:
            self.guardiao = None

        # regista cada avaliação do guardião nesta sessão (inclui as
        # rejeitadas, com o texto proposto) -- acesso rápido dentro do
        # próprio processo; o Registador (abaixo) persiste tudo em
        # disco, entre sessões, para a investigação.
        self.registo_guardiao: list[dict] = []

        self.registador = registador if registador is not None else Registador(
            id_estudante=obter_id_estudante())
        nomes_iniciais = [nome for nome, _ in (ficheiros_visiveis or [])]
        self.registador.inicio_sessao(
            fornecedor=fornecedor.nome, modelo=fornecedor.modelo,
            politica=vars(politica), nomes_ficheiros_iniciais=nomes_iniciais)

        if ficheiros_visiveis:
            self.considerar_ficheiros(ficheiros_visiveis)

    def considerar_ficheiros(self, ficheiros_visiveis: list[tuple[str, str]]) -> None:
        """Dá (ou substitui) ao Alguem a visão de um conjunto de
        ficheiros -- o ficheiro em que o estudante está a trabalhar, e
        qualquer um que ele inclua. Cada ficheiro é identificado pelo
        NOME no prompt, para o Alguem poder responder a perguntas tipo
        "o que faz a função X no ficheiro.algo?" com precisão. Chamar
        isto outra vez (ex: o estudante pede para 'considerar' um
        ficheiro diferente a meio da conversa) acrescenta uma nova nota
        ao histórico -- não apaga a conversa anterior."""
        self.nomes_ficheiros_visiveis = [nome for nome, _ in ficheiros_visiveis]
        blocos = [f"--- {nome} ---\n{conteudo}" for nome, conteudo in ficheiros_visiveis]
        texto = "\n\n".join(blocos)
        self.historico.append({
            "role": "system",
            "content": (
                "Ficheiro(s) que o estudante tem visíveis agora -- "
                "refere-te a eles pelo nome quando for útil, mas não os "
                f"resolvas por ele:\n\n{texto}"
            ),
        })
        self.registador.ficheiros_atualizados(self.nomes_ficheiros_visiveis)

    def conversar(self, mensagem_do_estudante: str) -> str:
        """Acrescenta a mensagem do estudante ao histórico, pede uma
        resposta ao fornecedor, passa-a pelo guardião (se ativo) --
        regenerando até MAX_TENTATIVAS vezes se for classificada como
        reveladora demais, e caindo para uma recusa segura fixa se
        mesmo assim não conseguir uma resposta aceitável -- guarda a
        resposta FINAL no histórico (nunca uma tentativa rejeitada), e
        devolve-a. Cada tentativa (aceite ou não) e a resposta final
        ficam registadas (registo_guardiao e o Registador em disco)."""
        turno = self.registador.novo_turno()
        self.historico.append({"role": "user", "content": mensagem_do_estudante})

        if self.guardiao is None:
            resposta = self.fornecedor.responder(self.historico)
            self.historico.append({"role": "assistant", "content": resposta})
            self.registador.resposta_final(
                turno, resposta, num_tentativas=1, veio_de_recusa_segura=False)
            return resposta

        mensagens_tentativa = list(self.historico)
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            resposta = self.fornecedor.responder(mensagens_tentativa)
            classificacao = self.guardiao.classificar(resposta)
            aceitavel = self._aceitavel(classificacao)
            nivel_aproximado = NIVEL_APROXIMADO_POR_CLASSIFICACAO[classificacao]

            self.registo_guardiao.append({
                "mensagem_do_estudante": mensagem_do_estudante,
                "tentativa": tentativa,
                "resposta": resposta,
                "classificacao": classificacao.value,
                "nivel_aproximado": nivel_aproximado,
                "aceitavel": aceitavel,
            })
            self.registador.tentativa_guardiao(
                turno, tentativa, mensagem_do_estudante, resposta,
                classificacao.value, nivel_aproximado, aceitavel)

            if aceitavel:
                self.historico.append({"role": "assistant", "content": resposta})
                self.registador.resposta_final(
                    turno, resposta, num_tentativas=tentativa, veio_de_recusa_segura=False)
                return resposta
            mensagens_tentativa = mensagens_tentativa + [
                {"role": "assistant", "content": resposta},
                {"role": "user", "content": PEDIDO_DE_REGENERACAO},
            ]

        # esgotou as tentativas sem conseguir uma resposta aceitável --
        # a tentativa rejeitada NUNCA entra no histórico persistente da
        # CONVERSA (não queremos que o modelo "veja" o que revelou
        # antes, para não reforçar esse comportamento nas trocas
        # seguintes) -- mas já ficou registada acima, para investigação
        self.historico.append({"role": "assistant", "content": RESPOSTA_SEGURA_POR_OMISSAO})
        self.registador.resposta_final(
            turno, RESPOSTA_SEGURA_POR_OMISSAO,
            num_tentativas=MAX_TENTATIVAS, veio_de_recusa_segura=True)
        return RESPOSTA_SEGURA_POR_OMISSAO

    def fechar_sessao(self) -> None:
        """Fecha o ficheiro de log desta sessão -- chamar quando a
        conversa com o estudante terminar (ex: escreveu 'sair')."""
        self.registador.fim_sessao()

    def _aceitavel(self, classificacao: Classificacao) -> bool:
        if classificacao not in CLASSIFICACOES_BLOQUEAVEIS:
            return True
        if classificacao is Classificacao.CODE:
            return self.politica.permite_gerar_codigo
        if classificacao is Classificacao.FULL_SOLUTION:
            return self.politica.permite_solucoes_completas
        return False  # pragma: no cover -- CLASSIFICACOES_BLOQUEAVEIS só tem estas duas
