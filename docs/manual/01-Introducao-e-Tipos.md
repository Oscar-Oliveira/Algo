# 1. Introdução e tipos

## 1.1 A forma de um programa

Todo o programa ALGO começa com um cabeçalho e tem um único bloco
`inicio`, que é onde a execução começa:

```algo
algoritmo "OlaMundo"

inicio
    escrever("Olá, mundo!")
```

- `algoritmo "Nome"` é sempre a primeira linha. O nome é só uma etiqueta
  (aparece em mensagens/ferramentas), não afeta a execução.
- `inicio` marca o início do programa principal. **Não existe `fim`** —
  o bloco termina onde a indentação volta a descer, tal como qualquer
  outro bloco da linguagem (`se`, `para`, `funcao`, ...).
- Só pode haver um `inicio`, e tem de ser a última coisa do ficheiro:
  nada pode vir depois dele.

Antes de `inicio` pode haver, por esta ordem quando presentes,
`importar` (bibliotecas — capítulo 8), `incluir` (outros ficheiros —
capítulo 9), `estrutura` (capítulo 7), `funcao`/`procedimento` (capítulo
6) e `constante`/variáveis globais (secção 1.5).

### Blocos por indentação

Não há chavetas nem `begin`/`end`: um bloco é tudo o que está indentado
um nível a mais do que a linha que o abre.

```algo
algoritmo "Indentacao"

inicio
    x:inteiro = 5
    escrever("antes")
    escrever("depois")
```

Regras da indentação (aplicadas por igual a todo o ficheiro):

- Cada nível é **1 tab OU 4 espaços** — nunca misturados na mesma linha,
  e o ficheiro inteiro tem de escolher um dos dois estilos (a primeira
  linha indentada decide; uma linha seguinte com o outro estilo é erro
  de compilação).
- Um bloco novo só pode aumentar **exatamente 1 nível** em relação ao
  bloco à volta — saltar 2 níveis de uma vez é erro.
- Uma linha em branco não conta para a indentação.

## 1.2 Comentários

```algo
// comentário até ao fim da linha

/* comentário
   de várias
   linhas */
```

`//` esconde o resto da linha, mesmo que essa linha contenha o que
pareceria abrir um comentário de bloco. `/* ... */` pode abranger várias
linhas; um `/*` sem `*/` a fechar é erro de compilação (não fica
silenciosamente por fechar até ao fim do ficheiro).

## 1.3 Os cinco tipos primitivos

| Tipo | Guarda | Literal | Exemplo |
|---|---|---|---|
| `inteiro` | um número inteiro | dígitos, sem ponto | `42`, `-7` |
| `decimal` | um número com casas decimais | dígitos com `.` | `3.14`, `.5`, `2.` |
| `booleano` | verdadeiro ou falso | `verdadeiro` / `falso` | `verdadeiro` |
| `cadeia` | texto | entre aspas duplas | `"Bom dia"` |
| `caracter` | exatamente 1 símbolo | entre aspas simples | `'a'` |

Notas por tipo:

- **`inteiro`** não tem limite de grandeza (nem overflow) — ao contrário
  de C/Java, onde um `int` tem um tamanho fixo em bits. `factorial(30)`
  calcula-se sem problema.
- **`decimal`** é o `float` habitual (vírgula flutuante de dupla
  precisão) — tem os mesmos limites e arredondamentos que qualquer outra
  linguagem com este tipo de número.
- **`caracter`** é sempre exatamente 1 símbolo — `'ab'` ou `''` são erro
  de compilação (a diferença para `cadeia` não é só a aspa: é a
  garantia de comprimento 1). O valor por omissão (sem inicializador)
  também respeita isto: é `' '` (espaço).
- Em `cadeia`/`caracter`, `\"`, `\'`, `\\` e `\n` são reconhecidos como
  escapes dentro do literal correspondente; qualquer outra barra
  invertida fica tal-e-qual.

Não existe um tipo "sem valor"/`void` para variáveis — só
`procedimento` (capítulo 6) não devolve nada.

## 1.4 Declarar e atribuir variáveis

