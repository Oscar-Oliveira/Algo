# Manual da Linguagem ALGO

Manual de referência e aprendizagem da linguagem ALGO — só a linguagem em
si (conceitos, sintaxe, exemplos). Não cobre instalação nem o CLI; para
isso ver [`ManualCLI.md`](../ManualCLI.md).

Cada capítulo é um ficheiro próprio, para se poder rever e corrigir por
partes. Os exemplos de código são escritos de raiz para este manual
(mínimos, um conceito de cada vez), não reaproveitados de `exemplos/`.

Achados (melhorias conceptuais, inconsistências, bugs) encontrados ao
escrever cada capítulo ficam registados num único documento,
[`PlanoAuditoria.md`](../PlanoAuditoria.md) (secção "Achados") — não
espalhados por cada capítulo — porque um achado grande pode obrigar a
rever capítulos já escritos.

## Capítulos

| # | Capítulo | Estado |
|---|----------|--------|
| 1 | [Introdução e tipos](01-Introducao-e-Tipos.md) | ✅ rascunho |
| 2 | [Operadores](02-Operadores.md) | ✅ rascunho |
| 3 | [Condicionais](03-Condicionais.md) | ✅ rascunho |
| 4 | [Ciclos](04-Ciclos.md) | ✅ rascunho |
| 5 | [Vetores e matrizes](05-Vetores-e-Matrizes.md) | ✅ rascunho |
| 6 | [Funções e procedimentos](06-Funcoes-e-Procedimentos.md) | ✅ rascunho |
| 7 | [Estruturas](07-Estruturas.md) | ✅ rascunho |
| 8 | [Bibliotecas](08-Bibliotecas.md) | ✅ rascunho |
| 9 | [Ficheiros e `incluir`](09-Ficheiros-e-Incluir.md) | ✅ rascunho |
| 10 | [`afirmar` e tratamento de erros](10-Afirmar-e-Tratamento-de-Erros.md) | ✅ rascunho |

A ordem segue a progressão pedagógica já usada em `exemplos/` (pastas
`01_variaveis_tipos` a `10_tratamento_erros`).

## Estado geral

Rascunho completo dos 10 capítulos. Todos os exemplos de código deste
manual foram executados contra o compilador real (não só escritos de
cabeça) para confirmar que compilam e produzem a saída mostrada.

7 achados registados em [`PlanoAuditoria.md`](../PlanoAuditoria.md) — 6 já corrigidos
(3 deles com mudança real de comportamento do compilador: valor por
omissão de `caracter`, tipagem de `^` encadeado, `conversao.paraBooleano("0")`;
os outros 3 eram só documentação/comentários desatualizados). 1 achado
original (indentação por tabs em `docs/bin/ReferenciaCompletaCLI.md`)
deixou de se aplicar — esse ficheiro foi apagado (ver commit
`ca1f1a4`). Por rever antes de considerar o manual "pronto": uma
passagem de revisão humana ao texto (tom, terminologia consistente
entre capítulos).
