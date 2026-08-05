# -*- coding: utf-8 -*-
"""Fornecedor Gemini (Google Generative Language API). Ao contrário da
OpenRouter, esta API tem um formato próprio: os papéis chamam-se "user"/
"model" (não "user"/"assistant"), e a instrução de sistema vai num
campo separado ("systemInstruction"), não como mais uma mensagem na
lista. Este ficheiro é onde essa tradução acontece -- o resto do
Alguem continua a falar sempre no formato neutro."""
from __future__ import annotations

import json
import urllib.request
import urllib.error

from .base import AgenteLLM, ErroFornecedorLLM

URL_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class FornecedorGemini(AgenteLLM):
    @property
    def nome(self) -> str:
        return "gemini"

    def _traduzir_mensagens(self, mensagens: list[dict]):
        """Separa a(s) mensagem(ns) de sistema (viram systemInstruction)
        das mensagens de conversa (viram 'contents', com role
        'user'/'model')."""
        partes_sistema = []
        conteudos = []
        for m in mensagens:
            if m["role"] == "system":
                partes_sistema.append(m["content"])
            else:
                papel_gemini = "model" if m["role"] == "assistant" else "user"
                conteudos.append({
                    "role": papel_gemini,
                    "parts": [{"text": m["content"]}],
                })
        instrucao_sistema = (
            {"parts": [{"text": "\n\n".join(partes_sistema)}]}
            if partes_sistema else None
        )
        return instrucao_sistema, conteudos

    def responder(self, mensagens: list[dict]) -> str:
        instrucao_sistema, conteudos = self._traduzir_mensagens(mensagens)
        corpo = {"contents": conteudos}
        if instrucao_sistema is not None:
            corpo["systemInstruction"] = instrucao_sistema

        url = f"{URL_API_BASE}/{self.modelo}:generateContent?key={self.api_key}"
        pedido = urllib.request.Request(
            url,
            data=json.dumps(corpo).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=60) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            corpo_erro = e.read().decode("utf-8", errors="replace")
            raise ErroFornecedorLLM(
                f"A Gemini recusou o pedido (HTTP {e.code}): {corpo_erro}"
            ) from e
        except urllib.error.URLError as e:
            raise ErroFornecedorLLM(
                f"Não foi possível contactar a Gemini: {e.reason}"
            ) from e

        try:
            texto = dados["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            raise ErroFornecedorLLM(
                f"Resposta da Gemini num formato inesperado: {dados}"
            ) from e
        if not isinstance(texto, str) or not texto:
            raise ErroFornecedorLLM(
                f"A Gemini não devolveu texto (resposta: {dados})"
            )
        return texto
