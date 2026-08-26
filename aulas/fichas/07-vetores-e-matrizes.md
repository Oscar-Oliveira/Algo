# Ficha de Trabalho — Aula 7: Vetores e Matrizes

## Antes de começares

- `nome:tipo[tamanho]` — índices vão de `0` a `tamanho - 1`.
- Literal `{...}` tem de ter exatamente o número certo de elementos.
- Um índice inválido (incluindo negativo) é erro em **runtime**; índices negativos não contam a partir do fim.
- Um vetor **não** se copia com `=` — copia elemento a elemento, com um `para`.
- Matriz: `tipo[linhas][colunas]`, acede-se com `m[i][j]`, percorre-se com `para` aninhados.
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Lista de compras

Declara um vetor de 5 posições do tipo `cadeia`. Pede ao utilizador 5 itens, um a um, e guarda-os no vetor. No fim, percorre o vetor e escreve a lista completa.

### Exercício 2 — Maior e menor valor

Pede quantos números o utilizador quer inserir (`n`), declara um vetor de tamanho `n`, e lê os `n` números. Percorre o vetor para encontrar e escrever o maior e o menor valor.

### Exercício 3 — Soma de uma matriz

Declara uma matriz `3x3` de `inteiro` com um literal `{{...}, {...}, {...}}`. Usa dois `para` aninhados para percorrer todas as posições e calcular a soma de todos os valores. Escreve o resultado.

## Parte 2 — Revisão da Aula 5

### Exercício 4 — Fatorial de um número

Pede um número (`inteiro`) e usa `para` para calcular o seu fatorial (produto de 1 até ao número), sem usar vetores. Escreve o resultado.

### Exercício 5 — Sequência de Fibonacci

Pede quantos termos mostrar (`inteiro`) e usa `para` para escrever essa quantidade de termos da sequência de Fibonacci (0, 1, 1, 2, 3, 5, 8, ...), sem usar vetores — guarda só os dois últimos valores em variáveis normais.

## Parte 3 — Consolidação (Aulas 1 a 7)

### Exercício 6 — Notas com destaque

Pede quantos alunos há. Usa **dois vetores paralelos**: um de `cadeia` (nomes) e um de `decimal` (notas), do mesmo tamanho. Lê o nome e a nota de cada aluno. No fim, calcula a média da turma e escreve o **nome** do aluno com a nota mais alta.

### Exercício 7 — Soma e contagem de positivos numa matriz

Declara uma matriz `2x3` de `inteiro` e lê os 6 valores do utilizador (com `para` aninhados). Calcula e escreve a soma total e quantos valores são positivos.

### Exercício 8 — Comparador de vetores

Declara dois vetores de `inteiro`, ambos de tamanho 4, com valores fixos (literal `{...}`). Percorre os dois ao mesmo tempo (mesmo índice `i`) e conta em quantas posições os valores são iguais. Escreve o resultado.
