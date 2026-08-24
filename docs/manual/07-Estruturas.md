# 7. Estruturas

## 7.1 Definir e usar

```algo
algoritmo "Exemplo"

estrutura Ponto
    x:inteiro
    y:inteiro

inicio
    p:Ponto = {x: 3, y: 4}
    escrever(p.x, ", ", p.y)
```

- `estrutura Nome` é declarada fora de `inicio`, com um ou mais campos
  `nome:tipo`, um por linha, tal como uma declaração normal.
- Um valor constrói-se com um literal `{campo: valor, ...}` — os nomes
  não têm de vir pela ordem da definição.
- Um campo lê-se e atribui-se com `.`: `p.x`, `p.x = 10`.

### Campos omitidos ficam com o valor por omissão

```algo
inicio
    p:Ponto = {x: 3}
    escrever(p.x, ", ", p.y)      // 3, 0 -- 'y' não foi dado, fica 0
```

## 7.2 Igualdade compara campo a campo

`==`/`<>` entre dois valores do mesmo tipo `estrutura` comparam todos
os campos, não a identidade do objeto:

```algo
inicio
    a:Ponto = {x: 1, y: 2}
    b:Ponto = {x: 1, y: 2}
    escrever(a == b)              // verdadeiro -- mesmos valores, variáveis diferentes
```

## 7.3 `estrutura` é sempre copiada por valor

Ao contrário de `vetor` (capítulo 5), `estrutura` copia normalmente com
`=` e com uma declaração a partir de outra variável — as duas variáveis
ficam completamente independentes a seguir:

```algo
inicio
    a:Ponto = {x: 1, y: 2}
    b:Ponto = a
    b.x = 99
    escrever(a.x, " ", b.x)       // 1 99 -- independentes
```

Isto vale em **todo** o sítio onde um valor `estrutura` circula:
atribuição, declaração, `retornar`, passar como argumento por valor
(sem `ref`), e **atribuir a um campo** — `no.seguinte = outroNo` copia
`outroNo` para dentro do campo, não guarda uma referência a ele (mais
em 7.5). Só um parâmetro `ref` (7.4) ou um campo `ref` (7.5) evita a
cópia.

## 7.4 Passar por referência

Tal como um parâmetro escalar, um parâmetro `estrutura` pode ser `ref`
— a função passa a mutar diretamente a variável do chamador, sem
devolver nada:

```algo
procedimento deslocar(ref p:Ponto, dx:inteiro, dy:inteiro)
    p.x = p.x + dx
    p.y = p.y + dy

inicio
    p:Ponto = {x: 0, y: 0}
    deslocar(p, 5, 3)
    escrever(p.x, " ", p.y)       // 5 3
```

## 7.5 Estruturas recursivas (árvores, listas)

Um campo pode ter o tipo da própria estrutura (ou de outra que aponte
de volta para ela) — útil para árvores e listas ligadas:

```algo
estrutura No
    valor:inteiro
    seguinte:No
```

Um campo desse tipo, se omitido no literal, fica `nulo` por omissão —
nunca tenta construir-se a si próprio infinitamente. `nulo` é o único
valor que se pode comparar com `==`/`<>` contra qualquer tipo
`estrutura`, o que dá o idioma habitual de percorrer até ao fim:

```algo
procedimento imprimir(lista:No)
    n:No = lista
    enquanto n <> nulo fazer
        escrever(n.valor)
        n = n.seguinte
```

### Constrói-se de uma vez, não por "apontadores" a mutar depois

Como todo o valor `estrutura` copia por valor (7.3) — **incluindo ao
atribuir a um campo** — não há forma de duas variáveis partilharem o
"mesmo" nó, ao contrário de listas ligadas em Java/C/Python (onde um
campo guarda uma referência real, e mutar o nó original propaga a
quem já apontava para ele) — a menos que o campo seja `ref` (ver
abaixo):

