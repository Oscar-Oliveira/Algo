# Avaliação Contínua 1 — Aulas 1 a 5 (Tipos, Operadores, Decisões, Ciclos)

## Antes de começares

- Duração sugerida: 90 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Cada exercício pede um programa `.algo` completo e independente.
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício).

### Exercício 1 — Reserva de hotel (4 valores)

Usa uma `constante TAXA_TURISTICA` (`decimal`) com o valor da taxa por noite. Pede o nome do hóspede (`cadeia`), o número de noites (`inteiro`), o preço da diária (`decimal`), se o pequeno-almoço está incluído (`booleano`) e a letra do quarto (`caracter`). Calcula o valor total da estadia (diária vezes noites, mais a taxa turística vezes noites) e escreve um resumo da reserva.

### Exercício 2 — Elegibilidade para maratona (3 valores)

Pede a idade do participante (`inteiro`) e se tem atestado médico válido (`booleano`). Calcula (sem usar `se`) uma variável `booleano` `podeParticipar`, que só é verdadeira se a idade for `>= 16` **e** o atestado for válido. Escreve o resultado.

### Exercício 3 — Calculadora de portagem (4 valores)

Pede o tipo de veículo (`inteiro`: 1-ligeiro, 2-pesado, 3-motociclo) e usa `escolher`/`caso`/`contrario` para escrever o valor da portagem correspondente (define tu os valores, um por tipo, usando `constante`; qualquer outro número deve escrever "Tipo inválido").

### Exercício 4 — Bilhetes de autocarro com promoção (4 valores)

Pede quantos bilhetes foram vendidos hoje (`inteiro`) e o preço de cada bilhete (`decimal`). Usa um ciclo `para` para simular a venda de cada bilhete, numerado de 1 até ao total: sempre que o número do bilhete for múltiplo de 10 (promoção), esse bilhete é grátis; caso contrário, soma o preço ao total arrecadado (padrão de acumulador). No fim, escreve o total arrecadado e quantos bilhetes foram oferecidos na promoção.

### Exercício 5 — Caixa de supermercado com fila (5 valores)

Usa `fazer ... enquanto` para simular uma caixa de supermercado: pede repetidamente o valor da compra de um cliente (`decimal`) e, se o valor for maior que `0`, se o cliente tem cartão de desconto (`booleano`) — se tiver, aplica um desconto de 10% ao valor. Acumula o total faturado pela caixa e conta quantos clientes foram atendidos. O ciclo repete enquanto o valor da compra introduzido for maior que `0` (um valor `0` ou negativo fecha a caixa, sem contar como cliente). No fim, escreve o total faturado e quantos clientes foram atendidos.
