# -*- coding: utf-8 -*-
"""Calcula, a partir dos logs em alguem/logs/*.jsonl, as métricas da
investigação que são diretamente computáveis (ver alguem/README.md,
secção "Métricas e logs", para a lista completa e quais precisam de
dados externos):

- Solution Leakage Rate
- Hint Dependency (nº médio de turnos por sessão)
- Hint Escalation (nível aproximado mais alto atingido por sessão)

Uso:
    python3 -m alguem.scripts.metricas [pasta_de_logs]

Sem argumentos, usa alguem/logs/ (a pasta por omissão)."""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

PASTA_LOGS_POR_OMISSAO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def carregar_eventos_por_sessao(pasta_logs: str) -> dict[str, list[dict]]:
    eventos_por_sessao: dict[str, list[dict]] = defaultdict(list)
    for caminho in sorted(glob.glob(os.path.join(pasta_logs, "*.jsonl"))):
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                evento = json.loads(linha)
                eventos_por_sessao[evento["id_sessao"]].append(evento)
    return eventos_por_sessao


def calcular_metricas_da_sessao(eventos: list[dict]) -> dict:
    tentativas = [e for e in eventos if e["tipo"] == "tentativa_guardiao"]
    respostas_finais = [e for e in eventos if e["tipo"] == "resposta_final"]
    inicio = next((e for e in eventos if e["tipo"] == "inicio_sessao"), None)

    n_tentativas = len(tentativas)
    n_rejeitadas = sum(1 for t in tentativas if not t["aceitavel"])

    return {
        "id_sessao": eventos[0]["id_sessao"] if eventos else None,
        "id_estudante": eventos[0]["id_estudante"] if eventos else None,
        "fornecedor": inicio["fornecedor"] if inicio else None,
        "modelo": inicio["modelo"] if inicio else None,
        "num_turnos": len(respostas_finais),
        "num_tentativas_totais": n_tentativas,
        "num_tentativas_rejeitadas": n_rejeitadas,
        "solution_leakage_rate": (n_rejeitadas / n_tentativas) if n_tentativas else None,
        "hint_escalation_maxima": (
            max((t["nivel_aproximado"] for t in tentativas), default=None)
        ),
        "num_recusas_seguras": sum(
            1 for r in respostas_finais if r["veio_de_recusa_segura"]),
    }


def calcular_metricas_globais(metricas_por_sessao: list[dict]) -> dict:
    sessoes_com_tentativas = [m for m in metricas_por_sessao if m["num_tentativas_totais"]]
    if not sessoes_com_tentativas:
        return {
            "num_sessoes": len(metricas_por_sessao),
            "num_estudantes": len({m["id_estudante"] for m in metricas_por_sessao}),
            "solution_leakage_rate_global": None,
            "hint_dependency_media": None,
        }
    total_tentativas = sum(m["num_tentativas_totais"] for m in sessoes_com_tentativas)
    total_rejeitadas = sum(m["num_tentativas_rejeitadas"] for m in sessoes_com_tentativas)
    return {
        "num_sessoes": len(metricas_por_sessao),
        "num_estudantes": len({m["id_estudante"] for m in metricas_por_sessao}),
        "solution_leakage_rate_global": total_rejeitadas / total_tentativas,
        "hint_dependency_media": (
            sum(m["num_turnos"] for m in metricas_por_sessao) / len(metricas_por_sessao)
        ),
    }


def gerar_relatorio(pasta_logs: str) -> dict:
    eventos_por_sessao = carregar_eventos_por_sessao(pasta_logs)
    metricas_por_sessao = [
        calcular_metricas_da_sessao(eventos) for eventos in eventos_por_sessao.values()
    ]
    return {
        "por_sessao": metricas_por_sessao,
        "globais": calcular_metricas_globais(metricas_por_sessao),
    }


def main():
    pasta_logs = sys.argv[1] if len(sys.argv) > 1 else PASTA_LOGS_POR_OMISSAO
    if not os.path.isdir(pasta_logs):
        print(f"❌ Pasta de logs não encontrada: {pasta_logs}")
        sys.exit(1)

    relatorio = gerar_relatorio(pasta_logs)
    globais = relatorio["globais"]

    print(f"Sessões analisadas: {globais['num_sessoes']}")
    print(f"Estudantes distintos: {globais['num_estudantes']}")
    if globais["solution_leakage_rate_global"] is not None:
        print(f"Solution Leakage Rate (global): {globais['solution_leakage_rate_global']:.1%}")
        print(f"Hint Dependency (turnos médios por sessão): {globais['hint_dependency_media']:.1f}")
    else:
        print("(sem tentativas do guardião registadas ainda)")

    print()
    print("Por sessão:")
    for m in relatorio["por_sessao"]:
        leakage = f"{m['solution_leakage_rate']:.0%}" if m["solution_leakage_rate"] is not None else "-"
        print(f"  {m['id_sessao'][:8]}  turnos={m['num_turnos']:<3}  "
              f"leakage={leakage:<5}  nível_max={m['hint_escalation_maxima']}  "
              f"modelo={m['fornecedor']}/{m['modelo']}")


if __name__ == "__main__":  # pragma: no cover -- só corre quando executado diretamente, nunca quando importado pelos testes
    main()
