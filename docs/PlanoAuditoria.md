# Plano de auditoria — compilador, documentos e online

Âmbito: `algo_lang/` (compilador), `docs/` + `context/` + `CLAUDE.md`
(documentação), `online/` (serviço web). **`alguem/` fica de fora**, por
pedido explícito.

Alternativa a uma reescrita ("v2"): auditoria incremental por execução
real, não por leitura/suposição. **Um único documento para tudo** — plano
e achados das três frentes, incluindo os achados que antes viviam em
`docs/manual/ACHADOS.md` (agora fundidos aqui, esse ficheiro deixou de
existir). Nada de achados espalhados por mais nenhum sítio.

## Metodologia

- Cada achado é **confirmado a correr o código real** (compilar/executar
  um programa, correr um teste, chamar um endpoint) antes de ser
  registado na secção "Achados" abaixo — nunca só inferido do código.
- Estado por achado: 🟢 confirmado só por leitura de código (baixo risco)
  · 🟡 confirmado a correr · ⚪ por decidir (observação, pode ser
  intencional — decisão do maintainer, não minha).
- Achados ficam registados, não corrigidos em silêncio — corrigir é um
  passo explícito e separado, sempre com a suite completa corrida
  antes/depois para confirmar zero regressão nova.

## Estado de partida (levantado em 2026-08-28)

- **Compilador**: os 10 capítulos do manual já foram auditados (6 achados
  já corrigidos e removidos deste documento — ver nota no início da
  secção "Achados"). A mudança de semântica `estrutura`/`vetor` de tipo
  por valor para tipo por referência (`AUDITORIA_2026-08-19 Fase 1.1`)
  já foi confirmada e commitada (commit `b75190e`). Não cobre a camada
  de ferramentas (`cli.py`, `linter.py`, `flowchart.py`, `tracer.py`) nem
  a estrutura interna do código. `pytest algo_lang/tests/ -m "not slow"`:
  911 passam, 44 falham (contagem subiu de 908 para 911 com os testes de
  regressão da Fase 2) — confirmadas como falhas de **ambiente** (testes
  que invocam o comando `algo` diretamente via subprocesso, fora do PATH
  neste ambiente), não bugs — ver achado 1.
- **Documentos**: `docs/bin/` (citado em `context/project-overview.md`
  como existente) foi apagado deliberadamente no commit `ca1f1a4`
  (2026-08-24) junto com o manual antigo em `.docx`, substituído por
  `docs/manual/` — referência já corrigida. Fora isso, nunca auditados
  como frente própria.
- **Online**: nunca auditado desta forma. 302 testes próprios
  (`online/tests/`), 3043 linhas em `online/*.py` (`main.py` 971L,
  `executor.py` 632L são os dois maiores). Superfície sensível por
  natureza (autenticação, execução de código de estudantes, credenciais
  LLM cifradas) — candidata a mais atenção por linha do que o resto.

## Fases

### Fase 0 — Baseline
`pytest algo_lang/tests/ -m "not slow"` e `cd online && pytest -v`;
registar passa/falha de cada uma como baseline para comparar depois de
cada fase seguinte.

### Fase 1 — ~~Compilador: fechar a Fase 1.1 já em curso~~ ✅ feito
`estrutura`/`vetor` por referência confirmado como design final e
commitado (`b75190e`).

### Fase 2 — Compilador: camada de ferramentas — ✅ feito
Auditar por execução `cli.py`, `linter.py`, `flowchart.py`, `tracer.py`
— nunca cobertos pela auditoria do manual. Exercitar caminhos principais
e de erro contra o compilador real (avisos do linter, fluxogramas com
estruturas de controlo aninhadas, trace de erro em runtime, `cli.py` com
flags inválidas/combinações raras). Também o sítio certo para marcar as
44 falhas de ambiente com um marker pytest dedicado, se houver tempo —
feito na Fase 5 (marker `requer_algo_no_path`), não aqui.

