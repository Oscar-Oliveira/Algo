# 4. Alguem

Área: **Definições → Alguem**. Requer admin global.

Define o comportamento do Alguem (o tutor): se está ligado, a
identidade do Tutor, e o Guardião — a segunda verificação que revê cada
resposta antes de chegar ao estudante. **Qual LLM cada um usa fica
noutra aba, "LLM" (capítulo 5)** — esta aba é só comportamento, não
fornecedor.

## 4.1 Ativar o Alguem

Checkbox "Ativar Alguem para os estudantes" — interruptor geral da
plataforma. Cada grupo/turma tem também o seu próprio interruptor
(capítulo 2, secção 2.4), que só pode desligar o Alguem numa turma
específica, nunca ligá-lo se estiver desligado globalmente aqui.

Se ativares o Alguem mas não houver nenhum LLM disponível para ele (nem
uma configuração global de Apoio, nem permissão para os estudantes
usarem a própria — ver capítulo 5), o painel avisa explicitamente: o
Alguem fica "ligado" mas indisponível na prática.

## 4.2 Tutor — identidade (prompt)

Texto que identifica o Tutor perante o estudante — editável livremente.
Um botão "Repor por omissão" mostra sempre o valor original do projeto
por baixo, para comparares antes de decidir mudar.

## 4.3 Guardião

O Guardião é uma segunda verificação, **independente do Tutor**, que
classifica cada resposta antes de ela chegar ao estudante — nunca é uma
escolha do estudante.

- **"Guardião Pedagógico ativo"**: liga/desliga esta verificação.
- **Nível máximo de ajuda**: um valor de 0 a 6 na escada de assistência
  do Alguem (0 = autonomia total, sem intervenção; 6 = explicação
  explícita da estratégia, ainda sem código). O nível 7 ("Código") fica
  sempre bloqueado à parte e nunca aparece como opção aqui — o Alguem
  nunca escreve a solução, seja qual for a política.
- Este nível é **sempre** enviado ao Tutor como instrução (faz sempre
  parte do que o LLM recebe), mas só é **imposto** de facto — bloqueando
  ou pedindo uma resposta mais contida no código, não só por pedido —
  enquanto o Guardião estiver ativo **e** tiver um LLM atribuído (aba
  LLM). Sem Guardião ativo, o nível é só um pedido ao LLM, sem garantia.
- **Critério de classificação (prompt)**: o texto que instrui o Guardião
  sobre como classificar uma resposta — também editável, com o mesmo
  botão de repor por omissão.

## 4.4 Referência da linguagem ALGO

Um resumo de sintaxe ALGO **gerado automaticamente a partir do
compilador** (nunca desatualiza) e enviado ao Tutor em todas as
conversas. Não é editável aqui — só para consulta e cópia (botão
"Copiar"), útil para confirmar exatamente o que o LLM recebe como
contexto da linguagem.
