# Findings Resolvidos

*Cada entrada corresponde a um finding removido de `AUDIT_PLAN.md`. Formato: ID, ficheiro(s) alterado(s), resumo da correção, commit.*

## Fase 0 — Contenção crítica de segurança

- **AL-01 + AL-32** [SEGURANÇA · CRÍTICA/ALTA] `algo_lang/compilador/codegen.py:_gerar_afirmar`, `algo_lang/tools/flowchart.py:texto_expr`. RCE via `afirmar`: a condição (texto vindo de `texto_expr`, não escapado) era interpolada diretamente numa f-string do Python gerado — uma condição contendo `{__import__(...)...}` executava código arbitrário quando a asserção falhava. Corrigido substituindo a reconstrução por f-string por `repr()` sobre a mensagem já formatada (nunca reavaliado como código). `texto_expr` documentado com o contrato de segurança (nunca embutir sem `repr()`/escaping adequado ao contexto de destino); confirmado que os call-sites de `flowchart.py` (`no()`/`aresta()`) já escapavam corretamente para o contexto DOT (sem `shape=record`, logo chavetas são texto inerte). Testes: `tests/test_correcoes_auditoria.py::test_afirmar_com_chavetas_na_condicao_nao_executa_codigo`, `::test_flowchart_texto_expr_com_chavetas_produz_dot_seguro`.
