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
`vscode-oniguruma` (as mesmas que o VS Code usa internamente) sobre
ficheiros de exemplo cobrindo boa parte da linguagem — declarações, tipos,
`estrutura`, `funcao`/`procedimento`, `constante`, comentários de bloco,
literais de array, `afirmar`, chamadas a bibliotecas, operadores, acesso a
campo de estrutura, `nulo`. Uma auditoria já encontrou casos reais que uma
verificação manual anterior tinha deixado passar (ex.: `nulo` sem
highlighting nenhum, acesso a campo colorido como chamada de biblioteca) —
por isso esta secção já não afirma cobertura exaustiva "token a token";
trata-se de validação pontual, não de uma garantia contínua. A única
garantia reproduzível e automática que existe hoje é
`test_vscode_grammar_nao_esquece_nenhuma_palavra_chave_do_lexer` (em
`algo_lang/tests/test_correcoes_auditoria.py`), que compara a lista de
palavras-chave do lexer com a gramática a cada corrida da suite de testes
— cobre só a presença de cada palavra-chave, não a correção do scope
atribuído. As regras de auto-indentação
(`increaseIndentPattern`/`decreaseIndentPattern`) foram testadas
manualmente linha a linha, com o mesmo aviso: sem teste automático
equivalente ainda.

## Personalizar cores

As cores concretas vêm do teu tema do VS Code (não desta extensão). Se
quiseres afinar cores específicas para o ALGO, podes mapear os âmbitos
(`scope`) usados na gramática (ex: `keyword.control.algo`,
`storage.type.algo`, `support.function.algo`) nas definições
`editor.tokenColorCustomizations` do teu `settings.json`.