Já cobertos e corrigidos (confirmados por execução, suite completa
verde antes/depois): `tracer.py` — `_valor_serializavel` rebentava com
"recursão infinita" num programa válido com um ciclo real entre
`estrutura`s (consequência da Fase 1.1, ciclos passaram a ser
possíveis); corrigido com deteção de ciclo por caminho (`<ciclo>` em
vez de recursar), teste de regressão em `test_tracer.py`.
`linter.py` — `_verificar_atribuicao_a_parametro_por_valor` avisava
(errado) que mutar um campo/elemento de um parâmetro `estrutura`/vetor
sem `ref` não era visto por quem chamou; corrigido para só avisar
quando o PRÓPRIO parâmetro é reatribuído (continua correto), testes
atualizados em `test_linter.py`. `flowchart.py` — testado com ciclos
aninhados + `sair`/`continuar`, sem problemas encontrados (a
duplicação de aresta a seguir a `sair`/`retornar` é intencional, já
documentada no código). `cli.py` (consola interativa) — uma linha como
`executa -h` mostrava a ajuda completa do argparse e LOGO A SEGUIR a
dica genérica "escreve 'ajuda'..." (a guarda só verificava
`comando in ("-h", "--help")`, não apanhava `-h` como flag de um
subcomando); corrigido para verificar `-h`/`--help` em qualquer posição
da linha, teste de regressão em `test_consola.py`.

Cobertura adicional (sem correções, nada encontrado): mais combinações
de flags inválidas em `cli.py` na consola — `--entradas`/`--formato`/
`--funcao` sem valor, `--limite-cpu abc` (tipo inválido), `--formato
bogus` (choice inválida), flags booleanas encadeadas
(`--mostrar-python --debug`), e o caso em que o valor de uma flag é o
nome de outra flag conhecida (`--funcao --formato svg`, heurística de
`_linha_com_ficheiro_por_omissao` diverge do argparse mas ambos
terminam no mesmo erro limpo "expected one argument", sem crash nem
substituição silenciosa errada de ficheiro). `flowchart.py` — testado
com 3 níveis de ciclos aninhados (`para` › `enquanto` › `para`) mais
`escolher` com `sair`/`continuar` dentro, confirmando por inspeção das
arestas geradas que cada `sair`/`continuar` aponta sempre para o ciclo
correto (o mais interior), mesmo atravessando o `escolher` (que não
empilha em `pilha_ciclos`, de propósito — `sair`/`continuar` nunca
visam um `escolher` sozinho, confirmado em `semantics.py:1216-1226`).

### Fase 3 — Documentos: consistência e referências — ✅ feito
Verificar que `docs/`, `context/project-overview.md` e `CLAUDE.md`
descrevem o repositório como ele é hoje — não como era (a referência a
`docs/bin/` já foi corrigida, ver Estado de partida). Seguir cada
referência a ficheiro/comando/flag citada nesses documentos; confirmar
`ManualCLI.md` contra as flags reais de `cli.py --help`; verificar se
`docs/manual/00-Indice.md` continua correto depois da Fase 1.

