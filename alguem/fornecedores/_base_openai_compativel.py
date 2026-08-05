# -*- coding: utf-8 -*-
"""Vários fornecedores (OpenAI, OpenRouter, HuggingFace, Ollama,
OpenCode Go) falam exatamente o mesmo formato de API -- o "chat
completions" popularizado pela OpenAI: POST para um endpoint com
`{"model": ..., "messages": [...]}`, resposta em
`{"choices": [{"message": {"content": ...}}]}`.

Em vez de repetir essa lógica HTTP em cada ficheiro, esta classe-base
implementa-a uma vez. Cada fornecedor concreto continua a ser a sua
própria classe, no seu próprio ficheiro (o pedido original) -- só
herdam esta base em vez de reescreverem tudo, e definem apenas o URL e
o nome. Isto é só para o transporte; a Gemini e a Anthropic não podem
usar isto porque falam formatos genuinamente diferentes (system prompt
separado, papéis diferentes, resposta com outra estrutura)."""
from __future__ import annotations

import json
import urllib.request
import urllib.error

from .base import AgenteLLM, ErroFornecedorLLM


class _FornecedorEstiloOpenAI(AgenteLLM):
    #: subclasses têm de definir isto -- o endpoint completo de chat
    #: completions desse fornecedor
    URL_API: str = ""

    def _cabecalhos(self) -> dict:
        """Subclasses podem sobrepor isto se precisarem de cabeçalhos
        diferentes de 'Authorization: Bearer ...' (nenhuma precisa,
        até agora, mas mantém a porta aberta sem forçar duplicação)."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def responder(self, mensagens: list[dict]) -> str:
        corpo = json.dumps({
            "model": self.modelo,
            "messages": mensagens,
        }).encode("utf-8")

        pedido = urllib.request.Request(
            self.URL_API, data=corpo, method="POST", headers=self._cabecalhos())
        try:
            with urllib.request.urlopen(pedido, timeout=60) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            corpo_erro = e.read().decode("utf-8", errors="replace")
            raise ErroFornecedorLLM(
                f"A {self.nome} recusou o pedido (HTTP {e.code}): {corpo_erro}"
            ) from e
        except urllib.error.URLError as e:
            raise ErroFornecedorLLM(
                f"Não foi possível contactar a {self.nome}: {e.reason}"
            ) from e

        try:
            conteudo = dados["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ErroFornecedorLLM(
                f"Resposta da {self.nome} num formato inesperado: {dados}"
            ) from e
        if not isinstance(conteudo, str) or not conteudo:
            # acontece, por exemplo, quando o modelo decide fazer uma
            # chamada de ferramenta (tool_calls) em vez de responder em
            # texto -- 'content' vem null nesse caso. Nunca queremos
            # devolver None/vazio como se fosse uma resposta válida: o
            # resto do Alguem (guardião, histórico da conversa) assume
            # sempre uma string.
            raise ErroFornecedorLLM(
                f"A {self.nome} não devolveu texto (resposta: {dados})"
            )
        return conteudo
