# Algo Online

Versão web do Algo + Alguem: vários estudantes, cada um com a sua
conta, código isolado por processo, e o seu próprio fornecedor de LLM.
Construído deliberadamente sem grandes *frameworks* — FastAPI, SQLite
puro (sem ORM), sem sistema de *templates* (HTML servido tal e qual).

**Estado**: primeira versão, testada (83 testes), nunca testada num
browser real nem em produção. Ver "O que falta" no fim.

## Arquitetura

```
online/
├── Dockerfile
├── docker-compose.yml
├── .env.exemplo          # copiar para .env e preencher
├── main.py            # aplicação FastAPI -- rotas HTTP + os 2 WebSockets
├── bd.py               # esquema SQLite (sem ORM)
├── autenticacao.py      # registo/login, hash de password (bcrypt)
├── credenciais.py        # credencial de LLM por conta, cifrada em repouso
├── cifragem.py            # cifragem simétrica (Fernet) das chaves de API
├── executor.py             # execução assíncrona e interativa de programas Algo
├── alguem_ponte.py          # constrói um Alguem a partir da credencial da BD
├── modo_codemirror.py    # gera o realce de sintaxe a partir do compilador
├── estatico/                 # HTML/CSS/JS -- sem framework de frontend
│   ├── vendor/codemirror/      # CodeMirror auto-hospedado (não depende de CDN)
│   └── visualizador/            # cópia do visualizador de rasto autónomo (não alterado)
└── tests/                     # 83 testes (pytest)
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
  CodeMirror é servido localmente (descarregado uma vez via `npm`,
  não em tempo real do browser do estudante), e o "modo" da linguagem
  é gerado dinamicamente a partir das palavras-chave reais do
  compilador (`/modo-algo.js`) -- nunca desatualiza.
- **Identificador pseudónimo separado da conta**: os logs do Alguem
  (ver `alguem/README.md`) usam um UUID gerado no registo, nunca o
  `id` da conta nem o email -- mantém a mesma filosofia de privacidade
  já estabelecida no resto do projeto, mesmo havendo agora contas
  reais com login.
- **Cada estudante traz a sua própria chave de LLM**, cifrada em
  repouso (Fernet) com uma chave de cifragem que nunca fica na base de
  dados nem no código.

## Docker

### Com docker compose (mais simples)

```bash
cd online
cp .env.exemplo .env
# edita o .env e preenche as duas chaves (instruções lá dentro)
docker compose up -d --build
```

### Sem docker compose

```bash
# a partir da pasta que contém algo_lang/, alguem/ E online/ como
# irmãs -- NÃO a partir de dentro de online/, porque o Dockerfile
# precisa de copiar as três (o contexto de build tem de as conter)
docker build -f online/Dockerfile -t algo-online .

docker run -d -p 8000:8000 \
  -e ONLINE_CHAVE_CIFRAGEM="<a tua chave gerada>" \
  -e ONLINE_CHAVE_SESSAO="<a tua outra chave gerada>" \
  -v algo_dados:/app/online/dados \
  algo-online
```

A imagem já traz o `graphviz` incluído — é o que resolve o fluxograma
sem precisar de nada instalado à parte na máquina que corre o
contentor. O volume `algo_dados` mantém a base de dados (contas,
credenciais) entre reinícios do contentor.

> **Nota de honestidade**: este ambiente de desenvolvimento não tem
> acesso ao Docker (sem *daemon* disponível), por isso **nunca
> consegui construir nem correr a imagem, nem o `docker compose`, a
> sério** — revi tudo linha a linha manualmente (caminhos, ordem de
> cópia, onde cada coisa fica montada, e validei a sintaxe YAML do
> `docker-compose.yml`), mas a primeira confirmação real de que builda
> e arranca tem de ser feita por ti.

## Como arrancar (sem Docker)

```bash
pip install -r requerimentos.txt --break-system-packages

# gerar as duas chaves obrigatórias (uma vez, guardar em segurança)
python3 -c "from cifragem import gerar_chave_nova; print(gerar_chave_nova())"
python3 -c "import secrets; print(secrets.token_hex(32))"

export ONLINE_CHAVE_CIFRAGEM="<a chave gerada acima>"
export ONLINE_CHAVE_SESSAO="<a segunda chave gerada acima>"

uvicorn main:app --reload
```

O servidor recusa-se a arrancar sem as duas variáveis de ambiente --
de propósito, para nunca gerar uma chave nova sozinho (isso tornaria
todas as credenciais já guardadas ilegíveis no reinício seguinte).

## Testes

```bash
cd online
python3 -m pytest -v
```

Isolamento sem variáveis de ambiente (mesma técnica já usada em
`alguem/tests/`): base de dados e pasta de logs do Alguem redirigidas
por `monkeypatch`, numa pasta temporária por teste — nenhum teste
escreve na base de dados real nem na pasta `alguem/logs/` real.

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
  ligação para abrir o visualizador autónomo já existente
  (`visualizador/algo-trace-viewer.html`, agora também servido pelo
  próprio serviço online em `/estatico/visualizador/`). Decisão
  deliberada: reaproveitar uma ferramenta já testada em vez de manter
  uma segunda implementação de navegação de passos só para a versão
  web.

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
- **Sem limite de pedidos** (*rate limiting*) — um estudante podia, em
  teoria, abrir execuções repetidamente sem controlo.
- **Rasto (tracer) só com entradas antecipadas** — decisão explícita
  de âmbito: `ler()` interativo a meio de um rasto (ao contrário da
  execução normal, que já é interativa) fica para uma versão seguinte.
- **Fluxograma só do programa principal** — não gera ainda um
  fluxograma por função/procedimento à parte, ao contrário da
  ferramenta de linha de comandos.
- **Isolamento por processo, não por contentor** — suficiente para uma
  turma confiável numa VM só, não para um serviço público hostil.