Já cobertos e corrigidos: duas referências a `docs/bin/` (apagado no
commit `ca1f1a4`) que ainda sobreviviam em `docs/manual/00-Indice.md`
(linhas 6 e 47) — a de `context/project-overview.md` já tinha sido
corrigida antes; `docs/ManualCLI.md` §3 confirmado contra `algo executa
--help`/`algo fluxograma --help`/`algo verifica --help` reais, faltavam
`--limite-cpu`/`--max-passos`/`--limite-tempo` na tabela de `executa`
(mencionadas só na §6) — adicionadas. `context/project-overview.md`
verificado à parte por leitura+grep (não corrida): `gerador_base.py`/
`GeradorCodigoBase`/`GeradorCodigo` (subclasse única), ausência de
`alguem/cli.py`, os 7 ficheiros de `fornecedores/` +
`_base_openai_compativel.py` partilhado, `executor.py` usa
`asyncio.create_subprocess_exec` para código de estudante (o único
`subprocess.run` restante é para o `dot` do graphviz, já corrido em
threadpool via `run_in_threadpool` — achado `ON-08` de uma auditoria
anterior, comentário próprio no código, não é uma regressão), os dois
ficheiros do visualizador (`.html`+`.jsx`), `main.py` com
`@app.exception_handler(Exception)` global, nomes das pastas em
`exemplos/` batem certo com `docs/manual/00-Indice.md`. Confirmado
também que os capítulos 5/6/7 do manual (`Vetores-e-Matrizes`,
`Funcoes-e-Procedimentos`, `Estruturas`) já descrevem a semântica por
referência de `vetor`/`estrutura` da Fase 1.1 — foram escritos depois
dessa mudança, nada a corrigir aí. Contagens de testes desatualizadas
encontradas e corrigidas a correr `pytest --collect-only -q` em cada
suite: `README.md` e `context/project-overview.md` diziam 792/173/83
testes para `algo_lang`/`alguem`/`online`; reais são 959/215/302 (a de
`online` estava a mais de 3,5x da realidade) — sem verificação
automática, estes números voltarão a ficar desatualizados à medida que
as suites crescem. `CLAUDE.md` em si verificado link a link (grep+leitura, não corrida):
`apoio.py:compilar/executar`, `modo_codemirror.py`, `grupos.py`,
`autenticacao.tornar_admin`/`remover_admin`, `atividade.py:log_atividade`,
`credenciais.py`/`cifragem.py:gerar_chave_nova` — todos existem como
descrito. Os 10 capítulos do manual lidos por inteiro, um a um (tom,
terminologia, referências cruzadas entre capítulos, estrutura):
consistentes entre si, sem inglês a escapar para o meio do texto em
português, todas as referências cruzadas (`capítulo N`/`N.M`) apontam
para secções que existem mesmo. Um achado: `01-Introducao-e-Tipos.md`
tinha "exactamente" (grafia pré-acordo ortográfico) numa frase, único
sítio em todo o manual — o resto usa sempre "exatamente" — corrigido.
Dois exemplos "completo" (capítulo 7, `CatalogoDeLivros`; capítulo 2,
`div`/`mod` com negativos e `2^3^2`) recorridos contra o compilador
real para confirmar que a saída documentada ainda bate certo — bate.

### Fase 4 — Online: auditoria por execução — ✅ feito
Primeira auditoria desta frente. Prioridade a `executor.py` (isolamento
de subprocessos, limites de recursos), `autenticacao.py`/
`credenciais.py`/`cifragem.py` (sessões, cifragem em repouso),
`grupos.py` (bloqueio de grupo desativado), `main.py` (handler de
exceção global devolve sempre JSON). Correr a suite própria
(`cd online && pytest -v`), depois exercitar manualmente os fluxos
principais e de erro contra um servidor local (registo, login, execução
de um programa ALGO com erro, pedido sem autenticação, grupo
desativado). Precisa de `ONLINE_CHAVE_CIFRAGEM`/`ONLINE_CHAVE_SESSAO`
(ver `context/project-overview.md` para gerar).

Bloqueio de ambiente encontrado e resolvido: `online/tests/conftest.py`
exige um Postgres real em `ONLINE_TEST_DATABASE_URL` (por omissão
`localhost:5433`), não disponível por omissão neste ambiente — Docker
Desktop estava instalado mas não corria. Arrancado manualmente +
container `postgres:16-alpine` descartável na mesma porta/credenciais
por omissão para desbloquear esta fase (não faz parte do repositório,
é só infraestrutura de teste local).

