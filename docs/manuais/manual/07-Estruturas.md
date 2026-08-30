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

### Declaração sem literal fica `nulo`; o literal `{...}` pode omitir campos

Uma declaração **sem** `={...}` nenhum não constrói nenhuma instância —
fica `nulo` (por omissão de qualquer `estrutura` sem valor inicial):

```algo
inicio
    p:Ponto              // p fica 'nulo', NÃO um Ponto com x=0, y=0
    // escrever(p.x)      // ERRO em runtime: tentaste aceder ao campo 'x' de um valor nulo
```

Um literal `{...}` pode omitir campos — cada campo em falta recebe o
valor por omissão do seu próprio tipo (o mesmo que uma declaração sem
literal desse tipo daria: `0`/`0.0`/`falso`/`""`/`' '` para um tipo
primitivo, `nulo` para um campo `estrutura`, um vetor já preenchido
para um campo vetor):

```algo
inicio
    p:Ponto = {x: 3}
    escrever(p.x, ", ", p.y)      // 3, 0 -- 'y' não foi dado, fica 0
```

Um literal **vazio** `{}` constrói explicitamente uma instância com
todos os campos por omissão — é a forma de obter o que uma declaração
sem literal costumava dar antigamente:

```algo
inicio
    p:Ponto = {}
    escrever(p.x, ", ", p.y)      // 0, 0
```

## 7.2 Igualdade compara por referência, não por conteúdo

`==`/`<>` entre dois valores `estrutura` comparam se são **a mesma
instância**, não se têm os mesmos campos — mesmo com conteúdo
idêntico, duas instâncias construídas separadamente são diferentes:

```algo
inicio
    a:Ponto = {x: 1, y: 2}
    b:Ponto = {x: 1, y: 2}
    escrever(a == b)              // falso -- mesmo conteúdo, instâncias diferentes
    c:Ponto = a
    escrever(a == c)              // verdadeiro -- 'c' é a MESMA instância que 'a'
```

`x == nulo`/`x <> nulo` continuam a funcionar normalmente para testar
se uma variável `estrutura` ainda não foi construída (é exatamente o
que uma comparação de identidade contra "nada" deve ser). Para
comparar o **conteúdo** de duas instâncias, escreve a tua própria
função de comparação, campo a campo:

```algo
funcao mesmoPonto(a:Ponto, b:Ponto):booleano
    retornar a.x == b.x e a.y == b.y
```

## 7.3 `estrutura` é um tipo por referência

Tal como `vetor` (capítulo 5), `estrutura` é um tipo **por
referência**: `=` e uma declaração a partir de outra variável não
copiam — as duas variáveis passam a apontar para a **mesma** instância:

```algo
inicio
    a:Ponto = {x: 1, y: 2}
    b:Ponto = a
    b.x = 99
    escrever(a.x, " ", b.x)       // 99 99 -- é a MESMA instância
```

Isto vale em **todo** o sítio onde um valor `estrutura` circula:
atribuição, declaração, `retornar`, passar como argumento por valor
(sem `ref`), e **popular um campo/elemento a partir de uma variável
existente** num literal — `no.seguinte = outroNo` guarda no campo uma
referência a `outroNo`, não uma cópia dele (mais em 7.5) — exatamente
os mesmos sítios onde um vetor também aliasa. Um parâmetro sem `ref`
já recebe essa mesma instância partilhada (mutar um campo dela é
visto pelo chamador); só uma **reatribuição completa** do parâmetro
(`p = {...}`, trocar por outra instância) precisa de `ref` para ser
vista pelo chamador — ver 7.4.

## 7.4 Passar por referência

Como visto em 7.3, mutar um campo não precisa de `ref` — um parâmetro
`estrutura` sem `ref` já aponta para a mesma instância do chamador:

