# Algo Online

Versão web do Algo + Alguem: vários estudantes, cada um com a sua
conta, agrupados opcionalmente em grupos, código isolado por processo,
e o seu próprio fornecedor de LLM. Construído deliberadamente sem
grandes *frameworks* — FastAPI, PostgreSQL puro (sem ORM), sem sistema
de *templates* (HTML servido tal e qual).

**Estado**: base de dados migrada de SQLite para PostgreSQL; sistema
de grupos, registo geral de atividade e gestão de privilégios de admin
acrescentados. Ver "O que falta" no fim.

## Arquitetura

```
online/
├── Dockerfile
├── docker-compose.yml       # inclui o serviço 'bd' (PostgreSQL)
├── .env.exemplo             # copiar para .env e preencher
├── main.py                  # aplicação FastAPI -- rotas HTTP + os 2 WebSockets
├── bd.py                    # esquema PostgreSQL (sem ORM, psycopg)
├── autenticacao.py          # registo/login, hash de password (bcrypt)
├── grupos.py                 # grupos: CRUD, código de junção, reatribuição
├── atividade.py               # registo geral de atividade (separado dos logs do Alguem)
├── limitador_registo.py        # rate limiting por IP no registo com código de grupo errado
├── credenciais.py            # credencial de LLM por conta, cifrada em repouso
├── cifragem.py                 # cifragem simétrica (Fernet) das chaves de API
├── executor.py                  # execução assíncrona e interativa de programas Algo
├── alguem_ponte.py               # constrói um Alguem a partir da credencial da BD
├── modo_codemirror.py         # gera o realce de sintaxe a partir do compilador
├── estatico/                      # HTML/CSS/JS -- sem framework de frontend
│   ├── vendor/codemirror6/           # CodeMirror 6 auto-hospedado (não depende de CDN)
│   └── visualizador/                 # visualizador de rasto (algo-trace-viewer.html/.jsx), só existe aqui
└── tests/                          # pytest
```

`algo_lang/` (o compilador) e `alguem/` (o tutor) não são alterados —
são só importados. A única adaptação foi `alguem_ponte.py`, que
constrói o `Alguem` a partir da credencial guardada na base de dados
em vez de um `config.json` local.

## Decisões de design que valem a pena conhecer

- **Sem persistência de código**: cada sessão é como um bloco de
  notas. Não há tabela de "programas" na base de dados.
- **Isolamento de execução**: um subprocesso por execução
  (`asyncio.create_subprocess_exec`, nunca `subprocess.run` -- esse
  bloquearia o servidor inteiro), numa pasta própria por estudante
  (pelo identificador pseudónimo, nunca pelo email), com limites de
  tempo de CPU e memória impostos pelo próprio sistema operativo
  (`resource.setrlimit`). Isto é isolamento razoável para uma turma
  numa VM só -- não é uma sandbox à prova de um utilizador hostil.
- **`compilar_ficheiro` do `cli.py` NÃO é reutilizado diretamente**:
  esse *wrapper* foi escrito para a consola e faz `sys.exit(1)` num
  erro de sintaxe, o que aqui terminaria o servidor inteiro para
  todos os estudantes. `executor.py` chama as primitivas do
  compilador diretamente (`parse`/`verificar`/`gerar_python`), e
  reimplementa também a resolução de `incluir` (`_resolver_inclusoes`
  do `cli.py` tinha o mesmo problema de `sys.exit(1)`).
- **Vários ficheiros por sessão, com `incluir` a funcionar a sério**:
  o estudante pode criar ficheiros adicionais (bibliotecas próprias) e
  usar `incluir "nome.algo"` no ficheiro principal -- todos os
  ficheiros abertos são enviados juntos ao servidor a cada execução/
  fluxograma/rasto, e escritos na mesma pasta antes de compilar.
- **Realce de sintaxe sem depender de nenhum CDN externo**: o
  CodeMirror 6 é servido localmente -- é distribuído como vários
  pacotes npm em ESM, sem build UMD pronto a usar, por isso
  `estatico/vendor/codemirror6/codemirror6.js` é um bundle único
  gerado uma vez com `esbuild` fora do projeto (ver o README nessa
  pasta; não há `package.json`/Node como dependência de build do
  `online/`). O "modo" da linguagem (um `StreamLanguage`) é gerado
  dinamicamente a partir das palavras-chave reais do compilador
  (`/modo-algo.js`) -- nunca desatualiza. Tab converte sempre para 4
  espaços e espaços/tabs ficam visíveis no editor.
- **Identificador pseudónimo separado da conta**: os logs do Alguem
  (ver `alguem/README.md`) usam um UUID gerado no registo, nunca o
  `id` da conta nem o email -- mantém a mesma filosofia de privacidade
  já estabelecida no resto do projeto, mesmo havendo agora contas
  reais com login.
- **Cada estudante traz a sua própria chave de LLM**, cifrada em
  repouso (Fernet) com uma chave de cifragem que nunca fica na base de
  dados nem no código.
