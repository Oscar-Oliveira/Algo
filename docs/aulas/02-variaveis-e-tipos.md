---
theme: "white"
customTheme: "estilo-aulas"
---

# Aula 2

## Variáveis e Tipos

Os 5 tipos primitivos, `constante`, e as regras de tipo da Linguagem Algorítmica

---

## Recapitulando a Aula 1

- Um **algoritmo** é uma sequência de passos para resolver um problema
- Um programa em Linguagem Algorítmica tem `algoritmo "Nome"` e um bloco `inicio`
- `escrever` mostra coisas, `ler` guarda o que o utilizador escreve
- Já usámos `cadeia` e `inteiro` — hoje vemos **todos** os tipos

---

## Objetivos de hoje

- Conhecer os 5 tipos primitivos da Linguagem Algorítmica
- Declarar variáveis, com e sem valor inicial
- Perceber o que é uma `constante`
- Saber o que acontece quando misturamos tipos

---

## O que é uma variável, outra vez

Uma variável é uma **caixa com nome** onde guardamos um valor.

Mas nem todas as caixas servem para tudo: uma caixa de sapatos não é boa para guardar água. Da mesma forma, cada variável em Linguagem Algorítmica **tem um tipo**, que diz que género de valor pode guardar.

---

## Porque precisamos de tipos

Se dissermos ao computador que `idade` é um número, ele sabe que pode somar 1 a `idade`. Se `idade` fosse só "uma caixa qualquer", o computador não saberia se isso faz sentido.

O tipo é uma **promessa**: esta caixa só guarda isto, e nada mais.

---

## Os 5 tipos primitivos

| Tipo | Guarda | Exemplo |
|---|---|---|
| `inteiro` | um número inteiro | `42`, `-7` |
| `decimal` | um número com casas decimais | `3.14` |
| `booleano` | verdadeiro ou falso | `verdadeiro` |
| `cadeia` | texto | `"Bom dia"` |
| `caracter` | exatamente 1 símbolo | `'a'` |

---

## `inteiro`

Números inteiros, sem casas decimais, sem limite de grandeza.

```algo
idade:inteiro = 15
numeroDeAlunos:inteiro = 28
saldo:inteiro = -10
```

Usa-se para contar coisas: pessoas, pontos, anos.

---

## `decimal`

Números com casas decimais.

```algo
altura:decimal = 1.70
preco:decimal = 9.99
media:decimal = 14.5
```

Usa-se sempre que o número pode ter "vírgula": preços, medidas, médias.

---

## `booleano`

Só tem dois valores possíveis: `verdadeiro` ou `falso`.

```algo
aprovado:booleano = verdadeiro
chove:booleano = falso
```

Usa-se para responder a perguntas de sim/não: "já terminou?", "está a chover?".

---

## `cadeia`

Texto, entre aspas duplas. Pode ter 0, 1 ou muitos caracteres.

```algo
nome:cadeia = "Rita"
morada:cadeia = "Rua das Flores, 12"
vazio:cadeia = ""
```

---

## `caracter`

Exatamente **1** símbolo, entre aspas simples. Nem mais, nem menos.

```algo
inicial:caracter = 'R'
resposta:caracter = 's'
```

`'ab'` ou `''` são erro — se precisas de mais do que 1 símbolo, usa `cadeia`.

---

## Declarar uma variável

```algo
idade:inteiro                  // sem valor inicial
nome:cadeia = "Rita"           // com valor inicial

idade = 20                     // atribuição, sempre com '='
```

O tipo vem **depois** dos dois pontos: `nome:tipo` — nunca `tipo nome`.

---

## Várias variáveis juntas

Só quando **não** têm valor inicial, podes declarar várias do mesmo tipo separadas por vírgula:

```algo
a, b, c:inteiro          // válido

x, y:inteiro = 0         // erro! não podes inicializar assim
```

---

## Valores por omissão

Uma variável nunca fica "vazia" — se não lhe deres valor, recebe um valor por omissão:

| Tipo | Valor por omissão |
|---|---|
| `inteiro` | `0` |
| `decimal` | `0.0` |
| `booleano` | `falso` |
| `cadeia` | `""` (texto vazio) |
| `caracter` | `' '` (um espaço) |

---

## Nomes de variáveis

- Começam por letra ou `_`
- Seguidos de letras, dígitos ou `_`
- Letras acentuadas são aceites: `preço` é válido
- Não podem ser uma palavra reservada da linguagem (`se`, `para`, `funcao`, `e`, `ou`, ...)

---

## `constante`

Uma variável que **nunca muda** depois de criada.

```algo
constante IVA:decimal = 1.23
constante ANO_LETIVO:inteiro = 2026

inicio
    precoFinal:decimal = 10.0 * IVA
```

- Tem sempre de ter valor inicial
- Nunca pode ser reatribuída depois

---

## Onde declarar uma `constante`

Pode ser declarada **fora** de `inicio` (constante global, visível em todo o programa) ou **dentro** de `inicio` (só visível aí).

```algo
algoritmo "Loja"

constante IVA:decimal = 1.23   // global

inicio
    precoBase:decimal = 10.0
    escrever(precoBase * IVA)
```

---

## Atenção: `+` não junta números com texto

```algo
idade:inteiro = 20

// escrever("Idade: " + idade)   // ERRO! cadeia + inteiro
escrever("Idade: ", idade)       // certo: argumentos separados por vírgula
```

`+` funciona entre dois números (soma) OU entre dois textos (concatenação) — nunca um de cada.

---

## Juntar texto com `+`

Entre dois `cadeia`/`caracter`, `+` **concatena** (junta):

```algo
inicial:caracter = 'R'
nome:cadeia = "Rita"

cracha:cadeia = inicial + ". " + nome
escrever(cracha)   // R. Rita
```

---

## Exemplo completo

```algo
algoritmo "FichaSimples"

constante ANO_LETIVO:inteiro = 2026

inicio
    nome:cadeia
    escrever("Nome: ")
    ler(nome)

    nota:decimal
    escrever("Nota (0 a 20): ")
    ler(nota)

    aprovado:booleano = nota >= 9.5

    escrever("Ano letivo: ", ANO_LETIVO)
    escrever(nome, " -- nota ", nota, " -- aprovado: ", aprovado)
```

---

## Resumo

- 5 tipos: `inteiro`, `decimal`, `booleano`, `cadeia`, `caracter`
- Declaração: `nome:tipo`, com ou sem valor inicial
- Toda a variável tem sempre um valor — nunca fica "vazia"
- `constante`: tem sempre valor inicial, nunca muda
- `+` exige dois números ou dois textos, nunca uma mistura

---

## Próxima aula

Vamos ver os **operadores**: aritméticos (`+`, `-`, `*`, `/`), relacionais (`>`, `<`, `==`, ...) e lógicos (`e`, `ou`, `nao`) — a base de qualquer decisão que um programa tem de tomar.

---

## Agora é a tua vez!

Abre a ficha de trabalho da Aula 2 e resolve os exercícios.
