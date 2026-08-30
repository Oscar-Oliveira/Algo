---
theme: "white"
customTheme: "estilo-aulas"
---

# Aula 3

## Operadores

Aritméticos, relacionais e lógicos

---

## Recapitulando

- **Aula 1:** algoritmo = sequência de passos; `escrever`/`ler`
- **Aula 2:** os 5 tipos primitivos, `constante`, valores por omissão
- Hoje: as ferramentas para **calcular** e **decidir** com esses valores

---

## Objetivos de hoje

- Calcular com os operadores aritméticos (`+` `-` `*` `/` `div` `mod` `^`)
- Comparar valores com os operadores relacionais
- Combinar condições com os operadores lógicos (`e` `ou` `nao`)
- Saber qual operador "liga" primeiro numa expressão

---

## Três famílias de operadores

| Família | Para quê | Devolve |
|---|---|---|
| **Aritméticos** | calcular | um número |
| **Relacionais** | comparar | `booleano` |
| **Lógicos** | combinar condições | `booleano` |

---

# Aritméticos

---

## `+` `-` `*` — como na escola

```algo
escrever(3 + 4)      // 7
escrever(10 - 6)      // 4
escrever(3 * 5)      // 15
```

Já usámos estes na Aula 2. Nada de novo aqui.

---

## `/` — divisão, sempre `decimal`

```algo
escrever(7 / 2)       // 3.5
escrever(4 / 2)       // 2.0  -- decimal, mesmo "a dar certo"
```

`/` nunca devolve `inteiro`, mesmo quando o resultado é um número redondo.

---

## `div` e `mod` — repartir por pessoas

Imagina 7 rebuçados para repartir por 2 amigos: cada um fica com 3, sobra 1.

```algo
escrever(7 div 2)     // 3   -- quantos cabem inteiros a cada um
escrever(7 mod 2)     // 1   -- o que sobra
```

`div`/`mod` só funcionam entre dois `inteiro`.

---

## `/` vs `div`/`mod` — em conjunto

```algo
algoritmo "Rebucados"

inicio
    total:inteiro = 17
    amigos:inteiro = 5

    escrever(total / amigos)       // 3.4   (/  -- decimal exato)
    escrever(total div amigos)     // 3     (div -- quantos inteiros cada um)
    escrever(total mod amigos)     // 2     (mod -- o que sobra)
```

---

## `^` — potência

```algo
escrever(2^10)         // 1024
escrever(3^2)           // 9
```

Usa-se para crescimento (juros, população) ou áreas/volumes (lado`^`2).

---

## `^` e o tipo do resultado

O resultado de `^` é normalmente `decimal` — só fica `inteiro` quando a base e o expoente estão escritos diretamente no código (não vêm de uma variável):

```algo
escrever(2^10)          // inteiro, porque "2" e "10" estão escritos ali

n:inteiro = 10
x:decimal = 2^n          // aqui já tem de ser decimal
```

Por agora, guarda o resultado de `^` numa variável `decimal` sempre que o expoente vier de uma variável.

---

## Regra da Aula 2, outra vez

`+` `-` `*` `/` exigem os dois lados **numéricos** (`+` também aceita os dois lados **texto**, para concatenar) — nunca uma mistura:

```algo
idade:inteiro = 20
// escrever("Idade: " + idade)     // ERRO
escrever("Idade: ", idade)          // certo
```

---

# Relacionais

---

## Comparar valores

```algo
==   igual
<>   diferente
<    menor
>    maior
<=   menor ou igual
>=   maior ou igual
```

Todos devolvem sempre um `booleano`: `verdadeiro` ou `falso`.

---

## Exemplo

```algo
idade:inteiro = 20
maiorDeIdade:booleano = idade >= 18

escrever(maiorDeIdade)         // verdadeiro
escrever(idade == 20)           // verdadeiro
escrever(idade <> 20)           // falso
```

---

## Comparar texto

`<` `>` `<=` `>=` também funcionam com `cadeia`/`caracter`, mas comparam pela ordem dos símbolos no computador (Unicode) — **não** é a ordem alfabética que aprendeste na escola:

