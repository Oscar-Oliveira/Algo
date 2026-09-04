# 8. Geral e backup

Área: **Definições → Geral**. Requer admin global.

## 8.1 Backup da base de dados

Botão "Descarregar base de dados" (`/api/admin/bd`) gera, na hora, um
dump `.sql` completo da base de dados — contas, grupos, credenciais de
LLM **ainda cifradas** (nunca em texto simples), registo de atividade —
via `pg_dump`, e descarrega-o com um nome no formato
`algo-online-AAAAMMDD-HHMMSS.sql`.

Pontos a ter em conta:

- É gerado sob pedido, não é um backup agendado — se precisares de
  backups regulares, tens de descarregar periodicamente (ou automatizar
  isso fora do painel, ex: um `cron` que chame esta rota).
- As credenciais de LLM continuam cifradas dentro do dump — sem a chave
  `ONLINE_CHAVE_CIFRAGEM` do servidor de origem, não são legíveis, o que
  faz este ficheiro seguro de guardar, mas também significa que
  restaurá-lo só faz sentido nessa mesma instância (ou noutra com a
  mesma chave de cifragem).
- A ação fica registada no Registo de Atividade (`bd_descarregada`).
- Requer `pg_dump` disponível no servidor — a imagem Docker oficial já
  o inclui.

Esta é atualmente a única definição na aba "Geral" — outras definições
globais da aplicação (Alguem, LLM) têm abas dedicadas por serem áreas
maiores (capítulos 4 e 5).
