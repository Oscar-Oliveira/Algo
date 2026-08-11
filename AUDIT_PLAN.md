# Project Audit and Correction Plan

*Gerado por auditoria de leitura integral de `algo_lang/`, `alguem/` e `online/`, incluindo re-verificação de uma auditoria anterior (108 itens) contra o estado atual do código, mais três passes novas (arquitetura, UX, alinhamento com o objetivo pedagógico). Nenhum ficheiro de código foi alterado nesta tarefa.*

## 1. Executive Summary

O projeto está funcionalmente maduro nos três subsistemas (compilador, tutor, web app), com pontos fortes genuínos: as mensagens de erro de compilação (léxico/sintático/semântico) são de qualidade acima da média para um público iniciante, a descoberta de ferramentas pedagógicas (fluxograma, rasto, linter) é bem exposta tanto na CLI como na web, e o design do "guardião" pedagógico mostra consciência incomum das suas próprias limitações (comentado explicitamente no código).

Dito isto, uma auditoria de segurança anterior identificou 108 problemas e **101 continuam por corrigir**, incluindo todos os 10 pontos de maior impacto então identificados — RCE via `afirmar`, leitura/escrita arbitrária de ficheiros (compilador, tutor e serviço web), SSRF via credencial Ollama, bloqueios síncronos que travam o servidor inteiro, contentor a correr como root, segredos herdados pelo subprocesso do estudante, e o guardião pedagógico sem tratamento de exceções nem comparação exata de categorias. Nenhum destes foi corrigido desde então.

A esta base juntam-se **39 findings novos** desta auditoria: 13 de arquitetura/qualidade de código, 19 de UX (dirigida a estudantes principiantes) e 7 de alinhamento com o objetivo pedagógico — dos quais o mais grave é que o `system_prompt` do tutor só proíbe explicitamente código **ALGO**, não Python, deixando uma via directa para obter a solução no próprio Python que o compilador gera (GOAL-01), o que ataca diretamente a promessa central do projeto ("nunca resolve o exercício pelo aluno").

**Total: 117 findings ativos** (bugs, segurança, arquitetura, UX, alinhamento pedagógico, funcionalidades pedidas) + **26 oportunidades de melhoria** não urgentes, organizados em **9 fases** de correção (Fase 0 a Fase 8), ordenadas por dependência e risco, começando pela contenção dos vetores de execução de código e acesso a ficheiros arbitrário.

Nada neste documento foi implementado — é um mapa para execução faseada futura.

## 2. Project Objective

Per `CLAUDE.md` e `context/project-overview.md`: **Algo** é uma linguagem de pseudocódigo em português (compila para Python) para ensinar programação; **Alguem** é um tutor Socrático baseado em LLM que apoia o estudante **sem nunca resolver o exercício por ele**. Ambos partilham o mesmo compilador (não modificado) entre uma CLI local (`algo_lang/`) e um serviço web multi-utilizador (`online/`, FastAPI), pensado para uma sala de aula confiável (não é um sandbox contra utilizadores hostis).

Critérios usados para avaliar alinhamento nesta auditoria:
- O tutor **nunca** deve produzir uma solução completa, em ALGO ou em qualquer outra linguagem, mesmo por decomposição do pedido em vários turnos.
- As ferramentas pedagógicas (linter, fluxograma, rasto) devem ser descobríveis e úteis a um estudante iniciante, sem exigir conhecimento de implementação.
- O modelo de ameaça assumido é "sala de aula confiável, não sandbox contra hostilidade" — mas mesmo assim, escrita/leitura arbitrária de ficheiros no servidor e RCE ultrapassam esse modelo de ameaça, porque afetam **outros** estudantes e o próprio servidor, não só quem executa o código.
- Os dados de investigação (Solution Leakage Rate, Hint Dependency) que o projeto se propõe a medir devem ser efetivamente computáveis a partir do que é registado.

## 3. Audit Findings

Formato por finding: `[Tipo · Prioridade · Esforço]` seguido de localização, descrição/impacto, causa provável, recomendação e dependências (quando relevantes). Tipos: BUG, ARQUITETURA, UX, SEGURANÇA, DESEMPENHO, FUNCIONALIDADE, PEDAGOGIA/DOMÍNIO, QUALIDADE DE CÓDIGO.

### 3.1 `algo_lang/` — Bugs e Segurança (25 findings)

