# 3. Utilizadores

Área: **Definições → Utilizadores**. Requer admin global.

Gere todas as contas registadas: aprovação, revogação, grupo/turma, e
privilégios de administrador.

## 3.1 Contas pendentes

Se o registo não estiver completamente aberto (ver capítulo 1, secção
1.2), uma conta nova aparece como **pendente** até seres aprovada. A
tabela mostra o estado de cada conta — aprova ou rejeita diretamente
nela:

- **Aprovar**: a conta passa a poder entrar.
- **Rejeitar**: **apaga a conta**, definitivamente — só funciona em
  contas ainda pendentes (nunca numa já aprovada, mesmo por engano), e
  fica registada no Registo de Atividade com o email como referência
  (a conta em si deixa de existir, por isso não há um "id" para apontar
  depois).

## 3.2 A coluna "Grupo" muda de significado

Consoante o tipo de conta, a mesma coluna representa coisas diferentes:

- **Estudante**: a turma a que pertence — no máximo uma. Podes
  reatribuí-la a outro grupo (ou remover, com "sem grupo") diretamente
  na tabela.
- **Admin global**: nada para escolher — já vê e gere tudo.
- **Admin de grupo**: as turmas que gere — pode ser mais do que uma,
  escolhidas com uma lista de checkboxes.

## 3.3 Revogar acesso

"Revogar" bloqueia o login de uma conta **já aprovada**, sem a apagar
(reverte o estado para "não aprovada" — a conta reaparece como pendente
se voltares a olhar para o histórico dessa forma). Nunca funciona numa
conta admin — é uma salvaguarda para não bloqueares um admin por
engano; retira-lhe primeiro o estatuto de admin se for isso que
pretendes. Não podes revogar-te a ti próprio.

## 3.4 Privilégios de administrador

- **Tornar admin / Tornar estudante**: concede ou remove o estatuto de
  admin. Removê-lo é recusado se isso deixasse a aplicação sem nenhum
  admin ativo, e nunca podes removê-lo a ti próprio. Ao remover,
  qualquer grupo que a conta geria como admin de grupo é limpo
  automaticamente.
- **Tornar admin global / Tornar admin de grupo**: alterna entre os dois
  tipos (ver capítulo 1, secção 1.3). Retirar o estatuto global é
  recusado se isso deixasse a aplicação sem nenhum admin global ativo, e
  nunca podes retirá-lo a ti próprio.

Todas estas ações (aprovar, rejeitar, revogar, conceder/remover admin,
alternar global/de grupo, reatribuir grupo) ficam registadas no Registo
de Atividade (capítulo 6), com o antes/depois quando aplicável.
