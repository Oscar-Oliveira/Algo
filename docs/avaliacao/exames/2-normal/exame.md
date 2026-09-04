# Exame — Época Normal (Aulas 1 a 14)

## Antes de começares

- Duração sugerida: 120 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Usa livremente tudo o que aprendeste no curso todo.
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício e na grelha de avaliação no fim).

### Exercício 1 — Desconto em farmácia (3 valores)

Pede a idade do cliente (`inteiro`) e se tem cartão de fidelidade (`booleano`). Escreve se tem direito a desconto: maiores de 65 anos têm sempre desconto; os restantes só têm desconto se tiverem cartão de fidelidade.

### Exercício 2 — Simulador de enchimento de piscina (3 valores)

Pede a capacidade de uma piscina em litros (`inteiro`) e o caudal de uma mangueira em litros por minuto (`inteiro`). Usa `enquanto` para calcular quantos minutos inteiros são precisos até a piscina ficar cheia (soma o caudal minuto a minuto). Escreve o total de minutos e quantos litros ficam a mais no último minuto (o volume acumulado pode ultrapassar ligeiramente a capacidade).

### Exercício 3 — Vendas diárias de uma padaria (4 valores)

Declara um vetor de 6 posições do tipo `decimal` (dias úteis, de segunda a sábado). Pede o valor de vendas de cada dia e guarda-o no vetor. No fim, calcula e escreve o total vendido na semana e o índice (0 a 5) do melhor dia de vendas.

### Exercício 4 — Ficha de cliente de ginásio (4 valores)

Define uma `estrutura Cliente` com os campos `nome` (`cadeia`) e `mensalidade` (`decimal`). Escreve uma `funcao calcularAnuidade(mensalidade:decimal):decimal` que calcula o valor anual com 2 meses grátis (paga-se só 10 meses). Pede os dados de um cliente, constrói-o, e escreve o valor da sua anuidade.

### Exercício 5 — Sistema de gestão de encomendas de correio (6 valores)

Usa `importar Cadeia`. Define uma `estrutura Encomenda` com os campos `destino` (`cadeia`), `peso` (`decimal`) e `entregue` (`booleano`). Pede os dados de 4 encomendas para um vetor, usando `afirmar` para garantir que o peso de cada uma é positivo. Escreve uma `funcao totalPorEntregar(encomendas:Encomenda[], tamanho:inteiro):inteiro` que conta quantas ainda não foram entregues. No fim, escreve a lista de destinos em maiúsculas (`cadeia.maiusculas`) e quantas encomendas faltam entregar.

## Grelha de Avaliação

| Exercício | Descrição | Cotação |
|---|---|---|
| 1 | Desconto em farmácia — operadores lógicos/relacionais, decisões | 3 valores |
| 2 | Enchimento de piscina — ciclo `enquanto` | 3 valores |
| 3 | Vendas diárias da padaria — vetor, acumulador, índice do máximo | 4 valores |
| 4 | Ficha de cliente de ginásio — estrutura, função | 4 valores |
| 5 | Encomendas de correio — `importar`, `afirmar`, estrutura, vetor, função | 6 valores |
| | **Total** | **20 valores** |
