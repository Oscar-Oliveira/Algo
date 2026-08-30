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

O literal pode ter **menos** elementos do que o tamanho declarado — os
valores dados ocupam as primeiras posições (`0`, `1`, ...) e as que
faltam, no fim, ficam com o valor por omissão do tipo:

```algo
inicio
    v:inteiro[5] = {1, 2, 3}
    escrever(v[0], " ", v[3], " ", v[4])    // 1 0 0
```

Ter **mais** elementos do que o tamanho declarado continua a ser erro
de compilação — não há onde os pôr:

```algo
inicio
    // v:inteiro[3] = {1, 2, 3, 4}    // ERRO! 4 valores para 3 posições
```

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

## 5.4 Um vetor é um tipo por referência: `=` não copia

Tal como `estrutura` (capítulo 7), um vetor é um tipo **por
referência**: `=`, uma declaração a partir de outra variável,
`retornar`, um argumento passado sem `ref` a uma função/procedimento
(capítulo 6), e um elemento/campo populado a partir de uma variável
existente num literal — todos fazem as duas variáveis apontarem para o
**mesmo** vetor por baixo, não para duas cópias independentes. Mudar
uma é mudar a outra:

```algo
inicio
    v1:inteiro[3] = {1, 2, 3}
    v2:inteiro[3] = v1
    v2[0] = 99
    escrever(v1[0], " ", v2[0])    // 99 99 -- é o MESMO vetor
```

O tamanho declarado (`inteiro[3]`) não faz parte do *tipo* de um
vetor — só é validado contra o valor real quando esse valor vem de
outra variável ou de uma chamada (nunca de um literal `{...}`, cujo
tamanho já é validado em compilação). Se não coincidir, é um erro
amigável em **runtime**, não em compilação:

```algo
inicio
    v1:inteiro[5] = {1, 2, 3, 4, 5}
    v2:inteiro[3]
    v2 = v1
    // erro em runtime: "este valor tem 5 elemento(s), mas o vetor de
    // destino tem tamanho 3"
```

Para obter uma cópia **independente** de um vetor (ou só de parte
dele), copia elemento a elemento com um ciclo — é a única forma:

```algo
algoritmo "CopiaDeVetor"

inicio
    v1:inteiro[5] = {1, 2, 3, 4, 5}
    copia:inteiro[5]
    i:inteiro
    para i de 0 ate 4 fazer
        copia[i] = v1[i]

    copia[0] = 99
    escrever(v1[0], " ", copia[0])    // 1 99 -- agora sim, independentes
```

## 5.5 Igualdade compara por referência, não por conteúdo

`==`/`<>` entre dois vetores comparam se são **o mesmo vetor**, não se
têm os mesmos elementos — mesmo com conteúdo idêntico, dois vetores
construídos separadamente são considerados diferentes:

```algo
inicio
    a:inteiro[3] = {1, 2, 3}
    b:inteiro[3] = {1, 2, 3}
    escrever(a == b)      // falso -- mesmo conteúdo, mas vetores diferentes
    c:inteiro[3] = a
    escrever(a == c)      // verdadeiro -- 'c' é o MESMO vetor que 'a'
```

`x == nulo`/`x <> nulo` continuam a funcionar normalmente para testar
se uma variável de vetor ainda não foi construída. Para comparar o
**conteúdo** de dois vetores, escreve a tua própria comparação
elemento a elemento:

```algo
funcao mesmoConteudo(a:inteiro[], tamA:inteiro, b:inteiro[], tamB:inteiro):booleano
    i:inteiro
    se tamA <> tamB entao
        retornar falso
    para i de 0 ate tamA - 1 fazer
        se a[i] <> b[i] entao
            retornar falso
    retornar verdadeiro
```

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
