# Manual Completo do ALGO — Instalação, Atualização e Utilização

Este manual assume que nunca instalaste nada disto antes. Vai passo a
passo desde instalar o que falta no teu computador até escreveres e
correres o teu primeiro programa ALGO dentro do VS Code. Não precisas
de saber nada de informática para além de ligar o computador e saber
onde ficam as tuas pastas.

## Índice

1. [O que vais instalar, em resumo](#1-o-que-vais-instalar-em-resumo)
2. [Instalar o Python](#2-instalar-o-python)
3. [Instalar o Visual Studio Code](#3-instalar-o-visual-studio-code)
4. [Obter os ficheiros do ALGO](#4-obter-os-ficheiros-do-algo)
5. [Instalar o ALGO — três formas possíveis](#5-instalar-o-algo--três-formas-possíveis)
6. [Instalar a extensão do ALGO no VS Code](#6-instalar-a-extensão-do-algo-no-vs-code)
7. [Criar o teu primeiro ficheiro `.algo`](#7-criar-o-teu-primeiro-ficheiro-algo)
8. [Abrir o terminal dentro do VS Code](#8-abrir-o-terminal-dentro-do-vs-code)
9. [Correr o teu programa](#9-correr-o-teu-programa)
10. [Visualizador web — ver a execução passo a passo](#10-visualizador-web--ver-a-execução-passo-a-passo)
11. [Referência rápida dos comandos](#11-referência-rápida-dos-comandos)
12. [Atualizar para uma versão nova](#12-atualizar-para-uma-versão-nova)
13. [Resolução de problemas comuns](#13-resolução-de-problemas-comuns)

---

## 1. O que vais instalar, em resumo

| Programa | Para quê | Já tens? |
|---|---|---|
| **Python** | É o que o ALGO usa por trás — sem ele, nada funciona | Provavelmente não |
| **Visual Studio Code** ("VS Code") | O editor onde vais escrever o código e correr os comandos | Talvez não |
| **ALGO** | A linguagem e o compilador em si (os ficheiros que te deram) | Não (é o que vamos instalar) |
| **Extensão ALGO do VS Code** | Dá cor ao código ALGO dentro do VS Code, para ser mais fácil de ler | Não |

Se já tiveres o Python e/ou o VS Code instalados, passa à frente essas
secções.

---

## 2. Instalar o Python

### Windows

1. Vai a [python.org/downloads](https://www.python.org/downloads/) e
   clica no botão amarelo grande para descarregar.
2. Abre o ficheiro descarregado.
3. **Muito importante**: no primeiro ecrã do instalador, marca a caixa
   em baixo que diz **"Add python.exe to PATH"** (ou "Add Python to
   PATH"), antes de clicares em "Install Now". Se não marcares esta
   caixa, o computador não vai conseguir encontrar o Python depois.
4. Deixa o instalador terminar.

### macOS

1. Vai a [python.org/downloads](https://www.python.org/downloads/) e
   descarrega a versão para macOS.
2. Abre o ficheiro `.pkg` descarregado e segue o instalador (Continuar,
   Continuar, Instalar).

### Linux

A maior parte das distribuições Linux já vem com Python instalado. Para
confirmar, ou instalar se faltar:

```bash
python3 --version
```

Se não aparecer um número de versão, instala com o gestor de pacotes da
tua distribuição (por exemplo, no Ubuntu/Debian: `sudo apt install
python3`).

### Confirmar que ficou instalado

Abre um terminal (ver secção 8 se ainda não souberes como) e escreve:

```bash
python3 --version        # Linux / macOS
python --version         # Windows
```

Deve aparecer algo como `Python 3.11.4` (o número pode ser diferente,
desde que comece por `3.8` ou mais).

---

## 3. Instalar o Visual Studio Code

1. Vai a [code.visualstudio.com](https://code.visualstudio.com/) e
   clica no botão de descarregar para o teu sistema.
2. Abre o ficheiro descarregado e segue o instalador (as opções por
   omissão servem perfeitamente).
3. Abre o VS Code para confirmares que ficou instalado — deve aparecer
   uma janela escura com um menu do lado esquerdo.

---

## 4. Obter os ficheiros do ALGO

- [ ] Extrai o ficheiro `.zip` que te deram para uma pasta fácil de
      encontrar — por exemplo, o Ambiente de Trabalho, ou uma pasta
      `Documentos\ALGO`.
- [ ] Confirma que, depois de extraíres, vês ficheiros como
      `pyproject.toml`, `README.md`, `algo.sh`, `algo.bat`,
      `algo.command`, e uma pasta chamada `algo_lang`. Se só vires uma
      *outra* pasta lá dentro (com estes ficheiros dentro dela), é
      porque o `.zip` tem uma pasta extra por fora — usa essa pasta de
      dentro a partir de agora.

A partir daqui, vou chamar a esta pasta **a pasta do ALGO**.

---

## 5. Instalar o ALGO — três formas possíveis

Só precisas de escolher **uma**. Se não tiveres a certeza, usa a
primeira (script de arranque) — é a mais simples.

### 5a. Script de arranque (mais simples, recomendado)

Dentro da pasta do ALGO, há um script diferente para cada sistema:

| Sistema | Ficheiro | Como correr |
|---|---|---|
| Windows | `algo.bat` | duplo-clique |
| macOS | `algo.command` | duplo-clique |
| Linux | `algo.sh` | `./algo.sh` num terminal |

Da primeira vez que o corres, demora uns segundos a preparar tudo
sozinho (não precisas de fazer mais nada — nem instalar mais nada à
mão). Nas vezes seguintes, arranca logo.

> **macOS**: da primeira vez que abrires `algo.command`, o macOS pode
> recusar com um aviso de "desenvolvedor não identificado". Clica com o
> **botão direito** no ficheiro → **Abrir** → confirma. Só acontece uma
> vez.

### 5b. Instalação manual com `pip`

Se preferires o processo "tradicional" do Python: abre um terminal
dentro da pasta do ALGO (ver secção 8) e escreve:

```bash
pip install -e .
```

Isto instala o comando `algo`, que passas a poder usar diretamente:

```bash
algo executa exemplos/soma.algo
```

### 5c. Execução direta com Python (sem usar o comando `algo`)

Há uma terceira forma de invocar o ALGO sem depender do comando `algo`
estar disponível — útil se, por alguma razão, esse comando não for
reconhecido no teu terminal.

- **Se instalaste com 5b** (pip, diretamente no teu Python): funciona
  logo, de qualquer pasta:

  ```bash
  python3 -m algo_lang.cli executa meus-programas/ola.algo   # Linux/macOS
  python -m algo_lang.cli executa meus-programas/ola.algo    # Windows
  ```

- **Se instalaste com 5a** (script de arranque): o ALGO ficou instalado
  só dentro da pasta `.venv` que o script criou, não no teu Python
  "principal" — por isso tens de apontar diretamente para o Python de
  lá dentro:

  ```bash
  .venv/bin/python -m algo_lang.cli executa meus-programas/ola.algo    # Linux/macOS
  .venv\Scripts\python -m algo_lang.cli executa meus-programas\ola.algo   # Windows
  ```

Nos dois casos, funciona exatamente da mesma forma que `algo executa
...`, só com um nome mais comprido para invocar.

---

## 6. Instalar a extensão do ALGO no VS Code

Isto dá cor ao teu código ALGO no VS Code (palavras-chave a azul,
texto a laranja, etc.), tornando-o muito mais fácil de ler.

1. Dentro da pasta do ALGO, entra em `algo_lang/editors/vscode-algo/` —
   repara que esta é a pasta que vais copiar, não o que está dentro dela.
2. Copia essa pasta inteira (`vscode-algo`) para a pasta de extensões
   do VS Code:
   - **Windows**: cola em `%USERPROFILE%\.vscode\extensions\`
     (podes colar isto na barra de endereços do Explorador de
     Ficheiros para ires diretamente lá)
   - **macOS / Linux**: cola em `~/.vscode/extensions/`
   - Se a pasta `extensions` não existir ainda, cria-a — é normal se
     for a primeira extensão que instalas manualmente.
3. Fecha o VS Code completamente e abre-o outra vez.
4. Para confirmares que funcionou: abre (ou cria) um ficheiro que
   termine em `.algo` — o código deve aparecer colorido automaticamente.

---

## 7. Criar o teu primeiro ficheiro `.algo`

1. Abre o VS Code.
2. No menu superior, **Ficheiro → Abrir Pasta...** (em inglês, *File →
   Open Folder...*), e escolhe **a pasta do ALGO** (a mesma da secção 4
   — a que tem o `pyproject.toml`, o `algo.sh`/`algo.bat`, etc.).

   > Porquê a pasta do ALGO, e não uma pasta separada para os teus
   > programas? Porque os scripts de arranque (`algo.sh`/`algo.bat`/
   > `algo.command`) só funcionam diretamente a partir de dentro desta
   > pasta (ou de uma pasta lá dentro) — se criares os teus programas
   > noutro sítio qualquer, terias sempre de indicar o caminho todo até
   > lá. Dentro da pasta do ALGO, podes à vontade criar uma pasta tua,
   > por exemplo `meus-programas/`, para os teres organizados.
3. No painel do lado esquerdo (o **Explorador**), clica com o botão
   direito na pasta e escolhe **Novo Ficheiro...** (ou usa o ícone de
   "novo ficheiro" — uma folha de papel com um `+` — depois de
   selecionares onde o queres criar). Se quiseres, cria primeiro uma
   pasta `meus-programas` (botão direito → **Nova Pasta...**) e cria o
   ficheiro lá dentro.
4. Escreve o nome do ficheiro terminado em `.algo`, por exemplo:
   `ola.algo`, e prime Enter.
5. Cola ou escreve este código:

```
algoritmo "Ola"
inicio
    escrever("Ola, ALGO!")
```

6. Guarda com `Ctrl+S` (Windows/Linux) ou `Cmd+S` (macOS).

Se instalaste a extensão (secção 6), deves ver as palavras `algoritmo`,
`inicio` e `escrever` com uma cor diferente do resto do texto.

---

## 8. Abrir o terminal dentro do VS Code

O terminal é onde vais escrever os comandos para correr o teu programa.

1. No menu superior do VS Code: **Terminal → Novo Terminal** (em
   inglês, *Terminal → New Terminal*).
2. Aparece um painel em baixo, normalmente com um fundo escuro e um
   cursor a piscar — é aqui que escreves os comandos.
3. Confirma que este terminal abriu **na pasta certa** (a pasta que
   abriste no passo 7.2) — normalmente o próprio terminal já mostra o
   caminho da pasta antes do cursor.

> **Atalho**: também podes abrir/fechar o terminal com `` Ctrl+` ``
> (a tecla do acento grave, ao lado do "1", em cima do Tab) em
> qualquer sistema.

---

## 9. Correr o teu programa

Tens duas formas de correr o `ola.algo` que criaste — usa a que
preferires.

### 9a. Comando direto

No terminal que abriste (a partir da pasta do ALGO — ver a nota da
secção 7), usa o comando correspondente à forma que escolheste
instalar na secção 5:

```bash
algo executa meus-programas/ola.algo                                    # 5b
./algo.sh executa meus-programas/ola.algo                               # 5a no Linux/macOS
algo.bat executa meus-programas\ola.algo                                # 5a no Windows
.venv/bin/python -m algo_lang.cli executa meus-programas/ola.algo       # 5c, depois de 5a (Linux/macOS)
python -m algo_lang.cli executa meus-programas\ola.algo                 # 5c, depois de 5b (Windows)
```

**Esperado**: aparece `Ola, ALGO!` no terminal.

### 9b. Consola interativa

Se escreveres só `algo` (ou `./algo.sh`, ou `algo.bat`, consoante a
forma que escolheste na secção 5) — **sem mais nada a seguir** — e
premires Enter, abre uma **consola**: uma "sessão" onde escreves os
comandos um a um, sem teres de repetir a palavra `algo` nem o nome do
ficheiro sempre que o usas outra vez.

```
$ ./algo.sh
--------------------------------------------------------------
  Consola ALGO
--------------------------------------------------------------
  ...

algo> executa meus-programas/ola.algo
✔ Compilado para: meus-programas/ola/ola.py
----- Execução -----
Ola, ALGO!

algo> sair
```

Isto é especialmente útil quando estás a trabalhar no mesmo ficheiro
durante um bocado — escreves, corres, corriges, corres outra vez —
sem teres de repetir tudo. Escreve `ajuda` a qualquer momento para
veres todos os comandos disponíveis, e `sair` para terminares a
consola.

Cada comando tem também um atalho de uma letra, para escreveres ainda
menos: `e` (executa), `c` (compila), `l` (lint), `f` (fluxograma), `a`
(ajuda). Por exemplo, `e meus-programas/ola.algo` funciona exatamente
como `executa meus-programas/ola.algo`.

### Onde vai parar o resultado

Depois de correres `algo executa meus-programas/ola.algo`, aparece uma
pasta nova `ola/` dentro de `meus-programas/`, ao lado do `ola.algo`,
com um ficheiro `ola.py` lá dentro — é o código Python que o ALGO
gerou automaticamente a partir do teu programa. Não precisas de mexer
nesse ficheiro.

---

## 10. Visualizador web — ver a execução passo a passo

Para programas com mais do que uma instrução, é muito útil poder ver o
programa a correr **devagar, um passo de cada vez**, com o valor de
cada variável à vista em cada momento — em vez de só veres o resultado
final no terminal. É para isso que serve o visualizador web.

### 10.1 Gerar o ficheiro de trace

Cria um programa com um bocadinho mais de conteúdo, por exemplo
`meus-programas/soma.algo`:

```
algoritmo "Soma"
inicio
    total:inteiro = 0
    i:inteiro
    para i de 1 ate 3 fazer
        total = total + i
    escrever("Total = ", total)
```

E corre-o com a opção `--json`:

```bash
algo executa meus-programas/soma.algo --json
```

**Esperado**: além do resultado normal, aparece uma linha `✔ Trace
gerado: .../soma_trace.json`. Este ficheiro `.json` (dentro da pasta
`meus-programas/soma/`, ao lado do `soma.py`) tem guardado o valor de
**todas as variáveis, em todos os passos** da execução — é o que o
visualizador vai ler.

### 10.2 Abrir o visualizador

O visualizador está na pasta do ALGO, em
`visualizador/algo-trace-viewer.html`. Dá duplo-clique nesse ficheiro
— abre no teu navegador normal (Chrome, Edge, Firefox, o que tiveres
por omissão). Não precisa de nenhuma instalação.

### 10.3 Carregar o trace

Na página que abriu, arrasta o ficheiro `soma_trace.json` (o que
geraste em 10.1) para dentro da janela, ou usa o botão para o
escolheres a partir de uma pasta.

**Esperado**: aparece o código do teu programa de um lado, e do outro
as variáveis com os seus valores. Usa os botões de avançar/recuar (ou
as setas do teclado, ← →) para andares passo a passo pela execução —
repara como a linha destacada e o valor de `total` vão mudando a cada
passo, até chegar a `total = 6`.

> Este ficheiro HTML é independente — não precisas de o abrir de
> dentro do VS Code nem de ter o ALGO a correr ao mesmo tempo. Podes
> até copiá-lo para outro computador sozinho, desde que leves também o
> `.json` que queres analisar.

---

## 11. Referência rápida dos comandos

| Comando | O que faz |
|---|---|
| `algo executa ficheiro.algo` | Compila e corre o programa |
| `algo executa ficheiro.algo --mostrar-python` | Mostra o código Python gerado antes de correr |
| `algo executa ficheiro.algo --debug` | Mostra o valor das variáveis a cada passo da execução |
| `algo executa ficheiro.algo --json` | Gera um ficheiro `.json` com o *trace* completo, para o visualizador web (secção 10) |
| `algo executa ficheiro.algo --json --entradas dados.txt` | Como acima, mas lendo os valores de `ler()` de um ficheiro de texto em vez de perguntar um a um |
| `algo compila ficheiro.algo` | Só compila (gera o `.py`, não corre) |
| `algo compila ficheiro.algo --minimo` | Gera Python mínimo, sem verificação de tipos prévia nem funções de apoio — útil para veres o Python "a seco" por trás do ALGO |
| `algo lint ficheiro.algo` | Avisa sobre enganos comuns (variáveis não usadas, comparações sempre verdadeiras, etc.) |
| `algo fluxograma ficheiro.algo` | Gera um diagrama do programa (principal + um por função/procedimento) |
| `algo fluxograma ficheiro.algo --funcao nome` | Gera o fluxograma só dessa função/procedimento |
| `algo fluxograma ficheiro.algo --formato svg` | Formato da imagem: `png` (por omissão), `svg` ou `pdf` |
| `algo` (sem mais nada) | Abre a consola interativa (secção 9b) |

Dentro da consola interativa, cada um destes comandos tem também um
atalho de uma letra: `e` (executa), `c` (compila), `l` (lint), `f`
(fluxograma), `a` (ajuda).

Todos os ficheiros gerados (`.py`, `.dot`, imagens, `.json`) ficam
numa **subpasta com o nome do programa**, ao lado do ficheiro `.algo`
original — por exemplo, `meuprograma.algo` gera
`meuprograma/meuprograma.py`, nunca um ficheiro solto ao lado do
código-fonte.

---

## 12. Atualizar para uma versão nova

Quando receberes uma versão nova do ALGO:

- **Se extraíres o `.zip` novo por cima da pasta antiga** (mesmo nome,
  mesmo sítio): não precisas de fazer mais nada — corre o script de
  arranque (ou o comando `algo`) normalmente, já vais estar a usar a
  versão nova.
- **Se extraíres para uma pasta nova ou com nome diferente**: corre o
  script de arranque de dentro dessa pasta nova — ele prepara tudo do
  zero automaticamente, tal como da primeira vez.
- **Se tiveres instalado com `pip install -e .`**: volta a correr esse
  mesmo comando de dentro da pasta nova.

A extensão do VS Code (secção 6) só precisa de ser reinstalada se a
pasta `algo_lang/editors/vscode-algo` tiver mudado — copia-a outra vez
por cima da anterior, se não tiveres a certeza.

---

## 13. Resolução de problemas comuns

**"python não é reconhecido" / "python3: command not found"**
O Python não está instalado, ou não ficou no PATH. Revê a secção 2 — no
Windows, confirma que marcaste "Add python.exe to PATH" no instalador
(se te esqueceste, o mais simples é desinstalar e instalar outra vez,
desta vez com a caixa marcada).

**"algo não é reconhecido" / "algo: command not found"**
Se instalaste com `pip install -e .`, confirma que o comando correu sem
erros. Se preferires não depender do comando `algo` ficar disponível,
usa a forma 5c (`python -m algo_lang.cli ...`), que funciona sempre.

**O código no VS Code não aparece colorido**
Confirma que copiaste a pasta `vscode-algo` (não só os ficheiros lá de
dentro) para a pasta de extensões, e que fechaste e voltaste a abrir o
VS Code depois. Confirma também que o nome do ficheiro termina mesmo
em `.algo`.

**macOS: "algo.command não pode ser aberto"**
Clica com o botão direito no ficheiro → Abrir → confirma. Só acontece
da primeira vez.

**O visualizador abre mas fica em branco, ou não carrega o `.json`**
Confirma que estás ligado à internet (o visualizador vai buscar duas
bibliotecas — React e Tailwind — a partir da internet, só na primeira
vez que a página abre) e que o ficheiro que arrastaste é mesmo um
`..._trace.json` gerado com `--json` (não o `.py` nem o `.algo`).

**O terminal abriu na pasta errada**
Escreve `cd caminho/para/a/pasta` (substitui pelo caminho real) para
mudares de pasta, ou fecha o terminal e abre outro depois de teres a
pasta certa aberta no VS Code (secção 7.2).

**Nenhuma das opções acima resolveu**
Lê a mensagem de erro completa — na maior parte dos casos ela já diz
exatamente o que falta.