Baseline (`cd online && pytest -v`): 295 passaram, 7 skipped, 0 falhas
— suite própria limpa, ao contrário do compilador (achado 1). Lido
`executor.py` inteiro (isolamento por subprocesso via
`asyncio.create_subprocess_exec`, limites de CPU/memória/descritores
via `resource.setrlimit` dentro do processo filho — nunca
`preexec_fn`, ambiente do subprocesso reduzido ao mínimo em
`_env_minimo()`, validação de caminhos em `_validar_nome_ficheiro`/
`_resolver_inclusoes` contra passeio de diretório, sanitização de SVG
em `_sanitizar_svg`) — nada de novo encontrado, já bem coberto por
achados `ON-XX` de auditorias anteriores citados nos próprios
comentários. `grupos.py`, `cifragem.py` e o fluxo de bloqueio de grupo
desativado em `autenticacao.py` lidos por inteiro.

Um achado encontrado e corrigido, com teste de regressão e suite
completa corrida antes/depois (295→296 a passar, 0 falhas nos dois
casos): o "bootstrap tardio" de admin em `autenticacao.autenticar()`
(ver histórico do achado 3, já removido daqui — conta cujo email só
entra em `ONLINE_EMAIL_ADMIN` depois de já existir e já pertencer a um
grupo entretanto desativado conseguia fazer login e ser promovida
nessa entrada, contornando o bloqueio de grupo desativado que o próprio
docstring da função promete "sem exceção"). Corrigido movendo a
verificação de `grupo_ativo` para dentro do próprio ramo de bootstrap,
antes de promover/devolver — teste `test_bootstrap_tardio_ainda_e_
bloqueado_por_grupo_desativado` em `test_autenticacao_e_credenciais.py`
reproduz o bug antes da correção (falhava com "DID NOT RAISE") e
confirma-o corrigido depois.

Lidos por inteiro (sem novos achados): `bd.py` (esquema idempotente,
pool de ligações, `gerar_backup_sql` via `pg_dump` em subprocesso
assíncrono, password nunca em argumento de linha de comandos),
`atividade.py`/`relatorios.py` (SQL sempre parametrizado, mesmo com
cláusulas `WHERE` construídas dinamicamente — os valores nunca são
interpolados, só os nomes de coluna fixos).

Servidor local real (`uvicorn`) arrancado contra o Postgres de teste,
exercitado com pedidos HTTP/WebSocket reais (não só via `TestClient`
em processo, como os 296 testes já fazem):
- `/api/eu` sem sessão → 401 JSON limpo (`{"detail": "Não autenticado."}`).
- corpo JSON malformado em `/api/registar` → 400 JSON limpo, nunca uma
  página de erro HTML.
- corpo acima de `LIMITE_TAMANHO_CORPO_BYTES` → 413 JSON limpo.
- registo válido → cookie de sessão real, `/api/eu` autenticado a
  seguir devolve o id correto.
- login com password errada e com email inexistente → mesma mensagem
  ("Email ou password incorretos."), confirmando por fora o que
  `autenticar()` já promete no docstring.
- `/ws/executar` de ponta a ponta com um programa real: compila,
  executa em subprocesso, `ler()` interativo a meio (entrada enviada
  pelo WebSocket chega ao stdin do processo), saída relançada linha a
  linha, `fim` com o código de saída correto. Repetido com um programa
  que dá erro em runtime (divisão por zero) — mensagem de erro chega
  como `saida` normal, `fim` com `codigo_saida: 1`. Relevante por
  correr **neste** ambiente Windows (não o Linux de produção): confirma
  que o caminho sem `resource.setrlimit` (só POSIX, ver comentários
  `pragma: no cover` em `executor.py`) funciona mesmo assim de ponta a
  ponta, não só em teoria.

Restante do servidor real também exercitado, sem novos achados:
- `/api/fluxograma` — programa com uma função, SVG devolvido com as
  rotinas corretas (`["Principal", "dobro"]`).
- `/api/linter` — aviso de variável nunca usada devolvido corretamente.
- `/api/rasto` — entradas antecipadas (`ler()` sem interação), trace e
  `consolaFinal` corretos.
