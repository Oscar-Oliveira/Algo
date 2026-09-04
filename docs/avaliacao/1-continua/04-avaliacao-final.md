# Avaliação Final — Frota de Táxis (Aulas 1 a 14)

## Antes de começares

- Duração sugerida: 120 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Usa livremente tudo o que aprendeste no curso todo.
- O Exercício 4 é maior que os outros — deixa-o para o fim.
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício).

### Exercício 1 — Cálculo de tarifa de viagem (4 valores)

Escreve uma `funcao calcularTarifa(distancia:decimal, horaPonta:booleano):decimal` que calcula o preço de uma viagem de táxi: uma tarifa base de `3.50€` mais `0.80€` por quilómetro percorrido; se for hora de ponta, acresce 20% ao valor total. Pede a distância e se é hora de ponta, e escreve o resultado da chamada à função.

### Exercício 2 — Motorista mais ativo (4 valores)

Define uma `estrutura Motorista` com os campos `nome` (`cadeia`) e `viagensFeitas` (`inteiro`). Pede os dados de 3 motoristas para um vetor. Escreve uma `funcao motoristaMaisAtivo(motoristas:Motorista[], tamanho:inteiro):cadeia` que devolve o nome do motorista com mais viagens feitas, e usa-a para escrever o resultado.

### Exercício 3 — Validação de matrícula (4 valores)

Usa `importar Cadeia`. Pede a matrícula de um táxi (`cadeia`) e usa `afirmar` para garantir que tem exatamente 6 carateres (formato simplificado). Escreve a matrícula em maiúsculas.

### Exercício 4 — Sistema de despacho de táxis (8 valores)

Constrói um programa com um **menu interativo** (repete até o utilizador escolher sair) que gere uma frota de táxis:

1. **Adicionar motorista** — pede o nome, e guarda-o com `viagensFeitas` a `0` (usa um vetor com capacidade máxima 10 e uma variável a contar quantos motoristas existem realmente).
2. **Listar motoristas** — mostra todos os motoristas e o número de viagens que cada um já fez.
3. **Despachar corrida** — pede a distância da corrida e se é hora de ponta, calcula a tarifa (com a lógica do Exercício 1), escolhe sempre o motorista com **menos** viagens feitas até ao momento (para equilibrar a distribuição), soma 1 às suas viagens, e escreve o motorista escolhido e a tarifa calculada.
4. **Sair** — termina o programa e escreve o total de motoristas na frota.

Usa `afirmar` para impedir adicionar motoristas além da capacidade máxima, e para impedir despachar uma corrida sem nenhum motorista na frota. Testa o programa com pelo menos 2 motoristas e 3 corridas despachadas.
