# Manual do Painel de Administração — Algo Online

Manual de referência para quem gere o Algo Online em `/admin`: professores
e administradores de turma/plataforma. Não cobre instalação nem
configuração do servidor (variáveis de ambiente, Docker, base de dados) —
para isso ver o `README.md` de `online/`.

Cada capítulo é um ficheiro próprio, um por área do painel — a mesma
divisão que a barra lateral de `/admin` usa. Os exemplos e capturas de
comportamento foram verificados diretamente no código-fonte (`online/`),
não assumidos.

## Capítulos

| # | Capítulo | Área da barra lateral |
|---|----------|------------------------|
| 1 | [Acessos e conceitos-chave](01-Acessos-e-Conceitos.md) | (transversal) |
| 2 | [Grupos](02-Grupos.md) | Definições → Grupos |
| 3 | [Utilizadores](03-Utilizadores.md) | Definições → Utilizadores |
| 4 | [Alguem](04-Alguem.md) | Definições → Alguem |
| 5 | [LLM](05-LLM.md) | Definições → LLM |
| 6 | [Registo de Atividade](06-Registo-de-Atividade.md) | Definições → Registo de Atividade |
| 7 | [Problemas Reportados](07-Problemas-Reportados.md) | Definições → Problemas Reportados |
| 8 | [Geral e backup](08-Geral-e-Backup.md) | Definições → Geral |
| 9 | [Investigação](09-Investigacao.md) | Trabalho → Investigação |
| 10 | [Apoio Pedagógico](10-Apoio-Pedagogico.md) | Trabalho → Apoio Pedagógico |

A ordem segue a divisão em dois grupos que a própria barra lateral do
painel já usa: "Definições" (configuração da plataforma) primeiro,
depois "Trabalho" (ferramentas do dia a dia com dados de estudantes).

## Convenções usadas neste manual

- **Admin global** vs **admin de grupo**: distinção central, explicada em
  detalhe no capítulo 1 — a maioria das áreas só está acessível, ou só
  aparece sem filtros, para um admin global.
- Uma ação marcada **destrutiva** apaga dados de forma **física e
  definitiva** (sem reciclagem/soft-delete) — confirma sempre antes de a
  usar.
- Caminhos de ficheiro e nomes de rota (`/api/admin/...`) aparecem entre
  crase só quando ajudam a confirmar que estás a olhar para a funcionalidade
  certa — este manual é para quem usa o painel, não para quem o desenvolve.