- **AL-07** [QUALIDADE DE CÓDIGO · ALTA · Alto] `compilador/codegen.py` + `codegen_minimo.py`. ~13 funções quase byte-a-byte duplicadas entre os dois geradores (ver ARCH-01 para o impacto estrutural). Recomendação: extrair uma camada de dispatch/funções partilhadas; tratar como refactor dedicado, não uma correção pontual.

### 3.2 `alguem/` — Bugs e Segurança (21 findings)

- **AG-04** [BUG · MÉDIA · Baixo] `fornecedores/_base_openai_compativel.py:49-53`. Erros HTTP, incluindo rate-limit (429), são todos tratados como o mesmo erro genérico — o estudante não sabe se deve esperar e tentar de novo. Recomendação: distinguir 429 e sugerir espera; mapear 401/403 para "credencial inválida".
- **AG-05** [SEGURANÇA · MÉDIA · Baixo] `fornecedores/_base_openai_compativel.py:62-64,72-74`. Mensagens de erro incluem o corpo bruto da resposta da API sem redação — pode expor detalhes internos do fornecedor ou, em alguns casos, fragmentos da própria chave. Recomendação: redigir/truncar o corpo antes de o mostrar ao utilizador.
- **AG-06** [QUALIDADE DE CÓDIGO · BAIXA · Baixo] `fornecedores/anthropic.py:79-83`. Uso de uma exceção de acesso a dicionário como controlo de fluxo para blocos de resposta não textuais. Recomendação: usar `.get()` com verificação explícita.
- **AG-07** [SEGURANÇA · ALTA · Baixo] `fornecedores/gemini.py:51`. A chave de API é passada na própria URL como query string — fica em logs de acesso, proxies e histórico do cliente HTTP. Recomendação: mover para cabeçalho de autenticação, como os outros fornecedores.
- **AG-18** [SEGURANÇA/PRIVACIDADE · ALTA · Médio] `nucleo/registador.py:76-98`. Texto integral das mensagens do estudante e das respostas é gravado em claro em disco. Recomendação: pelo menos avaliar redação de dados pessoais/sensíveis (o estudante pode colar informação pessoal por engano numa mensagem); documentar claramente a política de retenção para os utilizadores.
- **AG-20** [BUG · BAIXA · Baixo] `nucleo/identidade.py:23-31`. Condição de corrida entre verificar se o ficheiro de identificação existe e escrevê-lo. Recomendação: usar `open(..., "x")` (criação exclusiva) e tratar `FileExistsError`.

### 3.3 `online/` — Bugs e Segurança (31 findings)

- **ON-38** [QUALIDADE DE CÓDIGO/SEGURANÇA · ALTA · Médio] `online/tests/`. Nenhum teste cobre os cenários de maior risco (path traversal, SSRF, rate limiting, payloads grandes, CSRF). Recomendação: suite de testes de segurança dedicada, a crescer junto com as correções das Fases 0-1-4.

### 3.4 Arquitetura e Qualidade de Código (13 findings)

- **ARCH-01** [ARQUITETURA · ALTA · Alto] Adicionar um novo nó de AST exige alterações sincronizadas em ~9 `isinstance`/`elif` independentes espalhadas por `codegen.py`, `codegen_minimo.py`, `semantics.py`, `tools/linter.py`, `tools/flowchart.py` — sem verificação de exaustividade em tempo de compilação. Um branch esquecido falha silenciosamente (ex. o linter simplesmente não avalia o nó novo). Recomendação: introduzir um mecanismo de dispatch centralizado (visitor pattern ou registo por tipo de nó) que force, no mínimo, um erro claro quando um nó não tem handler.
- **ARCH-04** [QUALIDADE DE CÓDIGO · MÉDIA · Médio] Deteção de inclusões/importações duplicadas reimplementada de forma independente três vezes: `cli.py:_resolver_inclusoes`, `online/executor.py:_resolver_inclusoes` (já documentado em `CLAUDE.md`) e `tools/linter.py:369-398`. Recomendação: extrair uma função partilhada de normalização/deteção, usada pelas três (mantendo o `sys.exit` isolado só na versão da CLI, conforme o gotcha documentado).
- **ARCH-05** [QUALIDADE DE CÓDIGO · BAIXA · Baixo] `tests/` de `algo_lang` vive fora da pasta do subprojeto (na raiz do repositório), ao contrário de `alguem/tests/` e `online/tests/`, apesar de `algo_lang/` ser descrito como independente. Recomendação: mover para `algo_lang/tests/` se algum dia se pretender extrair o subprojeto isoladamente; baixa urgência.

### 3.5 Experiência de Utilização (19 findings)


### 3.6 Alinhamento com o Objetivo Pedagógico (5 findings)

