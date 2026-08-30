# Ficha de Trabalho — Aula 3: Operadores

## Antes de começares

- Aritméticos: `+` `-` `*` `/` (sempre `decimal`) `div`/`mod` (só entre `inteiro`) `^`
- Relacionais: `==` `<>` `<` `>` `<=` `>=` — devolvem sempre `booleano`, não se encadeiam (`a < b < c` é erro)
- Lógicos: `e` `ou` `nao` — só entre `booleano`
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Repartir rebuçados

Pede o número total de rebuçados (`inteiro`) e o número de amigos (`inteiro`). Calcula quantos rebuçados cada amigo recebe (`div`) e quantos sobram (`mod`), e escreve o resultado.

### Exercício 2 — Maioridade e nota positiva

Pede a idade (`inteiro`) e uma nota (`decimal`). Calcula duas variáveis `booleano`: se a pessoa é maior de idade (`>= 18`) e se a nota é positiva (`>= 9.5`). Escreve as duas.

### Exercício 3 — Entrada num evento

Pede a idade (`inteiro`) e se a pessoa tem convite especial (`booleano`). Usa `ou` para calcular se pode entrar: maior de 18 anos **ou** com convite. Escreve o resultado.

## Parte 2 — Revisão da Aula 2

### Exercício 4 — Idade do animal de estimação

Usa uma `constante` `ANO_ATUAL`. Pede o nome do animal (`cadeia`) e o ano de nascimento (`inteiro`). Calcula a idade aproximada e escreve uma frase com o resultado.

### Exercício 5 — Perfil de um produto

Declara uma variável de cada um dos 5 tipos primitivos para descrever um produto de loja (nome, preço, stock, disponível, categoria), todas com valor inicial. Escreve os valores todos.

## Parte 3 — Consolidação (Aulas 1 a 3)

### Exercício 6 — Classificador de notas

Pede três notas (`decimal`). Calcula a média e uma variável `booleano` `aprovado`, que só é verdadeira se a média for `>= 9.5` **e** todas as notas individuais forem `>= 5.0`. Escreve a média e se está aprovado.

### Exercício 7 — Festa de aniversário

Pede o orçamento total (`decimal`) e o número de convidados (`inteiro`); calcula o custo por convidado (`/`). Pede também o número de balões (`inteiro`) e o número de crianças (`inteiro`); calcula quantos balões cabem a cada criança (`div`) e quantos sobram (`mod`). Escreve tudo.

### Exercício 8 — Acesso a um parque aquático

Usa uma `constante` com a idade mínima para entrar sozinho. Pede o nome (`cadeia`), a idade (`inteiro`) e se vem acompanhado de um adulto (`booleano`). Calcula se pode entrar (idade suficiente **ou** acompanhado) e escreve uma frase personalizada com o nome e o resultado.
