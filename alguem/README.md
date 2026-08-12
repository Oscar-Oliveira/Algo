# Alguem

Tutor de algoritmia baseado em LLM, para acompanhar quem está a
aprender a programar com a linguagem [ALGO](../README.md). Não
resolve exercícios nem escreve código — dá a quantidade mínima de
ajuda que permita ao estudante avançar sozinho.

Vive nesta pasta, ao lado de `algo_lang/`. **`algo_lang/compilador/`
nunca é alterado nem depende de nada daqui.** O único ponto de
contacto é a consola do ALGO (`algo_lang/cli.py`), que importa este
pacote só para o `?` funcionar — essa dependência é só nessa direção.

**O Alguem só se chama de dentro da consola do ALGO, com `?` — não
tem script de arranque próprio.**

```
$ algo
algo> ?
--------------------------------------------------------------
A chamar o Alguem...
Olá! Sou o Alguem, o teu tutor de algoritmia.
(tenho visibilidade de: exercicio.algo, biblioteca.algo)
(escreve 'sair' para voltares à consola do ALGO, 'ficheiros' para
veres o que tenho visível, ou 'ficheiro nome.algo' para trocares)
--------------------------------------------------------------

tu> não sei como calcular a média de vários números
Alguem> Antes disso -- achas que precisas de guardar todos os
        números, ou há uma forma de ires somando à medida que os lês?
```

## Visibilidade de ficheiros

Quando chamas o Alguem, ele vê automaticamente **o ficheiro em que
estiveste a trabalhar** na sessão da consola (o último `executa`,
`compila`, `lint` ou `fluxograma` que correste) — **pelo nome**, não
só o conteúdo solto, para poder responder a perguntas do tipo "o que
faz a função X no `exercicio.algo`?" com precisão.

Se esse ficheiro tiver `incluir "..."`, os ficheiros incluídos também
são mostrados (recursivamente, se um incluído incluir outro) — o
estudante vai fazer perguntas sobre o código todo, não só o ficheiro
principal.

> Esta deteção de `incluir` é feita por expressão regular, não pelo
> compilador verdadeiro — de propósito: o estudante pode estar a pedir
> ajuda precisamente porque o ficheiro tem um erro de sintaxe, e mesmo
> assim os ficheiros incluídos devem ser detetados.

Dentro da conversa:

| Comando | O que faz |
|---|---|
| `ficheiros` | Mostra que ficheiros o Alguem tem visíveis agora |
| `ficheiro nome.algo` | Troca o ficheiro em que o Alguem se baseia (o Alguem passa a "considerar" esse ficheiro, e os que ele incluir) |
| `sair` | Volta à consola do ALGO |

O nome em `ficheiro nome.algo` é procurado primeiro tal e qual, depois
relativo à pasta do ficheiro que já estava ativo — por isso funciona
mesmo a meio de uma conversa sobre outro exercício.

## Estado atual

Implementado até agora:

- Conversa com o LLM, através de **7 fornecedores** (OpenRouter,
  Gemini, OpenAI, Anthropic, HuggingFace, Ollama, OpenCode Go), cada
  um na sua própria classe/ficheiro -- os 4 que falam o formato "chat
  completions" da OpenAI (OpenRouter, OpenAI, HuggingFace, OpenCode
  Go) partilham a mesma lógica HTTP, numa base comum
  (`_base_openai_compativel.py`), para não a repetir 4 vezes
- Política pedagógica configurável (`config.json`)
- A escada de 8 níveis de ajuda (0 = autonomia total, 7 = código,
  sempre bloqueado)
- Um *system prompt* construído a partir da política em vigor —
  políticas diferentes dão prompts diferentes, sem tocar em código
- Conhecimento real da sintaxe do ALGO (`nucleo/conhecimento_algo.py`
  importa a lista de palavras-chave diretamente de
  `algo_lang.compilador.lexer` — não é uma cópia escrita à mão)