```algo
idade:inteiro                  // sem valor inicial
nome:cadeia = "Rita"           // com valor inicial

idade = 20                     // atribuição, sempre com '='
```

- A declaração é sempre `nome:tipo`, com o tipo depois dos dois pontos
  — nunca `tipo nome` como em C/Java.
- Várias variáveis do mesmo tipo podem ser declaradas juntas,
  **separadas por vírgula, só sem valor inicial**:
  `a, b, c:inteiro` é válido; `a, b:inteiro = 0` é erro de sintaxe (não
  é possível inicializar mais que uma variável na mesma linha).
- Uma variável não pode ser lida antes de existir — declarar sem valor
  inicial dá-lhe logo um valor por omissão (nunca fica "indefinida"):

  | Tipo | Valor por omissão |
  |---|---|
  | `inteiro` | `0` |
  | `decimal` | `0.0` |
  | `booleano` | `falso` |
  | `cadeia` | `""` |
  | `caracter` | `' '` (um espaço) |

- Um nome de variável começa por letra ou `_`, seguido de
  letras/dígitos/`_` (letras acentuadas são aceites: `preço` é um nome
  válido). Não pode coincidir com uma palavra reservada (`se`, `para`,
  `funcao`, ...).

## 1.5 `constante`

```algo
constante IVA:decimal = 1.23

inicio
    precoFinal:decimal = 10.0 * IVA
```

- Tem sempre de ter um valor inicial — `constante X:inteiro` sem `=` é
  erro de sintaxe.
- Não pode ser reatribuída depois (nem por `=`, nem por `ler`, nem
  passada como argumento `ref` — capítulo 6).
- Pode ser declarada **fora** de qualquer função (constante global,
  visível em todo o programa) ou **dentro** de `inicio`/de uma função
  (só visível aí).
- Ao contrário de uma declaração normal, não aceita vários nomes
  separados por vírgula nem é um vetor.

### Variáveis globais vs. locais

Só o que é declarado **antes de `inicio`**, directamente no programa
(fora de qualquer `funcao`/`procedimento`), é global e fica visível
dentro das funções. Uma variável declarada dentro de `inicio` é local
ao programa principal — não é visível dentro de nenhuma função, mesmo
que `inicio` venha depois dela no ficheiro:

```algo
algoritmo "Escopo"

total:inteiro = 0        // global -- visível em toda a parte

funcao dobroDoTotal():inteiro
    retornar total * 2   // lê a global

inicio
    y:inteiro = 10        // local a 'inicio', não visível em funções
    escrever(dobroDoTotal())
```

## 1.6 `escrever` e `ler`

```algo
nome:cadeia
escrever("Como te chamas? ")
ler(nome)
escrever("Olá, ", nome, "!")
```

- `escrever` aceita vários argumentos separados por vírgula, de tipos
  diferentes, e **não insere nenhum separador entre eles** — a linha
  acima mostra `Olá, Rita!` porque o espaço depois da vírgula já está no
  próprio literal `"Olá, "`.
- `ler(variavel)` bloqueia à espera de uma linha de input e converte-a
  para o tipo declarado da variável; se a conversão falhar (ex. escrever
  letras onde se espera `inteiro`), pede o valor outra vez em vez de
  rebentar o programa. `booleano` aceita `verdadeiro`/`v`/`true` ou
  `falso`/`f`/`false` (outra coisa qualquer é pedida de novo);
  `caracter` só aceita exactamente 1 símbolo.

## 1.7 `+` não converte números para texto

Uma armadilha comum a evitar desde já: `+` exige os dois lados
numéricos (soma) OU os dois lados texto (`cadeia`/`caracter`,
concatenação) — nunca um de cada:

```algo
idade:inteiro = 20
// escrever("Idade: " + idade)     // ERRO de compilação: cadeia + inteiro
escrever("Idade: ", idade)         // certo: argumentos separados por vírgula
```

Isto é deliberado (nenhum outro operador da linguagem faz conversão
implícita entre tipos incompatíveis). A forma correta de misturar
texto e números é `escrever` com vários argumentos, como acima; para
construir uma única `cadeia` com um número lá dentro, converte-o
primeiro (`conversao.paraTexto`, capítulo 8).

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