```algo
inicio
    b:No = {valor: 2, seguinte: nulo}
    a:No = {valor: 1, seguinte: b}    // copia 'b' para dentro de a.seguinte
    b.valor = 99                      // só muda a variável 'b'
    escrever(a.seguinte.valor)        // 2 -- NÃO 99: a.seguinte já era outra cópia
```

### Campo `ref`: ligar sem copiar

Um campo pode ser marcado `ref` — tal como um parâmetro `ref` (7.4),
guarda um alias para OUTRA instância já existente em vez de copiar o
valor para dentro de si:

```algo
estrutura No
    valor:inteiro
    seguinte:ref No
```

Com isto, já é possível ligar um nó já existente e mutá-lo depois, ao
contrário do exemplo anterior:

```algo
inicio
    b:No
    b.valor = 2

    a:No
    a.valor = 1
    a.seguinte = b               // agora ALIAS, não cópia

    b.valor = 99
    escrever(a.seguinte.valor)   // 99 -- reflete a mutação de 'b'
```

`ref` só é permitido num campo escalar (sem `[]`) cujo tipo seja outra
`estrutura` — não num campo de tipo primitivo, nem num campo-vetor.
Uma cópia por valor da estrutura inteira (`c:No = a`, passar por
valor, `retornar`) continua a preservar esse aliasing — só o valor do
próprio campo `ref` nunca é copiado.

A forma correta de construir uma lista/árvore com campos SIMPLES (sem
`ref`) em ALGO é **de uma vez, de baixo para cima** (o último nó
primeiro, ou recursivamente) — nunca ligar um nó já existente e
mutá-lo depois à espera que isso se reflita por onde já passou:

```algo
algoritmo "ListaLigada"

estrutura No
    valor:inteiro
    seguinte:No

funcao construir(v:inteiro[], i:inteiro, tamanho:inteiro):No
    se i == tamanho entao
        retornar nulo
    retornar {valor: v[i], seguinte: construir(v, i + 1, tamanho)}

procedimento imprimir(lista:No)
    n:No = lista
    enquanto n <> nulo fazer
        escrever(n.valor)
        n = n.seguinte

inicio
    v:inteiro[3] = {10, 20, 30}
    lista:No = construir(v, 0, 3)
    imprimir(lista)
```

Para ligar nós dinamicamente (inserir/remover num nó já ligado,
percorrer e reatribuir livremente quem aponta para quem), um campo
`ref` já resolve a maior parte dos casos. Para cenários que precisem
de enumerar/gerir muitos nós por posição, o padrão alternativo
continua a ser representá-los num **vetor** de nós, em que `seguinte`
é um **índice** (`inteiro`) para outra posição do vetor, não outra
`estrutura` — um vetor pode ser mutado por `ref` livremente, ao
contrário de um campo `estrutura` sem `ref`.

## 7.6 Vetor de estruturas, estrutura com campo vetor

```algo
inicio
    pontos:Ponto[2] = {{x: 1, y: 1}, {x: 2, y: 2}}
    escrever(pontos[0].x, ", ", pontos[1].y)
```

```algo
estrutura Poligono
    lados:inteiro[3]

inicio
    p:Poligono = {lados: {3, 4, 5}}
    escrever(p.lados[0], " ", p.lados[1], " ", p.lados[2])
```

## Exemplo completo

```algo
algoritmo "CatalogoDeLivros"

estrutura Livro
    titulo:cadeia
    ano:inteiro
    lido:booleano

inicio
    livros:Livro[3]
    i:inteiro
    para i de 0 ate 2 fazer
        escrever("Título do livro ", i + 1, ": ")
        ler(livros[i].titulo)
        escrever("Ano: ")
        ler(livros[i].ano)
        livros[i].lido = falso

    livros[1].lido = verdadeiro

    para i de 0 ate 2 fazer
        estado:cadeia = "por ler"
        se livros[i].lido entao
            estado = "lido"
        escrever(livros[i].titulo, " (", livros[i].ano, ") -- ", estado)
```
