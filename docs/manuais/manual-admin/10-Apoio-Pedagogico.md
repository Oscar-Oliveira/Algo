# 10. Apoio Pedagógico

Área: **Trabalho → Apoio Pedagógico**. Acessível a admin global **e** a
admin de grupo (ver capítulo 1, secção 1.3) — um admin de grupo só
consegue escolher estudantes/grupos que gere.

Analisa o histórico de **um estudante** ou de **um grupo inteiro**
(sessões do Alguem e/ou execuções de código) e sugere apoio pedagógico —
**visível só para ti**, o(s) estudante(s) nunca vê(em) este texto. Usa o
LLM atribuído ao papel "Apoio Pedagógico" (capítulo 5) — nunca uma
escolha do estudante, e sem alternativa pessoal.

## 10.1 Fluxo em dois passos, sempre com revisão humana

Ao contrário de outras análises automáticas do painel, esta nunca
entrega o resultado final de uma vez:

1. **Gerar resumo**: monta o histórico (filtrado por data e por tipo —
   sessões do Alguem, execuções de código, ou ambos) como um texto
   compacto de factos, sem chamar nenhum LLM. Antes de gerares o resumo,
   um contador mostra quantos itens de histórico existem para os
   filtros escolhidos.
2. **Revês e editas** o resumo no próprio painel — podes corrigir,
   apagar ou acrescentar algo antes de continuar.
3. **Confirmar e analisar**: só agora o texto (tal como ficou depois da
   tua revisão) é enviado ao LLM configurado, e a sugestão de apoio
   pedagógico é devolvida.

Esta pausa intencional existe para nunca enviares histórico de
estudantes a um LLM externo sem oportunidade de revisão humana antes.

## 10.2 Sub-aba Individualizado

Escolhe um estudante (só dos que estão no teu âmbito), intervalo de
datas, e que tipos de histórico incluir. Segue o fluxo de 10.1.

## 10.3 Sub-aba Grupo

Mesmo fluxo, mas para uma turma inteira em vez de um estudante — útil
para uma visão geral de como uma turma está a lidar com uma matéria.

## 10.4 Sub-aba Definições

Só visível para um **admin global** (ao contrário das duas sub-abas
anteriores). Contém o prompt que instrui o LLM de Apoio Pedagógico — o
mesmo prompt serve tanto o modo Individualizado como o modo Grupo. Tem
o mesmo botão de "Repor por omissão" que os outros prompts editáveis
(capítulo 4). Qual LLM este papel usa continua a ficar na aba "LLM"
(capítulo 5), não aqui.

## 10.5 O que fica registado

Gerar uma análise (individual ou de grupo) é pelo menos tão sensível
como abrir a vista por estudante em Investigação — fica igualmente
auditado no Registo de Atividade (`apoio_pedagogico_gerado` /
`apoio_pedagogico_grupo_gerado`). A análise em si **nunca é gravada
como sessão** nem fica visível a estudantes.
