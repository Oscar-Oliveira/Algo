# 10 — Tratamento de erros

Assunto: `afirmar`, e as categorias de erro de execução traduzidas para
português (nunca um traceback do Python). Último assunto — cada exemplo
mistura deliberadamente construções de todos os anteriores.

## `testes_com_afirmar.algo`

Valida três funções próprias (`ehPar`, `somaVetor`,
`inverterTextoManual`) com `afirmar` antes de as dar como corretas.

Demonstra: `afirmar` não produz **nenhuma** saída quando a condição é
verdadeira — só o "Todos os testes passaram" no fim prova que todas as
afirmações anteriores passaram; reaproveita `para ... passo -1`
(assunto 04), vetores (05), funções (06) e `Cadeia` (08) para comparar a
implementação manual de inverter texto com `cadeia.inverter`.

## `catalogo_erros_runtime.algo`

Menu com uma opção por categoria de erro de execução reconhecida:
índice fora dos limites, divisão por zero, overflow numérico, recursão
infinita, campo de valor nulo, raiz negativa, texto inválido para
número, e uma `afirmar` falhada de propósito. Cada opção corre uma vez
(o programa pára na primeira) — testadas as 8 individualmente, todas dão
a mensagem amigável esperada, nunca um traceback.

Demonstra: reaproveita `escolher/caso` (03), estruturas recursivas (07,
para o campo `nulo`) e `Matematica`/`Conversao` (08) — é o exemplo mais
"catálogo" da coleção, cada `caso` isolado a propósito para poderes
correr o ficheiro várias vezes e ver cada erro à vez.

## `sistema_reservas_com_validacao.algo`

Sistema de reservas de hotel que usa `afirmar` como validação interna
das próprias funções auxiliares (`calcularPrecoTotal`,
`quartoDisponivel`) antes de as usar a sério — o contraste deliberado
com `catalogo_erros_runtime.algo`: aqui nenhuma afirmação falha, é o uso
normal e esperado de `afirmar` no dia a dia. Mistura vetor de estruturas
(05/07), funções (06), ciclos (04) e condicionais (03) num programa
"a sério", fechando a progressão de assuntos.
