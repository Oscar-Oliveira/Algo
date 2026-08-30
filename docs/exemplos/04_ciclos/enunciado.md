# 04 — Ciclos

Assunto: `para`, `enquanto`, `fazer...enquanto`, `sair`/`continuar`.

## `estatisticas_notas.algo`

Lê as notas de uma turma e calcula média, máximo, mínimo e nº de
aprovados.

Demonstra: `para i de 1 ate N fazer` com acumuladores (`soma`, `maior`,
`menor`, `aprovados`) declarados **antes** do ciclo para sobreviverem
entre iterações, e `se`/`senao` (assunto 03) dentro do corpo do `para`
para atualizar máximo/mínimo — incluindo o idioma de inicializar
`maior`/`menor` com a 1ª nota lida (`se i == 1 entao ...`) em vez de um
valor sentinela arbitrário.

## `jogo_adivinhar_numero.algo`

Jogo de adivinhar um número secreto fixo (a versão com número aleatório
fica para o assunto 08, com `matematica.aleatorio`).

Demonstra: `enquanto verdadeiro fazer` com `sair` em dois pontos
diferentes do corpo (acertou / esgotou tentativas) — o estilo moderno
preferido ao idioma mais antigo da bandeira booleana — e `continuar` para
um palpite fora do intervalo não contar como tentativa.

## `caixa_multibanco.algo`

Simulador de caixa multibanco: consultar saldo, depositar, levantar,
sair.

Demonstra: `fazer...enquanto` (corre sempre pelo menos uma vez, por isso
o menu aparece mesmo à primeira) a envolver um `escolher/caso` completo
do assunto 03, com `se`/`senao se`/`senao` dentro de cada `caso` para
validar o valor introduzido — o exemplo mais "cumulativo" até agora,
combina tipos, operadores, condicionais e ciclos.
