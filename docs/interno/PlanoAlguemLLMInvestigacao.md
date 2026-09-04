# Plano: configuração de LLM (global/pessoal) e investigação no Alguem

Documento de análise, não de implementação — regista o desenho
proposto para o utilizador validar antes de qualquer código ser
tocado. Ponto de partida: notas do utilizador sobre evoluir a
configuração de LLM do Alguem (hoje: um único fornecedor por conta,
sem opção global) para um modelo com várias configurações possíveis a
nível global e por estudante, com o admin a decidir a precedência
entre elas, e sobre querer um relatório de investigação mais completo
(dashboard, relatório, exportação, com filtros).

> **Nota de privacidade/ética**: uma das decisões desta ronda
> (ver "Decisões já validadas", ponto 4) é **remover a
> pseudonimização** dos logs e relatórios do Alguem, para o admin
> poder identificar diretamente o estudante por trás de uma conversa
> ou execução de código, e assim dar apoio pedagógico real. Isto
> reverte uma decisão de privacidade documentada em
> `online/README.md` ("Identificador pseudónimo separado da conta") e
> reforça o aviso que já existe em `alguem/README.md`: *"Se estiveres
> a investigar com estudantes reais, o log continua a conter o texto
> integral das conversas e do código deles -- vale a pena rever isto
> com a tua comissão de ética/RGPD antes de recolher dados assim."*
> Passa a aplicar-se com ainda mais força depois desta mudança — os
> dados deixam de estar sequer pseudonimizados por omissão. Este
> documento regista a decisão tal como pedida, mas a validação
> ética/RGPD junto da instituição continua a ser responsabilidade de
> quem opera o serviço, não algo que este projeto resolva sozinho.

## O que já existe hoje

- **Isolamento do Alguem**: já é como pretendido — `alguem/` não tem
  `cli.py` próprio, não é alcançável pela consola do ALGO, e a única
  forma de o invocar é `online/alguem_ponte.py:construir_alguem`
  (confirmado em `alguem/README.md` e no próprio pacote). **Nenhuma
  mudança necessária aqui.**
- **Configuração de LLM**: `online/credenciais.py` + `bd.py` (tabela
  `credencial_llm`) guardam **uma única** credencial por conta
  (`PRIMARY KEY (estudante_id)`), decisão documentada como "cada
  estudante traz e configura a sua própria chave". Não há
  configuração global de LLM hoje — só um interruptor liga/desliga
  (`definicoes.py`, `alguem_ativo`), sem escolha de fornecedor/modelo.
- **Guardião**: `alguem/nucleo/tutor.py` cria o `GuardiaoPedagogico`
  reaproveitando **sempre o mesmo fornecedor** do tutor
  (`GuardiaoPedagogico(fornecedor)`, `tutor.py:76`) — hoje não há
  noção de "LLM diferente para o guardião". Já suporta correr **sem**
  guardião (`guardiao=None`, quando `politica.usar_guardiao=False`) —
  este mecanismo é o que a nova regra de fallback vai reaproveitar.