- Visibilidade de ficheiros pelo nome, com resolução de `incluir`
- **Guardião Pedagógico** (`nucleo/guardiao.py`): um segundo passo de
  verificação, independente do *system prompt* — depois do Alguem
  responder, e antes de a resposta chegar ao estudante, uma segunda
  avaliação classifica-a em `SAFE` / `HINT` / `PARTIAL_SOLUTION` /
  `FULL_SOLUTION` / `CODE`. Se for `CODE` ou `FULL_SOLUTION` (e a
  política não permitir explicitamente), a resposta é descartada — sem
  nunca entrar no histórico da conversa, para não reforçar esse
  comportamento nas trocas seguintes — e pede-se ao modelo para
  responder outra vez, com uma pista mais pequena. Ao fim de 2
  tentativas sem sucesso, cai para uma recusa fixa e segura.

  Tem duas camadas: uma heurística barata (deteta blocos de código
  óbvios sem chamar o LLM outra vez) e, se essa não encontrar nada, a
  classificação pelo próprio LLM. Cada avaliação fica registada em
  `alguem.registo_guardiao` (mensagem, classificação, se foi aceite à
  primeira) — é o que permite calcular a métrica de investigação
  *Solution Leakage Rate* sem instrumentação externa.

  Pode ser desligado (`"usar_guardiao": false` na política), para
  comparar experimentalmente "com" e "sem" guardião — RQ5 da
  investigação: será que o *system prompt* sozinho já chega?

- **Logs para a investigação** (`nucleo/registador.py`,
  `nucleo/identidade.py`, `scripts/metricas.py`): cada sessão fica
  registada em `logs/*.jsonl`, com um identificador de estudante
  persistente (automático, sem pedir nada) — dá para calcular
  *Solution Leakage Rate* e *Hint Dependency* diretamente, e preserva
  o texto integral para as métricas que precisam de análise externa.
  Ver a secção "Métricas e logs" abaixo.

**O que ainda não está implementado** (fica para as próximas fases,
por decisão explícita de âmbito, não por esquecimento):

- **Modelo do estudante**: o identificador persiste entre sessões
  (acima), mas não há ainda nenhum *perfil conceptual* construído a
  partir disso — nenhuma noção de "domina SE, tem dificuldade em
  ENQUANTO". Cada conversa continua a começar do zero em termos de
  adaptação pedagógica, só não em termos de identificação.
- **Agente multi-etapa** (*Intent Manager*, prompts especializados de
  compreensão/decomposição/diagnóstico): esta versão usa um único
  *system prompt*, não um sistema de vários agentes especializados.

## Como configurar

1. Copia `config.exemplo.json` para `config.json` (o `config.json` já
   vem com placeholders — substitui pelos valores reais).
2. Preenche `fornecedor` (ver tabela abaixo), `modelo` (o nome exato
   do modelo nesse fornecedor), e a tua chave de API em
   `credenciais.<fornecedor>.api_key`.
3. Ajusta `politica_pedagogica` se quiseres um comportamento diferente
   do padrão (ver campos abaixo).

```json
{
  "fornecedor": "openrouter",
  "modelo": "openai/gpt-4o-mini",
  "credenciais": {
    "openrouter": { "api_key": "a-tua-chave-aqui" },
    "gemini": { "api_key": "a-tua-chave-aqui" },
    "openai": { "api_key": "a-tua-chave-aqui" },
    "anthropic": { "api_key": "a-tua-chave-aqui" },
    "huggingface": { "api_key": "o-teu-token-aqui" },
    "ollama": { "host": "http://localhost:11434" },
    "opencode": { "api_key": "a-tua-chave-aqui" }
  },
  "politica_pedagogica": {
    "modo": "socratic",
    "nivel_maximo_ajuda": 5,
    "permite_gerar_codigo": false,
    "permite_solucoes_completas": false,
    "prefere_perguntas": true,
    "pistas_progressivas": true
  }
}
```

Só precisas de preencher a secção `credenciais` do fornecedor que vais
mesmo usar (indicado em `"fornecedor"`) — as outras podem ficar com o
placeholder, não são lidas.

### Fornecedores disponíveis

| `fornecedor` | Exemplo de `modelo` | Precisa de chave? |
|---|---|---|
| `openrouter` | `openai/gpt-4o-mini` (dá acesso a dezenas de modelos por uma única chave) | Sim |
| `gemini` | `gemini-1.5-flash` | Sim |
| `openai` | `gpt-4o-mini` (API direta da OpenAI) | Sim |
| `anthropic` | `claude-sonnet-5` (API direta da Anthropic) | Sim |
| `huggingface` | `deepseek-ai/DeepSeek-V4-Pro:deepinfra` (o `:fornecedor` no fim escolhe quem hospeda o modelo -- omite para a HF escolher automaticamente) | Sim |
| `ollama` | `llama3.2` (corre **localmente**, na tua máquina) | Não |
| `opencode` | modelo à escolha da tua subscrição OpenCode Go | Sim |

