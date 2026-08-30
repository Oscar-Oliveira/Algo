# 01 — Variáveis e tipos

Assunto: os 5 tipos primitivos (`inteiro`, `decimal`, `booleano`, `cadeia`,
`caracter`), declaração com e sem valor inicial, `constante`, `ler`/`escrever`.

Nesta fase da linguagem ainda não há `se`, ciclos, funções nem bibliotecas —
os três exemplos são deliberadamente programas de sequência única (sem
ramificação), tal como qualquer estudante conseguiria escrever depois de só
ver este assunto.

## `ficha_inscricao.algo`

Regista a inscrição de um participante num workshop: nome, inicial para o
crachá, idade e se é sócio do clube. Calcula o ano de nascimento aproximado
a partir da idade e de uma constante `ANO_ATUAL`, e monta um crachá e um
resumo por concatenação de texto (`caracter` + `cadeia` + `cadeia`).

Demonstra: os 5 tipos primitivos, `constante` global, `ler` de cada tipo,
concatenação de texto com `+`, aritmética simples sobre `inteiro`.

## `fatura_compra.algo`

Recibo de uma compra de um único artigo: preço unitário, quantidade, e se o
cliente tem cartão de fidelização. Calcula subtotal, IVA e total.

Demonstra: `constante` decimal (taxa de IVA) e `constante` `caracter`
(símbolo de moeda), promoção automática `inteiro` → `decimal` numa
multiplicação (`precoUnitario * quantidade`), e o facto de `+` **não**
converter números para texto — a linha do artigo tem de ser escrita como
vários argumentos em `escrever(quantidade, " x ", nomeArtigo)`, não como
uma única `cadeia` concatenada, porque `inteiro + cadeia` é erro de
compilação.

## `conversor_unidades.algo`

Converte uma temperatura (Celsius → Fahrenheit) e uma distância
(quilómetros → milhas, multiplicada por um número de viagens).

Demonstra: várias `constante` decimais usadas em fórmulas, vários `ler`
seguidos de tipos diferentes, e guardar resultados intermédios em
variáveis com nome próprio em vez de repetir a expressão dentro de
`escrever`.