- **GOAL-02** [PEDAGOGIA/DOMÍNIO · ALTA · Alto] O guardião classifica cada resposta isoladamente, sem memória entre turnos — um estudante pode decompor o pedido ("dá-me a condição do ciclo" → "agora o incremento" → "agora a inicialização do acumulador") e obter a solução completa por partes, cada uma individualmente aceite como HINT/PARTIAL_SOLUTION. Recomendação: agregação de risco entre turnos (ex. o guardião recebe também um resumo do que já foi revelado na sessão, não só a resposta atual) — esforço alto porque exige repensar o contrato do guardião; considerar como item de investigação próprio antes de implementar.
- **GOAL-03** [PEDAGOGIA/DOMÍNIO · ALTA · Médio] O classificador do guardião reutiliza sempre o mesmo fornecedor/modelo escolhido pelo próprio estudante para o tutor principal (`tutor.py:51`) — um estudante que escolha deliberadamente um modelo fraco ou suscetível a jailbreak degrada simultaneamente a qualidade das respostas *e* do seu próprio guardrail, sem defesa em profundidade. Recomendação: considerar um modelo classificador fixo/independente da escolha do estudante (mesmo que mais barato), pelo menos como opção configurável pelo administrador.
- **GOAL-05** [PEDAGOGIA/DOMÍNIO · ALTA · Médio] Quando `usar_guardiao=false` (o modo experimental para RQ5 — "o system prompt sozinho basta sem o guardião?"), nenhum evento `tentativa_guardiao` é escrito, e `scripts/metricas.py` calcula `solution_leakage_rate` só a partir desses eventos — logo, para sessões sem guardião, a métrica fica `None`. A própria comparação com/sem guardião que o toggle foi construído para permitir está atualmente incalculável a partir dos logs. Recomendação: reclassificar offline as respostas guardadas (`resposta_final` já é preservada) com o guardião, mesmo quando ele não correu ao vivo, para obter a métrica comparável.
- **GOAL-08** [FUNCIONALIDADE · MÉDIA · Médio] `online/alguem_ponte.py:25,73`. A política pedagógica (`nivel_maximo_ajuda`, `permite_solucoes_completas`, etc.) é fixa por omissão para todas as sessões web, sem forma de um instrutor a configurar por turma/conta a partir do painel de administração (`admin.html` só tem Utilizadores/Atividade/Backup). Recomendação: aba de configuração de política no painel de admin — item de escopo médio, avaliar prioridade junto do responsável do projeto antes de implementar (pode ser adiado para Fase 8).

### 3.7 Funcionalidades Solicitadas (3 findings)

Pedidos explícitos do responsável do projeto, fora do que a auditoria original cobria — não são bugs encontrados por leitura de código, mas foram verificados contra o estado atual do código antes de serem descritos abaixo.

- **FEAT-01** [FUNCIONALIDADE · ALTA · Alto] `online/bd.py:33-40` (tabela `credencial_llm`) + `online/credenciais.py` + `online/alguem_ponte.py` + página de definições em `online/estatico/`. Atualmente cada conta só pode ter **uma** credencial de LLM ativa: `estudante_id` é a chave primária da tabela `credencial_llm`, e o próprio comentário em `credenciais.py:2-4` documenta que "escolher um fornecedor novo substitui" o anterior. Pedido: permitir configurar vários fornecedores/modelos em simultâneo e escolher qual usar. Recomendação: alterar `credencial_llm` para permitir múltiplas linhas por estudante (chave primária própria `id`, `estudante_id` como FK não-única, mais uma flag `ativa`/`predefinida` — uma migração de esquema, não só `CREATE TABLE IF NOT EXISTS`, porque a tabela já existe em instalações correntes); expor UI para listar/adicionar/remover credenciais e selecionar a ativa; `alguem_ponte.py` passa a resolver a credencial ativa (ou uma escolhida explicitamente na sessão, se se quiser trocar por turno) em vez de assumir sempre uma única linha. A mesma limitação estrutural existe na CLI local (`alguem/config.json` exige um único `fornecedor`/`modelo` de topo, mesmo podendo guardar várias chaves em `credenciais`) — avaliar, no mesmo pedido, se a CLI também deve ganhar forma de trocar o modelo ativo sem editar o ficheiro à mão. Dependências: requer decisão de produto sobre migração de dados existentes (contas já têm uma credencial gravada) antes de implementar.

## 4. Improvement Opportunities

Não são bugs — são melhorias de qualidade, robustez ou preparação para o futuro, sem urgência de correção. Agrupadas por subsistema.