> **Ollama**: se estiveres a correr o `ollama serve` na tua própria
> máquina, não precisas de nenhuma chave de API — só de instalar a
> [Ollama](https://ollama.com), correr `ollama pull llama3.2` (ou o
> modelo que quiseres) e apontar `"fornecedor": "ollama"` no
> `config.json`. É o único fornecedor em que **nenhum dado sai da tua
> máquina** — nem para OpenRouter, nem OpenAI, nem ninguém — o que
> resolve de vez a preocupação de privacidade/RGPD dos logs (ver mais
> abaixo) para quem o usar assim. Se a Ollama estiver a correr noutra
> máquina/porta, ajusta `credenciais.ollama.host`.

> **Nota de segurança**: por pedido explícito, as credenciais ficam
> como valor direto neste ficheiro (não como referência a uma
> variável de ambiente). Se fores partilhar esta pasta (por exemplo,
> num repositório Git), tem cuidado para não incluíres o teu
> `config.json` real — só o `config.exemplo.json` deve ser partilhado.

### Campos da política pedagógica

| Campo | Por omissão | O que faz |
|---|---|---|
| `modo` | `"socratic"` | `"socratic"` prioriza perguntas; `"explicativo"` permite explicações diretas (nível 6) sem passar primeiro pelos níveis de pergunta |
| `nivel_maximo_ajuda` | `5` | Até que nível da escada (0-6) o Alguem pode chegar; o nível 7 (código) está **sempre** bloqueado, seja qual for este valor |
| `permite_gerar_codigo` | `false` | Se `false`, o *system prompt* proíbe explicitamente qualquer código ALGO, mesmo em exemplos |
| `permite_solucoes_completas` | `false` | Se `false`, proíbe soluções completas mesmo que o estudante insista |
| `prefere_perguntas` | `true` | Prioriza responder com perguntas em vez de afirmações diretas |
| `pistas_progressivas` | `true` | Começa sempre pelo nível menos revelador razoável, só desce se o estudante continuar preso |
| `usar_guardiao` | `true` | Se `true`, cada resposta é verificada por um segundo passo (o Guardião Pedagógico) antes de chegar ao estudante -- ver secção acima |

## A escada de níveis de ajuda

| Nível | Nome | O que dá |
|---|---|---|
| 0 | Autonomia | Nenhuma intervenção |
| 1 | Pergunta de reflexão | "O que precisa de acontecer primeiro?" |
| 2 | Pergunta orientadora | "Que dados precisa de obter antes de começar?" |
| 3 | Pista conceptual | Nomeia um conceito/estratégia geral |
| 4 | Pista algorítmica | Descreve o passo seguinte em prosa, sem pseudocódigo |
| 5 | Pseudocódigo parcial | Estrutura incompleta, com lacunas |
| 6 | Explicação explícita | Explica a estratégia por extenso, sem código ALGO |
| 7 | Código | **Sempre bloqueado**, seja qual for a política |

A decisão de subir de nível fica, nesta versão, inteiramente a cargo
do LLM (a partir do histórico da conversa) — não há um mecanismo no
código a forçar essa transição. Um controlo explícito disso (útil para
medir "*hint escalation*" com rigor, para efeitos de investigação) é
trabalho para uma fase seguinte.

## Métricas e logs

