# Exame — Época Contínua (Aulas 1 a 14)

## Antes de começares

- Duração sugerida: 120 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Usa livremente tudo o que aprendeste no curso todo.
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício e na grelha de avaliação no fim).

### Exercício 1 — Elegibilidade para aula de natação (3 valores)

Usa uma `constante IDADE_MINIMA` (`inteiro`, valor 6). Pede a idade da criança (`inteiro`) e se já sabe nadar sozinha (`booleano`). Escreve se pode inscrever-se na aula: idade suficiente **e** ainda não sabe nadar sozinha (a aula é para principiantes); caso contrário, explica qual das duas condições falhou.

### Exercício 2 — Fila de espera numa oficina de bicicletas (3 valores)

Usa uma `constante TEMPO_REPARACAO` (`decimal`, minutos por bicicleta). Pede quantas bicicletas estão na fila (`inteiro`). Usa `para` para calcular o tempo de espera de cada bicicleta (a primeira espera um tempo de reparação, a segunda dois tempos de reparação, e assim sucessivamente) e soma tudo num acumulador. Escreve o tempo total de espera de toda a fila.

### Exercício 3 — Vendas de bilhetes de concerto (4 valores)

Declara um vetor de 5 posições do tipo `decimal`. Pede o preço de cada um dos 5 bilhetes vendidos e guarda-o no vetor. No fim, calcula e escreve a receita total e o preço do bilhete mais caro vendido.

### Exercício 4 — Ficha de morador de condomínio (4 valores)

Define uma `estrutura Morador` com os campos `nome` (`cadeia`) e `quotaMensal` (`decimal`). Escreve uma `funcao calcularDividaAnual(quota:decimal):decimal` que calcula o valor total pago num ano (12 meses). Pede os dados de um morador, constrói-o, e escreve o valor da sua dívida anual.

### Exercício 5 — Sistema de gestão de uma loja de brinquedos (6 valores)

Usa `importar Cadeia`. Define uma `estrutura Brinquedo` com os campos `nome` (`cadeia`), `preco` (`decimal`) e `emStock` (`booleano`). Pede os dados de 4 brinquedos para um vetor, usando `afirmar` para garantir que o preço de cada um é positivo. Escreve uma `funcao totalEmStock(brinquedos:Brinquedo[], tamanho:inteiro):inteiro` que conta quantos ainda estão em stock. No fim, escreve a lista de nomes em maiúsculas (`cadeia.maiusculas`) e quantos brinquedos estão em stock.

## Grelha de Avaliação

| Exercício | Descrição | Cotação |
|---|---|---|
| 1 | Aula de natação — `constante`, operadores lógicos, decisões | 3 valores |
| 2 | Fila de espera na oficina — ciclo `para`, acumulador | 3 valores |
| 3 | Bilhetes de concerto — vetor, acumulador, máximo | 4 valores |
| 4 | Ficha de morador — estrutura, função | 4 valores |
| 5 | Loja de brinquedos — `importar`, `afirmar`, estrutura, vetor, função | 6 valores |
| | **Total** | **20 valores** |