**algo_lang** — AL-10 (`CABECALHO_RUNTIME` morto em `codegen_minimo.py`, remover); AL-11 (`BIBLIOTECA_MINIMA` duplica `bibliotecas/*.py`, reutilizar); AL-14 (sem notação científica no lexer); AL-17 (comentário `pragma: no cover` órfão em `parser.py:336`); AL-20 (comentário órfão em `bibliotecas/cadeia.py:26`); AL-22 (descoberta de bibliotecas falha silenciosamente sem `NOME`, adicionar aviso/log); AL-25 (`except Exception` amplo no tracer descarta traceback, útil só para debug do próprio compilador); AL-26 (duas funções auxiliares do tracer tratam `dict` de forma inconsistente); AL-27 (limite de passos do trace fixo em 4000, sem flag de configuração); AL-38 (`cmd_lint` lê o ficheiro do disco duas vezes).

**alguem** — AG-01 (sem retry/backoff nos fornecedores LLM); AG-02 (sem tracking de tokens/custo); AG-03 (timeout HTTP fixo de 60s, não configurável); AG-08 (`URL_API` como propriedade a sobrepor atributo de classe, frágil a refactor); AG-09 (`except TypeError` demasiado amplo na fábrica de fornecedores); AG-17 (ficheiro de log sem gestor de contexto); AG-19 (sem rotação/limite de tamanho dos logs); AG-24 (até 4 chamadas LLM por turno sem visibilidade de custo — ligado a AG-02); AG-25 (guardião reutiliza sempre o modelo caro do tutor principal — ligado a GOAL-03, mas aqui como oportunidade de poupança de custo, não de segurança); AG-29 (importar `conhecimento_algo.py` insere caminho em `sys.path` como efeito colateral global).

**online** — ON-28 (sem `HEALTHCHECK` no Dockerfile); ON-29 (imagem base sem digest fixado); ON-31 (`pyproject.toml` sem metadados de projeto).

**Arquitetura** — ARCH-10 (arquitetura de logging só em disco local, sem abstração de armazenamento — teto de escalabilidade horizontal, aceitável para o âmbito atual de uma VM/sala de aula); ARCH-14 (ligação SQLite nova por pedido, sem pooling — igualmente aceitável ao âmbito atual, mas o primeiro ponto a rearquitetar se o volume crescer).

**Transversal** — considerar configurar um linter/formatter automático para Python (o projeto não tem nenhum, per `CLAUDE.md`) para apanhar uma parte destes itens automaticamente no futuro; considerar `pip-audit` ou `safety` no CI depois de ON-30 fixar versões.

## 5. Correction Roadmap

### Fase 0 — Contenção crítica de segurança
- **Objetivo**: eliminar os vetores de execução remota de código e leitura/escrita arbitrária de ficheiros antes de qualquer outra alteração.
- **Resolve**: ~~AL-01~~, ~~AL-32~~, ~~ON-01~~, ~~ON-02~~, ~~AG-27~~, ~~ON-14~~, ~~ON-05~~, ~~ON-27~~ (ver AUDIT_DONE.md).
- **Componentes**: `algo_lang/compilador/codegen.py`, `algo_lang/tools/flowchart.py`, `online/executor.py`, `alguem/nucleo/ficheiros_visiveis.py`, `online/credenciais.py`, `online/main.py`, `online/Dockerfile`.
- **Alterações principais**: reescrever a geração da mensagem de `afirmar` para nunca reinterpretar a condição do utilizador como f-string nova; aplicar o mesmo tratamento a `texto_expr`; confinar `incluir` a um diretório-base com `os.path.realpath` + verificação de prefixo (em `executor.py` e `ficheiros_visiveis.py`); restringir nomes de ficheiro de escrita a uma whitelist sem separadores de caminho; allowlist/bloqueio de IPs privados para o host Ollama; `env=` explícito no subprocesso do executor; `USER` não-root no Dockerfile.
- **Dependências**: nenhuma — primeira fase.
- **Riscos**: alterar a geração de `afirmar` pode mudar o texto exato de mensagens já usadas por testes existentes — validar com toda a suite antes de fechar a fase.
- **Critérios de conclusão**: suite de testes de `algo_lang` passa; teste dedicado confirma que uma condição de `afirmar` com chavetas não executa código; teste confirma que `incluir "../../etc/passwd"` (ou equivalente Windows) é rejeitado tanto no executor como no tutor; credencial Ollama com host de loopback/metadata é rejeitada; a imagem Docker corre como utilizador não-root.