Cada sessão do Alguem fica registada em `logs/<data>_<id>.jsonl` (um
evento por linha, [JSON Lines](https://jsonlines.org/)) -- é a
matéria-prima para as métricas descritas na investigação. Nem todas
são calculáveis só a partir do que o sistema regista; a tabela abaixo
diz quais são e quais precisam de dados externos (testes, avaliação
qualitativa):

| Métrica | O que mede | O Alguem calcula sozinho? |
|---|---|---|
| **Solution Leakage Rate** | % de respostas que revelaram demais (classificadas `FULL_SOLUTION`/`CODE` pelo guardião) | ✅ Sim -- `python3 -m alguem.scripts.metricas` |
| **Hint Dependency** | Nº médio de pedidos de ajuda (turnos) por sessão/exercício | ✅ Sim |
| **Hint Escalation** | Nível mais alto da escada (0-7) atingido numa sessão | ⚠️ Aproximado a partir da categoria do guardião (não há uma classificação de nível dedicada, por decisão explícita -- pouparia uma chamada ao LLM por resposta) |
| **Student Agency** | % de passos da resolução propostos pelo estudante, não pelo tutor | ❌ Precisa de codificação qualitativa do texto -- o log preserva a conversa integral para isso |
| **Cognitive Progression** | Fase em que o estudante está (compreende → estratégia → algoritmo → implementa) | ❌ Precisa do modelo do estudante (ainda não implementado) ou codificação manual |
| **Delayed Transfer** | Desempenho num problema novo, mesmo conceito, depois de usar o Alguem | ❌ Desenho experimental -- o log identifica qual exercício/ficheiro esteve em cada sessão, para correlacionar depois |
| **Learning Gain** | Diferença pré-teste/pós-teste | ❌ Externo por definição |

### O que fica em cada evento

- **`inicio_sessao`**: fornecedor, modelo, política pedagógica completa
  (para poderes filtrar por configuração A/B/C na análise), ficheiros
  iniciais.
- **`tentativa_guardiao`**: cada avaliação do guardião, **incluindo as
  rejeitadas** -- com o texto da resposta proposta, mesmo essa nunca
  tendo chegado ao estudante. É decisão deliberada: sem isto não dá
  para investigar leakage a sério (RQ5). O texto do estudante que
  gerou cada tentativa também fica registado.
- **`resposta_final`**: o que o estudante realmente viu, quantas
  tentativas foram precisas, se veio da recusa segura fixa.
- **`ficheiros_atualizados`**: sempre que a visibilidade de ficheiros
  muda (início da sessão, ou `ficheiro nome.algo`).
- **`fim_sessao`**: número total de turnos.

Todos os eventos têm `timestamp`, `id_sessao` e `id_estudante`.

### Identificador de estudante

Gerado automaticamente na primeira vez que o Alguem corre nesta
instalação (`.estudante_id`, um UUID aleatório) e reutilizado em todas
as sessões seguintes -- sem pedir nada ao estudante, sem sistema de
contas. Não identifica a pessoa (não é o nome nem o email, só permite
distinguir "esta instalação" de "outra"), mas já é o suficiente para
juntar várias sessões da mesma pessoa ao longo do tempo (necessário
para RQ1/RQ3, que comparam desempenho ao longo de várias interações).

> Se estiveres a investigar com estudantes reais, o log continua a
> conter o texto integral das conversas e do código deles -- vale a
> pena rever isto com a tua comissão de ética/RGPD antes de recolher
> dados assim; isto aqui só implementa o mecanismo, não substitui esse
> processo.

### Calcular as métricas

```bash
python3 -m alguem.scripts.metricas            # usa alguem/logs/ por omissão
python3 -m alguem.scripts.metricas /outra/pasta
```

Dá um resumo global (nº de sessões, nº de estudantes distintos,
*Solution Leakage Rate* e *Hint Dependency* globais) e uma linha por
sessão. `alguem.scripts.metricas.gerar_relatorio(pasta)` devolve os
mesmos números em dicionários Python, para quem preferir analisar com
`pandas` ou semelhante em vez do resumo em texto.

### Comparar fornecedores/modelos entre si

Cada evento `inicio_sessao` regista o `fornecedor` e o `modelo` usados
nessa sessão -- por isso, trocar de fornecedor no `config.json` entre
sessões (dos 7 disponíveis, ver "Como configurar" acima) e depois
filtrar os logs por esse campo é o que dá para responder à pergunta da
secção 12 do documento de investigação: *"o comportamento pedagógico
do Alguem é consistente entre diferentes LLMs?"* -- sem precisar de
mais nenhuma instrumentação, já está tudo no mesmo formato de log,
seja qual for o fornecedor por trás.

## Arquitetura

```
alguem/
├── config.json / config.exemplo.json   # modelo + credenciais + política
├── config.py                            # lê o config.json, monta o Alguem
├── __init__.py                          # API pública do pacote
├── .estudante_id                        # gerado automaticamente (não versionar)
├── logs/                                 # um .jsonl por sessão (não versionar)
├── nucleo/
│   ├── politica_pedagogica.py           # PoliticaPedagogica (dataclass)
│   ├── escada_de_ajuda.py               # os 8 níveis
│   ├── conhecimento_algo.py             # sintaxe real do ALGO, para as pistas
│   ├── ficheiros_visiveis.py            # resolve 'incluir', recursivamente
│   ├── guardiao.py                       # classifica e filtra respostas reveladoras
│   ├── identidade.py                     # id de estudante persistente e automático
│   ├── registador.py                     # escreve os eventos .jsonl da sessão
│   ├── system_prompt.py                 # junta tudo num prompt
│   └── tutor.py                         # classe Alguem: mantém a conversa
├── fornecedores/
│   ├── base.py                          # AgenteLLM (classe abstrata)
│   ├── _base_openai_compativel.py       # lógica HTTP partilhada (ver abaixo)
│   ├── openrouter.py                    # FornecedorOpenRouter
│   ├── openai.py                         # FornecedorOpenAI
│   ├── huggingface.py                    # FornecedorHuggingFace
│   ├── opencode.py                       # FornecedorOpenCode
│   ├── gemini.py                        # FornecedorGemini (formato próprio)
│   ├── anthropic.py                      # FornecedorAnthropic (formato próprio)
│   └── ollama.py                         # FornecedorOllama (local, sem chave)
├── scripts/
│   └── metricas.py                       # calcula as métricas a partir dos logs
└── tests/                                # suite própria (não mistura com a do ALGO)
```

Acrescentar um fornecedor novo é: criar `fornecedores/novo.py` com uma
classe, e registá-la em `fornecedores/__init__.py` (e em `FORNECEDORES`
na fábrica). Se o fornecedor falar o formato "chat completions" da
OpenAI (a maioria fala), a classe herda de `_FornecedorEstiloOpenAI` e
só precisa de definir `URL_API` e `nome` -- ver `openai.py` como
exemplo mínimo. Se falar um formato diferente (como a Gemini ou a
Anthropic, que separam a instrução de sistema do resto da conversa),
herda diretamente de `AgenteLLM` e implementa `responder()` de raiz.
Nada mais precisa de mudar.

O ponto de entrada real é `algo_lang/cli.py` (a função `_chamar_alguem`,
acionada pelo `?` da consola) — este pacote não tem `cli.py` próprio de
propósito, para não haver uma segunda forma de chamar o Alguem por
fora da consola.

## Sobre os testes

Este ambiente de desenvolvimento não tem acesso de rede às APIs
nenhuma — por isso toda a suite de testes simula a camada HTTP
(`unittest.mock`). O que está confirmado: a construção correta do
pedido para cada um dos 7 fornecedores (incluindo casos próprios de
cada um -- a separação do *system prompt* na Gemini/Anthropic, o
`max_tokens` obrigatório e os blocos de resposta da Anthropic, a
Ollama sem chave obrigatória e com *host* configurável, o sufixo de
fornecedor de inferência da HuggingFace), a leitura correta da
resposta, o tratamento de erros (rede, HTTP, formato inesperado), a
política pedagógica, a escada de ajuda, a construção do *system
prompt*, a resolução de `incluir` (incluindo aninhada e tolerante a
erros de sintaxe), o guardião (heurística, cada categoria de
classificação, a regeneração até ao limite de tentativas, e que uma
resposta rejeitada nunca fica no histórico), o identificador de
estudante persistente, o registador de eventos (cada tipo de evento,
incluindo tentativas rejeitadas), o script de métricas (com dados
sintéticos, matemática confirmada à mão), e o fluxo completo do
`Tutor`/`Alguem`. **A chamada real às APIs, com credenciais
verdadeiras, só pode ser confirmada por
ti**, fora deste ambiente.

Todos os testes isolam os logs numa pasta temporária própria, sem
variáveis de ambiente: os testes deste pacote usam `monkeypatch` direto
às constantes de `registador.py`/`identidade.py`; os testes que correm
o comando `algo` a sério, num subprocesso (`algo_lang/tests/test_consola.py` e
`algo_lang/tests/test_consola_alguem.py`, na suite do ALGO), copiam o projeto
inteiro para uma pasta temporária e correm a partir de lá. Nenhum
teste escreve alguma vez na pasta real `alguem/logs/`.

```bash
cd alguem
python3 -m pytest tests/ -v
```

A integração com a consola (`?`, `ficheiros`, `ficheiro nome.algo`)
está testada em `algo_lang/tests/test_consola_alguem.py`, na suite do próprio
ALGO (`algo_lang/tests/`), não aqui — é lá que faz sentido, porque
testa o `cli.py` do ALGO, não este pacote.
