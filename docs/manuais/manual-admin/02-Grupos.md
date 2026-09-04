# 2. Grupos

Área: **Definições → Grupos**. Requer admin global.

Um grupo representa uma turma. Serve para agrupar estudantes, gerar um
código de junção para o registo, e (opcionalmente) ligar/desligar o
Alguem só para essa turma.

## 2.1 Criar um grupo

Formulário "Criar grupo": só pede um nome (ex: "12ºA 2026"). Ao criar,
o servidor gera automaticamente um **código de junção** de alta entropia
— nunca escolhido por uma pessoa, para não ser adivinhável.

## 2.2 A tabela de grupos

Cada linha mostra: nome, estado (ativo/inativo), se o Alguem está
ligado para essa turma, número de membros, o código, e as ações
disponíveis.

## 2.3 Ativar / desativar um grupo

Desativar um grupo **bloqueia o login dos seus membros estudantes** —
mas não o de um admin de grupo que o gira (bloquear o acesso de um
professor só porque uma das várias turmas que gere foi desativada não
faria sentido). Reativar o grupo restaura o login desses membros.

Desativar não apaga nada — os dados do grupo e dos seus membros
continuam intactos, só o acesso é suspenso. Um grupo desativado também
deixa de aceitar novos registos com o código antigo.

## 2.4 Ligar/desligar o Alguem por grupo

Independentemente da definição global do Alguem (capítulo 4), cada grupo
tem o seu próprio interruptor "Alguem ativo/inativo". Isto permite, por
exemplo, desligar o apoio do Alguem só numa turma que esteja a fazer uma
avaliação, sem afetar as restantes.

## 2.5 Código de junção

- **Ver o código**: botão dedicado na linha do grupo — o código fica
  guardado cifrado (Fernet) na base de dados, nunca em claro; só é
  decifrado quando pedes para o ver.
- **Regenerar o código**: invalida o código antigo para novos registos.
  Estudantes já registados **não são afetados** — só deixa de ser
  possível usar o código antigo para entrar de novo neste grupo a partir
  de agora.

## 2.6 Exportar membros (CSV)

Descarrega um ficheiro CSV com os membros do grupo (email, data de
registo, estado de aprovação, se é admin). Útil para cruzar com uma
lista de turma externa.

## 2.7 Apagar um grupo

**Só é possível apagar um grupo sem nenhum membro estudante.** Se já
tiver estudantes, o botão de apagar é recusado com uma mensagem clara —
usa "Desativar" em vez disso (2.3). Isto é intencional: apagar é uma
ação destrutiva pedida explicitamente, e um "não aconteceu nada" sem
explicação seria confuso.

Um admin de grupo que gira este grupo **não conta como membro** para
este efeito — só a pertença de estudantes bloqueia a eliminação.

Apagar um grupo é físico e definitivo (sem reciclagem) e fica registado
no Registo de Atividade (capítulo 6).

## 2.8 Onde a pertença a um grupo aparece noutro sítio

- Atribuir/mudar o grupo de uma conta já registada faz-se na aba
  **Utilizadores** (capítulo 3), não aqui.
- Que grupos um **admin de grupo** gere também se define em
  **Utilizadores** — um admin de grupo pode gerir mais do que uma turma;
  um estudante normal pertence no máximo a uma.
