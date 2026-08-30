# Aulas de Algoritmia com ALGO

Curso de 14 aulas para quem nunca programou.

## Estrutura

```
aulas/
├── estilo-aulas.css          tema partilhado por todos os slides
├── 01-nome-da-aula.md        slides da aula 1 (reveal.js)
├── 02-nome-da-aula.md        slides da aula 2
├── ...
├── diagramas/
│   └── 04-nome-da-aula/      diagramas .dot + .svg usados nos slides da aula 4
└── fichas/
    ├── 01-nome-da-aula.md            ficha de trabalho da aula 1
    ├── 02-nome-da-aula.md
    ├── ...
    └── solucoes/
        ├── 01-nome-da-aula/          soluções em ALGO da aula 1
        │   ├── exercicio-1-....algo
        │   └── ...
        └── 02-nome-da-aula/
```

A partir da Aula 4, os conteúdos ficam mais abstratos (decisões, ciclos, ...) e os slides incluem fluxogramas/diagramas feitos em [Graphviz](https://graphviz.org/) para ajudar a visualizar. Cada diagrama tem um ficheiro `.dot` (fonte, editável) e o `.svg` gerado a partir dele (o que é efetivamente mostrado no slide via imagem markdown). Para regenerar um `.svg` depois de editar o `.dot`:

```bash
dot -Tsvg diagramas/04-nome-da-aula/nome.dot -o diagramas/04-nome-da-aula/nome.svg
```

Os slides ficam todos na raiz de `aulas/`, ao lado de `estilo-aulas.css`, porque a extensão [vscode-reveal](https://marketplace.visualstudio.com/items?itemName=evilz.vscode-reveal) só resolve `customTheme` a partir da própria pasta do `.md` (não segue `../`) — estarem no mesmo nível é o que permite a todos partilharem um único ficheiro de tema. Cada slide deck referencia-o no front matter, sem a extensão `.css`:

```yaml
---
theme: "white"
customTheme: "estilo-aulas"
---
```

As aulas são construídas uma de cada vez; cada uma só é dada como fechada depois de confirmada.

## Plano das 14 aulas

| # | Aula | Estado |
|---|------|--------|
| 1 | [O que é um algoritmo?](01-o-que-e-um-algoritmo.md) — conceito, primeiro programa, `escrever`/`ler` | ✅ pronta para revisão |
| 2 | [Variáveis e tipos](02-variaveis-e-tipos.md) — os 5 tipos primitivos, `constante`, valores por omissão | ✅ pronta para revisão |
| 3 | [Operadores](03-operadores.md) — aritméticos, relacionais, lógicos | ✅ pronta para revisão |
| 4 | [Decisões](04-decisoes.md) — `se` / `senao` / `senao se` / `escolher` | ✅ pronta para revisão |
| 5 | [Ciclos](05-ciclos.md) — `para` (contado) e `enquanto`/`fazer ... enquanto` (condicionado), com diagramas de memória; inclui bloco dedicado a **traçagem** (o que é, como se faz, exemplos sem ciclos) | ✅ pronta para revisão |
| 6 | [Revisão](06-revisao.md) — consolidação a meio do curso (aulas 1 a 5) | ✅ pronta para revisão |
| 7 | [Vetores e matrizes](07-vetores-e-matrizes.md) — listas de valores e tabelas | ✅ pronta para revisão |
| 8 | [Funções e procedimentos](08-funcoes-e-procedimentos.md) | ✅ pronta para revisão |
| 9 | [Estruturas](09-estruturas.md) — agrupar dados relacionados | ✅ pronta para revisão |
| 10 | [Bibliotecas, `incluir` e tratamento de erros](10-bibliotecas-incluir-erros.md) — `importar`, ficheiros, `afirmar` | ✅ pronta para revisão |
| 11 | [Revisão final](11-revisao-final.md) — consolidação de todo o curso (aulas 1 a 10) | ✅ pronta para revisão |
| 12 | [Aula de exercícios I](12-exercicios-quotidiano-financas.md) — tema: vida quotidiana e finanças (fácil → médio) | ✅ pronta para revisão |
| 13 | [Aula de exercícios II](13-exercicios-jogos-simulacoes.md) — tema: jogos e simulações (médio → avançado) | ✅ pronta para revisão |
| 14 | [Aula de exercícios III](14-exercicios-organizacao-dados.md) — tema: organização de dados, mini-projeto final (avançado) | ✅ pronta para revisão |

Cada ficha de trabalho das aulas 1 a 5, 7 a 10 segue o mesmo formato: 3 exercícios da matéria nova, 2 de revisão da(s) aula(s) anterior(es), e 3 a 5 de consolidação de tudo o que já foi dado (a partir da Aula 2 — a Aula 1 não tem matéria anterior para rever).

As aulas 6 e 11 são inteiramente de revisão: juntam exercícios que combinam, respetivamente, as aulas 1 a 5 e as aulas 1 a 10, sem matéria nova.

As aulas 12 a 14 não introduzem sintaxe nova — são só de prática, cada uma com um tema de aplicação diferente e um nível de dificuldade crescente em relação à anterior, usando livremente tudo o que foi dado até à aula 11.
