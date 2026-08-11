# -*- coding: utf-8 -*-
"""Fornecedor Anthropic (Claude), API direta
(https://docs.anthropic.com/en/api/messages). Formato próprio,
diferente do "chat completions" da OpenAI:

- a instrução de sistema vai num campo 'system' à parte, não como mais
  uma mensagem na lista (a mesma situação da Gemini -- ver gemini.py);
- 'max_tokens' é obrigatório no pedido (a OpenAI trata-o como
  opcional);
- a resposta vem como uma lista de blocos de conteúdo
  (`content: [{"type": "text", "text": ...}, ...]`), não uma única
  string direta."""
from __future__ import annotations

from .base import AgenteLLM, ErroFornecedorLLM, pedir_json

URL_API = "https://api.anthropic.com/v1/messages"
VERSAO_API = "2023-06-01"
MAX_TOKENS_POR_OMISSAO = 1024


class FornecedorAnthropic(AgenteLLM):
    @property
    def nome(self) -> str:
        return "anthropic"

    def _traduzir_mensagens(self, mensagens: list[dict]):
        """Separa a(s) mensagem(ns) de sistema (viram o campo 'system')
        das mensagens de conversa (a Anthropic já usa 'user'/
        'assistant', tal como o formato neutro do Alguem -- não há
        tradução de papéis a fazer aqui, só a separação do system)."""
        partes_sistema = []
        conversa = []
        for m in mensagens:
            if m["role"] == "system":
                partes_sistema.append(m["content"])
            else:
                conversa.append({"role": m["role"], "content": m["content"]})
        sistema = "\n\n".join(partes_sistema) if partes_sistema else None
        return sistema, conversa

    def responder(self, mensagens: list[dict]) -> str:
        sistema, conversa = self._traduzir_mensagens(mensagens)
        corpo = {
            "model": self.modelo,
            "max_tokens": MAX_TOKENS_POR_OMISSAO,
            "messages": conversa,
        }
        if sistema is not None:
            corpo["system"] = sistema

        cabecalhos = {
            "x-api-key": self.api_key,
            "anthropic-version": VERSAO_API,
            "Content-Type": "application/json",
        }
        dados = pedir_json(URL_API, corpo, cabecalhos, "Anthropic")

        try:
            blocos_texto = [b["text"] for b in dados["content"] if b.get("type") == "text"]
            if not blocos_texto:
                raise KeyError("sem blocos de texto na resposta")
            return "".join(blocos_texto)
        except (KeyError, IndexError, TypeError) as e:
            raise ErroFornecedorLLM(
                f"Resposta da Anthropic num formato inesperado: {dados}"
            ) from e