- `/api/projeto/download` + `/api/projeto/upload` — round-trip .zip
  preserva o conteúdo; um .zip com um nome `../../../evil.algo`
  (path traversal) é corretamente rejeitado por `projeto._validar_nome`
  (lido antes: nunca escreve em disco com o nome do .zip, só devolve
  dicts em memória — path traversal nem seria possível mesmo sem essa
  validação, é defesa em profundidade).
- `/api/admin/pendentes` (rota admin-only) — 403 com sessão de conta
  normal, 401 sem sessão nenhuma — controlo de acesso confirmado por
  fora, não só pelos testes em processo.
- `/ws/alguem` — devolve sempre "O Alguem está temporariamente
  desativado" (`ALGUEM_ATIVO = False` em `main.py:745`, comentado como
  `TEMP` enquanto o editor é corrigido — decisão do maintainer já
  documentada no código, não um achado). Isto significa que os ramos de
  "não autenticado"/"sem credencial configurada" não foram exercitados
  por fora (ficam cobertos só pelos testes em processo) enquanto a
  flag continuar `False`. Sem acesso de rede neste ambiente para testar
  uma conversa real com um fornecedor de LLM (ver `CLAUDE.md`).

### Fase 5 — Regressão final — ✅ feito
`pytest algo_lang/tests/ -v` completo (incluindo `slow`) e
`cd online && pytest -v` completo, uma vez no fim. Critério de sucesso:
ambas 100% verdes (as 44 falhas de ambiente já não existem se a Fase 2
as tiver isolado com marker).

Primeira corrida (antes do marker): `algo_lang/tests/` completo
(incluindo `slow`) — 47 falham, 911 passam, 1 skipped. As 47 eram as
mesmas 44 do achado 1 original mais 3 só visíveis com `slow` incluído
(`test_algo_sh.py`) — confirmado por nome, nenhuma era um caso novo.

Marker pytest `requer_algo_no_path` implementado: registado em
`pyproject.toml` (`[tool.pytest.ini_options].markers`, junto de
`slow`), com o hook em `algo_lang/tests/conftest.py`
(`pytest_collection_modifyitems`) que só adiciona `skip` aos testes
marcados quando `shutil.which("algo") is None` — nunca aos não
marcados, e nunca quando `algo` está mesmo no PATH (confirmado nos dois
sentidos: com a função do hook chamada isoladamente com
`shutil.which` gorado, e de ponta a ponta com um `algo.bat` falso a
sério no PATH do Windows — os testes voltam a correr, e falham a
sério, em vez de serem saltados). Aplicado aos 42 testes confirmados
como `FileNotFoundError` por `algo` não estar no PATH (as 44 do achado
1 original MENOS 2 de `test_algo_sh.py` que afinal falhavam por uma
razão diferente — ver achado 1 revisto abaixo) em
`test_consola.py`/`test_correcoes_auditoria.py`/`test_estruturas.py`/
`test_fluxogramas.py`/`test_linter.py`/`test_tracer.py`.

