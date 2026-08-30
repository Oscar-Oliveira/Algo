---
theme: "white"
customTheme: "estilo-aulas"
---

# Aula 12

## Exercícios I

Tema: Vida Quotidiana e Finanças

---

## Sem matéria nova

A partir de agora não há mais sintaxe para aprender — já viste tudo o que precisas (Aulas 1 a 11). Estas 3 aulas finais são só para **praticar**, com temas diferentes e dificuldade crescente.

---

## O tema de hoje

Contas do dia a dia: trocos, descontos, contas de restaurante, orçamentos, poupanças, juros. É onde a maior parte das pessoas usa cálculos deste tipo sem se aperceber — e é um ótimo campo de treino porque os números são fáceis de verificar à mão.

---

## Como abordar qualquer exercício

1. **Que dados preciso de ler?** E de que tipo (`inteiro`, `decimal`, ...)?
2. **O que tenho de calcular?** Escreve a fórmula em português antes de a traduzir para Linguagem Algorítmica
3. **Preciso de decidir alguma coisa?** (`se`/`senao`) — ou de repetir? (`para`/`enquanto`)
4. **O que escrevo no fim?** — testa sempre com valores que sabes de cabeça

---

## Exemplo resolvido: preço com IVA

*(este exemplo não está na tua ficha — é só para veres o raciocínio)*

**1. Dados:** o preço sem IVA (`decimal`)
**2. Cálculo:** `precoComIVA = precoSemIVA + precoSemIVA * 23%`
**3. Decisão/repetição:** nenhuma — é só uma conta direta
**4. Saída:** o preço final

---

## Em código

```algo
algoritmo "PrecoComIVA"

constante TAXA_IVA:decimal = 23.0

inicio
    precoSemIVA:decimal
    escrever("Preço sem IVA: ")
    ler(precoSemIVA)

    precoComIVA:decimal = precoSemIVA + precoSemIVA * TAXA_IVA / 100.0
    escrever("Preço com IVA: ", precoComIVA)
```

---

## Exemplo resolvido: fatura de eletricidade por escalões

Regra: os primeiros 100 kWh custam €0.15 cada; o que passar disso custa €0.20 cada. Isto **precisa** de uma decisão — o preço muda consoante o consumo.

```algo
algoritmo "FaturaEletricidade"

inicio
    consumo:decimal
    escrever("Consumo em kWh: ")
    ler(consumo)

    total:decimal
    se consumo <= 100.0 entao
        total = consumo * 0.15
    senao
        total = 100.0 * 0.15 + (consumo - 100.0) * 0.20

    escrever("Total a pagar: ", total)
```

---

## Repara

- `total` foi declarada **antes** do `se`, sem valor inicial — só assim continua a existir depois do bloco (Aula 4)
- A fórmula do `senao` só cobra €0.20 à parte que passa dos 100 kWh, não ao consumo todo

---

## A tua ficha de hoje

8 exercícios, do mais simples (uma conta direta) ao mais elaborado (comparar duas opções e decidir qual é melhor). Usa livremente tudo o que já sabes: tipos, ciclos, vetores, funções, estruturas — o que fizer sentido para cada problema.

---

## Agora é a tua vez!

Abre a ficha de trabalho da Aula 12 e resolve os 8 exercícios, por ordem.
