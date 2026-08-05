# -*- coding: utf-8 -*-
"""Regista, em JSON Lines (um evento por linha), tudo o que acontece
numa sessão do Alguem -- é a matéria-prima para as métricas da
investigação (ver alguem/README.md, secção "Métricas e logs"):

- Solution Leakage Rate e Hint Dependency/Escalation calculam-se
  diretamente a partir destes eventos (ver alguem/scripts/metricas.py);
- Student Agency e Cognitive Progression precisam do texto integral
  das trocas, que fica todo aqui, para codificação qualitativa depois;
- Learning Gain e Delayed Transfer precisam de conseguir juntar esta
  sessão a outras da mesma pessoa (o 'id_estudante') e a avaliações
  externas -- os logs não calculam isso sozinhos, só tornam possível.

Cada sessão tem o seu próprio ficheiro (nome com data/hora + um
identificador aleatório da sessão), para nunca haver escrita
concorrente entre sessões diferentes. Escreve-se cada evento
imediatamente (flush a cada linha) -- se o processo for interrompido a
meio, o que já aconteceu não se perde."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

PASTA_LOGS_POR_OMISSAO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Registador:
    def __init__(self, id_estudante: str, pasta_logs: str | None = None):
        # o valor por omissão é resolvido AQUI, não na assinatura --
        # de propósito, para os testes conseguirem isolar os logs numa
        # pasta temporária com monkeypatch (um valor por omissão fixo
        # na assinatura fica decidido na primeira vez que o módulo é
        # importado, e nunca mais muda, mesmo com monkeypatch)
        if pasta_logs is None:
            pasta_logs = PASTA_LOGS_POR_OMISSAO
        self.id_sessao = str(uuid.uuid4())
        self.id_estudante = id_estudante
        self.turno_atual = 0
        os.makedirs(pasta_logs, exist_ok=True)
        marca_tempo = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        self.caminho = os.path.join(pasta_logs, f"{marca_tempo}_{self.id_sessao[:8]}.jsonl")
        self._ficheiro = open(self.caminho, "a", encoding="utf-8")

    def _escrever(self, evento: dict) -> None:
        evento_completo = {
            "timestamp": _agora_iso(),
            "id_sessao": self.id_sessao,
            "id_estudante": self.id_estudante,
            **evento,
        }
        self._ficheiro.write(json.dumps(evento_completo, ensure_ascii=False) + "\n")
        self._ficheiro.flush()

    def inicio_sessao(self, fornecedor: str, modelo: str, politica: dict,
                       nomes_ficheiros_iniciais: list[str]) -> None:
        self._escrever({
            "tipo": "inicio_sessao",
            "fornecedor": fornecedor,
            "modelo": modelo,
            "politica": politica,
            "ficheiros_iniciais": nomes_ficheiros_iniciais,
        })

    def ficheiros_atualizados(self, nomes_ficheiros: list[str]) -> None:
        self._escrever({
            "tipo": "ficheiros_atualizados",
            "ficheiros": nomes_ficheiros,
        })

    def tentativa_guardiao(self, turno: int, tentativa: int, mensagem_estudante: str,
                            resposta_proposta: str, classificacao: str,
                            nivel_aproximado: int, aceitavel: bool) -> None:
        self._escrever({
            "tipo": "tentativa_guardiao",
            "turno": turno,
            "tentativa": tentativa,
            "mensagem_estudante": mensagem_estudante,
            "resposta_proposta": resposta_proposta,
            "classificacao": classificacao,
            "nivel_aproximado": nivel_aproximado,
            "aceitavel": aceitavel,
        })

    def resposta_final(self, turno: int, resposta: str, num_tentativas: int,
                        veio_de_recusa_segura: bool) -> None:
        self._escrever({
            "tipo": "resposta_final",
            "turno": turno,
            "resposta": resposta,
            "num_tentativas": num_tentativas,
            "veio_de_recusa_segura": veio_de_recusa_segura,
        })

    def fim_sessao(self) -> None:
        self._escrever({"tipo": "fim_sessao", "num_turnos": self.turno_atual})
        self._ficheiro.close()

    def novo_turno(self) -> int:
        self.turno_atual += 1
        return self.turno_atual
