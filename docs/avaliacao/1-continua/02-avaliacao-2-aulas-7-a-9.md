# Avaliação Contínua 2 — Aulas 7 a 9 (Vetores/Matrizes, Funções/Procedimentos, Estruturas)

## Antes de começares

- Duração sugerida: 90 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Cada exercício pede um programa `.algo` completo e independente.
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício).

### Exercício 1 — Registo de temperaturas da semana (4 valores)

Declara um vetor de 7 posições do tipo `decimal`. Pede a temperatura registada em cada um dos 7 dias da semana e guarda-a no vetor. No fim, calcula e escreve a temperatura média da semana e o índice (0 a 6) do dia mais quente.

### Exercício 2 — Mapa de lugares de cinema (3 valores)

Declara uma matriz `2x4` de `caracter` (2 filas, 4 lugares por fila). Usa um literal para a preencher com `'L'` (livre) e `'O'` (ocupado), à tua escolha. Usa dois `para` aninhados para contar e escrever quantos lugares estão livres.

### Exercício 3 — Conversor de distância (4 valores)

Escreve uma `funcao kmParaMilhas(km:decimal):decimal` que converte quilómetros em milhas (1 km = 0.621371 milhas). Pede uma distância em quilómetros e escreve o resultado da chamada à função.

### Exercício 4 — Aplicar imposto a um preço (3 valores)

Escreve um `procedimento aplicarImposto(ref preco:decimal, taxa:decimal)` que aumenta o preço na percentagem indicada pela taxa (ex.: taxa `0.23` aumenta 23%). No programa principal, mostra o preço antes e depois de chamares o procedimento.

### Exercício 5 — Ficha de funcionário (3 valores)

Define uma `estrutura Funcionario` com os campos `nome` (`cadeia`), `salario` (`decimal`) e `departamento` (`cadeia`). Pede os três valores, constrói um `Funcionario`, e escreve um resumo com os seus dados.

### Exercício 6 — Melhor atleta de uma equipa de ginástica (3 valores)

Define uma `estrutura Atleta` com os campos `nome` (`cadeia`) e `pontuacao` (`decimal`). Declara um vetor de 4 `Atleta` e pede os dados de cada um. Escreve uma `funcao encontrarMelhor(atletas:Atleta[], tamanho:inteiro):cadeia` que devolve o nome do atleta com maior pontuação, e usa-a para escrever o resultado.
