---
theme: "white"
customTheme: "estilo-aulas"
---

# Aula 13

## Exercícios II

Tema: Jogos e Simulações

---

## Sem matéria nova, mais difícil

Ainda sem sintaxe nova — mas os problemas de hoje juntam mais peças ao mesmo tempo (estruturas, vetores, matrizes, funções, `matematica.aleatorio`) do que a Aula 12.

---

## O tema de hoje

Jogos e simulações: sorte (dados, moedas), decisão (pedra-papel-tesoura), progresso (forca), e simulações mais completas (batalhas, corridas, rankings). É um ótimo campo de treino porque força a pensar em **estado que muda ao longo do tempo** — exatamente o que um `enquanto`/`para` existe para fazer.

---

## Ferramenta nova (de biblioteca, não de sintaxe): `matematica.aleatorio`

```algo
importar Matematica

inicio
    dado:inteiro = matematica.aleatorio(1, 6)     // 1 a 6, ambos possíveis
```

Já viste isto na Aula 10 — hoje vais usá-lo a sério, para simular sorte.

---

## Exemplo resolvido: contar caras e coroas

*(este exemplo não está na tua ficha)*

```algo
algoritmo "ContarLancamentos"

importar Matematica

inicio
    n:inteiro
    escrever("Quantos lançamentos? ")
    ler(n)

    caras:inteiro = 0
    i:inteiro
    para i de 1 ate n fazer
        se matematica.aleatorio(0, 1) == 0 entao
            caras = caras + 1

    escrever("Caras: ", caras, " de ", n)
```

---

## Repara

- `matematica.aleatorio(0, 1)` dá `0` ou `1` — decidimos que `0` é "cara"
- Como o resultado é aleatório, **não há uma saída certa** para comparar — testa correndo o programa várias vezes e confirma que os números fazem sentido (`caras` nunca maior que `n`, por exemplo)

---

## Uma dica para os exercícios mais difíceis

Alguns exercícios de hoje (jogo do galo, batalha, ranking) têm **vários pedaços** a trabalhar juntos. Antes de escrever código:

1. Que dados preciso de guardar? (uma `estrutura`? um vetor? uma matriz?)
2. O que muda a cada volta do ciclo?
3. Quando é que o ciclo tem de parar?

---

## A tua ficha de hoje

8 exercícios, médio → avançado: moeda ao ar, dado com histograma, pedra-papel-tesoura, jogo da forca, vencedor do jogo do galo, batalha por turnos, ranking com ordenação, e uma simulação de corrida.

---

## Agora é a tua vez!

Abre a ficha de trabalho da Aula 13 e resolve os 8 exercícios, por ordem.
