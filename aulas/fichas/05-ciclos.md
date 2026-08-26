# Ficha de Trabalho — Aula 5: Ciclos

## Antes de começares

- `para i de A ate B fazer` — repetição contada; `i` tem de estar declarada antes; `ate` inclui o valor final.
- `enquanto condicao fazer` — testa **antes**; pode nunca correr.
- `fazer ... enquanto condicao` — testa **depois**; corre sempre pelo menos uma vez.
- Padrão de acumulador/contador: variável a `0` **antes** do ciclo, atualizada lá dentro.
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Tabuada de um número

Pede um número (`inteiro`) e usa `para` para escrever a sua tabuada, de 1 a 10 (`numero x i = resultado`).

### Exercício 2 — Contagem decrescente de lançamento

Pede um número de segundos (`inteiro`) e usa `enquanto` para contar decrescentemente até 0, escrevendo cada valor, terminando com "Descolagem!".

### Exercício 3 — Pede um número positivo até acertar

Usa `fazer ... enquanto` para pedir repetidamente um número (`inteiro`) até o utilizador introduzir um valor positivo (`> 0`). No fim, escreve o número recebido.

## Parte 2 — Revisão da Aula 4

### Exercício 4 — Classificador de temperatura

Pede uma temperatura (`decimal`) e usa `se`/`senao se`/`senao` para classificar: "Gelado" (< 0), "Frio" (< 15), "Ameno" (< 25), ou "Quente".

### Exercício 5 — Cor do semáforo

Pede um número (`inteiro`, 1 a 3) e usa `escolher`/`caso`/`contrario` para escrever o significado: 1 = "Pare", 2 = "Atenção", 3 = "Siga", outro valor = "Inválido".

## Parte 3 — Consolidação (Aulas 1 a 5)

### Exercício 6 — Soma dos números pares

Pede um número `n` (`inteiro`). Usa `para` para percorrer de 1 até `n`, somando (com o padrão de acumulador) apenas os números pares. Escreve a soma final.

### Exercício 7 — Validação de PIN

Usa uma `constante` com um PIN correto (`inteiro`). Usa `fazer ... enquanto` para pedir repetidamente um PIN até acertar, e escreve "Acesso permitido" no fim.

### Exercício 8 — Contagem de números positivos

Pede quantos números o utilizador vai inserir (`inteiro`). Usa `para` para ler esse número de valores, um a um, contando (com o padrão de contador) quantos são positivos. Escreve o total no fim.
