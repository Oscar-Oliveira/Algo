# Decisões de arquitetura, segurança e design

Catálogo dos comentários do código-fonte que documentam uma decisão não
óbvia — arquitetura, limitação conhecida, segurança/privacidade,
algoritmo não trivial, contrato de API pública ou trabalho futuro ainda
válido. Gerado na Tarefa 1 da revisão do projeto (2026-08-29), a partir
de uma leitura integral de `algo_lang/`, `alguem/` e `online/`
(excluindo testes). Não substitui os comentários no código — é um
índice para consulta rápida sem ter de percorrer os 55 ficheiros; a
fonte da verdade continua a ser o comentário junto ao código
(referenciado por ficheiro:linha).

Muitos destes comentários já usam tags (`ARCH-##`, `ON-##`, `AG-##`,
`AL-##`, `UX-##`, `GOAL-##`) de auditorias anteriores — ver
`docs/PlanoAuditoria.md` para o histórico dessas auditorias.

---

## algo_lang/

### bibliotecas/__init__.py
- L2-15 — contrato de registo para adicionar uma nova biblioteca embutida (arquitetura/API)

### bibliotecas/cadeia.py
- L26-28, L33-34 (`subcadeia`) — contrato 0-based/fim-exclusivo; porque `_AlgoErroAmigavel` não é reembrulhado (API)
- L48-55 (`procurar`) — porque `-1` de "não encontrado" é intencional; `sub` vazio é rejeitado (limitação/design)
- L64-69 (`substituir`), L76-81 (`dividir`) — rejeições de casos-limite deliberadas; convenção `dims_retorno` para vetores (API/arquitetura)

### bibliotecas/conversao.py
- L6-11 — contrato de tradução de erros (`ValueError` vs `_AlgoErroAmigavel`) (arquitetura)
- L24-30 (`paraInteiro`) — algoritmo de parse manual, porque evita `float()` (algoritmo)
- L54-56 (`paraDecimal`) — único ponto onde `nan`/`inf` podem ser construídos em ALGO (limitação/API)
- L67-77 (`paraBooleano`) — porque `"não"`/`"nao"`/`"0"` têm tratamento especial (armadilha pedagógica numa linguagem em português) (design)

### bibliotecas/matematica.py
- L16-27 (`potencia`) — referência ao bug #35; assimetria deliberada float/overflow com o operador `^` (algoritmo/limitação)
- L40-42 (`absoluto`) — `"numeric"` como marcador de "tipo espelha o argumento", cruzado com `semantics.py` (API)

### compilador/lexer.py
- L27-31 (`Token.coluna`) — porque tokens estruturais assumem coluna 1 por omissão
- L81-85, L102-105 (`_remover_comentarios_bloco`) — ordem de deteção `//` vs `/* */`; separador exigido em comentários de bloco de uma linha
- L118-124, L150-151 (`_medir_indentacao`/`tokenizar`) — regras de consistência tabs-vs-espaços (algoritmo/design)

### compilador/ast_nodes.py
- L18-21 (`Programa.aliases_inclusao`) — populado por `inclusoes.py`, não pelo parser (arquitetura)
- L197, L200-203 (`Chamada`) — nomes com ponto para chamadas de biblioteca; `acessos` permite indexar o resultado sem variável intermédia (API)
- L226-230, L303-317 (`texto_expr`, tag ARCH-02) — porque este helper de renderização vive aqui e não em `tools/flowchart.py`; contrato de escaping (arquitetura)

### compilador/inclusoes.py
- L2-12 (tag ARCH-04) — lógica de deteção de colisões partilhada entre `cli.py` (pode `sys.exit`) e `online/executor.py` (nunca pode) (arquitetura)
- L17-30 (`ColisaoDeInclusao`), L42-66 (`mesclar_biblioteca_no_programa`) — contrato completo de colisões entre categorias e mangling de aliases (arquitetura/API)

### compilador/gerador_base.py
- L2-16 — ficheiro é resto de uma divisão de um `codegen_minimo.py` já removido; alguns comentários ainda referem esse modo morto (arquitetura/histórico)
- L34-43 (`ErroInternoCompilador`, tag ARCH-03) — distingue falhas de invariante interna de `ErroSemantico` esperado (arquitetura)
- L172-177 (`_gerar_para`, tag AL-XX) — porque `passo` é elevado a variável temporária (bug de dupla-avaliação com efeitos secundários) (algoritmo)

