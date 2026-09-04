# Exame — Época Especial (Aulas 1 a 14)

## Antes de começares

- Duração sugerida: 120 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Usa livremente tudo o que aprendeste no curso todo.
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício e na grelha de avaliação no fim).

### Exercício 1 — Elegibilidade para bolsa de estudo (3 valores)

Pede a média do aluno (`decimal`) e se está em situação de carência económica (`booleano`). Escreve se tem direito a bolsa: média `>= 14` **e** carência económica.

### Exercício 2 — Simulador de esvaziamento de reservatório (3 valores)

Pede o volume inicial de um reservatório em litros (`inteiro`) e o caudal de saída em litros por minuto (`inteiro`). Usa `enquanto` para calcular quantos minutos inteiros são precisos até o reservatório ficar vazio (volume `<= 0`). Escreve o total de minutos.

### Exercício 3 — Tempos de uma corrida de estafetas (4 valores)

Declara um vetor de 4 posições do tipo `decimal` com o tempo (em segundos) de cada corredor de uma equipa de estafetas. Pede os 4 tempos e guarda-os no vetor. No fim, calcula e escreve o tempo total da equipa e o tempo do corredor mais rápido.

### Exercício 4 — Ficha de artesão numa feira (4 valores)

Define uma `estrutura Artesao` com os campos `nome` (`cadeia`) e `vendasDia` (`decimal`). Escreve uma `funcao comissao(vendas:decimal):decimal` que calcula 10% de comissão sobre as vendas do dia. Pede os dados de um artesão, constrói-o, e escreve o valor da sua comissão.

### Exercício 5 — Sistema de gestão de uma plataforma de streaming (6 valores)

Usa `importar Cadeia`. Define uma `estrutura Utilizador` com os campos `nome` (`cadeia`) e `ativo` (`booleano`). Pede os dados de 4 utilizadores para um vetor, usando `afirmar` (com `cadeia.comprimento`) para garantir que o nome não é vazio. Escreve uma `funcao contarAtivos(utilizadores:Utilizador[], tamanho:inteiro):inteiro` que conta quantos têm subscrição ativa. No fim, escreve a lista de nomes em maiúsculas e quantos utilizadores estão ativos.

## Grelha de Avaliação

| Exercício | Descrição | Cotação |
|---|---|---|
| 1 | Bolsa de estudo — operadores lógicos/relacionais, decisões | 3 valores |
| 2 | Esvaziamento de reservatório — ciclo `enquanto` | 3 valores |
| 3 | Corrida de estafetas — vetor, acumulador, mínimo | 4 valores |
| 4 | Ficha de artesão — estrutura, função | 4 valores |
| 5 | Plataforma de streaming — `importar`, `afirmar`, estrutura, vetor, função | 6 valores |
| | **Total** | **20 valores** |
