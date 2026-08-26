# Ficha de Trabalho — Aula 13: Exercícios II (Jogos e Simulações)

## Antes de começares

Não há matéria nova nesta ficha — usa livremente tudo o que já aprendeste (Aulas 1 a 11), incluindo `matematica.aleatorio` da Aula 10. Os exercícios estão ordenados do mais simples para o mais elaborado. Como há aleatoriedade envolvida, não há uma "saída certa" para comparar — corre o programa várias vezes e confirma que os resultados fazem sentido.

### Exercício 1 — Moeda ao ar

Pede quantas vezes lançar uma moeda, simula os lançamentos com `matematica.aleatorio`, e conta quantas caras e quantas coroas saíram.

### Exercício 2 — Histograma de um dado

Pede quantos lançamentos de um dado (1 a 6) simular. Usa um vetor de 6 posições para contar quantas vezes cada face saiu, e escreve o histograma no fim.

### Exercício 3 — Pedra, papel, tesoura

Pede a escolha do jogador (1-Pedra, 2-Papel, 3-Tesoura), gera uma escolha aleatória para o computador, e decide quem ganha.

### Exercício 4 — Jogo da forca simplificado

Usa uma palavra secreta fixa. Mostra o progresso com `_` nas letras por adivinhar. Pede letras até a palavra estar completa ou até um número máximo de erros ser atingido.

### Exercício 5 — Vencedor do jogo do galo

Declara uma matriz `3x3` de `caracter` já preenchida (com um literal). Escreve uma `funcao verificarVencedor(tabuleiro:caracter[][], marca:caracter):booleano` que verifica linhas, colunas e as duas diagonais. Usa-a para determinar se há um vencedor.

### Exercício 6 — Batalha por turnos

Define uma `estrutura Monstro` (`nome`, `vida`, `ataque`). Cria dois monstros e simula uma batalha por turnos (cada um ataca o outro alternadamente) até um deles ficar com vida menor ou igual a zero.

### Exercício 7 — Ranking de jogadores

Pede os dados de vários jogadores (`nome`, `pontuacao`) para um vetor de estruturas. Ordena-os por pontuação decrescente (podes usar o método simples de comparar vizinhos e trocar, repetidamente) e escreve o ranking final.

### Exercício 8 — Simulação de corrida

Define uma `estrutura Corredor` (`nome`, `posicao`). Simula uma corrida em que, a cada volta, cada corredor avança uma quantidade aleatória, até um deles atingir a distância da meta. Escreve o vencedor e em que volta venceu.