- **Grupos**: geridos por um admin, com um código de junção
  gerado pelo servidor (alta entropia, nunca escolhido por uma
  pessoa). Guardado de duas formas -- um hash SHA-256 determinístico
  (`grupo.codigo_hash`, para verificar o código submetido no registo
  por *lookup* indexado) e uma cópia cifrada com Fernet
  (`grupo.codigo_cifrado`, para o admin poder voltar a consultar o
  código em claro no painel a qualquer momento). O código no registo é
  **sempre opcional** -- um admin pode atribuir/mudar o grupo de
  qualquer conta depois. Desativar um grupo bloqueia o login dos seus
  membros **sem exceção**, incluindo contas admin (decisão explícita:
  simplicidade e previsibilidade acima de evitar um caso raro de
  auto-exclusão).
- **Registo geral de atividade** (`atividade.py`, tabela
  `log_atividade`): separado dos logs de conversa com o Alguem
  (`alguem/nucleo/registador.py`, ficheiros `.jsonl`, inalterados). A
  eliminação de registos é **física e definitiva** (sem soft-delete) --
  decisão explícita, ver `notes.md`. O separador "Atividade" (métricas
  do Alguem) no painel de admin está temporariamente oculto por CSS
  (funcionalidade ainda não usada), sem apagar dados nem a rota.
- **Privilégios de admin**: um único booleano (`estudante.admin`), sem
  tabela de papéis. Conceder/remover fica registado em
  `log_atividade`; remover está protegido contra auto-remoção e contra
  deixar a aplicação sem nenhum admin ativo (ambas as guardas embutidas
  na própria query SQL, não só na rota).

## Docker

### Com docker compose (mais simples)

```bash
cd online
cp .env.exemplo .env
# edita o .env e preenche as chaves e as credenciais do Postgres (instruções lá dentro)
docker compose up -d --build
```

`docker-compose.yml` já inclui o serviço `bd` (PostgreSQL, imagem
`postgres:16-alpine`), com os dados guardados no volume
`algo_dados_postgres`. `algo-online` só arranca depois de `bd` reportar
saudável (`depends_on: condition: service_healthy`).

### Sem docker compose

```bash
# a partir da pasta que contém algo_lang/, alguem/ E online/ como
# irmãs -- NÃO a partir de dentro de online/, porque o Dockerfile
# precisa de copiar as três (o contexto de build tem de as conter)
docker build -f online/Dockerfile -t algo-online .

docker run -d -p 8000:8000 \
  -e ONLINE_CHAVE_CIFRAGEM="<a tua chave gerada>" \
  -e ONLINE_CHAVE_SESSAO="<a tua outra chave gerada>" \
  -e ONLINE_DATABASE_URL="postgresql://utilizador:password@host:5432/base_de_dados" \
  --pids-limit=512 \
  algo-online
```

Sem `docker-compose.yml`, precisas de um PostgreSQL próprio acessível
(container, serviço gerido, ou instalação local) -- este comando não
sobe nenhum.

`--pids-limit` (ou `pids_limit:` no `docker-compose.yml`) limita o
número de processos dentro do contentor via cgroups -- isolado por
contentor, e por isso o mecanismo correto para conter um fork-bomb
vindo de um programa de estudante (ON-04). `online/executor.py` já
limita CPU/memória/descritores de ficheiro por execução via
`RLIMIT_CPU`/`RLIMIT_AS`/`RLIMIT_NOFILE`, mas deliberadamente não usa
`RLIMIT_NPROC` para processos -- esse é um contador por UID do próprio
kernel, partilhado com processos fora do contentor, e confirmado pouco
fiável em testes (tanto afetado por processos não relacionados como,
nalguns motores de contentores, nem sequer aplicado).

A imagem já traz o `graphviz` e o `postgresql-client` (para o
`pg_dump` usado no backup, ver `/api/admin/bd`) incluídos — nada a
instalar à parte na máquina que corre o contentor. Os dados (contas,
grupos, credenciais, registo de atividade) vivem no PostgreSQL do
serviço `bd`, não num ficheiro dentro do contentor `algo-online`.

## Como arrancar (sem Docker)

```bash
pip install -r requerimentos.txt --break-system-packages

# gerar as duas chaves obrigatórias (uma vez, guardar em segurança)
python3 -c "from cifragem import gerar_chave_nova; print(gerar_chave_nova())"
python3 -c "import secrets; print(secrets.token_hex(32))"

export ONLINE_CHAVE_CIFRAGEM="<a chave gerada acima>"
export ONLINE_CHAVE_SESSAO="<a segunda chave gerada acima>"
export ONLINE_DATABASE_URL="postgresql://utilizador:password@localhost:5432/algo_online"

uvicorn main:app --reload --ws-max-size 2000000
```

