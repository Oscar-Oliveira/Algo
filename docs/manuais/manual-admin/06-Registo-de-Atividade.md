# 6. Registo de Atividade

Área: **Definições → Registo de Atividade**. Requer admin global.

Registo geral de atividade da aplicação — contas, grupos, privilégios,
definições, configurações de LLM, backups — **separado das conversas
com o Alguem** (essas ficam em Investigação, capítulo 9). Ver também
capítulo 1, secção 1.5, sobre a diferença entre as duas coisas.

## 6.1 Colunas e filtros

Cada linha mostra: data/hora, tipo de evento, ator (quem fez a ação),
alvo (sobre quem/o quê incidiu), grupo relacionado, e um botão de
detalhes com o resto do contexto em JSON (ex: o antes/depois de uma
reatribuição de grupo).

Filtros disponíveis: utilizador, grupo, tipo de evento, e intervalo de
datas — combináveis.

## 6.2 Exemplos de eventos registados

Não é uma lista fechada, mas cobre praticamente toda ação administrativa
deste manual: `conta_aprovada`, `conta_rejeitada`, `conta_revogada`,
`admin_concedido`/`admin_revogado`, `admin_global_alterado`,
`grupos_geridos_alterados`, `grupo_reatribuido`, `grupo_criado`/
`_editado`/`_ativado`/`_desativado`/`_eliminado`,
`grupo_alguem_ativado`/`_desativado`, `log_apagado`,
`investigacao_estudante_visto`, `apoio_pedagogico_gerado`,
`relatorio_apagado`, `definicao_alterada`, `prompt_alterado`/
`_reposto_omissao`, `execucoes_apagadas`, `bd_descarregada`,
`llm_configuracao_criada`/`_editada`/`_apagada`, `llm_selecao_alterada`,
`llm_permissao_alterada`.

Note-se que ver a linha temporal de um estudante em Investigação
(`investigacao_estudante_visto`) e gerar uma análise de Apoio
Pedagógico (`apoio_pedagogico_gerado`) **também ficam aqui** — são
acessos sensíveis a dados de estudantes, tratados com o mesmo nível de
auditoria que qualquer outra ação administrativa.

## 6.3 Apagar registos

Seleciona linhas (checkbox por linha, ou "selecionar tudo") e usa
"Apagar selecionados". **Eliminação física e definitiva, sem
reciclagem** — decisão de simplicidade explícita do projeto, não uma
omissão. Não há forma de recuperar um registo apagado.

## 6.4 Exportar CSV

Botão "Exportar CSV" — respeita os filtros aplicados no momento.
