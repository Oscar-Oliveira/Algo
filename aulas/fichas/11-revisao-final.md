# Ficha de Trabalho — Aula 11: Revisão Final (Aulas 1 a 10)

## Antes de começares

Esta é a última ficha antes das aulas de prática livre. Os exercícios combinam tudo o que o curso ensinou: tipos, operadores, decisões, ciclos, vetores/matrizes, funções/procedimentos, estruturas, bibliotecas, `incluir` e `afirmar`. Testa sempre o teu programa a correr, não só a lê-lo.

### Exercício 1 — Registo de despesas por categoria

Define uma `estrutura Despesa` (`descricao`, `valor`, `categoria`). Pede várias despesas para um vetor, usando `afirmar` para garantir que o valor é positivo. Escreve uma `funcao totalPorCategoria` que soma as despesas de uma categoria (usa `importar Cadeia` para comparar sem distinguir maiúsculas/minúsculas), e mostra o total de uma categoria escolhida pelo utilizador.

### Exercício 2 — A palavra mais longa de uma frase

Pede uma frase com exatamente 5 palavras. Usa `cadeia.dividir` para a separar, guarda cada palavra numa `estrutura Palavra` (`texto`, `tamanho`) dentro de um vetor, e escreve qual é a mais longa.

### Exercício 3 — Soma recursiva de um vetor

Escreve uma `funcao somaVetor(v:inteiro[], i:inteiro, tamanho:inteiro):inteiro` **recursiva** (sem ciclos) que soma todos os elementos de um vetor. Testa com um vetor de 5 números.

### Exercício 4 — Gestor de contactos com validação

Cria um ficheiro `biblioteca_validacoes.algo` com uma `funcao ehTelefoneValido(tel:cadeia):booleano` (usa `cadeia.comprimento`). Cria um `principal.algo` que o `incluir`, define uma `estrutura Contacto`, e usa `afirmar` com a função de validação antes de guardar cada contacto num vetor.

### Exercício 5 — Tabuleiro do jogo do galo

Declara uma matriz `3x3` de `caracter`, preenche-a toda com `'-'` usando `para` aninhados, marca algumas posições com `'X'`/`'O'`, e escreve o tabuleiro linha a linha (concatenando os caracteres numa `cadeia`).

### Exercício 6 — Sistema de notas completo

Define uma `estrutura Aluno` com `nome` (`cadeia`) e `notas` (vetor de 3 `decimal`). Pede os dados de vários alunos, usando `afirmar` para garantir que cada nota está entre `0` e `20`. Escreve uma `funcao media` (recebe o vetor de notas) e uma `funcao classificar` (recebe a média, devolve "Aprovado"/"Reprovado"). No fim, para cada aluno, escreve o nome em maiúsculas (`importar Cadeia`), a média, e a classificação.