### Fase 1 — Estabilização do executor online
- **Objetivo**: eliminar os bloqueios síncronos e a falta de limites de concorrência que podem travar o servidor inteiro.
- **Resolve**: ~~ON-03~~, ~~ON-04~~, ~~ON-06~~, ~~ON-07~~, ~~ON-08~~, ~~ON-09~~, ~~ON-16~~, ~~ON-17~~, ~~ARCH-11~~, ~~ARCH-12~~ -- Fase 1 concluída (ver AUDIT_DONE.md).
- **Componentes**: `online/executor.py`, `online/main.py`, `online/bd.py`, `online/autenticacao.py`.
- **Alterações principais**: semáforo global de execuções concorrentes; `RLIMIT_NPROC`/`RLIMIT_NOFILE`; mover `graphviz` e `bcrypt` para threadpool; pasta de trabalho por execução com lock (não por estudante); acesso à BD via threadpool; dependência FastAPI partilhada para "resolver pseudónimo → preparar pasta".
- **Dependências**: Fase 0 (mesmo ficheiro `executor.py` já alterado).
- **Riscos**: mudanças de concorrência podem introduzir regressões subtis — testar sob carga simulada antes de fechar.
- **Critérios de conclusão**: teste de carga com N execuções concorrentes não bloqueia um pedido não relacionado durante a execução; novos testes de `online/tests/` cobrindo path traversal/limites/SSRF.

### Fase 2 — Robustez do compilador
- **Objetivo**: corrigir os defeitos funcionais do compilador identificados na secção 3.1 que ainda não foram tratados na Fase 0.
- **Resolve**: ~~AL-02~~, ~~AL-04~~, ~~AL-05~~, ~~AL-06~~, ~~AL-09~~, ~~AL-12~~, ~~AL-13~~, ~~AL-15~~, ~~AL-16~~, ~~AL-18~~, ~~AL-19~~, ~~AL-21~~, ~~AL-28~~, ~~AL-29~~, ~~AL-31~~, ~~AL-33~~, ~~AL-34~~, ~~AL-35~~, ~~AL-36~~ -- Fase 2 concluída (ver AUDIT_DONE.md).
- **Componentes**: `algo_lang/compilador/*`, `algo_lang/bibliotecas/*`, `algo_lang/tools/linter.py`, `algo_lang/cli.py`.
- **Dependências**: Fase 0 (`codegen.py` já alterado, evitar conflitos).
- **Riscos**: AL-05 (semântica de `div`/`mod`) exige uma decisão de produto documentada antes de implementar — pode alterar o comportamento de programas existentes; não implementar sem essa decisão explícita.
- **Critérios de conclusão**: suite de testes do compilador atualizada e a passar, com um novo teste por bug corrigido.

### Fase 3 — Integridade pedagógica do tutor
- **Objetivo**: fechar as lacunas que permitem ao guardião falhar, ser enganado, ou ser contornado — e alinhar o sistema com a promessa de "nunca resolve o exercício".
- **Resolve**: ~~AG-10~~, ~~AG-11~~, ~~AG-12~~, ~~AG-13~~, ~~AG-14~~, ~~AG-15~~, ~~AG-16~~, ~~AG-21~~, ~~AG-22~~, ~~AG-23~~, ~~AG-26~~, ~~AG-28~~, ~~AG-30~~, ~~AG-31~~, ~~GOAL-01~~, ~~ARCH-07~~, ~~ARCH-08~~, ~~ARCH-09~~, ~~UX-07~~, ~~UX-08~~, ~~UX-09~~ -- Fase 3 concluída (ver AUDIT_DONE.md). **Adiados** (decisão explícita do responsável do projeto, 2026-08-09) **para a Fase 8**: AG-18, GOAL-02, GOAL-03, GOAL-05 — ver essa secção.
- **Componentes**: `alguem/nucleo/*`, `alguem/scripts/metricas.py`.
- **Alterações principais**: `try/except` em `tutor.py` à volta de cada chamada externa, com remoção de mensagens incompletas do histórico; comparação exata (não substring) da categoria do guardião, com fallback seguro; delimitador aleatório por pedido no prompt de classificação; validação de `nivel_maximo_ajuda`; system prompt e heurística rápida agnósticos de linguagem (não só ALGO); avaliar agregação de risco entre turnos; considerar modelo classificador independente da escolha do estudante; garantir que sessões sem guardião continuam a produzir dados reclassificáveis para RQ5.
- **Dependências**: Fase 0 (correções base já podem ter começado a tocar `tutor.py`/`guardiao.py` indiretamente — verificar sobreposição).
- **Riscos**: recalibrar a heurística de deteção de código pode aumentar falsos positivos se mal ajustada — validar com os exemplos de nível 5 documentados em `escada_de_ajuda.py` antes de fechar.
- **Critérios de conclusão**: `alguem/tests/` passa; novos testes cobrindo: exceção do fornecedor a meio do turno não corrompe o histórico; uma resposta com solução completa em Python é bloqueada mesmo com `usar_guardiao=false`; `nivel_maximo_ajuda` negativo é rejeitado na configuração.

