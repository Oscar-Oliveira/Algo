---
theme: "white"
customTheme: "estilo-aulas"
---

# Aula 9

## Estruturas

Agrupar vários valores relacionados numa única variável

---

## Recapitulando

- **Aula 7:** vetores — muitos valores do **mesmo** tipo
- **Aula 8:** funções e procedimentos — lógica reutilizável
- Hoje: agrupar valores de tipos **diferentes**, mas relacionados entre si

---

## Objetivos de hoje

- Definir e usar uma `estrutura`
- Perceber que `estrutura` é um tipo por referência, tal como vetor (Aula 7)
- Passar uma `estrutura` por referência
- Vetor de estruturas, e estrutura com campo vetor
- Estruturas recursivas (listas ligadas)

---

## O problema

```algo
pontoX:inteiro = 3
pontoY:inteiro = 4
```

Duas variáveis separadas, mas que só fazem sentido **juntas** (representam um ponto). Nada impede de as confundir, ou esquecer uma delas ao passares os dados a uma função.

---

## A solução: uma `estrutura`

Pensa numa **ficha**: um "Ponto" tem sempre um `x` e um `y`; uma "Pessoa" tem sempre um nome e uma idade. Uma `estrutura` agrupa campos relacionados debaixo de um único nome.

---

# Definir e usar

---

## Sintaxe

```algo
estrutura Ponto
    x:inteiro
    y:inteiro

inicio
    p:Ponto = {x: 3, y: 4}
    escrever(p.x, ", ", p.y)      // 3, 4
```

- `estrutura Nome`, um campo `nome:tipo` por linha, declarada fora de `inicio`
- Constrói-se com `{campo: valor, ...}` — a ordem dos campos no literal não importa
- Acede-se e atribui-se com `.`: `p.x`, `p.x = 10`

---

## Em diagrama

![Uma estrutura Ponto mostrada como um registo com dois campos, x igual a 3 e y igual a 4](diagramas/09-estruturas/estrutura-registo.svg)

---

## Declaração sem literal fica `nulo`; o literal `{...}` pode omitir campos

```algo
p:Ponto              // p fica 'nulo', NÃO um Ponto com x=0, y=0
// escrever(p.x)      // ERRO em runtime: campo de um valor nulo

q:Ponto = {x: 3}
escrever(q.x, ", ", q.y)      // 3, 0 -- 'y' não foi dado, fica 0

r:Ponto = {}
escrever(r.x, ", ", r.y)      // 0, 0 -- literal VAZIO constrói tudo por omissão
```

Só uma declaração **sem** `={...}` nenhum é que fica `nulo`. O literal
`{...}`, mesmo vazio, constrói sempre uma instância — os campos que
faltarem ficam com o valor por omissão do seu tipo (Aula 2).

---

## Igualdade compara por referência, não por conteúdo

```algo
a:Ponto = {x: 1, y: 2}
b:Ponto = {x: 1, y: 2}
escrever(a == b)              // falso! mesmo conteúdo, instâncias diferentes
c:Ponto = a
escrever(a == c)              // verdadeiro -- 'c' é a MESMA instância que 'a'
```

`==`/`<>` entre duas `estrutura` comparam se são **a mesma instância**, não os campos. Para comparar conteúdo, escreve a tua própria função:

```algo
funcao mesmoPonto(a:Ponto, b:Ponto):booleano
    retornar a.x == b.x e a.y == b.y
```

---

# `estrutura` é um tipo por referência

---

## Tal como vetor!

Lembra-te da Aula 7: `=` não copia um vetor. Uma `estrutura` faz exatamente o mesmo:

```algo
a:Ponto = {x: 1, y: 2}
b:Ponto = a
b.x = 99
escrever(a.x, " ", b.x)       // 99 99 -- é a MESMA instância
```

Isto vale em **todo** o sítio onde um valor `estrutura` circula: atribuição, declaração, `retornar`, passar como argumento sem `ref`, e **atribuir a um campo** — exatamente os mesmos sítios onde um vetor aliasa (Aulas 7 e 8). `estrutura` e vetor comportam-se da mesma forma em todo o lado.

---

# Passar por referência

---

## `ref` numa `estrutura`

Já viste acima que mutar um campo de uma `estrutura` passada como argumento **já** afeta a variável do chamador, com ou sem `ref` — é a mesma aliasing de sempre:

```algo
procedimento deslocar(p:Ponto, dx:inteiro, dy:inteiro)
    p.x = p.x + dx
    p.y = p.y + dy

inicio
    p:Ponto = {x: 0, y: 0}
    deslocar(p, 5, 3)
    escrever(p.x, " ", p.y)       // 5 3 -- sem 'ref'!
```

`ref` só faz diferença se o procedimento **reatribuir o parâmetro a outra instância** (não um campo, o parâmetro inteiro):