```algo
procedimento deslocar(p:Ponto, dx:inteiro, dy:inteiro)
    p.x = p.x + dx
    p.y = p.y + dy

inicio
    p:Ponto = {x: 0, y: 0}
    deslocar(p, 5, 3)
    escrever(p.x, " ", p.y)       // 5 3 -- sem 'ref'!
```

`ref` só faz diferença quando o próprio parâmetro é **reatribuído** a
outra instância (`p = {...}`), não um dos seus campos:

```algo
procedimento reiniciar(ref p:Ponto)
    p = {x: 0, y: 0}          // troca a instância a que 'p' aponta

inicio
    p:Ponto = {x: 9, y: 9}
    reiniciar(p)
    escrever(p.x, " ", p.y)       // 0 0 -- só com 'ref'
```

Sem `ref`, essa reatribuição fica presa à função — o chamador continua
a ver a instância original:

```algo
procedimento reiniciarSemRef(p:Ponto)
    p = {x: 0, y: 0}          // só troca a cópia local de 'p'

inicio
    p:Ponto = {x: 9, y: 9}
    reiniciarSemRef(p)
    escrever(p.x, " ", p.y)       // 9 9 -- sem 'ref', não propaga
```

## 7.5 Estruturas recursivas (árvores, listas)

Um campo pode ter o tipo da própria estrutura (ou de outra que aponte
de volta para ela) — útil para árvores e listas ligadas:

```algo
estrutura No
    valor:inteiro
    seguinte:No
```

Um campo desse tipo pode ser omitido no literal — fica `nulo` por
omissão, tal como qualquer campo `estrutura` (7.1) — ou dado
explicitamente como `nulo` para deixar claro "sem próximo nó". Nunca
se tenta construir a estrutura a si própria infinitamente. `nulo` é o
único valor que se pode comparar com `==`/`<>` contra qualquer tipo
`estrutura` (7.2 é sobre comparar duas instâncias; contra `nulo` a
comparação continua por identidade, exatamente o que se quer), o que
dá o idioma habitual de percorrer até ao fim:

```algo
procedimento imprimir(lista:No)
    n:No = lista
    enquanto n <> nulo fazer
        escrever(n.valor)
        n = n.seguinte
```

### Construir de uma vez, recursivamente

Uma forma comum de construir uma lista é de baixo para cima (o último
nó primeiro), recursivamente:

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

### Ligar nós dinamicamente

Como um campo `estrutura` aliasa (7.3) em vez de copiar, também é
possível ligar/desligar nós **depois** de construídos — atribuir a
`no.seguinte` guarda uma referência ao nó dado, e mutar esse nó por
qualquer um dos dois nomes é visível no outro:

```algo
inicio
    b:No = {valor: 2, seguinte: nulo}
    a:No = {valor: 1, seguinte: b}
    imprimir(a)                        // 1 depois 2

    meio:No = {valor: 99, seguinte: b}
    a.seguinte = meio                  // insere 'meio' entre 'a' e 'b'
    imprimir(a)                        // 1, 99, 2

    b.valor = 0
    escrever(meio.seguinte.valor)      // 0 -- meio.seguinte é a MESMA instância que 'b'
```

## 7.6 Vetor de estruturas, estrutura com campo vetor

```algo
inicio
    pontos:Ponto[2] = {{x: 1, y: 1}, {x: 2, y: 2}}
    escrever(pontos[0].x, ", ", pontos[1].y)
```

Um vetor em si (capítulo 5) continua a preencher-se sozinho quando
declarado sem literal — mas, para um vetor de `estrutura`, cada
posição fica com o valor por omissão do **tipo do elemento**, que para
`estrutura` é `nulo` (7.1), não uma instância já construída:

```algo
inicio
    pontos:Ponto[2]           // {nulo, nulo} -- NÃO duas instâncias de Ponto
    pontos[0] = {x: 1, y: 1}  // constrói a instância antes de a usar
    escrever(pontos[0].x)
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
        livros[i] = {}      // vetor de 'estrutura' começa com posições 'nulo' (7.6); constrói cada uma
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