### Fase 4 — Robustez e segurança da app online
- **Objetivo**: fechar os problemas de autenticação, sessão, validação de entrada e XSS na aplicação web.
- **Resolve**: ~~ON-10~~, ~~ON-11~~, ~~ON-12~~, ~~ON-13~~, ~~ON-15~~, ~~ON-19~~, ~~ON-20~~, ~~ON-21~~, ~~ON-22~~, ~~ON-23~~, ~~ON-25~~, ~~ON-26~~, ~~ON-30~~, ~~ON-35~~, ~~ON-33~~, ~~ON-34~~ -- Fase 4 concluída (ver AUDIT_DONE.md).
- **Componentes**: `online/autenticacao.py`, `online/main.py`, `online/cifragem.py`, `online/estatico/app.js`, `requerimentos.txt`.
- **Alterações principais**: rate limiting de login por conta; mensagens de erro genéricas ao cliente; validação de corpo JSON com 400 explícito; remover acesso direto a `editor.html` sem sessão; limites de tamanho de mensagem/pedido; verificação de origem/CSRF; `textContent`/sanitização em vez de `innerHTML` para erro e SVG; pinning de dependências; `https_only` configurável.
- **Dependências**: Fase 1 (mesmos ficheiros de rotas já alterados).
- **Riscos**: rate limiting mal calibrado pode bloquear turmas inteiras atrás do mesmo IP de rede escolar — limitar por conta, não só por IP.
- **Critérios de conclusão**: testes de autenticação cobrindo tentativas falhadas repetidas; confirmação manual de que `innerHTML` de erro/SVG está sanitizado; dependências fixadas sem CVEs conhecidos.

### Fase 5 — UX crítica e "quick wins"
- **Objetivo**: eliminar os pontos de confusão/abandono mais graves para um estudante iniciante, incluindo o único finding UX classificado CRÍTICA.
- **Resolve**: ~~UX-01~~, ~~UX-02~~, ~~UX-03~~, ~~UX-04~~, ~~UX-05~~, ~~UX-06~~, ~~UX-11~~, ~~UX-12~~, ~~UX-13~~, ~~UX-14~~, ~~UX-15~~, ~~UX-16~~, ~~UX-17~~, ~~UX-18~~, ~~UX-19~~, ~~AL-08~~, ~~AL-23~~, ~~AL-24~~, ~~ON-37~~, ~~FEAT-02~~, ~~FEAT-03~~ -- Fase 5 concluída (ver AUDIT_DONE.md).
- **Componentes**: `algo_lang/compilador/codegen.py` (mensagens), `algo_lang/tools/tracer.py`, `algo_lang/cli.py` (`_mostrar_banner`), `online/estatico/visualizador/algo-trace-viewer.html`, `online/estatico/app.js`, `online/estatico/editor.html`, `online/estatico/estilo.css`, `online/modo_codemirror.py`.
- **Alterações principais**: localizar mensagens de runtime comuns (`math domain error`, etc.); incluir número de linha em erros de runtime; fallback local para os CDNs do visualizador de rasto (replicar o padrão já usado para o CodeMirror); painel do Alguém visível/destacado por omissão; indicador "a pensar..." no chat; reativar o chat após erro de credencial; ligar erros de compilação ao gutter do CodeMirror; rótulos de texto na toolbar; logo ASCII art no banner da consola (FEAT-03); toggle de tema claro/escuro no `online`, persistido em `localStorage` (FEAT-02).
- **Dependências**: Fase 2 (mensagens de erro do compilador). Pode correr em paralelo com as Fases 3 e 4.
- **Riscos**: baixo — mudanças maioritariamente de apresentação.
- **Critérios de conclusão**: teste manual com CDNs bloqueados (DevTools network block) confirma fallback funcional; percurso de "primeiro uso" testado manualmente de ponta a ponta na CLI e na web.

