# Ficha de Trabalho — Aula 4: Decisões

## Antes de começares

- `se condicao entao ... senao ...` — a condição é sempre `booleano`.
- `senao se` encadeia várias condições; só corre a **primeira** verdadeira.
- `escolher expressao / caso valor / contrario` compara um valor a várias opções; `caso 1, 2` aceita vários valores; nunca há "queda" para o caso seguinte.
- Uma variável declarada **dentro** de um ramo desaparece fora dele — se precisares dela depois, declara-a antes do `se`.
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Aprovado ou reprovado

Pede uma nota (`decimal`) e escreve "Aprovado" se for `>= 9.5`, ou "Reprovado" caso contrário.

### Exercício 2 — Classificador de escalão etário

Pede a idade (`inteiro`) e usa `senao se` para escrever "Criança" (< 12), "Adolescente" (< 18), "Adulto" (< 65) ou "Idoso" (65 ou mais).

### Exercício 3 — Estação do ano

Pede um mês (`inteiro`, 1 a 12) e usa `escolher`/`caso`/`contrario` para escrever a estação do ano correspondente (agrupa os meses de cada estação no mesmo `caso`).

## Parte 2 — Revisão da Aula 3

### Exercício 4 — Elegível para desconto

Pede a idade (`inteiro`) e se o cliente é VIP (`booleano`). Calcula (sem usar `se`) uma variável `booleano` que diz se é elegível para desconto: idade `>= 65` **ou** ser VIP. Escreve o resultado.

### Exercício 5 — Divisão de tarefas

Pede o número total de tarefas (`inteiro`) e o número de pessoas (`inteiro`). Calcula quantas tarefas cabem a cada pessoa (`div`) e quantas sobram (`mod`).

## Parte 3 — Consolidação (Aulas 1 a 4)

### Exercício 6 — Classificador de IMC

Pede o peso em kg (`decimal`) e a altura em metros (`decimal`). Calcula o IMC (`peso / altura^2`) e usa `senao se` para escrever a categoria: "Abaixo do peso" (< 18.5), "Peso normal" (< 25), "Excesso de peso" (< 30), ou "Obesidade".

### Exercício 7 — Elegibilidade para a carta de condução

Usa uma `constante` com a idade mínima (18). Pede a idade (`inteiro`) e se a pessoa já fez o exame prático (`booleano`). Usa `se`/`senao se`/`senao` para escrever: se ainda não tem idade, se falta o exame prático, ou se já pode tirar a carta.

### Exercício 8 — Escolha de menu

Usa quatro `constante` do tipo `decimal` com o preço de 4 pratos. Pede a opção escolhida (`inteiro`, 1 a 4) e a quantidade (`inteiro`). Declara `nomePrato` e `precoUnitario` **antes** do `escolher` (por causa da regra do âmbito), usa `escolher`/`caso`/`contrario` para preencher os dois, e no fim calcula e escreve o total (preço × quantidade).
