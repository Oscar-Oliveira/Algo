# ALGO Language — realce de sintaxe para VS Code

Extensão mínima que dá realce de sintaxe (cores) a ficheiros `.algo` no
Visual Studio Code: palavras-chave, tipos, cadeias de texto, caracteres,
comentários, números, chamadas a bibliotecas (`matematica.raiz`), nomes de
funções/procedimentos/estruturas, etc.

## Instalação (pasta desempacotada — mais simples)

1. Copia esta pasta (`vscode-algo`) para a pasta de extensões do VS Code:
   - **Windows:** `%USERPROFILE%\.vscode\extensions\`
   - **macOS/Linux:** `~/.vscode/extensions/`
2. Reinicia o VS Code.
3. Abre qualquer ficheiro `.algo` — o realce de sintaxe é ativado
   automaticamente.

## Instalação alternativa (empacotada, `.vsix`)

Se tiveres o `vsce` instalado (`npm install -g @vscode/vsce`):

```bash
cd vscode-algo
vsce package
code --install-extension algo-language-0.1.0.vsix
```

## O que está incluído

- `package.json` — associa a extensão `.algo` à linguagem `algo`
- `language-configuration.json` — comentários (`//`, `/* */`),
  emparelhamento de parênteses/chavetas/parênteses retos, auto-indentação
  depois de linhas que abrem um bloco (`se...entao`, `para...fazer`,
  `funcao`, `estrutura`, `escolher`, `caso`, etc.)
- `syntaxes/algo.tmLanguage.json` — gramática TextMate com o realce de
  sintaxe propriamente dito

## Testado com o motor real do VS Code

A gramática foi validada com as bibliotecas `vscode-textmate` e
`vscode-oniguruma` (as mesmas que o VS Code usa internamente) sobre um
ficheiro de exemplo cobrindo toda a linguagem — declarações, tipos,
`estrutura`, `funcao`/`procedimento`, `constante`, comentários de bloco,
literais de array, `afirmar`, chamadas a bibliotecas, e todos os
operadores — não é só "parece bem", foi tokenizado a sério e conferido
token a token. As regras de auto-indentação (`increaseIndentPattern`/
`decreaseIndentPattern`) foram também testadas linha a linha contra
todas as construções da linguagem.

## Personalizar cores

As cores concretas vêm do teu tema do VS Code (não desta extensão). Se
quiseres afinar cores específicas para o ALGO, podes mapear os âmbitos
(`scope`) usados na gramática (ex: `keyword.control.algo`,
`storage.type.algo`, `support.function.algo`) nas definições
`editor.tokenColorCustomizations` do teu `settings.json`.