- **Relatório de investigação**: já existe, mas está **desligado por
  CSS** — a aba "Atividade" em `admin.html:21-25` ("Separador
  'Atividade' (métricas do Alguem) fica temporariamente oculto --
  funcionalidade ainda não usada") mostra hoje: sessões, estudantes
  distintos, Solution Leakage Rate e Hint Dependency globais, mais uma
  tabela por sessão (`online/main.py:517`,
  `alguem/scripts/metricas.py`). Não tem filtro por grupo, nem
  gráficos, nem exportação.
- **Grupos**: já existem (`online/grupos.py`, `estudante.grupo_id`),
  usados hoje só para gerir turmas/códigos de acesso — nenhuma métrica
  do Alguem é filtrável por grupo atualmente.
- **Pseudonimização**: os logs do Alguem usam sempre `id_pseudonimo`
  (`autenticacao.obter_id_pseudonimo`), nunca o id da conta nem o
  email — decisão de privacidade documentada, mas que esta ronda
  decide **reverter** (ver "Decisões já validadas", ponto 4). Nota
  importante: `id_pseudonimo` tem **dois** usos distintos hoje, só um
  dos quais está em causa —
  1. identificar sessões nos logs do Alguem (`alguem_ponte.py:102`) —
     **este é o que deixa de usar o pseudónimo**;
  2. nomear a pasta temporária de execução de código de cada
     estudante em `executor.py:preparar_pasta_execucao` (chamado a
     partir de `main.py` nas rotas de execução) — isto é uma medida de
     isolamento/segurança de sistema de ficheiros (evita usar o email
     diretamente num caminho de disco), **não uma anonimização de
     dados de investigação**, e fica tal como está.
- **Código do estudante**: hoje **não há persistência nenhuma** — cada
  execução corre numa pasta temporária efémera
  (`online/executor.py`), sem tabela `programs` nem histórico
  guardado (decisão documentada em `online/README.md`, "No code
  persistence"). Esta ronda decide criar esse histórico (ver secção
  9).
- **Política pedagógica**: hoje é **fixa e global**,
  `POLITICA_POR_OMISSAO` em `alguem_ponte.py:26`, construída uma
  única vez a partir dos valores por omissão de
  `PoliticaPedagogica` (`alguem/nucleo/politica_pedagogica.py`) — o
  admin não tem hoje nenhuma forma de a mudar sem editar código. Isto
  inclui `nivel_maximo_ajuda`, o valor que limita até onde a escada de
  ajuda (0-7) pode subir, e `usar_guardiao`, que liga/desliga o
  Guardião Pedagógico por completo.

## Decisões já validadas com o utilizador

1. **Guardião sem LLM disponível** (nem global ativo para esse papel,
   nem permissão para o estudante usar o seu): a conversa continua
   **sem guardião** — equivale a `usar_guardiao=false`. Mecanismo já
   existe em `tutor.py` (`guardiao=None`).
2. **Identificação de cada configuração de LLM guardada** (agora que
   pode haver várias, a nível global e por estudante): cada uma tem
   uma **etiqueta escolhida por quem a cria** (não só fornecedor+
   modelo), para permitir repetir fornecedor+modelo com credenciais
   diferentes e dar nomes memoráveis (ex: "GPT rápido para testes").
3. **Relatório de investigação**: focado nos dados do **Alguem** (não
   a fundir com `log_atividade`, que é de eventos de conta/admin,
   assunto diferente). Para além da lista de sessões que já existe,
   deve haver também um **dashboard com gráficos** e um **relatório**,
   ambos com **filtros** (grupo incluído), e uma **exportação**.
4. **Remover a pseudonimização** dos logs/relatórios do Alguem — os
   dados passam a identificar diretamente o estudante (não só um
   `id_pseudonimo`), para o admin poder ligar uma conversa ou uma
   execução de código à pessoa real e dar apoio pedagógico. Ver a nota
   de privacidade/ética acima.
5. **Histórico de código executado**: guardar **todas** as tentativas
   de execução/debug de cada estudante, sem limite nem substituição da
   anterior — é o que permite acompanhar a evolução ao longo do tempo.
6. **Apoio pedagógico gerado por LLM**: a análise corre **sob pedido**
   do admin, por estudante (o admin escolhe um estudante na lista e
   pede a análise nesse momento) — não é um processo automático/
   periódico para todos.
7. **Visibilidade das sugestões de apoio pedagógico**: ficam visíveis
   **só para o admin/professor** — o estudante nunca vê o texto
   gerado diretamente (pelo menos nesta fase).
8. **Registo de auditoria de acesso**: sim, deve haver um registo de
   quando um admin abre a vista detalhada de um estudante (secção 10)
   — dados deixaram de estar pseudonimizados, este acesso é sensível.
9. **Prompts totalmente editáveis pelo admin**: os três prompts (tutor,
   Guardião, apoio pedagógico) ficam livremente editáveis, **incluindo
   o núcleo de segurança** (`IDENTIDADE` em `system_prompt.py`, as
   categorias em `PROMPT_CLASSIFICACAO` de `guardiao.py`) — decisão
   explícita apesar do risco identificado (ver secção 13).
10. **Exportação**: CSV e JSON, os dois formatos.
11. **Eliminação de histórico**: só o histórico de código executado
    (secção 9) tem uma ferramenta de eliminação dedicada (últimos XX
    dias, seleção manual, ou tudo) — as sessões do Alguem
    (`logs/*.jsonl`) e as configurações de LLM antigas **não** entram
    nesta ferramenta (ficam só com a eliminação normal, uma a uma, já
    prevista no CRUD de `configuracao_llm`).
12. **Acesso aos dados de investigação por grupo**: um admin não-global
    só vê os dados de investigação (Alguem/código, secções 6/9/10/11)
    dos grupos que gere — um admin **global** vê tudo, sem restrição.
    Um admin pode gerir vários grupos (não só um). Estudantes sem
    grupo só são visíveis a admins globais.
13. **As abas de administração da plataforma ficam só para admin
    global**: Utilizadores, Grupos, Problemas Reportados, Registo de
    Atividade e Definições (interruptor do Alguem, LLM global,
    prompts, nível do Guardião — secções 5/8/13) deixam de estar
    acessíveis a um admin não-global. Isto **reverte** a primeira
    versão desta secção (que dizia o oposto — só os dados novos
    ficavam restritos). Na prática, um admin de grupo só tem acesso à
    aba de Investigação (secção 6), filtrada aos seus grupos — é a
    única coisa que um admin não-global consegue fazer no painel.
14. **Definições de LLM do estudante, só dentro do painel do Alguem**:
    confirmado que já é assim hoje (`editor.html`, `painel-alguem` >
    `vista-definicoes-alguem`) — decisão é manter, nunca introduzir
    uma página de conta separada, só estender esse mesmo espaço para
    suportar várias configurações com etiqueta e os seletores de papel
    ativo (ver secção 5b).
15. **Uma só relação para conta↔grupo, não duas** (decidido já na
    implementação da Fase 1, não na proposta original desta secção):
    em vez de manter `estudante.grupo_id` (pertença de estudante) e a
    tabela `admin_grupo` (âmbito de gestão de um admin de grupo) como
    dois sítios separados, ambos passam a viver na mesma relação —
    `estudante_grupo(estudante_id, grupo_id)` — com a cardinalidade
    certa por tipo de conta decidida pelo código (`grupos.py`), não
    pelo esquema: um estudante tem no máximo uma linha, um admin de
    grupo pode ter várias, um admin global não precisa de nenhuma. A
    tabela `admin_grupo` referida na secção 15 abaixo e na Fase 1 foi
    substituída por esta — `bd.py` migra os dois sítios antigos para
    `estudante_grupo` automaticamente no arranque.
16. **Grupo desativado só bloqueia o login de estudantes, não de
    admins** (também decidido na implementação da Fase 1): a regra
    antiga era "sem exceção, incluindo contas admin" — fazia sentido
    quando só havia um tipo de admin, mas deixou de fazer sentido com
    o admin de grupo (que pode gerir várias turmas ao mesmo tempo):
    bloquear-lhe o login só porque UMA delas foi desativada não seria
    razoável. A partir de agora só uma conta não-admin fica bloqueada
    por esta razão.
17. **Guardião nunca é escolha pessoal do estudante** (reverte a
    proposta original desta secção -- "por estudante, só para
    apoio/guardião" --, decidido já na implementação da Fase 2): o
    estudante escolhe UM único LLM (usado para conversar); esse mesmo
    fornecedor serve também de guardião até o admin decidir o
    contrário a nível global, sem o estudante alguma vez ver ou
    escolher um "guardião" como conceito à parte -- deixar o
    estudante escolher o seu próprio guardião defeitava o propósito
    dele (uma verificação de segurança pensada para ser independente
    do estudante). `selecao_llm_estudante` fica só com
    `apoio_config_id`; a seleção e a permissão pessoal para
    "guardiao" deixam de existir em `configuracao_llm.py`
    (`PAPEIS_PESSOAIS = {"apoio"}`, distinto de
    `PAPEIS_GLOBAIS = {"apoio", "guardiao"}`, que continua a existir
    só para a escolha do admin). O painel do estudante (secção 5b)
    passa a ter um único seletor "LLM ativo", não dois; o painel do
    admin mantém os dois seletores GLOBAIS (apoio/guardião, secção 5)
    mas perde o checkbox "Estudantes podem usar o próprio LLM para
    guardião" (nunca fez sentido sem a seleção pessoal).

## Desenho proposto

### 1. Modelo de configuração de LLM (global + pessoal, múltiplas, 3 papéis)

Três papéis, não dois: **apoio** (o tutor), **guardião** (verificação
de segurança pedagógica), e **apoio pedagógico** (análise de
progresso para o admin, secção 11 — sempre da plataforma, nunca do
estudante, sem alternativa pessoal nem interruptor de permissão,
porque não é o estudante quem a usa).

Substituir a tabela `credencial_llm` (1 linha por conta) por uma nova
tabela `configuracao_llm`, com `estudante_id` **anulável**: `NULL` =
configuração **global** (só o admin gere), preenchido = configuração
**pessoal** dessa conta. Campos: `id`, `estudante_id` (nullable),
`etiqueta`, `fornecedor`, `modelo`, `api_key_cifrada`, `host`,
`criado_por` (para configs globais, qual admin as criou — reaproveita
o padrão já usado em `grupo.criado_por`), `criado_em`, `atualizado_em`.
Reaproveita tal e qual: `FORNECEDORES_VALIDOS`, `_validar_host_ollama`
(SSRF, `credenciais.py:29-51`), `cifrar`/`decifrar` (`cifragem.py`).

"Seleções ativas" **por papel**, cada uma apontando para uma linha de
`configuracao_llm`:

- **Global**: três novos registos em `definicao` (mesmo padrão
  chave/valor de `alguem_ativo`) — `llm_global_apoio_id`,
  `llm_global_guardiao_id` e `llm_global_apoio_pedagogico_id` —
  guardando o `id` da configuração global ativa para cada papel, ou
  vazio se o admin não escolheu nenhuma. Só o terceiro
  (`apoio_pedagogico`) não tem equivalente pessoal — é sempre esta
  seleção global, ou nenhuma.
- **Por estudante**, só para apoio/guardião: uma tabela pequena
  `selecao_llm_estudante(estudante_id PK, apoio_config_id, guardiao_config_id)`,
  ambos nullable, apontando só para configs desse próprio estudante.

Duas permissões globais (não três — `apoio_pedagogico` não precisa,
ver acima), também em `definicao` (mesmo padrão booleano de
`alguem_ativo`): `estudantes_podem_llm_apoio` e
`estudantes_podem_llm_guardiao`.

### 2. Regra de precedência (apoio e guardião calculados independentemente)

```
para cada papel (apoio, guardiao):
  se existe configuração GLOBAL ativa para este papel:
      usar essa configuração global (ignora tudo o resto)
  senão se a permissão "estudantes podem usar o próprio LLM" (deste papel) está ligada:
      usar a configuração PESSOAL ativa do estudante para este papel, se existir
      senão: [ver "quando falta LLM" abaixo]
  senão:
      [ver "quando falta LLM" abaixo]

quando falta LLM:
  apoio    -> Alguem fica indisponível (ErroAlguemIndisponivel, mensagem clara sobre porquê)
  guardiao -> conversa continua sem guardião (decisão já validada)
```

O interruptor existente `alguem_ativo` continua a mandar por cima de
tudo isto (Alguem desligado = desligado, independentemente de haver
LLM configurado).

O terceiro papel não segue esta regra — é mais simples, por não ter
alternativa pessoal:

```
apoio_pedagogico:
  se existe configuração GLOBAL ativa -> usa-a
  senão -> a aba "Apoio Pedagógico" fica indisponível, com mensagem clara
```

### 3. Alterações no `alguem/` e `online/alguem_ponte.py`

- `alguem/nucleo/tutor.py`: `Alguem.__init__` já aceita `guardiao:
  GuardiaoPedagogico | None` explícito — passa a ser **sempre**
  `alguem_ponte.construir_alguem` a decidir e passar isto (nunca
  deixar o `elif politica.usar_guardiao` construir sozinho a partir do
  fornecedor do tutor), porque agora o fornecedor do guardião pode ser
  diferente do fornecedor do apoio.
- `online/alguem_ponte.py:construir_alguem`: passa a resolver **dois**
  `AgenteLLM` (via `criar_fornecedor`, já existente) seguindo a regra
  de precedência acima — um para apoio (obrigatório), outro para
  guardião (opcional). Ambos precisam de decifrar a `api_key` certa a
  partir de `configuracao_llm`.
- Novo módulo (ex: `online/configuracao_llm.py`, substituindo
  `credenciais.py`) com as operações CRUD sobre `configuracao_llm` +
  seleção ativa por papel, global e pessoal — reaproveitando toda a
  validação já existente em `credenciais.py`.

### 4. Registo para investigação (`alguem/nucleo/registador.py`)

Ampliar `inicio_sessao` com os campos que tornam o novo modelo
analisável sem depender da base de dados relacional (mantém
`metricas.py` livre de ligação à BD, como é hoje):

- `apoio_escopo`: `"global"` | `"pessoal"`
- `guardiao_escopo`: `"global"` | `"pessoal"` | `"indisponivel"`
- `guardiao_fornecedor` / `guardiao_modelo` (hoje só há um par
  fornecedor/modelo, implicitamente do apoio)
- `grupo`: nome do grupo do estudante nesse momento (ou `null`),
  resolvido em `alguem_ponte.py` a partir de `estudante.grupo_id` —
  **denormalizado no evento por decisão deliberada**: preserva o grupo
  tal como era nessa sessão mesmo que o estudante mude de grupo
  depois, e evita `metricas.py` ter de consultar a BD para filtrar por
  grupo.

**Identificação do estudante no evento** (`id_estudante`, hoje
`id_pseudonimo`): passa a ser a identificação real da conta — proposta
é o **email**, por ser o mesmo identificador já mostrado noutras
partes do admin (ex. `relatorios.listar_relatorios`), evitando um
segundo lookup só para mostrar quem é. `alguem_ponte.py:102` deixa de
chamar `obter_id_pseudonimo` e passa o email diretamente. A coluna
`estudante.id_pseudonimo` e `autenticacao.obter_id_pseudonimo`
continuam a existir só para o uso de isolamento de pasta em
`executor.py` (não relacionado, ver "O que já existe hoje").

### 5. Painel de admin — Definições

Na aba "Definições" (`online/paginas_privadas/admin.html`,
`online/estatico/admin.js`, ao lado do interruptor `alguem_ativo` já
existente):

- Gestão de configurações globais de LLM (criar/editar/apagar, mesmo
  formulário que hoje existe para a credencial pessoal do estudante,
  reaproveitando os campos fornecedor/modelo/chave/host/etiqueta).
- Dois seletores "LLM ativo para Apoio" / "LLM ativo para Guardião"
  (dropdown das configurações globais existentes, com opção "Nenhum --
  deixar ao critério do estudante").
- Dois interruptores: "Estudantes podem usar o próprio LLM para
  apoio" / "...para guardião".

### 5b. Painel do estudante — tudo dentro do painel do Alguem, nunca numa página à parte

Confirmado no código (`online/paginas_privadas/editor.html:213-277`):
as definições de LLM do estudante **já** vivem só dentro do próprio
painel do Alguem, não numa página de conta separada — `painel-alguem`
tem duas vistas que se alternam no mesmo espaço (`botao-definicoes-
alguem` troca `vista-conversa-alguem` por `vista-definicoes-alguem`,
`botao-fechar-definicoes` volta atrás), hoje com um único formulário
(fornecedor/modelo/chave/host). O aviso "Ainda não configuraste um
fornecedor de LLM" dentro da conversa já liga diretamente para lá
(`botao-ir-definicoes`). **Decisão confirmada**: continua assim — a
gestão de configurações de LLM do estudante nunca ganha uma página de
conta à parte, só estende o que já existe dentro do painel do Alguem.

Desenho proposto para caber várias configurações (com etiqueta) e os
dois seletores de papel ativo no mesmo espaço estreito de um painel
lateral, sem virar uma página cheia de campos:

- `vista-definicoes-alguem` passa a ter **dois níveis**, dentro do
  mesmo painel (mesmo espírito da alternância conversa/definições que
  já existe):
  1. **Lista** (vista por omissão ao abrir): cada configuração
     guardada como uma linha compacta (etiqueta + "fornecedor ·
     modelo"), com ícones de editar/apagar; no topo, os dois
     seletores "Ativo para apoio" / "Ativo para guardião" (dropdown
     das configurações da lista) — só aparecem/ficam ativos quando a
     permissão correspondente do admin estiver ligada (secção 5);
     quando desligada, mostra uma linha explicativa ("O apoio está
     definido pela plataforma") em vez do seletor.
     um botão "+ Nova configuração" abre o nível 2.
  2. **Formulário** (o que já existe hoje, + campo `Etiqueta`): editar
     uma configuração existente ou criar uma nova; "Guardar" volta à
     lista, "Fechar"/cancelar também.
- O aviso `aviso-credencial-alguem` mantém-se, só o texto passa a
  refletir o papel em falta (ex. "Ainda não tens uma configuração
  ativa para apoio").

### 6. Painel de admin — Investigação (revive + expande a aba "Atividade")

Reaproveita a aba já existente e hoje escondida (`admin.html:21-25`,
`main.py:517 rota_admin_atividade`, `alguem/scripts/metricas.py`) em
vez de criar uma nova do zero, mas passa a ter três secções, todas com
os mesmos filtros no topo (grupo, período, fornecedor/modelo, escopo
apoio/guardião):

1. **Dashboard** (gráficos) — sessões ao longo do tempo, Solution
   Leakage Rate por grupo, distribuição do nível máximo de escalada
   (0-7), sessões por fornecedor/modelo separando escopo global vs.
   pessoal, distribuição de turnos por sessão. (Quando isto for
   implementado, seguir a skill `dataviz` do projeto para o desenho
   dos gráficos.)
2. **Relatório** — a tabela por sessão que já existe hoje, com as
   colunas novas (grupo, escopo apoio, escopo guardião).
3. **Exportação** — download em **CSV e JSON** (ambos, decisão
   validada) dos dados filtrados, para análise externa (pandas, etc.)
   — endpoint novo em `main.py`, por cima de `metricas.gerar_relatorio`
   com os filtros aplicados.

Identifica diretamente por email (ver secção 4 — já não há
pseudonimização), e ganha um botão "ver este estudante" por linha, que
abre a vista descrita na secção 10.

### 8. Controlo da política pedagógica pelo admin (nível do guardião)

Hoje `POLITICA_POR_OMISSAO` (`alguem_ponte.py:26`) é construída uma
única vez, com os valores por omissão de `PoliticaPedagogica` — o
admin não consegue mudar nada sem editar código. Passa a haver, na
aba "Definições", controlo sobre os dois campos diretamente ligados ao
Guardião:

- **`nivel_maximo_ajuda`** (0-6): até que nível da escada de ajuda o
  Alguem/Guardião pode chegar — guardado em `definicao` (mesmo padrão
  chave/valor), lido por `alguem_ponte.construir_alguem` em vez do
  valor fixo da dataclass.
- **`usar_guardiao`**: liga/desliga o Guardião Pedagógico por
  completo — já existe como campo da política, só falta ser
  configurável.

Os restantes campos de `PoliticaPedagogica` (`modo`,
`permite_gerar_codigo`, `permite_solucoes_completas`,
`prefere_perguntas`, `pistas_progressivas`) ficam **fora de âmbito**
por agora — o pedido foi especificamente sobre o nível do Guardião,
não sobre reabrir toda a política a variação pelo admin.

### 9. Registo de execução de código por estudante

Nova tabela, ex. `execucao_codigo` (mesmo espírito de `log_atividade`,
mas para código, não eventos de conta): `id`, `estudante_id`, `tipo`
(`"executa"` | `"debug"`), `nome_ficheiro_principal`, `ficheiros`
(JSON — nome + conteúdo de cada ficheiro enviado, o mesmo que já
chega a `/ws/executar`/`/ws/debug` em `main.py:800-925`), `resultado`
(sucesso / erro de compilação / erro em execução — texto resumido,
não a saída completa linha a linha), `criado_em`. **Histórico
completo, sem limite nem substituição** (decisão validada, ponto 5).

Ponto de registo: nas rotas WebSocket já existentes
`ws_executar`/`ws_debug` (`main.py`), imediatamente depois de receber
`mensagem_inicial` (que já traz `ficheiros`/`principal`) — não requer
tocar em `executor.py` nem no compilador. Corre em paralelo à
execução em si, não a atrasa.

Cresce sem limite por estudante ativo — vale a pena o admin ter noção
do volume de armazenamento ao longo de um semestre/ano (ver "Perguntas
em aberto").

### 10. Vista de pedidos ao Alguem e código, por estudante (admin)

Com a identificação direta (secção 4) e o novo registo de código
(secção 9), a aba de investigação (secção 6) ganha uma vista de
detalhe por estudante — acedida a partir do relatório/dashboard
("ver este estudante") ou de uma pesquisa direta por email: linha
temporal única, juntando as sessões do Alguem (`alguem/logs/*.jsonl`
dessa pessoa) e as execuções de código (`execucao_codigo` dessa
pessoa), por ordem cronológica. É a matéria-prima da aba de apoio
pedagógico (secção 11) — o LLM de apoio pedagógico recebe exatamente
esta vista como contexto.

### 11. Apoio Pedagógico — terceiro papel de LLM, sempre da plataforma

Nova aba no admin, "Apoio Pedagógico": o admin escolhe um estudante
(sob pedido, decisão validada, ponto 6) e pede uma análise. O pedido
junta o histórico desse estudante (secção 10 — conversas com o Alguem
e código executado) num prompt, envia ao LLM configurado em
`llm_global_apoio_pedagogico_id` (secção 1 — **sempre** da plataforma,
nunca uma configuração do próprio estudante, sem exceção nem
interruptor), e mostra a resposta **só ao admin/professor** (decisão
validada, ponto 7) — nunca ao estudante.

Não corre em segundo plano nem é armazenada como um novo tipo de
"sessão" do Alguem — é uma ferramenta de leitura/análise para o admin,
não uma conversa nova a registar como investigação. (Se, mais tarde,
se quiser medir o impacto do próprio apoio pedagógico, isso pede um
desenho próprio — fora de âmbito aqui.)

Precisa de uma política/prompt próprios (não reaproveita o *system
prompt* do tutor em `alguem/nucleo/system_prompt.py`, que é para
conversar com o estudante, não para analisar um histórico e sugerir
apoio a um professor) — editável pelo admin como qualquer um dos três
prompts (secção 13). Para histórico longo (muitas sessões/execuções),
a direção decidida é **resumir antes de enviar** ao LLM de apoio
pedagógico, em vez de truncar ou enviar tudo em bruto — mecanismo
exato de resumo (uma chamada extra ao LLM por sessão longa? um resumo
incremental?) fica para a fase de implementação.

### 13. Prompts editáveis pelo admin (tutor, Guardião, apoio pedagógico)

> **Aviso de segurança**: esta secção documenta uma decisão explícita
> de expor **todo** o texto dos três prompts a edição pelo admin,
> incluindo a parte hoje fixa no código que é a rede de segurança
> pedagógica — `IDENTIDADE` em `alguem/nucleo/system_prompt.py:11-32`
> ("nunca resolves o exercício pelo estudante...") e as definições das
> 5 categorias dentro de `PROMPT_CLASSIFICACAO` em
> `alguem/nucleo/guardiao.py:103-136` ("SAFE", "HINT", ...,
> "FULL_SOLUTION", "CODE"). Um admin que edite mal este texto pode
> enfraquecer, sem querer, a proteção contra o Alguem revelar soluções
> — é um risco aceite deliberadamente, não um efeito colateral
> ignorado. Vale a pena, na implementação, pelo menos guardar um
> histórico de versões de cada prompt (para reverter uma edição má) e
> mostrar o texto por omissão lado a lado, mesmo que a validação
> automática de conteúdo fique fora de âmbito.

Nova tabela `prompt_configuravel` (ou reaproveitar `definicao`, se o
texto for curto — os três prompts atuais não são): `chave` (`"tutor"`
| `"guardiao"` | `"apoio_pedagogico"`), `texto`, `atualizado_em`,
`atualizado_por`. `alguem_ponte.construir_alguem` (e o novo caminho do
apoio pedagógico, secção 11) passam a ler daqui em vez das constantes
`IDENTIDADE`/`PROMPT_CLASSIFICACAO`/o prompt do apoio pedagógico —
sem linha guardada, usa-se o texto atual como valor por omissão (mesmo
padrão de "sem linha para uma chave, assume-se o valor por omissão"
já usado em `definicoes.py`).

Nova aba (ou secção dentro de "Definições") no admin: um editor de
texto por prompt, com o valor por omissão visível e um botão "repor
por omissão".

### 14. Eliminação do histórico de execução de código

Só o histórico de código (secção 9) — não as sessões do Alguem, não as
configurações de LLM antigas (decisão validada, ponto 11). Na mesma
área onde o histórico é consultado (secção 6/10), o admin pode
eliminar: por **período** (ex. "apagar tudo com mais de 90 dias"), por
**seleção manual** (escolher linhas específicas na tabela), ou
**tudo**. `DELETE FROM execucao_codigo WHERE ...` simples, sem soft-
delete nem papelaria — decisão explícita de simplicidade, coerente com
"Simplicidade First" do projeto, a rever se algum dia for preciso
desfazer uma eliminação.

### 15. Controlo de acesso: admin global vs. admin de grupo

Hoje um admin é só um booleano (`estudante.admin`), sem nenhuma
ligação a um grupo — qualquer admin gere/vê qualquer grupo por igual
(`grupo.criado_por` é só um registo de quem criou, não uma restrição
de acesso), e todas as abas do painel são iguais para todos os admins.
Esta ronda introduz uma segunda categoria — **admin de grupo** — mais
limitada que o admin de hoje (que passa a chamar-se **admin global**):

- **Admin global**: continua a ver e gerir tudo — Utilizadores,
  Grupos, Problemas Reportados, Registo de Atividade, Definições
  (interruptor do Alguem, LLM global, prompts editáveis, nível do
  Guardião — secções 5/8/13), e os dados de investigação (secções
  6/9/10/11) de **todos** os grupos.
- **Admin de grupo** (não-global): só consegue aceder à aba de
  Investigação (secção 6), e só aos dados dos grupos que gere — as
  restantes abas (Utilizadores, Grupos, Problemas Reportados, Registo
  de Atividade, Definições) ficam **inacessíveis**, escondidas na
  barra lateral (mesmo padrão de classe `escondido` já usado hoje para
  a aba "Atividade") e bloqueadas do lado do servidor.

- **Admin ↔ grupo, muitos-para-muitos**: relação `estudante_grupo(
  estudante_id, grupo_id)` — a mesma tabela que guarda a pertença de
  um estudante ao seu grupo, reaproveitada (ver "Decisões já
  validadas", ponto 15) — um admin de grupo pode ter várias linhas
  (gerir vários grupos, um professor com várias turmas), não só uma.
- **Distinção global/grupo**: novo campo booleano (ex.
  `estudante.admin_global`) — é este campo que decide qual das duas
  categorias acima uma conta admin tem.
- **Regra de acesso** (dentro da aba de Investigação): para um admin
  de grupo, os dados de investigação (dashboard, relatório,
  exportação, vista detalhada por estudante, apoio pedagógico) só
  incluem estudantes cuja linha em `estudante_grupo` aponte para um
  dos grupos geridos por esse admin — os restantes **não aparecem de
  todo** (não é uma versão anonimizada, é ausência total dos dados
  desse estudante para esse admin). Dentro do que vê, o admin
  continua a ver o email diretamente (secção 4 — já não há
  pseudonimização), sem restrição adicional.
- **Estudantes sem grupo** (sem linha em `estudante_grupo`): os seus
  dados de investigação só ficam visíveis a admins **globais** —
  nenhum admin "de grupo" os vê, mesmo que giram outros grupos.
- **Gestão**: a atribuição de grupos a um admin (e o interruptor
  "admin global") fica na aba "Utilizadores", ao lado do
  interruptor que já existe para tornar uma conta admin
  (`autenticacao.tornar_admin`/`remover_admin`).
- **Aplicação**: dois níveis de verificação do lado do servidor, ambos
  no mesmo espírito de `admin_atual` (`online/main.py`), já usado
  para proteger as rotas de admin em geral —
  1. rotas de Utilizadores/Grupos/Problemas Reportados/Registo de
     Atividade/Definições passam a exigir explicitamente
     `admin_global` (não só `admin`) — um admin de grupo recebe 403
     em qualquer uma;
  2. dentro das rotas de Investigação (secções 6/9/10/11), um admin de
     grupo só recebe (listagens) ou só acede (vista de um estudante
     específico, apoio pedagógico) dados de estudantes nos seus
     grupos — fora disso, listagens filtram silenciosamente e um
     pedido direto a um estudante fora do âmbito devolve 403.

### 16. Fora de âmbito / sem mudanças

- Os restantes campos de `PoliticaPedagogica` além de
  `nivel_maximo_ajuda`/`usar_guardiao` (ver secção 8).
- `log_atividade` (eventos de conta/admin) fica separado do relatório
  de investigação do Alguem, por decisão explícita (ver "Decisões já
  validadas", ponto 3).
- O isolamento de pasta de execução por `id_pseudonimo` em
  `executor.py` (ver "O que já existe hoje") — não é afetado pela
  remoção da pseudonimização nos logs/relatórios.

## Faseamento de implementação

Seis fases, cada uma com um âmbito fechado e demonstrável por si —
pensadas para serem analisadas e aceites uma de cada vez, não como um
único bloco. A ordem segue as dependências reais entre elas (uma fase
só assume o que as anteriores já entregaram).

### Fase 1 — Permissões (admin global vs. admin de grupo) — ✅ implementada

- `estudante.admin_global`, relação `estudante_grupo` (secção 15 —
  substitui a tabela `admin_grupo` da proposta original, ver "Decisões
  já validadas", ponto 15).
- Utilizadores/Grupos/Problemas Reportados/Registo de Atividade/
  Definições passam a exigir `admin_global` (servidor + esconder na
  UI).
- Gestão de atribuição de grupos a um admin, na aba Utilizadores
  (coluna "Grupo" fundida — muda de significado consoante o tipo de
  conta: dropdown único para estudante, checkboxes para admin de
  grupo, texto fixo para admin global).
- **Base para tudo o resto**: sem isto, não há onde aplicar a
  filtragem por grupo nas fases seguintes. Migração: admins existentes
  ficam `admin_global=true` por omissão — implementado via `DEFAULT
  TRUE` na própria coluna (`bd.py`), que se aplica automaticamente às
  linhas já existentes no momento do `ALTER TABLE`, sem precisar de um
  `UPDATE` de migração à parte; novos admins nascem globais pela mesma
  razão (ver "Perguntas em aberto").
- Bónus descoberto durante a implementação: grupo desativado deixa de
  bloquear o login de um admin (só de estudantes) — ver "Decisões já
  validadas", ponto 16.
- **Demonstrável no fim**: um admin de grupo já não vê as abas
  restritas; um admin global não nota diferença nenhuma.

### Fase 2 — Definições de LLM (configuração múltipla, papéis, precedência) — ✅ implementada

- Tabela `configuracao_llm` (substitui `credencial_llm`), migração dos
  dados existentes, `selecao_llm_estudante`, chaves em `definicao`
  para seleção global por papel e permissões de uso pessoal (secções
  1, 3, 4 parcial).
- UI admin (Definições — restrita a `admin_global`, depende da Fase 1):
  gestão de configs globais, seletores de papel ativo, interruptores
  de permissão.
- UI estudante: lista + formulário com etiqueta, seletores de papel
  ativo (secção 5b), dentro do painel do Alguem.
- Regra de precedência (secção 2) já cobre os dois papéis, apoio e
  guardião, mesmo que `alguem_ponte.py` ainda resolva só um fornecedor
  nesta fase (o guardião continua a reaproveitar o do apoio até à
  Fase 3 — a tabela e a seleção já suportam os dois, só falta ligar).
- **Demonstrável no fim**: admin e estudante conseguem gerir várias
  configurações com etiqueta; a que está realmente em uso (para
  conversar) já respeita a precedência, sem ainda ter um guardião
  separado.

### Fase 3 — Alguem (guardião com LLM próprio, nível configurável, prompts editáveis) — ✅ implementada

- `alguem_ponte.construir_alguem` passa a resolver dois fornecedores
  (apoio e guardião), `tutor.py` recebe sempre `guardiao` explícito
  (secção 3).
- Controlo pelo admin de `nivel_maximo_ajuda` e `usar_guardiao`
  (secção 8).
- Prompts editáveis — tutor e Guardião (secção 13; o prompt de "apoio
  pedagógico" pode já ter o campo criado aqui, mas só é usado na
  Fase 6).
- Corrigido durante a implementação: `nivel_maximo_ajuda` vai só de
  0 a 6, não 0-7 — o nível 7 ("Código") fica sempre bloqueado à parte
  por `permite_gerar_codigo` (fixo a `False`, fora de âmbito nesta
  fase), por isso oferecer 7 no seletor seria uma opção sem efeito
  nenhum.
- Painel de admin (Definições) reorganizado em três secções — LLM
  (armazém de configurações), Tutor e Guardião — cada uma com o seu
  seletor de LLM ativo, permissões/prompt reunidos no mesmo bloco, em
  vez de espalhados; inclui notas explícitas sobre os dois pontos que
  geram confusão na prática: uma seleção global manda sempre sobre a
  pessoal (a permissão pessoal fica sem efeito enquanto isso for
  verdade), e o Guardião nunca partilha configuração com o LLM pessoal
  do estudante.
- **Demonstrável no fim**: o guardião pode correr com um modelo
  diferente do tutor; o admin muda o nível máximo de ajuda e o texto
  dos dois prompts sem tocar em código.

### Fase 4 — Registo para investigação (identificação direta + código executado) — ✅ implementada

- `id_estudante` nos eventos do Alguem passa a email, não
  `id_pseudonimo` (secção 4).
- Novos campos em `inicio_sessao`: `apoio_escopo`, `guardiao_escopo`,
  `guardiao_fornecedor`/`guardiao_modelo`, `grupo`. `guardiao_escopo`
  só usa "global" ou "indisponivel" na prática -- nunca "pessoal", já
  que o ponto 17 (decidido depois desta secção ter sido escrita) tirou
  ao guardião qualquer seleção pessoal.
- Tabela `execucao_codigo` + registo em `/ws/executar`/`/ws/debug`
  (secção 9). O registo em si corre depois de o estudante já ter
  recebido o resultado da sua execução (fim/erro/erro_compilacao já
  enviados) -- não bloqueia nada que ele perceba, só adia por uma
  escrita à BD o momento em que o pedido WebSocket termina de vez do
  lado do servidor.
- Ferramenta de eliminação do histórico de código, por período/
  seleção/tudo (secção 14) -- implementada como três rotas de admin
  (`/api/admin/execucoes/apagar[-por-periodo|-tudo]`), sem UI própria
  ainda: como a Fase 4 explicitamente não tem "interface de consulta
  visual", a UI para as três (incluindo poder escolher linhas da
  tabela para a seleção manual) fica para a Fase 5, que já vai ter essa
  tabela.
- **Demonstrável no fim**: os logs já identificam a pessoa diretamente;
  cada execução/debug fica gravada; o admin consegue limpar histórico
  de código antigo (via API, ainda sem botão dedicado -- ver acima).
  Ainda sem interface de consulta visual (isso é a Fase 5).

### Fase 5 — Relatórios / Investigação (dashboard, relatório, exportação, vista por estudante) — ✅ implementada

- Revive e expande a aba "Atividade" → "Investigação" (secção 6):
  dashboard com gráficos, relatório tabular, exportação CSV e JSON,
  filtros (grupo incluído).
- Vista detalhada por estudante (secção 10), com registo de auditoria
  de cada acesso (decisão validada, ponto 8) -- reaproveita
  `log_atividade` (tipo `investigacao_estudante_visto`), sem tabela
  nova.
- Restrição por grupo aplicada aqui (depende da Fase 1) sobre os
  dados da Fase 4 -- usa sempre a pertença ATUAL do estudante
  (`estudante_grupo`), nunca o campo `grupo` denormalizado nas
  sessões (esse é só para exibição/filtro de relatório, preservando o
  que era verdade na altura).
- Novo módulo `online/investigacao.py` faz a ponte entre os logs
  `.jsonl` do Alguem (via `alguem.scripts.metricas`, agora também a
  expor os campos da Fase 4) e a base de dados -- os logs não sabem
  nada de grupos/contas, só o `id_estudante` (email); a filtragem por
  grupo cruza os dois.
- Eliminação do histórico de código (secção 14/Fase 4, cujas rotas já
  existiam mas sem UI) ganha finalmente controlos na aba Investigação
  -- seleção manual dentro da vista por estudante, período/tudo num
  painel à parte -- ambos só visíveis a admin global, como o resto da
  secção 14 já previa.
- Gráficos em SVG desenhado à mão (sem biblioteca externa), seguindo a
  skill `dataviz`: paleta categórica validada (azul/laranja), barras
  com `<title>` como camada de hover mínima, rótulos diretos, eixo/
  grelha recessivos. Simplificação assumida face à skill: sem toggle
  de vista em tabela nem modo de textura para CVD/impressão -- cortado
  por ser um painel interno, não uma página pública.
- **Demonstrável no fim**: um admin global vê o dashboard/relatório de
  todos; um admin de grupo só vê os seus grupos; cada consulta a um
  estudante fica auditada.

### Fase 6 — Apoio Pedagógico (terceiro papel de LLM)

Desenho fechado com o utilizador (2026-09-04), afinando a secção 11
original em três pontos que só ficaram claros ao desenhar o ecrã: o
LLM deste papel precisa do mesmo seletor que apoio/guardião já têm, o
admin escolhe explicitamente QUAL estudante e QUE tipos de log entram
na análise (não é sempre "tudo"), e o resumo de histórico longo passa
por uma revisão humana antes de seguir para o LLM.

- **Papel `apoio_pedagogico` em `configuracao_llm.PAPEIS_GLOBAIS`**
  (passa a ter 3 elementos, não 2) -- reaproveita tal e qual toda a
  máquina já construída na Fase 2 para apoio/guardião: CRUD de
  configurações, `definir_selecao_global`/`obter_selecao_global`,
  a rota genérica `/api/admin/llm/selecao` e a listagem `/api/admin/llm`
  (já devolve `selecao_global` com uma entrada por papel em
  `PAPEIS_GLOBAIS`, sem precisar de mudança nenhuma em `main.py` para
  isto). **Não** entra em `PAPEIS_PESSOAIS` -- nunca há alternativa
  pessoal nem permissão para o estudante, como já decidido. Na aba
  "LLM" do admin, o seletor "LLM ativo para Apoio Pedagógico" fica ao
  lado dos de Apoio/Guardião (mesma secção "Atribuição de papéis"),
  sem checkbox de permissão a acompanhar (só os dois papéis pessoais
  têm um).
- **Prompt `apoio_pedagogico` em `prompts_configuraveis.PROMPTS_OMISSAO`**
  -- texto por omissão explica ao LLM que está a analisar histórico de
  UM estudante (conversas com o Tutor e/ou código executado) para dar
  uma sugestão de apoio pedagógico a um professor, nunca para o
  estudante ver. Editável só por admin global, como tutor/guardião
  (mesma rota genérica `/api/admin/prompts/*`, sem mudança em
  `main.py`), mas o editor deste prompt vive dentro da nova aba
  "Apoio Pedagógico" (não na aba "Alguem", que é só Tutor/Guardião),
  visível só quando `EH_ADMIN_GLOBAL` -- um admin de grupo continua a
  poder gerar análises (ver acesso abaixo), só não edita o prompt nem
  o LLM.
- **Novo módulo `online/apoio_pedagogico.py`**, no mesmo espírito de
  `online/investigacao.py` (ponte entre logs `.jsonl`/BD e o admin,
  `alguem/` continua sem saber nada disto):
  - Reaproveita o controlo de acesso por grupo da Investigação (secção
    15) -- extrai-se de `investigacao.py` uma função pública
    `verificar_acesso_estudante(admin_id, admin_global, estudante_id)`
    (o que hoje está só dentro de `vista_estudante`) para os dois
    módulos usarem a mesma lógica, e uma nova
    `investigacao.listar_estudantes_no_ambito_admin(admin_id,
    admin_global) -> list[{"id", "email"}]` (lista de CONTAS, não de
    sessões -- ao contrário de `listar_sessoes_no_ambito`, inclui
    estudantes sem nenhuma sessão do Alguem ainda, para o seletor
    conseguir apontar também a quem só tem execuções de código) --
    nova rota `/api/admin/investigacao/estudantes` expõe isto,
    reaproveitada tanto pelo seletor da Investigação (resolve também a
    "pesquisa direta por email" que a secção 10 previa e ainda não
    tinha ficado exposta) como pelo novo seletor do Apoio Pedagógico.
  - `montar_blocos_historico(estudante_id, *, tipos, data_inicio,
    data_fim, pasta_logs=None) -> list[dict]`: um bloco
    `{"timestamp", "texto", "tipo"}` por sessão do Alguem (se
    `"alguem" in tipos`) e/ou por execução de código (se
    `"codigo" in tipos`). `tipos` é `{"alguem"}`, `{"codigo"}` ou
    `{"alguem", "codigo"}` (pelo menos um -- validado).
    `historico_codigo.listar_por_estudante` ganha `data_inicio`/
    `data_fim` opcionais (mesma convenção ISO-8601 já usada em
    `investigacao.filtrar_sessoes`), para o filtro de período também
    cobrir código, não só sessões.
  - **Revisto em 2026-09-04, depois de uma primeira versão implementada**:
    a ideia original desta secção usava a transcrição real da sessão
    (pergunta + resposta por turno) e, se não coubesse num limite de
    carateres, chamava o próprio LLM de apoio pedagógico para a
    resumir (map-reduce). Trocado por um desenho mais simples e mais
    barato depois de reconsiderado com o utilizador: cada bloco passa a
    ser um FACTO compacto de uma linha (reaproveitando as métricas que
    `metricas.calcular_metricas_da_sessao` já calcula -- turnos,
    Solution Leakage Rate, nível máximo de escalada -- para sessões; o
    `resultado` já resumido de `execucao_codigo`, para código), não a
    transcrição integral. Isto normalmente já cabe sozinho no limite,
    sem precisar de encolher nada; quando não cabe,
    `_truncar_por_tamanho` corta de forma **determinística** (mantém o
    início e o fim do período, a meio orçamento de carateres cada, para
    preservar sinal de progressão ao longo do tempo em vez de só
    recência, e assinala quantos itens ficaram de fora pelo meio) --
    **nenhum LLM é chamado neste passo**. Perde-se o conteúdo literal
    das trocas (menos narrativo), mas ganha-se: zero custo/latência
    extra, nada para um resumo-LLM hallucinate ou cortar em silêncio, e
    o que o admin revê antes de confirmar é a informação real, não a
    paráfrase de um LLM sobre ela.
  - **Revisão humana obrigatória antes da análise final** -- por isso
    o fluxo continua em DOIS pedidos distintos, nunca um só:
    1. `preparar_resumo(...) -> str` -- monta os blocos e, se
       necessário, trunca-os deterministicamente; devolve o texto para
       o admin ler e, se quiser, editar. **Não fala com nenhum LLM,
       nem exige um configurado.**
    2. `gerar_analise(estudante_id, resumo_texto, admin_id) -> str` --
       o admin confirma (com o texto tal como ficou, editado ou não);
       só agora se envia esse texto, mais o prompt `apoio_pedagogico`,
       ao LLM configurado, e a resposta é devolvida -- **o único passo
       do fluxo que fala com um LLM**. Não fica gravada como sessão
       nova (decisão validada, ponto 6) -- só o pedido fica auditado
       (ver abaixo).
  - `contar_historico(...) -> {"total", "alguem", "codigo"}`:
    pré-visualização da quantidade de histórico para os filtros
    escolhidos, ANTES de pedir o resumo -- também nunca fala com um
    LLM. Rota `/api/admin/apoio-pedagogico/contagem`, chamada pela UI
    sempre que o estudante/período/tipos mudam.
- **Auditoria**: gerar uma análise (não só ver o histórico bruto) fica
  registado em `log_atividade` (tipo `apoio_pedagogico_gerado`, ator =
  admin, alvo = estudante), mesmo espírito do ponto 8 já aplicado à
  vista por estudante -- é pelo menos tão sensível.
- **Acesso**: as rotas de geração (estudantes/resumo/análise) usam
  `admin_atual` (não `admin_global_atual`), tal como as de Investigação
  -- um admin de grupo só consegue escolher estudantes dentro dos seus
  grupos (`verificar_acesso_estudante` levanta `ErroAcessoNegado` ->
  403 fora disso). As rotas de configuração (seleção do LLM, prompt)
  continuam `admin_global_atual`, como todo o resto da secção 15.
- **UI**: o botão "Apoio Pedagógico" já existe na barra lateral
  (`admin.html`), hoje desativado (`disabled`, classe `brevemente`) --
  esta fase ativa-o. Dentro da aba: seletor de estudante (reaproveita
  `/api/admin/investigacao/estudantes`), período (dois campos de
  data, iguais aos da Investigação), dois checkboxes "Execuções de
  código" / "Sessões do Alguem" (pelo menos um marcado, ambos por
  omissão), botão "Gerar resumo" -> mostra o resumo numa caixa de
  texto editável com "Confirmar e analisar" / "Cancelar" -> ao
  confirmar, mostra a análise devolvida num painel de leitura. Editor
  do prompt (só admin global) fica no fundo da mesma aba.
- Depende de todas as fases anteriores (é o que junta LLM, permissões,
  registo e a vista por estudante num único fluxo).
- **Demonstrável no fim**: o admin escolhe um estudante, um período e
  os tipos de log, revê (e pode editar) o resumo gerado, confirma, e
  recebe uma sugestão de apoio pedagógico -- sem o estudante alguma
  vez ver esse texto. Um admin de grupo só consegue fazer isto para
  estudantes dos seus grupos.
- **Extensão em 2026-09-04: Apoio por Grupo.** Continua **um só** botão
  na barra lateral ("Apoio Pedagógico"), agora com TRÊS subabas, nesta
  ordem: "Individualizado" (o que já ficou descrito acima), "Grupo"
  (mesmo fluxo, mas para uma turma inteira) e "Definições" (por
  último). Reaproveita tudo entre Individualizado/Grupo: mesmo papel/
  config de LLM, mesmo prompt `apoio_pedagogico` (generalizado para
  cobrir os dois casos), mesmo mecanismo de resumo determinístico -- só
  junta os blocos de cada membro do grupo (`grupos.listar_membros`),
  prefixados com `[email do estudante]` para o LLM conseguir distinguir
  um padrão comum à turma de algo isolado a uma pessoa
  (`apoio_pedagogico.montar_blocos_historico_grupo`). Acesso pelo mesmo
  princípio (`investigacao.verificar_acesso_grupo` -- admin de grupo só
  escolhe grupos que gere); rotas em `/api/admin/apoio-pedagogico/
  grupo/*` e `/api/admin/apoio-pedagogico/grupos` (listagem, âmbito-
  filtrada). A subaba "Grupo" não tem "Definições" própria -- reaproveita
  a mesma configuração de LLM/prompt da subaba "Definições" (que serve
  os dois modos).

## Perguntas em aberto para a fase de implementação

Não bloqueiam este documento, mas têm de ser decididas antes de
escrever código:

- Nomes exatos finais de tabelas/colunas (`configuracao_llm`,
  `selecao_llm_estudante`, `prompt_configuravel`, chaves em
  `definicao`).
- Migração das credenciais pessoais já existentes em `credencial_llm`
  para `configuracao_llm` (etiqueta por omissão, ex.
  `"{fornecedor} · {modelo}"`) — **decidido**: os dados antigos podem
  ser simplesmente descartados depois da migração, `credencial_llm`
  não precisa de ficar por compatibilidade.
- Limite (se algum) ao número de configurações que uma conta ou o
  admin podem guardar.
- Se fica só no painel de admin ou também como comando de linha (como
  `alguem/scripts/metricas.py` já é hoje).
- Formato exato do histórico de versões dos prompts editáveis (secção
  13) — quantas versões guardar, se o "repor por omissão" conta como
  uma edição no histórico.
- Exato formato de entrada para o LLM de apoio pedagógico (secção 11):
  quanto histórico incluir e como resumir sessões longas para caber no
  contexto do modelo — **decidido em direção**: resumir antes de
  enviar (não truncar nem enviar tudo em bruto), mecanismo exato de
  resumo por definir na implementação.
- Estado por omissão dos admins **já existentes** quando a restrição
  por grupo (secção 15) entrar em vigor: hoje todos são, na prática,
  "globais" (veem tudo, sem distinção) — migrá-los todos para
  `admin_global=true` preserva o acesso atual sem surpresa, mas vale a
  pena confirmar explicitamente antes de implementar, para não ser
  uma escolha silenciosa.