### Fase 6 — Qualidade de código e arquitetura
- **Objetivo**: reduzir a duplicação e o acoplamento estrutural que tornam o projeto frágil a mudanças futuras, feito só depois de as correções funcionais estarem estáveis.
- **Resolve**: AL-07, ARCH-01, ~~ARCH-02~~, ~~ARCH-03~~, ARCH-04, ARCH-05, ~~ARCH-06~~, ~~ARCH-13~~, ~~ARCH-15~~, ~~ON-24~~.
- **Componentes**: `compilador/codegen.py` + `codegen_minimo.py`, `tools/linter.py`, `alguem/fornecedores/`, `online/credenciais.py`.
- **Alterações principais**: extrair uma camada de dispatch/funções partilhadas entre os dois geradores de código; remover a dependência invertida de `codegen.py` sobre `tools/flowchart.py`; unificar deteção de inclusões duplicadas; unificar a lista de fornecedores válidos entre `alguem` e `online`; extrair helper HTTP partilhado para os fornecedores que ainda não o usam.
- **Dependências**: Fases 0-2 (evitar refatorizar ficheiros ainda a mudar por razões de segurança/correção).
- **Riscos**: o refactor de `codegen.py`/`codegen_minimo.py` é o item de maior esforço do plano — fazer com cobertura de testes máxima antes de mexer, como mudança puramente estrutural (sem alterar comportamento observável).
- **Critérios de conclusão**: suite de testes completa (`algo_lang` + `alguem` + `online`) passa sem alteração de resultado esperado.

### Fase 7 — Operações e infraestrutura
- **Objetivo**: melhorias operacionais de baixo risco, sem dependências fortes de outras fases.
- **Resolve**: ON-28, ON-29, ON-31.
- **Componentes**: `Dockerfile`, `pyproject.toml`.
- **Alterações principais**: `HEALTHCHECK`; digest fixado na imagem base; metadados de projeto em `pyproject.toml`.
- **Dependências**: idealmente depois da Fase 0 (Dockerfile já alterado lá para o `USER`).
- **Riscos**: mínimo.
- **Critérios de conclusão**: `docker build` com healthcheck funcional.

### Fase 8 — Instrumentação de investigação e controlo pedagógico (opcional)
- **Objetivo**: melhorias de âmbito de produto/investigação, a validar com o responsável do projeto antes de avançar — não bloqueiam as fases anteriores.
- **Resolve**: GOAL-08, AG-02, AG-24, AG-25, FEAT-01. **Adiados da Fase 3** (decisão explícita do responsável do projeto, 2026-08-09): AG-18 (avaliar redação de dados sensíveis nos logs / documentar política de retenção), GOAL-02 (agregação de risco entre turnos — o próprio finding já sugeria tratar como item de investigação à parte, esforço Alto), GOAL-03 (modelo classificador fixo/independente do estudante, configurável pelo administrador), GOAL-05 (script de reclassificação offline para tornar `solution_leakage_rate` calculável também sem guardião ao vivo).
- **Componentes**: `alguem/scripts/metricas.py`, `online/estatico/admin.html`, `online/alguem_ponte.py`, `online/bd.py`, `online/credenciais.py`, `alguem/config.py`.
- **Alterações principais**: painel de administração para configurar política pedagógica por turma/conta; tracking básico de tokens/custo por sessão; script de reclassificação offline para GOAL-05; migração de `credencial_llm` para múltiplas credenciais por estudante com seleção da ativa, mais UI para a gerir (FEAT-01); modelo classificador fixo configurável (GOAL-03); avaliação de redação de dados sensíveis nos logs (AG-18).
- **Dependências**: Fase 3. FEAT-01 depende ainda de decisão de produto sobre migração de dados de contas existentes.
- **Riscos**: pode expandir o âmbito do projeto além do MVP atual — confirmar prioridade antes de implementar. FEAT-01 é uma migração de esquema sobre uma tabela já em produção — planear rollback antes de aplicar.
- **Critérios de conclusão**: instrutor consegue alterar `nivel_maximo_ajuda` sem tocar em código; estudante consegue guardar mais do que uma credencial de LLM e escolher qual usar sem perder as anteriores.

## 6. Recommended Order of Implementation

**0 → 1 → 2 → 3 → 4 → 5 (paralelo a 3/4) → 6 → 7 (paralelo, a qualquer momento após 0) → 8 (opcional)**

