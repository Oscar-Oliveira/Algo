# 4. Ciclos

## 4.1 `para`

```algo
inicio
    i:inteiro
    para i de 1 ate 5 fazer
        escrever(i)
```

Saída: `1 2 3 4 5` (`ate` é **inclusivo** — inclui o `5`, ao contrário de
`range`/`for` em Python, onde o limite superior fica de fora).

> **A variável de controlo tem de ser declarada ANTES do ciclo.**
> `para i de 1 ate 5 fazer` sem `i:inteiro` numa linha anterior é erro
> de compilação — ao contrário de pseudocódigo tradicional (ou de
> Python/JavaScript), onde `para`/`for` costuma declarar a variável
> implicitamente. Depois do ciclo terminar, `i` continua a existir, com
> o último valor que teve dentro do ciclo (`5` no exemplo acima, não
> `6`).

### `passo`

```algo
inicio
    i:inteiro
    para i de 10 ate 2 passo -2 fazer
        escrever(i)
```

Saída: `10 8 6 4 2`. Sem `passo`, o valor por omissão é `1` (sempre
ascendente). Com `passo` negativo, `de`/`ate` continuam ambos
inclusivos, agora a descer. Um ciclo cujo sentido de `de`/`ate` não
combina com o sinal do `passo` (ex.: `de 1 ate 10 passo -1`) não corre
nenhuma vez — não é erro, só um ciclo vazio, tal como um `range()` vazio
em Python. `passo` igual a `0` é sempre erro (o ciclo nunca avançaria) —
detetado em compilação quando é um literal, e em runtime (com mensagem
amigável) quando só se conhece o valor ao correr o programa.

`de`, `ate` e `passo` só aceitam `inteiro` — não há `para` sobre
`decimal`.

## 4.2 `enquanto`

```algo
inicio
    n:inteiro = 10
    enquanto n > 0 fazer
        escrever(n)
        n = n - 1
```

Testa a condição **antes** de cada iteração (incluindo a primeira) — se
começar falsa, o corpo nunca corre nenhuma vez.

## 4.3 `fazer ... enquanto`

```algo
inicio
    opcao:inteiro
    fazer
        escrever("1) Somar  2) Sair -- escolhe: ")
        ler(opcao)
    enquanto opcao <> 1 e opcao <> 2

    escrever("Escolheste ", opcao)
```

Testa a condição **depois** de cada iteração — o corpo corre sempre
**pelo menos uma vez**, mesmo que a condição já comece falsa. É o
padrão certo para "pede um valor até ser válido" (como acima), onde não
há nada para testar antes da primeira leitura.

## 4.4 `sair` e `continuar`

`sair` termina o ciclo mais interior imediatamente (equivalente a
`break`); `continuar` salta logo para a próxima iteração desse mesmo
ciclo, sem executar o resto do corpo (equivalente a `continue`). Os
dois só são válidos dentro de `para`/`enquanto`/`fazer...enquanto` — usados
fora de um ciclo são erro de compilação — e afetam sempre só o ciclo
**mais interior** que os contém.

```algo
inicio
    i:inteiro
    para i de 1 ate 20 fazer
        se i mod 2 <> 0 entao
            continuar          // ímpares: salta já para o próximo i
        se i > 10 entao
            sair               // para de todo o ciclo aqui
        escrever(i)
```

Saída: `2 4 6 8 10` — os ímpares nunca chegam ao `escrever` (`continuar`),
e o ciclo para de vez assim que `i` passa de `10` (`sair`).

`sair`/`continuar` dentro de um `escolher` (que não é, por si, um
ciclo) continuam a afetar o ciclo em torno do `escolher`, não têm
nenhum efeito especial sobre o `escolher` em si (não existe "sair de um
`caso`" — não faria sentido, já que não há fallthrough a evitar):

```algo
inicio
    i:inteiro
    para i de 1 ate 5 fazer
        escolher i
            caso 3
                sair            // sai do 'para', não só do 'caso'
            contrario
                escrever(i)
```

Saída: `1 2` — ao chegar a `i == 3`, `sair` termina o `para` (o
`escolher` não tem nenhuma noção própria de "sair").

## Exemplo completo

```algo
algoritmo "TabuadaComParagem"

inicio
    base:inteiro
    escrever("Tabuada de: ")
    ler(base)

    i:inteiro
    para i de 1 ate 10 fazer
        resultado:inteiro = base * i
        se resultado > 50 entao
            escrever("(parado -- resultado passou de 50)")
            sair
        escrever(base, " x ", i, " = ", resultado)
```
