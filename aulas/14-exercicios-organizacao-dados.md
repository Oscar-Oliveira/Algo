---
theme: "white"
customTheme: "estilo-aulas"
---

# Aula 14

## Exercícios III

Tema: Organização de Dados — Mini-Projeto Final

---

## A última aula do curso

Sem matéria nova, mais uma vez — mas com o desafio mais avançado do curso: sistemas que **guardam, procuram, ordenam e relacionam** dados, terminando num mini-projeto que junta praticamente tudo o que aprendeste.

---

## O tema de hoje

Organizar dados é o que a maior parte dos programas realmente faz: uma lista de contactos, uma agenda, um inventário, uma biblioteca. As perguntas repetem-se sempre: *Como guardo isto? Como encontro um item específico? Como ordeno? Como relaciono duas coisas?*

---

## Padrões que vais usar hoje

- **Procurar**: percorrer um vetor até encontrar o que procuras (ou chegar ao fim sem encontrar)
- **Ordenar**: comparar vizinhos e trocar, repetidamente, até tudo ficar na ordem certa
- **Filtrar**: percorrer e só agir nos elementos que cumprem uma condição
- **Relacionar**: comparar pares de elementos entre si

---

## Exemplo resolvido: procurar num vetor

*(este exemplo não está na tua ficha)*

```algo
funcao procurarIdade(idades:inteiro[], tamanho:inteiro, alvo:inteiro):inteiro
    i:inteiro
    para i de 0 ate tamanho - 1 fazer
        se idades[i] == alvo entao
            retornar i
    retornar -1
```

Padrão clássico: percorre tudo; se encontrares, `retornar` logo o índice; se chegares ao fim sem encontrar, `retornar -1`.

---

## Exemplo resolvido: um vetor de "tamanho variável"

Um vetor tem sempre um tamanho fixo — mas podes usar uma variável extra para saberes **quantas posições estão realmente a ser usadas**:

```algo
itens:cadeia[20]        // capacidade máxima
numItens:inteiro = 0     // quantos estão realmente ocupados

// para adicionar:
itens[numItens] = "novo item"
numItens = numItens + 1
```

Este é o truque por trás do mini-projeto de hoje.

---

## Sobre o mini-projeto (último exercício)

O Exercício 8 é maior que os anteriores: um **sistema completo**, com menu interativo (como viste na Aula 6), que junta estrutura, vetor "de tamanho variável", funções de procura, biblioteca `Cadeia`, e `afirmar`. Deixa-o para o fim, depois de resolveres os outros 7.

---

## A tua ficha de hoje

7 exercícios (lista telefónica, agenda, inventário, estatísticas, catálogo com empréstimos, conflitos de horário, vendas por mês) e o mini-projeto final: um sistema de gestão de biblioteca completo.

---

## Chegaste ao fim do curso

Depois desta ficha, já sabes tudo o que este curso tinha para ensinar sobre algoritmia — e já o aplicaste em dezenas de programas diferentes. O resto é praticar mais.

---

## Agora é a tua vez!

Abre a ficha de trabalho da Aula 14. Boa sorte com o mini-projeto final!
