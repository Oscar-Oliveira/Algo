# Ficha de Trabalho — Aula 9: Estruturas

## Antes de começares

- `estrutura Nome` com campos `nome:tipo`, um por linha; literal `{campo: valor, ...}`; acede-se com `.`.
- Uma declaração sem literal (`p:Ponto`) fica `nulo`; o literal `{...}` pode omitir campos (ficam por omissão) e `{}` constrói tudo por omissão.
- `estrutura` (e vetor) é um tipo por referência em toda a parte, incluindo `=` — as duas variáveis passam a apontar para a mesma instância. `==`/`<>` comparam se é a mesma instância, não os campos.
- Um vetor de `estrutura` sem literal (`v:Tipo[n]`) começa com todas as posições `nulo` — constrói cada uma (`v[i] = {...}`) antes de usar os seus campos.
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Área de um retângulo com estrutura

Define uma `estrutura Retangulo` com os campos `largura` e `altura` (`decimal`). Pede os dois valores, constrói um `Retangulo`, e escreve a sua área.

### Exercício 2 — Comparar dois pontos

Define uma `estrutura Ponto` com os campos `x` e `y` (`inteiro`). Pede as coordenadas de dois pontos. `==` entre duas `estrutura` compara se é a mesma instância, não os campos — por isso dois pontos lidos separadamente dão sempre "diferentes" com `==`, mesmo com as mesmas coordenadas. Escreve uma `funcao mesmoPonto(a:Ponto, b:Ponto):booleano` que compara `x` e `y` campo a campo, e usa-a para escrever se os pontos são iguais ou diferentes.

### Exercício 3 — Agenda de contactos

Define uma `estrutura Contacto` com `nome` e `telefone` (`cadeia`). Declara um vetor de 3 `Contacto`, pede os dados de cada um, e no fim escreve a lista completa.

## Parte 2 — Revisão da Aula 8

### Exercício 4 — Contar pares com uma função

Escreve uma `funcao ehPar(numero:inteiro):booleano`. Pede quantos números o utilizador quer inserir, lê-os para um vetor, e usa a função para contar quantos são pares.

### Exercício 5 — Normalizar uma nota

Escreve um `procedimento normalizarNota(ref nota:decimal)` que ajusta a nota para `20` se for maior que `20`, ou para `0` se for menor que `0`. Testa com um valor fora dos limites.

## Parte 3 — Consolidação (Aulas 1 a 9)

### Exercício 6 — Estrutura com campo vetor

Define uma `estrutura Equipa` com um campo `nome` (`cadeia`) e um campo `jogadores` (vetor de 3 `cadeia`). Constrói uma equipa com um literal e escreve o nome e a lista de jogadores.

### Exercício 7 — Aumentar o raio de um círculo

Define uma `estrutura Circulo` com `centroX`, `centroY` e `raio` (todos `decimal`). Escreve um `procedimento aumentarRaio(c:Circulo, incremento:decimal)` que soma o incremento ao raio. Testa com um círculo e um incremento.

### Exercício 8 — Catálogo de filmes

Define uma `estrutura Filme` com `titulo` (`cadeia`), `ano` (`inteiro`) e `visto` (`booleano`). Pede os dados de 3 filmes para um vetor de `Filme`. Escreve uma `funcao contarVistos(filmes:Filme[], tamanho:inteiro):inteiro` que conta quantos já foram vistos. No fim, escreve a lista de filmes e quantos já foram vistos.
