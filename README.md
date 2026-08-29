# Algo + Alguem — projeto completo

**Algo** é uma linguagem algorítmica em português (pseudocódigo
estruturado, executável) para ensinar programação e pensamento
algorítmico. **Alguem** é o tutor baseado em LLM que a acompanha —
ajuda sem nunca resolver o exercício pelo estudante.

Este pacote junta tudo: o compilador, a extensão do VS Code, o
visualizador de execução passo a passo, o tutor Alguem, e o serviço
web (várias contas, cada uma com o seu próprio ficheiro/biblioteca,
cada uma com o seu fornecedor de LLM). **Os dois modos de uso — linha
de comandos e serviço web — partilham exatamente o mesmo compilador**,
nunca alterado entre um e outro (ver `docs/` para a confirmação disto,
se precisares).

## Como usar — dois modos

### 1. Linha de comandos (uso individual, numa máquina)

```bash
./algo.sh        # Linux/macOS -- ./algo.command também funciona no macOS
algo.bat         # Windows
```

Instala tudo o que for preciso na primeira vez (ambiente virtual
Python) e abre a consola interativa. `algo executa`, `algo fluxograma`,
`algo verifica`. Referência completa em `docs/ManualCLI.md`.

### 2. Serviço web (várias pessoas, cada uma com a sua conta)

```bash
cd online
cp .env.exemplo .env   # preenche as duas chaves (instruções no ficheiro)
docker compose up -d --build
```

Cada estudante cria a sua própria conta e configura o seu próprio
fornecedor de LLM. Editor com realce de sintaxe, execução isolada por
processo, fluxograma, rasto (download do `.json` + ligação para o
visualizador), painéis redimensionáveis. Detalhes completos,
arquitetura, e o que ainda falta testar em `online/README.md`.

## Estrutura

```
.
├── algo.sh / algo.bat / algo.command   # arranque da consola local
├── algo_lang/          # o compilador -- nunca alterado entre CLI e online
│   ├── tests/            # suite de testes do compilador (CLI)
│   └── editors/vscode-algo/ # extensão de realce de sintaxe para VS Code
├── alguem/              # o tutor LLM -- reaproveitado tal e qual pelos dois modos
├── online/                # o serviço web (FastAPI) -- ver online/README.md
├── visualizador/              # visualizador autónomo do rasto (algo-trace-viewer.html)
├── exemplos/                    # programas Algo de exemplo, organizados por assunto (01_variaveis_tipos/, 02_operadores/, ...)
└── docs/                            # manual da CLI, decisões de design (bin/: material arquivado)
```

## `docs/` — manuais e material de apoio

| Ficheiro | Para quem |
|---|---|
| `ManualCLI.md` | Manual do estudante: consola interativa, extensão do VS Code, e (por fim) instalar Python e usar a linha de comandos |
| `bin/` | Material arquivado — versões supersedidas ou não atualizadas (manual de instalação anterior, roteiro de testes manuais, sebenta de exercícios, guia do docente, referência completa da linguagem em Word e em Markdown) |

## Sub-projetos com o seu próprio README

Cada parte tem documentação própria, mais detalhada do que cabe aqui:
- `alguem/README.md` — arquitetura do tutor, política pedagógica, fornecedores de LLM, guardião, métricas
- `online/README.md` — arquitetura do serviço web, decisões de design, como arrancar (com ou sem Docker), o que ainda falta testar

## Estado dos testes

- `algo_lang` (compilador): 959 testes — corre com `python3 -m pytest algo_lang/tests/`
- `alguem` (tutor): 215 testes — corre com `python3 -m pytest alguem/tests/`
- `online` (serviço web): 302 testes — corre com `cd online && python3 -m pytest`

## O que ainda não está confirmado (honestidade)

- O `online/` nunca correu num browser real — só a API por trás foi
  testada, a sério, com um servidor `uvicorn` real (ver
  `online/README.md` para o detalhe do que foi e não foi confirmado).
- O `docker-compose.yml` e o `Dockerfile` do `online/` nunca foram
  construídos nem corridos neste ambiente de desenvolvimento (sem
  acesso a Docker) — revistos manualmente, não testados de facto.
