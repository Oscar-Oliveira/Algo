# Exame — Época de Recurso (Aulas 1 a 14)

## Antes de começares

- Duração sugerida: 120 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Usa livremente tudo o que aprendeste no curso todo.
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício e na grelha de avaliação no fim).

### Exercício 1 — Verificador de acesso a spa (3 valores)

Usa uma `constante IDADE_MINIMA` (`inteiro`, valor 16). Pede a idade do visitante (`inteiro`) e se vem acompanhado de um adulto (`booleano`). Escreve se pode entrar: idade suficiente, ou menor de idade mas acompanhado; caso contrário, escreve que não pode entrar.

### Exercício 2 — Simulador de carregamento de bateria (3 valores)

Pede a percentagem de bateria já carregada (`inteiro`, 0 a 100) e a velocidade de carregamento em pontos percentuais por minuto (`inteiro`). Usa `enquanto` para calcular quantos minutos faltam até atingir 100%. Escreve o total de minutos.

### Exercício 3 — Leituras de um frigorífico industrial (4 valores)

Declara um vetor de 6 posições do tipo `decimal` com leituras de temperatura ao longo do dia. Pede as 6 leituras e guarda-as no vetor. No fim, calcula e escreve a temperatura média e a leitura mais alta registada.

### Exercício 4 — Ficha de aluno de condução (4 valores)

Define uma `estrutura Aluno` com os campos `nome` (`cadeia`) e `horasTreino` (`decimal`). Escreve uma `funcao estaPronto(horas:decimal):booleano` que devolve verdadeiro se as horas de treino forem `>= 20`. Pede os dados de um aluno, constrói-o, e usa a função para escrever se já está pronto para o exame de condução.

### Exercício 5 — Sistema de gestão de uma clínica veterinária (6 valores)

Usa `importar Cadeia`. Define uma `estrutura Animal` com os campos `nome` (`cadeia`), `especie` (`cadeia`) e `vacinado` (`booleano`). Pede os dados de 4 animais para um vetor, usando `afirmar` (com `cadeia.comprimento`) para garantir que o nome não é vazio. Escreve uma `funcao contarVacinados(animais:Animal[], tamanho:inteiro):inteiro` que conta quantos já estão vacinados. No fim, escreve a lista de animais com a espécie em maiúsculas e quantos estão vacinados.

## Grelha de Avaliação

| Exercício | Descrição | Cotação |
|---|---|---|
| 1 | Acesso a spa — `constante`, operadores lógicos, decisões | 3 valores |
| 2 | Carregamento de bateria — ciclo `enquanto` | 3 valores |
| 3 | Frigorífico industrial — vetor, média, máximo | 4 valores |
| 4 | Ficha de aluno de condução — estrutura, função | 4 valores |
| 5 | Clínica veterinária — `importar`, `afirmar`, estrutura, vetor, função | 6 valores |
| | **Total** | **20 valores** |