```algo
procedimento reiniciar(ref p:Ponto)
    p = {x: 0, y: 0}          // troca a instância a que 'p' aponta

inicio
    p:Ponto = {x: 9, y: 9}
    reiniciar(p)
    escrever(p.x, " ", p.y)       // 0 0 -- só com 'ref'
```

Sem `ref`, essa reatribuição fica presa à função:

```algo
procedimento reiniciarSemRef(p:Ponto)
    p = {x: 0, y: 0}          // só troca a cópia local do parâmetro

inicio
    p:Ponto = {x: 9, y: 9}
    reiniciarSemRef(p)
    escrever(p.x, " ", p.y)       // 9 9 -- sem 'ref', não propaga
```

Tal como um parâmetro escalar (Aula 8), `ref` faz a função mutar diretamente a variável do chamador — a diferença é que numa `estrutura` isso só é observável quando reatribuis o parâmetro inteiro, porque mutar um campo já era visível de qualquer forma.

---

# Vetores + Estruturas

---

## Vetor de estruturas

```algo
pontos:Ponto[2] = {{x: 1, y: 1}, {x: 2, y: 2}}
escrever(pontos[0].x, ", ", pontos[1].y)     // 1, 2
```

Cada posição do vetor é uma `Ponto` completa — mas só porque o literal dá as duas. Sem literal (`pontos:Ponto[2]`, sozinho), cada posição fica `nulo`, não uma instância pronta a usar — constrói-a primeiro (`pontos[i] = {}` ou um literal completo).

---

## Estrutura com campo vetor

```algo
estrutura Poligono
    lados:inteiro[3]

inicio
    p:Poligono = {lados: {3, 4, 5}}
    escrever(p.lados[0], " ", p.lados[1], " ", p.lados[2])
```

Um campo também pode ser um vetor.

---

# Estruturas recursivas

---

## Um campo pode ser do mesmo tipo da estrutura

```algo
estrutura No
    valor:inteiro
    seguinte:No
```

Útil para representar uma sequência: cada nó aponta para "o próximo". Um campo deste tipo pode ser omitido no literal (fica `nulo` por omissão) ou dado explicitamente como `nulo` para marcar "sem próximo nó" — nunca se tenta construir a estrutura a si própria infinitamente.

---

## Percorrer até ao fim

```algo
procedimento imprimir(lista:No)
    n:No = lista
    enquanto n <> nulo fazer
        escrever(n.valor)
        n = n.seguinte
```

`nulo` é o único valor que se pode comparar com `==`/`<>` contra qualquer `estrutura` — dá o idioma habitual de "percorrer até acabar".

---

## Ligar nós dinamicamente

Como um campo `estrutura` aliasa em vez de copiar, dá para ligar/desligar nós **depois** de construídos — atribuir a `no.seguinte` guarda uma referência ao nó dado:

```algo
b:No = {valor: 2, seguinte: nulo}
a:No = {valor: 1, seguinte: b}
imprimir(a)                        // 1 depois 2

meio:No = {valor: 99, seguinte: b}
a.seguinte = meio                  // insere 'meio' entre 'a' e 'b'
imprimir(a)                        // 1, 99, 2

b.valor = 0
escrever(meio.seguinte.valor)      // 0 -- meio.seguinte é a MESMA instância que 'b'
```

---

## Construir de uma vez, recursivamente

Também é comum construir uma lista de baixo para cima, recursivamente:

```algo
funcao construir(v:inteiro[], i:inteiro, tamanho:inteiro):No
    se i == tamanho entao
        retornar nulo
    retornar {valor: v[i], seguinte: construir(v, i + 1, tamanho)}
```

---

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
        livros[i] = {}      // vetor de 'estrutura' começa com posições 'nulo'; constrói cada uma
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

---

## Resumo

- `estrutura Nome` com campos `nome:tipo`; literal `{campo: valor, ...}`; acede-se com `.`
- Declaração sem literal fica `nulo`; literal `{...}` pode omitir campos (ficam por omissão); `{}` constrói tudo por omissão
- `==`/`<>` comparam por referência (mesma instância), não campo a campo — escreve a tua própria função para comparar conteúdo
- `estrutura` é um tipo por referência em toda a parte, incluindo campos e `=` — tal como vetor (Aula 7)
- `ref` num parâmetro faz uma reatribuição completa propagar de volta ao chamador
- Vetor de estruturas (posições ficam `nulo`, não instâncias), estrutura com campo vetor, e estruturas recursivas — nós podem ligar-se dinamicamente com campos normais

---

## Próxima aula

Vamos ver **bibliotecas**: as ferramentas prontas a usar que já vêm com a Linguagem Algorítmica (`matematica`, `cadeia`, `conversao`, ...), através de `importar`.

---

## Agora é a tua vez!

Abre a ficha de trabalho da Aula 9 e resolve os exercícios.