### compilador/parser.py
- L46-58 (`LIMITE_PROFUNDIDADE_EXPR`) — checklist de todos os pontos de recursão direta que têm de chamar o guarda de profundidade (limitação/arquitetura)
- L62-75 (`LIMITE_PROFUNDIDADE_ARVORE`) — porque uma cadeia de operadores plana ainda precisa de guarda própria, ligado ao limite de nesting do próprio CPython (limitação)
- L744-754 — porque operadores relacionais encadeados (`a < b < c`) são deliberadamente rejeitados (design)
- L862-869 (`parse_biblioteca`) — contrato de API para parsing de ficheiros incluídos

### compilador/codegen.py
- L20-29 (`sys.stdout.reconfigure`) — porque a reconfiguração UTF-8 importa para o ambiente do subprocesso do `online/executor.py` (segurança/arquitetura)
- L152-184, L187-221 (tradutores de erro) — cada um documenta o invariante de runtime garantido por `semantics.py` que torna a tradução segura (arquitetura/limitação)
- L262-270 (`_algo_pot`), L273-281 (`_algo_indice`), L307-318 (verificação de tamanho de vetor agregado) — redes de segurança deliberadas, cada uma com o modo de falha que previne (segurança/limitação)
- L536-552 (`_gerar_estrutura`) — ausência de `__eq__`/`__deepcopy__` é intencional (semântica referencial) (design)
- L614-626, L647-666 (deteção de aliasing de `ref` em runtime) — algoritmo detalhado para o que `semantics.py` não consegue resolver estaticamente (algoritmo/limitação)