Razão: a Fase 0 vem primeiro porque resolve os únicos itens com impacto irreversível/sobre terceiros (RCE, leitura/escrita de ficheiros no servidor, segredos, root) — sem isto, qualquer outro trabalho corre no mesmo ambiente inseguro. A Fase 1 segue imediatamente porque toca o mesmo ficheiro (`executor.py`) já alterado na Fase 0 e remove os riscos de disponibilidade (bloqueios síncronos). A Fase 2 estabiliza o compilador antes de a Fase 3 (tutor) e a Fase 5 (UX) dependerem de mensagens de erro corretas. A Fase 3 é colocada antes da Fase 4 porque protege a promessa central do projeto (não vazar soluções) — prioritária face a hardening genérico de autenticação. A Fase 5 (UX) pode decorrer em paralelo às Fases 3/4 porque toca ficheiros maioritariamente distintos, mas depende da Fase 2 para as mensagens de erro que vai localizar. A Fase 6 (refactor de qualidade) é deliberadamente deixada para o fim, para não obrigar a repetir testes de regressão de segurança sobre código ainda a ser reestruturado. A Fase 7 é independente e pode ser feita em qualquer altura depois da Fase 0. A Fase 8 é opcional e só deve avançar após validação de âmbito.

## 7. Validation Strategy

- **Regressão automática contínua**: `tests/` (algo_lang), `alguem/tests/` (173 testes) e `online/tests/` (83 testes) devem passar a cada fase; nenhuma fase é considerada concluída com testes a falhar.
- **Testes novos dirigidos por finding**: cada finding CRÍTICA/ALTA de segurança ganha um teste de regressão específico (ex.: tentativa de RCE via `afirmar`, tentativa de path traversal em `incluir`, tentativa de escrita fora da pasta do estudante, tentativa de SSRF via host Ollama) antes de ser dado como corrigido — nunca confiar só em correção manual/visual.
- **Testes manuais de fluxo web**: login, editor, execução, fluxograma, rasto, chat — testados manualmente em navegador após as Fases 1, 4 e 5, incluindo com CDNs bloqueados via DevTools (para validar UX-11).
- **Teste de carga leve**: simular N execuções concorrentes após a Fase 1 para validar limites de concorrência e ausência de bloqueio do event loop.
- **Revisão de segurança dirigida**: correr `/security-review` (ou equivalente) sobre o diff de cada uma das Fases 0, 1 e 4 antes de considerar essas fases prontas para deploy.
- **Validação pedagógica manual**: sessões de teste com o guardião ligado/desligado, tentando extrair soluções por decomposição multi-turno (GOAL-02) e pedindo explicitamente "em Python" (GOAL-01), depois da Fase 3.
- **Atualização do plano**: no fim de cada fase, marcar os findings resolvidos nesta secção do documento (ex. `~~AL-01~~ — corrigido em <data/commit>`) antes de avançar para a fase seguinte, para que este ficheiro continue a refletir o estado real.

## 8. Future Considerations

Questões a não implementar já, mas a reconsiderar numa fase futura ou se o âmbito do projeto mudar:

- **GOAL-06**: aproximação das 5 categorias do guardião para os 8 níveis da escada de ajuda — já documentada como *trade-off* deliberado no próprio código; só revisitar se dados de investigação mostrarem imprecisão real.
- **GOAL-07**: métricas de Agência do Estudante, Progressão Cognitiva, Transferência Adiada e Ganho de Aprendizagem precisam de dados externos/codificação qualitativa — fora do âmbito de engenharia deste plano.
- **GOAL-09**: ausência de persistência de código (sem tabela `programs`) é uma escolha de design deliberada ("scratch pad", per `CLAUDE.md`); só reconsiderar se o objetivo do projeto passar a incluir acompanhamento de progresso do estudante pelo instrutor.
- **ARCH-10 / ARCH-14**: arquitetura de logging local em disco e ligação SQLite por-pedido têm um teto de escalabilidade claro; aceitável para "uma sala de aula, uma VM"; só revisitar se o âmbito de implantação mudar para múltiplas réplicas.
- **ON-36**: migração de CodeMirror 5 para 6 — mudança de peso considerável, sem urgência funcional; só numa fase de modernização de frontend dedicada.
- **AL-37**: leitura de stdin byte-a-byte no REPL é uma escolha deliberada (evita roubar bytes destinados a um subprocesso filho); não alterar sem repensar a arquitetura de I/O da consola.
- **AL-14 / AL-16**: notação científica e literais `{...}` fora de declarações são melhorias de linguagem de baixo impacto pedagógico imediato — reavaliar consoante feedback real de alunos/professores.
- **Escalar `online/` para múltiplas réplicas**: exigiria repensar armazenamento de sessão, logs e acesso à BD (ver ARCH-10/14); não é um requisito do âmbito atual.
