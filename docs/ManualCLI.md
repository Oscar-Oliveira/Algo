# Manual da Linha de Comandos — `algo`

Manual do estudante para o dia a dia com o ALGO: a consola interativa
(a forma normal de trabalhar), o editor (VS Code com realce de
sintaxe), e só no fim os detalhes de instalação do Python — não
precisas de ler essa parte se o script de arranque já te funcionou.

Para a sintaxe da própria linguagem (tipos, `estrutura`, funções...),
ver o `README.md` da raiz do projeto.

## Índice

1. [Abrir a consola](#1-abrir-a-consola)
2. [A consola interativa](#2-a-consola-interativa)
3. [Os três comandos, com todas as opções](#3-os-três-comandos-com-todas-as-opções)
4. [Onde ficam os ficheiros gerados](#4-onde-ficam-os-ficheiros-gerados)
5. [O editor: VS Code](#5-o-editor-vs-code)
6. [Detalhes técnicos (códigos de saída, limites)](#6-detalhes-técnicos-códigos-de-saída-limites)
7. [Se o script de arranque não funcionar: Python à mão](#7-se-o-script-de-arranque-não-funcionar-python-à-mão)

---

## 1. Abrir a consola

Dentro da pasta do ALGO, há um script diferente por sistema — corre o
teu:

| Sistema | Ficheiro | Como correr |
|---|---|---|
| Windows | `algo.bat` | duplo-clique (ou `algo.bat` numa consola) |
| macOS | `algo.command` | duplo-clique (ou `./algo.command` na Terminal) |
| Linux | `algo.sh` | `./algo.sh` num terminal |

Da primeira vez, demora uns segundos a preparar tudo sozinho (não
precisas de instalar nada à mão nem perceber o que está a acontecer);
nas vezes seguintes arranca logo. No fim, abre a consola:

```
$ ./algo.sh

                        _    _     ____   ___
       ####            / \  | |   / ___| / _ \
     ########         / _ \ | |  | |  _ | | | |
   ############      / ___ \| |__| |_| || |_| |
 ################   /_/   \_\_____\____| \___/

--------------------------------------------------------------

  Escreve um comando e prime Enter -- sem escrever "algo" à frente.
  Cada um tem também um atalho de uma letra (entre parêntesis).

    executa <ficheiro.algo>  (e)   compila e corre o programa
    verifica <ficheiro.algo> (v)   avisos de possíveis enganos
    fluxograma <ficheiro.algo> (f) gera um diagrama do programa

    ajuda  (a)                     esta lista, com mais detalhe e exemplos
    sair   (s)                     termina a consola

  Depois de usares um ficheiro uma vez, os comandos seguintes
  reutilizam-no -- não precisas de repetir o nome.
--------------------------------------------------------------

algo>
```

> **macOS**: da primeira vez que abrires `algo.command` por
> duplo-clique, o macOS pode recusar com "desenvolvedor não
> identificado" — clica com o **botão direito** → **Abrir** → confirma.
> Só acontece uma vez.

Se o script não funcionar de todo (mensagem de erro sobre Python em
falta), salta para a [secção 7](#7-se-o-script-de-arranque-não-funcionar-python-à-mão).

---

## 2. A consola interativa

É aqui que passas a maior parte do tempo: escreves um comando, vês o
resultado, corriges o teu ficheiro `.algo` no editor, e voltas a
escrever o comando — sem teres de repetir `algo` nem o nome do
ficheiro sempre que o usas outra vez.

```
algo> executa soma.algo
✔ Compilado para: soma/soma.py

----- Execução -----
5

algo> verifica
✔ Nenhum aviso — o linter não encontrou nada a assinalar.

algo> sair
Até à próxima!
```

Repara que o segundo comando (`verifica`) não precisou de indicar o
ficheiro outra vez — a consola lembra sempre o **último ficheiro usado
na sessão**, e só o pede de volta se indicares um nome diferente.

### Atalhos de uma letra

Para escreveres ainda menos:

| Atalho | Comando |
|---|---|
| `e` | `executa` |
| `v` | `verifica` |
| `f` | `fluxograma` |
| `a` | `ajuda` |
| `s` | `sair` |

```
algo> e soma.algo --debug
algo> v
algo> f --formato svg
```

### `ajuda`

Escreve `ajuda` (ou `a`) a qualquer momento para veres a lista de
comandos, as opções de cada um, exemplos, e o ficheiro atual da
sessão.

### Erros não fecham a consola

Um comando com erro — de compilação (sintaxe, tipos), ou um nome de
comando que não existe — só mostra o erro e volta ao prompt; nunca
fecha a consola. Se o erro foi de compilação, o ficheiro continua
"atual": corrige-o no editor e escreve só `e` outra vez, sem repetir o
nome.

### Sair

Qualquer um destes termina a sessão: `sair`, `exit`, `quit`, `s`, ou
`Ctrl+D`.

---

## 3. Os três comandos, com todas as opções

### `executa <ficheiro.algo>`

Compila e corre o programa.

| Opção | Efeito |
|---|---|
| `--mostrar-python` | mostra o código Python gerado antes de o executar |
| `--debug` | mostra na consola o valor das variáveis a cada passo da execução |
| `--json` | gera um `..._trace.json` com o trace completo, para abrir no [visualizador web](#4-onde-ficam-os-ficheiros-gerados) |
| `--entradas FICHEIRO` | com `--debug`/`--json`: lê os valores de `ler()` de um ficheiro de texto (um por linha), em vez de perguntar interativamente |

```
algo> e soma.algo
algo> e soma.algo --debug
algo> e soma.algo --json --entradas valores.txt
```

### `fluxograma <ficheiro.algo>`

Gera um diagrama do programa: o principal **e mais um para cada
função/procedimento**. Uma chamada a uma rotina tua aparece com
contorno duplo, em vez de misturar a lógica dela no mesmo diagrama.

| Opção | Efeito |
|---|---|
| `--funcao NOME` | gera só o fluxograma dessa função/procedimento |
| `--formato png\|svg\|pdf` | formato da imagem (por omissão: `png`) |

```
algo> f soma.algo
algo> f soma.algo --formato svg
algo> f soma.algo --funcao calcularMedia
```

Se tiveres o [Graphviz](https://graphviz.org/) instalado, a imagem
gera-se automaticamente a partir do `.dot`. Sem ele, só o `.dot` é
gerado — abre-o em qualquer visualizador de Graphviz online (basta
colar o conteúdo do ficheiro).

### `verifica <ficheiro.algo>`

Avisos de possíveis enganos (variáveis nunca usadas, comparações
sempre verdadeiras, etc.) sem impedir a compilação. Sem opções.

```
algo> v soma.algo
```

---

## 4. Onde ficam os ficheiros gerados

Tudo o que os comandos geram (`.py`, `.dot`, imagens, `.json`) fica
numa **subpasta com o nome do ficheiro `.algo`**, ao lado do próprio
ficheiro — cada comando só acrescenta os seus próprios ficheiros, sem
apagar os dos outros. Por exemplo, depois de correres `executa`,
`executa --json` e `fluxograma` sobre o mesmo `soma.algo`:

```
soma.algo
soma/
├── soma.py
├── soma.dot
├── soma.png
└── soma_trace.json
```

O `..._trace.json` gerado por `--json` abre-se no **visualizador
web**, disponível apenas na versão online do Algo (`/estatico/visualizador/`):
arrasta o `.json` para dentro da janela e usa as setas ← → para andares
passo a passo pela execução, com o valor de cada variável à vista.

---

## 5. O editor: VS Code

O ALGO não precisa de nenhum editor específico — qualquer um serve.
Mas há uma extensão mínima para o [VS Code](https://code.visualstudio.com/)
que dá cor ao código `.algo` (palavras-chave, tipos, texto,
comentários...), o que ajuda bastante a ler e a apanhar erros de
digitação.

### 5.1 Instalar a extensão

1. Dentro da pasta do ALGO, entra em
   `algo_lang/editors/vscode-algo/` — é **esta pasta** que vais copiar,
   não o que está lá dentro.
2. Copia a pasta inteira (`vscode-algo`) para a pasta de extensões do
   VS Code:
   - **Windows**: `%USERPROFILE%\.vscode\extensions\`
   - **macOS/Linux**: `~/.vscode/extensions/`
   - Se a pasta `extensions` não existir, cria-a.
3. Fecha o VS Code por completo e abre-o outra vez.
4. Abre (ou cria) um ficheiro `.algo` — o código deve aparecer
   colorido automaticamente.

### 5.2 Verificar se a extensão está atualizada

Se recebeste uma versão nova do ALGO, a extensão pode ter ficado com
palavras-chave novas por reconhecer. Cola isto num ficheiro `.algo`
qualquer, só para veres as cores — cobre **todas** as palavras-chave da
linguagem, mas **não o corras** (`executa`/`verifica`): tem de propósito
um `incluir` para um ficheiro que não existe e um `nulo` num sítio
inválido, só para caber tudo num único exemplo pequeno; vai dar erro se
tentares compilá-lo, o que é esperado:

```
algoritmo "Teste"

importar Matematica
incluir "lib.algo" como lib

constante LIMITE:inteiro = 10

estrutura Ponto
    x:inteiro
    y:inteiro

funcao dobro(x:inteiro):inteiro
    retornar x * 2

procedimento mover(ref p:Ponto)
    p.x = p.x + 1

inicio
    ativo:booleano = verdadeiro
    valor:inteiro = nulo
    afirmar dobro(2) == 4, "falhou"

    se ativo e nao falso entao
        escrever("sim")
    senao
        escrever("não")

    para i de 1 ate LIMITE passo 1 fazer
        se i mod 2 == 0 ou i div 2 == 0 entao
            continuar
        sair

    enquanto ativo fazer
        ativo = falso

    escolher valor
        caso 1
            escrever("um")
        contrario
            escrever("outro")

    ler(valor)
```

Se **todas** as palavras a negrito/azul acima (`algoritmo`, `importar`,
`incluir`, `como`, `constante`, `estrutura`, `funcao`, `retornar`,
`procedimento`, `ref`, `inicio`, `verdadeiro`, `nulo`, `afirmar`, `se`,
`e`, `nao`, `falso`, `entao`, `senao`, `escrever`, `para`, `de`, `ate`,
`passo`, `fazer`, `mod`, `ou`, `div`, `continuar`, `sair`, `enquanto`,
`escolher`, `caso`, `contrario`, `ler`) aparecerem destacadas de igual
forma, a extensão está atualizada. Se alguma aparecer como texto
normal (sem cor), a tua cópia da extensão é mais antiga do que a
versão do ALGO que tens — repete o passo 2 de [5.1](#51-instalar-a-extensão)
(copia a pasta `vscode-algo` outra vez, substituindo a antiga) e
reinicia o VS Code.

> As cores em si vêm do teu tema do VS Code, não da extensão — o que a
> extensão garante é que cada palavra-chave, tipo, etc. tem um estilo
> **diferente** do texto normal, seja qual for o tema.

---

## 6. Detalhes técnicos (códigos de saída, limites)

Só relevante se estiveres a correr o ALGO a partir de um script, ou
quiseres perceber porque é que um programa foi interrompido.

- **Códigos de saída**: `0` em sucesso; qualquer erro de compilação ou
  de execução termina com um código diferente de zero.
- **Limite de tempo**: `algo executa` (sem `--debug`/`--json`) pára ao
  fim de **10s de tempo de CPU** — não de relógio, por isso não
  interrompe um programa à espera de `ler()`. Serve para apanhar
  ciclos infinitos. Com `--debug`/`--json`, o limite é de 4000 passos
  executados ou 10s de CPU acumulado, o que vier primeiro. Estes
  limites podem ser ajustados por invocação com `--limite-cpu SEGUNDOS`
  (sem `--debug`/`--json`) ou `--max-passos N`/`--limite-tempo SEGUNDOS`
  (com `--debug`/`--json`), sem editar o compilador.

---

## 7. Se o script de arranque não funcionar: Python à mão

Esta secção só é preciso ler se `algo.bat`/`algo.sh`/`algo.command`
(secção 1) te deu erro. O motivo mais comum é o **Python não estar
instalado** no teu computador.

### 7.1 Instalar o Python

1. Vai a [python.org/downloads](https://www.python.org/downloads/) e
   descarrega a versão para o teu sistema (precisas de **3.8 ou
   mais recente**).
2. Abre o instalador.
   - **Windows**: no primeiro ecrã, marca a caixa **"Add python.exe to
     PATH"** antes de clicares em "Install Now" — se saltares este
     passo, o computador não vai encontrar o Python depois, e tens de
     desinstalar e instalar outra vez.
   - **macOS**: segue o instalador normalmente (Continuar, Continuar,
     Instalar).
   - **Linux**: a maioria das distribuições já vem com Python; para
     confirmar, `python3 --version` num terminal.
3. Confirma que ficou instalado, num terminal:
   ```bash
   python3 --version        # Linux / macOS
   python --version         # Windows
   ```
   Deve aparecer `Python 3.x.x`.
4. Volta a correr o script da [secção 1](#1-abrir-a-consola) — desta
   vez deve funcionar.

### 7.2 Correr sem o script (avançado)

Se ainda assim preferires não depender do script de arranque, há duas
alternativas equivalentes:

```bash
pip install -e .                        # instala o comando 'algo' no teu Python
algo executa meuprograma.algo
```

```bash
# sem instalar nada -- aponta diretamente para o módulo Python
python3 -m algo_lang.cli executa meuprograma.algo    # Linux/macOS
python -m algo_lang.cli executa meuprograma.algo     # Windows
```

Nos dois casos, `executa`/`fluxograma`/`verifica` e todas as opções da
[secção 3](#3-os-três-comandos-com-todas-as-opções) funcionam
exatamente da mesma forma.
