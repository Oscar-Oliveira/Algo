# 9. Investigação

Área: **Trabalho → Investigação**. Acessível a admin global **e** a
admin de grupo (ver capítulo 1, secção 1.3) — um admin de grupo vê tudo
já filtrado às turmas que gere, e nunca tem a opção "todos os grupos".

Dashboard, relatório e exportação a partir das **sessões reais do
Alguem** — ao contrário do Registo de Atividade (capítulo 6), aqui há
**identificação direta por email**, porque o objetivo é um professor
perceber como os seus estudantes estão a usar o apoio.

## 9.1 Filtros

Grupo, intervalo de datas, fornecedor de LLM, escopo do Apoio (qualquer/
global/pessoal — se a sessão usou a configuração da plataforma ou a
própria do estudante) e escopo do Guardião (qualquer/global/
indisponível — se houve segunda verificação ou não). Os filtros aplicam-se
às duas sub-abas seguintes.

## 9.2 Sub-aba Dashboard

Cartões de métricas e gráficos, calculados sobre as sessões filtradas:

- **Sessões** e **Estudantes distintos**.
- **Solution Leakage Rate**: fração das tentativas de resposta do Tutor
  que o Guardião rejeitou (teve de bloquear/reformular por revelarem
  demais) — quanto mais baixo, melhor o Tutor está a respeitar a escada
  de ajuda por si só, sem precisar do Guardião a corrigi-lo.
- **Hint Dependency**: número médio de turnos de conversa por sessão.
- Gráficos: sessões por dia, Leakage Rate por grupo, distribuição do
  nível máximo de escalada atingido (0–7, ver a escada de ajuda no
  capítulo 4), turnos por sessão, e sessões por fornecedor/modelo
  cruzado com o escopo do apoio.

## 9.3 Sub-aba Relatório

Uma linha por sessão: estudante, grupo, turnos, leakage, nível máximo
atingido, modelo usado no Apoio, escopo do apoio, escopo do guardião, e
número de recusas seguras (vezes em que o Alguem recusou explicitamente
dar a solução). Colunas ordenáveis por turnos/leakage/nível/recusas.

- **Exportar CSV / Exportar JSON**: respeitam os filtros ativos.
- **Ver** (por linha): abre a **vista por estudante** (secção 9.4).

## 9.4 Vista por estudante

Uma **linha temporal única**, cronológica, combinando sessões do Alguem
e execuções/debug de código desse estudante — pensada para veres o
percurso completo, não só as conversas isoladas do resto do trabalho.

Abrir esta vista é um acesso sensível a dados identificáveis de um
estudante — **fica sempre registado no Registo de Atividade**
(`investigacao_estudante_visto`), mesmo que sejas admin global.

### Eliminar histórico de código executado

Dentro desta vista (e também na sub-aba Relatório, mais abaixo, para um
âmbito mais amplo) há ferramentas para eliminar o **histórico de
execução/debug de código** — nunca as sessões do Alguem, que não têm
eliminação pelo painel. Três modos, sempre sem confirmação a meio nem
reciclagem:

- **Seleção manual**: escolhe execuções específicas na linha do tempo e
  apaga só essas.
- **Por período**: apaga tudo com mais de N dias (campo "dias", omissão
  90).
- **Tudo**: apaga o histórico de execuções inteiro — pede uma
  confirmação explícita porque é irreversível sobre todos os dados, não
  só uma seleção.
