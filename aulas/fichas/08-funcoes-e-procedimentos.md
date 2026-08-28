# Ficha de Trabalho — Aula 8: Funções e Procedimentos

## Antes de começares

- `funcao nome(parametros):tipo` — devolve sempre um valor; todo caminho tem de acabar em `retornar <expressão>`.
- `procedimento nome(parametros)` — não devolve valor; `retornar` sem expressão é opcional.
- Sem `ref`, um parâmetro **escalar** é uma **cópia** — mudanças não saem da função. Um parâmetro **vetor/estrutura** sem `ref` NÃO é cópia — mutar um elemento/campo sai da função; só reatribuir o parâmetro inteiro é que não sai.
- Com `ref`, o parâmetro aponta para a **mesma** variável do chamador — mudanças (incluindo reatribuir tudo) são visíveis depois.
- Um vetor como parâmetro usa colchetes vazios: `v:tipo[]`.
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Área de um retângulo

Escreve uma `funcao areaRetangulo(base:decimal, altura:decimal):decimal` que devolve a área. Lê a base e a altura do utilizador e escreve o resultado da chamada à função.

### Exercício 2 — Saudação personalizada

Escreve um `procedimento saudarPessoa(nome:cadeia, idade:inteiro)` que escreve uma frase de saudação com o nome e a idade. Chama-o duas vezes, com pessoas diferentes.

### Exercício 3 — Dobrar um valor por referência

Escreve um `procedimento dobrarValor(ref valor:inteiro)` que duplica o valor recebido. No programa principal, mostra o valor de uma variável antes e depois de chamares o procedimento, para confirmares que a mudança "sai" da função.

## Parte 2 — Revisão da Aula 7

### Exercício 4 — Contar pares num vetor

Pede quantos números o utilizador quer inserir, lê-os para um vetor, e conta (sem usar funções) quantos são pares. Escreve o resultado.

### Exercício 5 — Soma das diagonais de uma matriz

Declara uma matriz `3x3` de `inteiro` com um literal. Sem usar funções, calcula e escreve a soma da diagonal principal (`m[i][i]`) e da diagonal secundária (`m[i][2-i]`).

## Parte 3 — Consolidação (Aulas 1 a 8)

### Exercício 6 — Função que recebe um vetor

Escreve uma `funcao media(v:decimal[], tamanho:inteiro):decimal` que devolve a média dos valores do vetor. Declara um vetor de notas com um literal e escreve o resultado da chamada à função.

### Exercício 7 — Potência recursiva

Escreve uma `funcao potencia(base:inteiro, expoente:inteiro):inteiro` recursiva (sem usar `^`), que calcula `base` elevado a `expoente` (assume `expoente >= 0`). Testa com pelo menos um valor.

### Exercício 8 — Sistema de notas com função

Escreve uma `funcao classificarNota(nota:decimal):cadeia` que devolve `"Aprovado"` ou `"Reprovado"`. Pede quantos alunos há, lê as notas para um vetor, e para cada uma chama a função e escreve o resultado. No fim, escreve quantos alunos foram aprovados no total.
