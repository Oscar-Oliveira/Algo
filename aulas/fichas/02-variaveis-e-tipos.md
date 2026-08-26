# Ficha de Trabalho — Aula 2: Variáveis e Tipos

## Antes de começares

- Já conheces os 5 tipos primitivos: `inteiro`, `decimal`, `booleano`, `cadeia`, `caracter`.
- Sabes declarar variáveis com e sem valor inicial, e o que é uma `constante`.
- Lembra-te: `+` só funciona entre dois números OU entre dois textos — nunca um número e um texto. Para misturar, usa `escrever` com vários argumentos separados por vírgula.
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Perfil de jogador

Cria uma variável de cada um dos 5 tipos primitivos para descrever uma personagem de jogo (por exemplo: `nome`, `vida`, `velocidade`, `ativo`, `classe`), todas com valor inicial. Escreve os valores todos.

### Exercício 2 — Valores por omissão

Declara uma variável de cada tipo **sem** valor inicial, e escreve os valores logo a seguir (sem lhes chamares `ler` nem lhes atribuíres nada). Confirma que os valores mostrados correspondem à tabela de valores por omissão da aula.

### Exercício 3 — Bilhete de cinema

Cria duas `constante` do tipo `decimal`: o preço base de um bilhete e o desconto de sócio. Pede ao utilizador a idade (`inteiro`) e se é sócio (`booleano`), e escreve um resumo com o preço final (preço base menos o desconto). *(Como ainda não vimos `se`, o desconto é sempre aplicado, mesmo que a resposta seja "falso" — é só para praticar `constante` e os tipos `decimal`/`booleano`.)*

## Parte 2 — Revisão da Aula 1

### Exercício 4 — Apresentação com cidade

Pede o nome e a cidade natal do utilizador (`ler`, dois `cadeia`) e escreve uma frase de apresentação.

### Exercício 5 — Anos de experiência

Pede uma atividade que o utilizador pratica (`cadeia`) e há quantos anos a pratica (`inteiro`), e escreve uma frase de incentivo com essa informação.

## Parte 3 — Consolidação (Aulas 1 e 2)

### Exercício 6 — Cartão de sócio de biblioteca

Usa uma `constante` `ANO_ATUAL`. Pede o nome, uma inicial (`caracter`), o ano de nascimento (`inteiro`) e se é leitor assíduo (`booleano`). Calcula a idade aproximada (`ANO_ATUAL` menos o ano de nascimento) e escreve um cartão de sócio completo.

### Exercício 7 — Recibo simples

Pede o nome de um artigo (`cadeia`), o preço unitário (`decimal`) e a quantidade (`inteiro`). Calcula o total (preço vezes quantidade) e escreve um recibo com a linha do artigo e o total.

### Exercício 8 — Ficha de inscrição num clube

Junta tudo: usa pelo menos duas `constante`, pede dados dos 5 tipos primitivos (nome, inicial para o crachá, ano de nascimento, se já praticou desporto, altura), calcula a idade aproximada, monta um crachá por concatenação de texto, e escreve um resumo completo da inscrição.