### compilador/semantics.py
- L14-21, L238-244 (bugs #23/#27) — nomes reservados fixos vs. por biblioteca (limitação)
- L388-410 (`_todos_caminhos_devolvem`) — análise conservadora de caminhos de retorno; porque `sair`/`continuar` quebram o raciocínio sequencial simples (algoritmo)
- L530-546 (`_globais_lidas_transitivamente`) — problema de duas passagens que motiva esta análise transitiva separada (arquitetura)
- L1511-1519, L1522-1536 (aliasing de `ref`) — limitação conhecida documentada explicitamente (`v[i]` vs `v[j]` não resolvido), com ponteiro para o teste que cobre isto (limitação)

### cli.py
- L212-216 (`LIMITE_CPU_SEGUNDOS`) — tempo de CPU vs. tempo de relógio; técnica partilhada com `online/executor.py` (segurança/arquitetura)
- L218-225 (`_bootstrap_limite_cpu`) — valor lido de novo a cada chamada, para permitir monkeypatch em testes (design)
- L654-663 — fix da duplicação da dica de ajuda em `executa -h`, explicado pelo comportamento observável, não pelo número do bug (design)
- L695-700 (`main`) — porque `algo.bat`/`algo.sh` sozinhos não cobrem o crash do terminal Windows com UTF-8 (limitação)

### tools/flowchart.py
- L6-9 (reexport, tag ARCH-02), L13-19 (`ErroInternoFluxograma`, tag ARCH-01) — substitui uma falha silenciosa anterior (arquitetura, achado histórico)

### tools/linter.py
- L196-205 (`_verificar_recursao_sem_condicao`) — filosofia deliberada de preferir falsos negativos a falsos positivos (algoritmo/limitação)
- L338-345 (`_verificar_uso_de_globais`) — porque constantes são isentas do aviso de acesso direto a globais (design)
- L556-566 (`_verificar_ciclo_verdadeiro_sem_saida`) — idioma de "flag booleana em ciclo" visado por este aviso, cruzado com o equivalente ao nível de função (algoritmo)

### tools/tracer.py
- L18-26 (`LIMITE_TEMPO_SEGUNDOS`) — porque um limite só de passos não basta (ciclos caros por passo) (limitação)
- L66-81 (`_valor_serializavel`) — ciclos de aliasing entre estruturas/vetores são um programa ALGO válido (pós "Fase 1.1"/`AUDITORIA_2026-08-19`); deteção de ciclos por caminho, não global (arquitetura, referência a auditoria anterior)
- L362-369 — código a correr sob `sys.settrace()` aqui é invisível ao `coverage.py` (só um tracer ativo de cada vez); correção verificada manualmente (limitação, lacuna documentada nas métricas de teste)

**Nota:** `gerador_base.py:83` tem uma referência curta a um "ponto 5" externo não visível no ficheiro — provavelmente um documento de design/PR já desaparecido. Inofensivo, mas vale a pena confirmar se ainda faz sentido.

---

## alguem/

### __init__.py
- L2-6 — fronteira de arquitetura: `algo_lang` nunca depende de `alguem/`; sem `cli.py` próprio; só acessível via `online/` (arquitetura)

### config.py
- L2-6 — único ponto que conhece o nome do ficheiro de configuração (arquitetura)
- L63-67 — campos de credenciais não consumidos caem para o construtor do fornecedor, ligado a `AgenteLLM.REQUER_API_KEY` (API)

### fornecedores/__init__.py
- L23-31 (`criar_fornecedor`) — pass-through de `**extras`; hoje só o Ollama usa isto (arquitetura)

### fornecedores/_base_openai_compativel.py
- L2-14 — porque existe esta base partilhada e porque Gemini/Anthropic não a podem usar (arquitetura)
- L48-53 — `content` pode ser `null` em respostas de tool-call; nunca pode propagar como resposta vazia (API)

### fornecedores/anthropic.py, gemini.py, huggingface.py, ollama.py, openai.py, opencode.py, openrouter.py
- Docstrings de módulo explicam diferenças de formato de API por fornecedor (arquitetura)
- `ollama.py` L2-11 — execução só local elimina preocupações de privacidade/RGPD nos logs (segurança/privacidade)

### fornecedores/base.py
- L2-14 — abstração de mensagem neutra permite trocar de fornecedor só por configuração (arquitetura)
- L37-40 (`REQUER_API_KEY`) — fornecedores locais podem não precisar de chave (API)

### nucleo/conhecimento_algo.py
- L2-11 — palavras-chave lidas ao vivo de `algo_lang.compilador.lexer`, com fallback (arquitetura/limitação)
- L27-30 (tag AG-30) — `except ImportError` alargado para `except Exception`, cobre também um `algo_lang` presente mas corrompido (limitação)

### nucleo/escada_de_ajuda.py
- L2-9 — princípio de ajuda mínima; decisão de QUANDO subir de nível fica ao critério do LLM, sem mecanismo separado a **forçar a subida** — ver README (trabalho futuro). Verificado contra `tutor.py:246-251`: `_nivel_maximo_efetivo` impõe um teto, não força a subida — comentário continua correto, não está desatualizado.

### nucleo/guardiao.py
- L2-13 — verificação em duas camadas, independente da system prompt (arquitetura/segurança)
- L23-30 (tag ARCH-07) — palavras-chave heurísticas têm de ficar sincronizadas com o lexer; falha alto no import (limitação/segurança)
- L40-46 (tag GOAL-01) — heurística também deteta Python, porque estudantes podem contornar deteção só-ALGO (segurança)
- L64-74 (tag ARCH-08) — contrato explícito entre `Classificacao` e `tutor.py._aceitavel` (API)
- L82-84, L87-93 — racional de `CLASSIFICACOES_BLOQUEAVEIS` e mapeamento aproximado de nível sem chamada extra ao LLM (limitação)
- L162-165 (tag AG-14) — delimitador aleatório por pedido, para prevenir spoofing (segurança)
- L171-176 (tag AG-11) — falha de rede/API durante classificação falha em modo seguro (segurança)
- L178-180 (tag AG-12) — correspondência exata, não substring, para evitar falso positivo de "not FULL_SOLUTION" (algoritmo)
- L183-186 — saída do LLM não reconhecida falha em modo seguro (segurança)

### nucleo/identidade.py
- L2-10 — ID persistente anónimo, explicitamente não ligado à identidade real (privacidade/segurança)

### nucleo/ficheiros_visiveis.py
- L2-10 — deliberadamente por regex, não pelo parser real, para continuar a funcionar em ficheiros com erros de sintaxe (arquitetura/limitação)
- L18-22 (tag AG-28) — limites de ficheiros/bytes para limitar tamanho/custo da prompt (limitação)
- L31-37 (tag AG-27) — racional de confinamento de caminho, cruzado com `online/executor.py` (tag ON-02) (segurança, path traversal)
- L53 — caminhos em unidades/discos diferentes no Windows (limitação, particularidade de plataforma)

### nucleo/politica_pedagogica.py
- L2-6 — política orientada a dados permite configs experimentais A/B (arquitetura)
- L21-24 (tag AG-15) — racional de validação (nível negativo/fora de intervalo quebraria a inclusão do nível 0 silenciosamente) (limitação)

### nucleo/registador.py
- L2-18 — esquema de logging ligado diretamente às métricas de investigação, ficheiro por sessão, flush imediato (arquitetura)
- L35-39 — `pasta_logs` por omissão resolvido dentro do `__init__`, não na assinatura, especificamente para permitir monkeypatch em testes (particularidade Python)
- L113-116 (tag AG-26) — distinção `fechar()` vs `fim_sessao()` para uma sessão que nunca chegou a começar (gestão de recursos)

### nucleo/system_prompt.py
- L2-6 — prompt construída dinamicamente por política, permite configs experimentais sem alterar código (arquitetura)

### nucleo/tutor.py
- L2-5 — orquestração central, agnóstica de fornecedor (arquitetura)
- L22-26 (tag UX-09) — escalada não começa no nível máximo configurado, cresce com os turnos (algoritmo/UX)
- L29-31 (tag UX-08) — variantes de recusa escolhidas ao acaso para não parecer um bot avariado (UX)
- L48-50 (tag AG-21) — distingue recusa pedagógica de erro de comunicação com o fornecedor (API)
- L70-72 — guardião só é criado se a política o pedir (questão de investigação RQ5) (arquitetura/investigação)
- L80-83 — distinção entre `registo_guardiao` em memória e `Registador` em disco (arquitetura)
- L86-89 (tag AG-26) — só fecha um `Registador` criado internamente em caso de falha, nunca um fornecido pelo chamador (gestão de recursos)
- L116-120 (tag AG-23) — delimitador aleatório + framing explícito "isto é DADOS" para reduzir superfície de prompt injection via código do estudante (segurança)
- L195-199 — tentativas rejeitadas nunca entram no histórico persistente da conversa, para não reforçar comportamento de fuga, embora continuem a ser registadas (algoritmo/segurança)
- L213-219 (tags AG-21/AG-22) — tem de retirar a mensagem de utilizador incompleta em falha do fornecedor (Anthropic exige alternância estrita user/assistant) (limitação específica de fornecedor)
- L226-232 (tag ARCH-08) — espelho do comentário de contrato em `guardiao.py`, do lado consumidor (API)
- L234-238 (tags AG-13/UX-09) — teto de nível tem de ser imposto em código, não só pedido na prompt (segurança)
- L246-249 (tag UX-09) — racional da fórmula de escalada (algoritmo)

### scripts/metricas.py
- L2-14 — métricas calculadas ligadas às métricas de investigação definidas no README (API/arquitetura)
- L35-38, L53-59 (tag AG-31 ×2) — linhas de log malformadas/de esquema antigo não podem rebentar o script; lógica explícita de omissão por campo (`aceitavel` assume rejeitado, `veio_de_recusa_segura` assume falso) (limitação/algoritmo)

---

## online/

### alguem_ponte.py
- L2-6 — única adaptação necessária para reutilizar `alguem/` sem modificações (arquitetura)
- L34-40 (`limitar_ficheiros_visiveis`) — duplica o limite de AG-28 no ponto de entrada online, porque ficheiros submetidos pelo browser contornam a resolução de `incluir` (segurança)
- L77-85 ("Achado 2") — revalida o host do Ollama a cada conversa, para encolher a janela de SSRF por DNS rebinding (segurança)

### atividade.py
- L2-8 — log separado dos próprios logs do Alguem; eliminações são sempre físicas/finais (arquitetura)

### autenticacao.py
- L2-13 — distinção bcrypt (irreversível) vs. Fernet (reversível); semântica da env var de admin-gate (segurança/arquitetura)
- L29-33 (tag ON-11) — rate limiting por conta (não por IP), com backoff progressivo (segurança)
- L48-53 (`ErroCodigoGrupoInvalido`) — subclasse para permitir rate limiting por IP seletivo (arquitetura)
- L64-68 (tag ON-13) — lista pequena e deliberada de palavras-passe comuns, em vez da rockyou completa (segurança)
- L92-102 (`registar`, tag ON-12) — mensagem de erro genérica para evitar enumeração de emails (segurança)
- L140-143 (`obter_id_pseudonimo`) — nunca regista id real/email (segurança)
- L153-168 (`autenticar`, tag ON-11) — racional de timing/enumeração; decisão de grupo desativado bloquear também admins (segurança)
- L213-218 ("bootstrap tardio") — promoção tardia a admin continua a respeitar o bloqueio de grupo desativado (segurança)
- L267-275 (`rejeitar_conta`) — porque o email (não o id) é o único rasto de auditoria que resta após eliminação (arquitetura)
- L297-301 (`revogar_conta`) — guarda simétrica a `rejeitar_conta`, não pode revogar um admin (segurança)
- L314-324 (`remover_admin`) — COUNT atómico na cláusula WHERE para evitar corrida entre duas remoções concorrentes (segurança/algoritmo)

### bd.py
- L2-10 — porque não há ORM/framework de migrações; sem tabela `programs` por design (arquitetura)
- L161-170 (`gerar_backup_sql`) — pg_dump via subprocesso assíncrono (não bloqueia); password passada por env, não argv (segurança/arquitetura)

### cifragem.py
- L2-10 — chave nunca guardada em BD/código; recusa auto-gerar (segurança)
- L20-27 (tag ON-10) — verificação de entropia deliberadamente rudimentar, com o que cobre e o que não cobre (segurança)
- L42-46 (`gerar_chave_nova`) — tem de correr manualmente uma vez, nunca auto-gerada em runtime (segurança)

### credenciais.py
- L17-22 (tag ARCH-13) — fornecedores válidos derivados do registo `FORNECEDORES`, em vez de lista à mão que podia divergir (arquitetura)
- L29-37 (`_validar_host_ollama`) — racional de SSRF (pedido do servidor para um host escolhido pelo estudante) (segurança)
- L72-78 (tag ON-15) — campo `host` restrito só ao Ollama, para evitar valor guardado mas inutilizável silenciosamente (segurança)

### executor.py
- L2-11 — isolamento interativo; porque contorna `algo_lang.cli` (arquitetura)
- L48-61 (tag ON-04) — racional do limite de file descriptors; limitação de nº de processos deixada deliberadamente ao `--pids-limit` do Docker (RLIMIT_NPROC pouco fiável) (limitação)
- L71-76 — critério de limpeza é IDADE da pasta, não "todas menos a mais recente", para nunca apagar a pasta de uma execução concorrente (arquitetura)
- L84-95 (`_env_minimo`, tag ON-05) — subprocesso do estudante nunca pode herdar segredos do servidor (segurança)
- L98-124 (`_limpar_pastas_antigas_em_fundo`) — corre fora do event loop quando existe um (arquitetura)
- L126-142 (`preparar_pasta_execucao`, tags ON-07/ARCH-11) — uma pasta por execução, não por estudante, para evitar colisões em pedidos concorrentes (arquitetura, nota de regressão)
- L145-166 (`_resolver_inclusoes`, tag ON-02) — confinamento de caminho contra `../`; mensagens de erro indistinguíveis (segurança)
- L176-178 — `ValueError` de `os.path.commonpath` em unidades Windows diferentes (limitação)
- L228-236 (`_validar_nome_ficheiro`, tag ON-01) — dupla verificação: whitelist + realpath contra traversal (segurança)
- L247-254 (`_escrever_ficheiros_e_analisar`) — partilhado por 3 chamadores; contrato do que ainda não está verificado (arquitetura)
- L282-296 (`compilar_codigo`) — motivo explícito para contornar o `sys.exit(1)` de `cli.compilar_ficheiro` (arquitetura)
- L308-321 (`RecursionError`) — defesa em profundidade; a correção real vive no parser (limitação)
- L329-335 (`SaidaExcessiva`, tag ON-09) — particularidade do buffer de linha de 64KB do `StreamReader` do asyncio (limitação)
- L354-367 (`iniciar`, tags ON-04/ON-06) — porque `preexec_fn` é inseguro com threads; técnica de duplo-exec em alternativa (segurança/limitação)
- L397-398 — processo filho no Windows escreve `\r\n` (limitação)
- L416-426 (`correr_com_limite_de_tempo`) — timeout cobre só o arranque; cada input reagenda a janela (algoritmo)
- L460-470 (`_sanitizar_svg`, tag ON-34) — defesa em profundidade contra XSS no SVG do graphviz injetado via innerHTML (segurança)
- L558-566, L571-576 (`analisar_linter`) — porque `verificar()` é ignorado; referência cruzada ao bug #10 (`RecursionError`) (arquitetura/limitação)
- L591-604 (`gerar_rasto`) — contrato com os campos JSON esperados pelo visualizador de traço (API)

### grupos.py
- L2-14 — porque SHA-256 (não bcrypt) para o código de adesão, mais racional de armazenamento duplo (segurança)
- L27-29 — alfabeto evita carateres visualmente ambíguos (uso em quadro de sala de aula) (algoritmo/UX)
- L31 (`_TAMANHO_CODIGO`) — justificação de ~61 bits de entropia (segurança)
- L138-142 (`verificar_codigo`) — código errado/inexistente/desativado deliberadamente indistinguíveis (segurança)

### limitador_registo.py
- L2-12 — por IP com hash (não por conta/texto simples), limiar mais generoso que o login (NAT partilhado em sala de aula) (segurança)

### modo_codemirror.py
- L2-5 — gerado a partir das palavras-chave reais do lexer, para evitar divergência (arquitetura)
- L31-36 (tag ON-37) — aviso explícito em vez de fallback silencioso para palavras-chave não classificadas (limitação)
- L51-55 — porque o CM6 precisa de `StreamLanguage` escrito à mão vs. o `defineSimpleMode` declarativo do CM5 (arquitetura)

### projeto.py
- L2-9 — sem persistência em BD, o `.zip` é o próprio registo (arquitetura)
- L22-26 — limites de defesa contra zip bomb (segurança)
- L50-55 (`_ler_entrada_com_limite`) — `info.file_size` não é de confiar antes de ler; tem de ser lido em stream com teto contínuo (segurança)

### main.py
- L2-6 — racional de ser framework-light (arquitetura)
- L44-52 (tag ON-21) — páginas privadas deliberadamente fora do mount `StaticFiles`, para preservar verificações de sessão (segurança)
- L55-59 — `docs/exemplos/` vive fora de `online/`, lido de novo a cada pedido para evitar divergência (arquitetura)
- L81-84 (tag ON-25), L85-88 (tag ON-35) — max-age de sessão explícito; cookie HTTPS-only por omissão (segurança)
- L94-97, L100-106 (limitador de tamanho do corpo) — ressalva de cobertura só por Content-Length (limitação)
- L121-126, L129-136 (verificação CSRF Origin/Referer) — segunda camada além do SameSite; alcance do que bloqueia e não bloqueia (segurança)
- L159-176 (handler global de exceções, tag ON-19) — sempre JSON; texto da exceção nunca chega ao cliente (segurança)
- L190-196 (`corpo_json`, tag ON-20) — tratamento de JSON malformado para evitar 500s (limitação)
- L214-221 (`pasta_execucao_atual`, tag ARCH-12) — dependência partilhada; porque a rota WebSocket não a pode usar (arquitetura)
- L325-327 — porque o evento de auditoria de conta rejeitada guarda o email, não `alvo_id` (arquitetura)
- L567-568 (`rota_obter_credencial`) — chave de API nunca é devolvida ao cliente (segurança)
- L672-677 (`_listar_exemplos`) — sem caminho fornecido pelo pedido, logo sem risco de traversal (segurança)
- L732-736 (`rota_modo_algo`) — regenerado por pedido para atualidade, em vez de lista copiada à mão (arquitetura)
- L742-745 (`ALGUEM_ATIVO = False`) — flag temporária de desativação, com instruções de reativação (também toca `app.js` no frontend) (trabalho futuro)
- L754-758 (tag ON-03) — semáforo de execuções concorrentes, configurável por env (segurança)
- L875-879 (tag ARCH-09) — `fechar_sessao()` tem de correr em qualquer caminho de saída, não só em disconnect (arquitetura)
- L909-911 (tag ON-08) — chamada ao binário `dot` é bloqueante, tem de correr em threadpool (limitação)
