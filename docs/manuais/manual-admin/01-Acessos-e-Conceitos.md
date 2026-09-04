# 1. Acessos e conceitos-chave

## 1.1 Como chegar ao painel

O painel de admin fica em `/admin` (ex: `https://a-tua-instância/admin`).
Só é visível depois de entrares com uma conta que tenha privilégio de
administrador — sem isso, o servidor devolve um erro de acesso, não uma
versão "vazia" do painel.

## 1.2 A primeira conta de admin

Não existe nenhum ecrã de "criar o primeiro admin" — o mecanismo é a
variável de ambiente `ONLINE_EMAIL_ADMIN` (lista de emails separados por
vírgula, definida por quem instala o servidor):

- **Sem `ONLINE_EMAIL_ADMIN` definida**: o registo fica completamente
  aberto e sem aprovação — é o comportamento mais simples, pensado para
  uma instância de teste/aula única sem necessidade de gerir pedidos de
  acesso.
- **Com `ONLINE_EMAIL_ADMIN` definida**: qualquer conta registada com um
  desses emails torna-se automaticamente admin e fica aprovada assim que
  faz login pela primeira vez (mesmo que se tivesse registado antes de a
  variável ser definida). Todas as outras contas novas ficam **pendentes**
  até um admin as aprovar — ver capítulo 3.

Uma conta que se torna admin desta forma nasce **admin global** (ver
1.3) — o valor por omissão da coluna correspondente na base de dados é
`TRUE`, precisamente para preservar este comportamento até alguém a
restringir a um grupo específico.

## 1.3 Admin global vs. admin de grupo

Há dois privilégios booleanos por conta, não um único "é admin":

| | Admin **global** | Admin **de grupo** |
|---|---|---|
| Vê e gere | Tudo | Só o que pertence aos grupos que gere |
| Áreas acessíveis | Todas | Só **Investigação** e **Apoio Pedagógico** |
| Pode gerir vários grupos? | Não aplicável (já vê tudo) | Sim — um admin de grupo pode ter mais do que uma turma atribuída |
| Login bloqueado se UM grupo gerido for desativado? | — | Não — só o login de estudantes membros é bloqueado |

As áreas **Utilizadores**, **Grupos**, **Problemas Reportados**, **Registo
de Atividade**, **Alguem**, **LLM** e **Geral** exigem admin global
explicitamente — um admin de grupo que tente aceder a estas rotas recebe
um erro 403 (proibido), não uma versão vazia.

Em **Investigação** e **Apoio Pedagógico**, um admin de grupo *consegue*
entrar, mas tudo o que vê já vem filtrado às turmas que gere — nunca
escolhe "todos os grupos" nem vê estudantes fora do seu âmbito.

Para alternar uma conta entre os dois tipos, ou definir que grupos um
admin de grupo gere, usa-se a aba **Utilizadores** (capítulo 3).

### Salvaguardas embutidas

Estas proteções estão na própria instrução que altera a base de dados
(não só no botão do painel), por isso não têm exceção mesmo por engano:

- Uma conta **nunca pode retirar o próprio estatuto de admin**, nem
  **revogar-se a si própria**.
- Retirar o estatuto de admin (ou de admin global) a alguém é recusado
  se isso deixasse a aplicação **sem nenhum admin ativo** (ou, no caso do
  estatuto global, sem nenhum admin global ativo).
- Ao retirar o estatuto de admin a uma conta, os grupos que ela geria
  como admin de grupo são limpos automaticamente (deixa de fazer sentido
  "gerir" turmas depois de voltar a ser estudante).

## 1.4 Contas pendentes, aprovação e o código de junção

Quando o registo não está completamente aberto (ver 1.2), uma conta nova
fica pendente até seres aprovada por um admin global — ver capítulo 3.
Enquanto pendente, o login devolve uma mensagem explícita a dizer isso,
para o estudante não se voltar a registar por engano.

O **código de junção** de um grupo (capítulo 2) é sempre **opcional** no
registo — nunca obrigatório. Um estudante pode registar-se sem código e
ser atribuído a um grupo mais tarde por um admin, na aba Utilizadores.

## 1.5 Registo geral de atividade vs. sessões do Alguem

Duas coisas fáceis de confundir, com propósitos diferentes:

- **Registo de Atividade** (capítulo 6): eventos administrativos —
  contas aprovadas/revogadas, privilégios concedidos, grupos criados,
  configurações de LLM alteradas, backups descarregados, etc. Nunca
  contém conversas com o Alguem.
- **Investigação** (capítulo 9): dados de *investigação/pedagogia* a
  partir das conversas reais com o Alguem — identificação direta por
  email, pensado para um professor perceber como os seus estudantes
  estão a usar o apoio.

## 1.6 Ações destrutivas

Várias ações neste painel apagam dados de forma **física e definitiva**
— sem reciclagem, sem "desfazer": eliminar registos de atividade,
eliminar histórico de execuções de código, apagar um relatório, apagar um
grupo sem membros. Isto é uma decisão de simplicidade deliberada do
projeto, não uma omissão — confirma sempre o que vais apagar antes de o
fazeres, sobretudo nas ações "apagar tudo".
