# 5. Vetores e matrizes

## 5.1 Declarar e indexar

```algo
inicio
    notas:decimal[5]              // vetor de 5 posições, todas 0.0
    notas[0] = 18.5
    escrever(notas[0])
```

- Um vetor de 1 dimensão declara-se `nome:tipo[tamanho]`.
- Os índices vão de `0` a `tamanho - 1` — tal como em Python, Java, C#
  (não começam em 1).
- Sem inicializador, cada posição fica com o valor por omissão do tipo
  (capítulo 1) — `0` para `inteiro`, `0.0` para `decimal`, etc.

### Literal `{ }`

```algo
inicio
    primos:inteiro[5] = {2, 3, 5, 7, 11}
    escrever(primos[0], primos[4])
```

O literal tem de ter exatamente o número de elementos do tamanho
declarado — nem a mais, nem a menos (erro de compilação, não
preenchimento/corte silencioso).

### Percorrer um vetor

```algo
inicio
    notas:decimal[5] = {14.0, 9.5, 18.0, 12.5, 16.0}
    i:inteiro
    soma:decimal = 0.0
    para i de 0 ate 4 fazer
        soma = soma + notas[i]
    escrever("Média: ", soma / 5)
```

Um padrão comum é guardar o tamanho numa `constante` e usar
`tamanho - 1` no `ate`, para não repetir o número:

```algo
inicio
    constante TAMANHO:inteiro = 5
    notas:decimal[TAMANHO] = {14.0, 9.5, 18.0, 12.5, 16.0}
    i:inteiro
    para i de 0 ate TAMANHO - 1 fazer
        escrever(notas[i])
```

### Índices inválidos

Um índice fora de `0 .. tamanho-1` é sempre erro em **runtime**, nunca
em compilação (o compilador não segue os valores das variáveis) —
inclui índices negativos, que **não** "contam a partir do fim" como em
Python:

```algo
inicio
    v:inteiro[5] = {1, 2, 3, 4, 5}
    escrever(v[-1])       // erro em runtime, NÃO devolve o último elemento
    escrever(v[5])        // erro em runtime -- só 0..4 são válidos
```

## 5.2 Matrizes (2+ dimensões)

```algo
inicio
    tabuleiro:inteiro[3][3]
    tabuleiro[0][0] = 1
    tabuleiro[1][1] = 1
    tabuleiro[2][2] = 1
```

Uma matriz `inteiro[8][8]` pode ter tantas dimensões quantas
precisares (`[3][3][3]`, ...); cada par de colchetes indexa mais um
nível. Um literal aninhado usa o mesmo número de níveis de `{ }` que
dimensões:

```algo
inicio
    m:inteiro[2][2] = {{1, 2}, {3, 4}}
    escrever(m[0][1], " ", m[1][0])     // 2 3
```

Percorre-se com `para` aninhados, um por dimensão:

```algo
inicio
    m:inteiro[2][3] = {{1, 2, 3}, {4, 5, 6}}
    i:inteiro
    j:inteiro
    para i de 0 ate 1 fazer
        para j de 0 ate 2 fazer
            escrever(m[i][j])
```

Cada linha de uma matriz não inicializada é a sua própria cópia
independente — mudar `m[0][0]` nunca afeta `m[1][0]`, ao contrário do
erro clássico em Python de construir uma matriz com `[[0]*n]*n` (onde
as `n` linhas seriam todas o MESMO objeto por baixo).

## 5.3 Tamanho calculado em runtime

O tamanho de um vetor não precisa de ser um literal — pode ser qualquer
expressão `inteiro`, incluindo uma variável, avaliada quando a
declaração corre:

```algo
inicio
    n:inteiro
    escrever("Quantos números? ")
    ler(n)

    v:inteiro[n]
    i:inteiro
    para i de 0 ate n - 1 fazer
        v[i] = i * i
```

Um tamanho negativo, ou maior do que **10 milhões de elementos no
total** (produto de todas as dimensões, para uma matriz), é erro em
runtime com mensagem amigável, não um `MemoryError`/travamento cru.

## 5.4 Um vetor não se copia com `=`

Ao contrário de `estrutura` (capítulo 7), que copia por valor tanto com
`=` como ao declarar `p2:Ponto = p1`, um vetor **não pode ser o valor
de uma atribuição nem de uma declaração** — nenhuma das duas formas
abaixo compila:

```algo
inicio
    v1:inteiro[3] = {1, 2, 3}
    v2:inteiro[3]
    // v2 = v1                    // ERRO: 'v2' é um vetor; não pode ser atribuído diretamente
    // v3:inteiro[3] = v1         // ERRO: 'v1' é um vetor; falta indexá-lo
```

As únicas formas de obter uma cópia independente de um vetor são: uma
**função que o devolve** (`retornar`), um **literal** `{...}`, ou
passá-lo como argumento normal (sem `ref`) a uma função/procedimento —
os três copiam por valor (capítulo 6). Sem nenhuma dessas, a única
alternativa é copiar elemento a elemento:

```algo
algoritmo "CopiaDeVetor"

inicio
    v1:inteiro[3] = {1, 2, 3}
    v2:inteiro[3]
    i:inteiro
    para i de 0 ate 2 fazer
        v2[i] = v1[i]

    v2[0] = 99
    escrever(v1[0], " ", v2[0])    // 1 99 -- independentes
```

> **Nota / achado**: `docs/DecisoesELimitacoesConhecidas.md` (secção
> "Cópia por valor e `ref`") diz que "atribuição, declaração, retornar,
> e literais `{...}` copiam structs/vetores por valor" — verdade para
> `estrutura`, mas **não** para vetor: `atribuição`/`declaração` a
> partir de uma variável são rejeitadas em compilação para um vetor,
> nunca chegam a copiar nada. Ver [`ACHADOS.md`](ACHADOS.md).

## Exemplo completo

```algo
algoritmo "NotasDaTurma"

inicio
    n:inteiro
    escrever("Quantos alunos? ")
    ler(n)

    notas:decimal[n]
    i:inteiro
    para i de 0 ate n - 1 fazer
        escrever("Nota do aluno ", i + 1, ": ")
        ler(notas[i])

    soma:decimal = 0.0
    maior:decimal = notas[0]
    para i de 0 ate n - 1 fazer
        soma = soma + notas[i]
        se notas[i] > maior entao
            maior = notas[i]

    escrever("Média da turma: ", soma / n)
    escrever("Nota mais alta: ", maior)
```
