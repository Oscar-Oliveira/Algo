# 5. LLM

Área: **Definições → LLM**. Requer admin global.

O "armazém" de configurações de fornecedores de LLM geridas pela
plataforma, e qual delas cada papel do Alguem usa. A ativação e o
comportamento de cada papel (Tutor, Guardião) ficam na aba "Alguem"
(capítulo 4) — esta aba é só sobre credenciais e atribuição.

## 5.1 Configurações guardadas

Cada configuração tem: etiqueta (nome livre para a reconheceres),
fornecedor, modelo, e credencial. Fornecedores suportados: OpenRouter,
Google Gemini, OpenAI, Anthropic (Claude), HuggingFace, Ollama (local,
sem chave de API) e OpenCode Go.

- **Nova configuração de LLM**: abre um formulário com etiqueta,
  fornecedor, modelo, e ou uma chave de API (a maioria dos fornecedores)
  ou um endereço de servidor (só Ollama, que corre localmente e não usa
  chave).
- A chave de API é **cifrada em repouso** (Fernet, com a chave definida
  em `ONLINE_CHAVE_CIFRAGEM` no servidor) e **nunca é devolvida** pelo
  painel depois de guardada — só o resto dos dados (etiqueta, fornecedor,
  modelo, host) é mostrado de volta, para confirmares o que já está
  configurado sem expor o segredo outra vez.
- **Testar**: cada configuração tem um botão que faz um pedido mínimo
  real ao fornecedor, só para confirmar que a chave/modelo/host
  funcionam — não altera nem guarda nada.
- Apagar uma configuração global é permitido mesmo que esteja atribuída
  a um papel — nesse caso o papel fica sem LLM (equivalente a escolher
  "Nenhuma" na atribuição, secção 5.2).

## 5.2 Atribuição de papéis

Três papéis, cada um com a sua própria configuração global (podem ser
todas diferentes, ou a mesma):

- **Apoio (Tutor)**: o LLM que conversa com o estudante. Se deixares
  "Nenhuma", e a permissão pessoal abaixo estiver ligada, cada estudante
  usa a configuração que ele próprio escolher no editor.
- **Guardião**: o LLM da segunda verificação (capítulo 4). Este papel
  **nunca** usa o LLM pessoal de um estudante, mesmo que a permissão de
  Apoio esteja ligada — só esta configuração global. Sem nenhuma
  escolhida, ou com o Guardião desativado na aba Alguem, as conversas
  continuam sem esta verificação extra.
- **Apoio Pedagógico**: o LLM que analisa o histórico de um estudante ou
  grupo, sob pedido de um admin (capítulo 10). Nunca é uma escolha do
  estudante e não tem alternativa pessoal — sem uma configuração aqui, a
  aba "Apoio Pedagógico" fica indisponível.

## 5.3 Permitir o LLM pessoal do estudante

Só existe para o papel **Apoio** — checkbox "Permitir o próprio LLM
quando não houver nenhum definido pela plataforma". Se houver uma
configuração global de Apoio escolhida, ela **manda sempre** enquanto lá
estiver, quer os estudantes tenham ou não permissão para configurar a
sua própria — o painel avisa disto quando é o caso.

Sem uma configuração global de Apoio e com esta permissão desligada, o
Alguem fica indisponível para os estudantes na prática (mesmo que o
interruptor geral, na aba Alguem, esteja ligado).
