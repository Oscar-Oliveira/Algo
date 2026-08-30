---
theme : "white"
customTheme: "estilo-aulas"
---

# Aula 1

## O que é um Algoritmo?

Introdução à algoritmia + o primeiro programa em ALGO

---

## Objetivos de hoje

- Perceber o que é um algoritmo (sem computadores!)
- Ver que já usas algoritmos todos os dias
- Escrever o teu primeiro programa em ALGO
- Pedir dados ao utilizador e mostrar resultados no ecrã

---

## O que é um algoritmo?

Um **algoritmo** é uma sequência de passos, bem definidos e pela ordem certa, para resolver um problema ou realizar uma tarefa.

---

## Já usas algoritmos todos os dias

Pensa numa receita de bolo:

1. Pré-aquecer o forno
2. Misturar farinha, ovos e açúcar
3. Colocar a massa na forma
4. Levar ao forno 40 minutos
5. Deixar arrefecer

Isto **é** um algoritmo.

---

## Outro exemplo: ir a casa de um amigo

1. Sair de casa e virar à esquerda
2. Andar até ao semáforo
3. Virar à direita na rua da escola
4. É a terceira casa à esquerda

A **ordem** dos passos importa — trocar o passo 1 com o 3 leva-te a um sítio errado.

---

## E montar um móvel (tipo IKEA)?

- Instruções numeradas, passo a passo
- Cada passo depende dos anteriores
- Se saltares um passo, o móvel fica torto (ou nem fecha!)

---

## Características de um algoritmo

- **Sequência** de passos claros, sem ambiguidade
- **Ordem** importa
- **Número finito** de passos (tem sempre um fim)
- Recebe uma **entrada** e produz uma **saída**

---

## Entrada → Processamento → Saída

Receita de bolo:

- **Entrada:** farinha, ovos, açúcar
- **Processamento:** misturar e cozer
- **Saída:** um bolo

Todo o programa de computador segue este padrão.

---

## E os computadores?

Um **programa** é um algoritmo escrito numa linguagem que o computador consegue executar.

O computador não "pensa" — só segue os passos, exatamente como estão escritos, um a um.

---

## A linguagem ALGO

Vamos escrever os nossos algoritmos na linguagem **ALGO**:

- Parecida com português
- Feita para aprender a programar
- Cada programa que escreveres... é um algoritmo!

---

## A forma de um programa ALGO

```algo
algoritmo "OlaMundo"

inicio
    escrever("Olá, mundo!")
```

- `algoritmo "Nome"` é sempre a primeira linha (é só uma etiqueta)
- `inicio` marca onde o programa começa a correr
- **Não existe `fim`** — o bloco acaba quando a indentação volta atrás

---

## Blocos por indentação

- Não há chavetas `{ }` nem `begin` / `end`
- O que está indentado (avançado) pertence ao bloco de cima
- Cada nível = 1 tab OU 4 espaços (nunca misturar os dois)

```algo
inicio
    escrever("esta linha está dentro do inicio")
    escrever("esta também")
```

---

## `escrever` — mostrar coisas no ecrã

```algo
escrever("Olá, mundo!")
escrever("Isto", " ", "escreve", " ", "tudo", " ", "junto")
```

- Podes escrever várias coisas separadas por vírgulas
- **Não** junta espaços sozinho — tens de os pôr tu, entre aspas

---

## Comentários

```algo
// isto é um comentário de uma linha, o computador ignora-o

/* isto é um comentário
   que pode ter
   várias linhas */
```

Servem para explicares o teu código a ti próprio (e a quem o ler depois).

---

## `ler` — pedir dados ao utilizador

Para ler algo do utilizador, primeiro precisamos de uma **variável**: uma caixa com nome onde guardamos um valor.

```algo
nome:cadeia
escrever("Como te chamas? ")
ler(nome)
escrever("Olá, ", nome, "!")
```

Por agora usamos só `cadeia` (texto) e `inteiro` (número inteiro). Na próxima aula vemos todos os tipos.

---

## Exemplo completo

```algo
algoritmo "Cumprimento"

inicio
    nome:cadeia
    escrever("Como te chamas? ")
    ler(nome)

    idade:inteiro
    escrever("Quantos anos tens? ")
    ler(idade)

    escrever("Olá, ", nome, "! Vejo que tens ", idade, " anos.")
```

---

## Resumo

- Algoritmo = sequência de passos para resolver um problema
- Já usas algoritmos todos os dias (receitas, direções, instruções)
- Um programa ALGO começa com `algoritmo "Nome"` e `inicio`
- `escrever` mostra coisas, `ler` guarda o que o utilizador escreve numa variável
- Os blocos formam-se por indentação, não por chavetas

---

## Próxima aula

Vamos conhecer **todos os tipos de dados** de ALGO (`inteiro`, `decimal`, `booleano`, `cadeia`, `caracter`), como declarar variáveis com e sem valor inicial, e o que é uma `constante`.

---

## Agora é a tua vez!

Abre a ficha de trabalho da Aula 1 e resolve os exercícios.