Precisas de um PostgreSQL a correr e acessível nessa DSN antes de
arrancar (ex: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=... postgres:16-alpine`
para desenvolvimento local). O esquema é criado automaticamente no
arranque (`bd.preparar_bd()`, idempotente).

O servidor recusa-se a arrancar sem `ONLINE_CHAVE_CIFRAGEM`/
`ONLINE_CHAVE_SESSAO` -- de propósito, para nunca gerar uma chave nova
sozinho (isso tornaria todas as credenciais já guardadas ilegíveis no
reinício seguinte). Sem `ONLINE_DATABASE_URL`, falha já no arranque do
ciclo de vida da aplicação (`bd.preparar_bd()`), com um erro claro.

`ONLINE_CHAVE_CIFRAGEM` tem sempre de vir do comando acima
(`gerar_chave_nova()`) -- nunca escrita à mão. Uma chave pouco
aleatória (ON-10) é rejeitada no arranque com um erro claro.

Variáveis de ambiente opcionais (ON-25/ON-35): `ONLINE_SESSAO_MAX_AGE_SEGUNDOS`
(omissão: 14 dias) controla há quanto tempo uma sessão fica válida;
`ONLINE_HTTPS_ONLY=1` (omissão: desligado, para não partir o
desenvolvimento local sem TLS) faz o cookie de sessão nunca ser
enviado em texto simples -- definir sempre que o serviço estiver atrás
de HTTPS em produção.

## Testes

```bash
cd online
# precisa de um PostgreSQL de teste acessível -- por omissão
# postgresql://postgres:teste@localhost:5433/algo_teste (ver
# tests/conftest.py), configurável via ONLINE_TEST_DATABASE_URL
python3 -m pytest -v
```

Isolamento: uma base de dados de teste dedicada (nunca a de produção),
com todas as tabelas esvaziadas (`TRUNCATE ... RESTART IDENTITY
CASCADE`) antes de cada teste. A pasta de logs do Alguem continua
redirigida por `monkeypatch` (mesma técnica de sempre) para uma pasta
temporária por teste — nenhum teste escreve na pasta `alguem/logs/`
real. O teste do backup (`/api/admin/bd`, via `pg_dump`) é ignorado
automaticamente se `pg_dump` não estiver no `PATH` do ambiente onde os
testes correm.

## Correções recentes (feedback de uso real)

- **Erro 500 nas Definições do LLM**: causa real era `ONLINE_CHAVE_CIFRAGEM`
  só ser validada no primeiro uso, não ao arrancar -- corrigido para
  falhar cedo e claramente. Acrescentada também uma rede de segurança
  global: nenhum erro inesperado volta a devolver texto simples em vez
  de JSON (o sintoma reportado, "Unexpected token... is not valid
  JSON", era exatamente isto).
- **Separadores de ficheiros**: o botão "+ novo ficheiro" já não fica
  dentro da área com scroll -- fica sempre fixo e visível, só a lista
  de separadores desliza.
- **Painéis redimensionáveis**: dois divisores arrastáveis entre os 3
  painéis, com largura mínima.
- **Fluxograma de bibliotecas**: agora dá para escolher ver o
  fluxograma de qualquer função/procedimento, incluindo os que vêm de
  ficheiros incluídos via `incluir`, não só o programa principal.
- **Rasto: já não tem navegação passo-a-passo própria**. Gera o
  ficheiro `..._trace.json` (exatamente igual ao que `algo executa
  --json` produz, sem nenhum filtro), dá para descarregar, e há uma
  ligação para abrir o visualizador em `/estatico/visualizador/`
  (`online/estatico/visualizador/algo-trace-viewer.html` -- já não
  existe cópia nenhuma fora do online). Decisão deliberada:
  reaproveitar uma ferramenta já testada em vez de manter uma segunda
  implementação de navegação de passos só para a versão web.

## O que falta (honestidade, não lista de vergonha)

- **O servidor foi confirmado a correr a sério** (não só `TestClient`)
  — arranquei um `uvicorn` real várias vezes, testando com pedidos
  HTTP e WebSocket reais: registo, sessão por cookie, ficheiros
  estáticos, execução interativa, e `incluir` entre vários ficheiros
  a resolver corretamente através de um WebSocket real. **O frontend
  em si (o HTML/CSS/JS a correr num browser) continua por confirmar
  visualmente** — só testei a API por trás dele.
- **O `Dockerfile` nunca foi construído nem corrido a sério** — este
  ambiente não tem acesso a Docker; foi revisto manualmente, linha a
  linha, não testado de facto (ver a nota na secção Docker acima).
- **Sem HTTPS configurado** — `https_only=False` no cookie de sessão é
  aceitável em desenvolvimento local, não em produção.
- **Sem limite de pedidos geral** (*rate limiting*) — um estudante
  podia, em teoria, abrir execuções repetidamente sem controlo. Existe
  rate limiting específico só em dois pontos: login por conta (ON-11)
  e tentativas de registo com código de grupo errado, por IP
  (`limitador_registo.py`).
- **Rasto (tracer) só com entradas antecipadas** — decisão explícita
  de âmbito: `ler()` interativo a meio de um rasto (ao contrário da
  execução normal, que já é interativa) fica para uma versão seguinte.
- **Isolamento por processo, não por contentor** — suficiente para uma
  turma confiável numa VM só, não para um serviço público hostil.