```algo
escrever("Z" < "a")     // verdadeiro! (maiúsculas vêm antes)
escrever("ana" < "bruno")   // verdadeiro (esta já bate certo)
```

---

## Armadilha: não podes encadear comparações

```algo
a:inteiro = 1
b:inteiro = 5
c:inteiro = 10

// a < b < c        // ERRO de compilação!
```

O que parece "a é menor que b, que é menor que c" **não existe** em ALGO. Escreve as duas comparações por extenso, ligadas por `e` (já a seguir):

```algo
a < b e b < c        // certo
```

---

# Lógicos

---

## `e` `ou` `nao` — combinar condições

Pensa em regras do dia a dia:

- "Preciso de chapéu-de-chuva **se** está a chover **e** vou a pé"
- "Posso entrar **se** tenho 18 anos **ou** tenho um convite"
- "Não está a chover" = **nao** está a chover

---

## `e` — os dois têm de ser verdade

```algo
temGuardaChuva:booleano = falso
estaAChover:booleano = verdadeiro

precisaDeGuardaChuva:booleano = estaAChover e nao temGuardaChuva
escrever(precisaDeGuardaChuva)     // verdadeiro
```

---

## `ou` — pelo menos um tem de ser verdade

```algo
idade:inteiro = 15
temConvite:booleano = verdadeiro

podeEntrar:booleano = idade >= 18 ou temConvite
escrever(podeEntrar)               // verdadeiro (tem convite)
```

---

## `nao` — inverte

```algo
chove:booleano = verdadeiro
escrever(nao chove)         // falso
```

`e`, `ou` e `nao` só funcionam entre valores `booleano` — nunca entre números diretamente.

---

## Juntar tudo

```algo
media:decimal = 12.5
notaMinima1:decimal = 10.0
notaMinima2:decimal = 10.0

aprovado:booleano = media >= 9.5 e notaMinima1 >= 5.0 e notaMinima2 >= 5.0
escrever(aprovado)          // verdadeiro
```

---

# Qual liga primeiro?

---

## Precedência dos operadores

Do que "liga" primeiro (mais apertado) para o que liga por último (mais solto):

| Ordem | Operadores |
|---|---|
| 1º | `^` |
| 2º | `-` (negativo) |
| 3º | `*` `/` `div` `mod` |
| 4º | `+` `-` |
| 5º | `==` `<>` `<` `>` `<=` `>=` |
| 6º | `nao` |
| 7º | `e` |
| 8º (último) | `ou` |

---

## Exemplos

```algo
escrever(-2^2)       // -4   -- '^' primeiro: -(2^2)
escrever(-2 * 3)      // -6   -- '-' antes de '*'
escrever(2 + 3 * 4)    // 14   -- '*' antes de '+'
```

Na dúvida: usa **parênteses**. Nunca há penalização por ter parênteses a mais.

---

## Exemplo completo

```algo
algoritmo "MediaEClassificacao"

inicio
    n1:decimal
    n2:decimal
    escrever("Nota 1: ")
    ler(n1)
    escrever("Nota 2: ")
    ler(n2)

    media:decimal = (n1 + n2) / 2
    aprovado:booleano = media >= 9.5 e n1 >= 5.0 e n2 >= 5.0

    escrever("Média: ", media)
    escrever("Aprovado: ", aprovado)
```

---

## Resumo

- **Aritméticos:** `+` `-` `*` `/` (sempre decimal) `div`/`mod` (só inteiro) `^`
- **Relacionais:** `==` `<>` `<` `>` `<=` `>=` — devolvem sempre `booleano`; não se encadeiam
- **Lógicos:** `e` `ou` `nao` — só entre `booleano`
- Na dúvida sobre a ordem, usa parênteses

---

## Próxima aula

Vamos usar os operadores relacionais e lógicos para o programa **decidir** o que fazer: `se`, `senao` e `senao se`.

---

## Agora é a tua vez!

Abre a ficha de trabalho da Aula 3 e resolve os exercícios.