Segunda corrida (com o marker): `algo_lang/tests/` completo — **5
falham** (só `test_algo_sh.py`, razão diferente de "algo fora do
PATH" — ver achado 1 revisto), 911 passam, 43 skipped.

Achado 1 revisto também fechado: as 5 falhas de `test_algo_sh.py`
confirmaram-se **não ser bugs** — o próprio docstring do módulo já
dizia que só faz sentido correr em POSIX (`algo.bat`, o equivalente
para Windows, é só revisto manualmente); 3 delas invocam `algo.sh`
como processo, o que o Windows não sabe interpretar sem um shebang
(`OSError: [WinError 193]`), as outras 2 criam symlinks num PATH
falso, privilégio que esta conta Windows não tem (`OSError: [WinError
1314]`). Adicionado `@pytest.mark.skipif(os.name != "posix", ...)` só
a essas 5 (não ao módulo inteiro — `test_algo_command_e_identico_ao_
algo_sh` não usa subprocesso nenhum e já passava em Windows, ficou
de fora do skip). `algo_lang/tests/`: **911 passam, 0 falham, 48
skipped** — critério de sucesso desta fase agora cumprido por
completo, não só na prática.

`cd online && pytest -v` completo — 298 passam, 7 skipped, 0 falham.

## Achados

Só os achados ainda **abertos** (por corrigir ou por decidir) ficam
aqui. Os já corrigidos foram removidos deste documento depois de
confirmados fechados — o histórico completo (11 achados do manual, 6
deles corrigidos) fica em `git log`/`git show HEAD:docs/manual/ACHADOS.md`
se algum dia for preciso consultá-lo, mas deixa de viver neste
documento vivo.

#### 2. [Online] `_validar_host_ollama` (ON-14) é contornável por DNS rebinding — 🟡 mitigado (parcial), correção completa fora de âmbito

`online/credenciais.py:_validar_host_ollama` resolve o hostname do
`host` do Ollama (escolhido pelo estudante) e rejeita-o se algum IP
resolvido for privado/loopback/link-local/reservado/multicast — mas só
corria uma vez, em `guardar_credencial`, ao **guardar** a credencial. A
cadeia até ao pedido HTTP real não revalidava nada: o `host` guardado
saía da BD tal e qual em `credenciais.obter_credencial`
(`online/credenciais.py:97-112`), passava sem validação nova por
`online/alguem_ponte.py` para `FornecedorOllama.__init__`
(`alguem/fornecedores/ollama.py:22-24`, só faz `.rstrip("/")`), e o
pedido real usa `urllib.request.urlopen` sobre esse URL em
`alguem/fornecedores/base.py:pedir_json` (linha 78) — que faz a sua
PRÓPRIA resolução DNS, independente da que `_validar_host_ollama` já
fez. Confirmado a correr: `_validar_host_ollama` bloqueia
`http://127.0.0.1:...` corretamente, mas construir um
`FornecedorOllama(host="http://127.0.0.1:<porta>")` diretamente e
chamar `.responder(...)` contactava esse serviço em loopback sem
qualquer resistência. Um estudante que controle um domínio com TTL
baixo podia assim apontá-lo para um IP público ao guardar a credencial
(passa a validação) e depois para `127.0.0.1`/um IP interno antes de o
Alguem ser efetivamente usado (SSRF por DNS rebinding, contorna o
ON-14 documentado no próprio código).

**Mitigado** (não corrigido por completo — ver nota de âmbito abaixo):
`online/alguem_ponte.py:construir_alguem` volta a chamar
`_validar_host_ollama(credencial.host)` imediatamente antes de
construir o fornecedor, revalidando a cada conversa nova em vez de só
confiar na validação feita ao guardar. Confirmado a correr com dois
testes novos em `online/tests/test_alguem_ponte.py`
(`test_construir_alguem_rejeita_host_que_passou_a_apontar_para_interno`
e `test_construir_alguem_aceita_host_ollama_ainda_valido`) — o primeiro
falhava com "DID NOT RAISE" antes desta alteração (confirmado por
`git stash` da alteração e correr o teste), passa depois. Isto encurta
muito a janela de exploração (de "válida enquanto a credencial existir"
para "válida durante uma única troca de mensagens"), mas **não fecha o
buraco por completo** — continua a existir uma janela entre esta
revalidação e o pedido HTTP real em `pedir_json`, e a correção
definitiva (resolver e fixar o IP no momento do próprio pedido) só
pode viver em `alguem/fornecedores/base.py:pedir_json`, partilhado
pelos 7 fornecedores. **Por pedido explícito, `alguem/` fica fora do
âmbito desta auditoria** — por isso essa correção completa não foi
feita aqui, só a mitigação possível do lado de `online/`.

## Fora de âmbito

- `alguem/` — excluído por pedido explícito.
- Reescrita ("v2") de qualquer um dos três projetos.
- Novas funcionalidades (linguagem, documentação ou serviço online).
