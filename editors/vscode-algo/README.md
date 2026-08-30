# ALGO Language — realce de sintaxe e diagnósticos para VS Code

Extensão que dá realce de sintaxe (cores) a ficheiros `.algo` no Visual
Studio Code — palavras-chave, tipos, cadeias de texto, caracteres,
comentários, números, chamadas a bibliotecas (`matematica.raiz`), nomes de
funções/procedimentos/estruturas, etc. — e assinala erros/avisos do
compilador diretamente no editor (ver secção "Diagnósticos").

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

## Diagnósticos (erros e avisos no editor)

Ao gravar (ou abrir) um ficheiro `.algo`, a extensão corre `algo verifica
--json` em segundo plano e mostra o resultado como sublinhados vermelhos
(erros léxicos/sintáticos/semânticos) ou amarelos (avisos do linter) —
reaproveita o compilador real (`algo_lang/compilador/`), sem o modificar;
ver `algo_lang/cli.py:_cmd_verifica_json`.

Para encontrar o executável `algo`, por esta ordem:

1. A definição `algo.caminhoExecutavel`, se a preencheres (`Ficheiro →
   Preferências → Definições`, procura por "ALGO").
2. Um `.venv` local (na pasta do ficheiro aberto ou nalgum antepassado até à
   raiz do workspace) — o mesmo `.venv` que `algo.sh`/`algo.bat` criam.
3. Um `algo` simples, à espera de o encontrar no `PATH`.

Se nenhum resultar, aparece um aviso uma única vez por sessão com um atalho
para a definição.

### Limitações conhecidas (v1)

- Só corre ao gravar/abrir, não a cada tecla — isso exigiria escrever o
  conteúdo não gravado num ficheiro temporário, o que partiria a resolução
  de `incluir` contra ficheiros irmãos.
- Ficheiros com um `incluir` quebrado (biblioteca em falta, colisão de
  nomes) ou com bytes inválidos não-UTF-8 não produzem diagnósticos nessa
  corrida (o compilador sai antes de haver JSON para imprimir) — os
  diagnósticos anteriores ficam visíveis até à próxima corrida bem-sucedida,
  em vez de serem apagados às cegas.

## O que está incluído

- `package.json` — associa a extensão `.algo` à linguagem `algo`, regista o
  tema de ícones e a definição `algo.caminhoExecutavel`
- `language-configuration.json` — comentários (`//`, `/* */`),
  emparelhamento de parênteses/chavetas/parênteses retos, auto-indentação
  depois de linhas que abrem um bloco (`se...entao`, `para...fazer`,
  `funcao`, `estrutura`, `escolher`, `caso`, etc.)
- `syntaxes/algo.tmLanguage.json` — gramática TextMate com o realce de
  sintaxe propriamente dito
- `extension.js` — ativação da extensão e diagnósticos (ver acima)

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

## Ícones de ficheiro (opcional)

A extensão inclui um tema de ícones de ficheiro mínimo, "Algo Minimal", que
dá um ícone distinto a ficheiros `.algo` no explorador. Para o ativar: `Ctrl+Shift+P`
→ **File Icon Theme** → **Algo Minimal**.

Nota: o VS Code não permite adicionar um ícone só para um tipo de ficheiro
dentro do teu tema atual — um tema de ícones substitui sempre o conjunto
inteiro. O "Algo Minimal" usa ícones genéricos simples para todos os outros
ficheiros e pastas, pelo que ativá-lo faz perder os ícones por linguagem do
teu tema habitual (JS, Python, etc.) fora dos ficheiros `.algo`.

## Problemas / contacto

Encontraste um problema? Contacta Óscar Oliveira (oao@estg.ipp.pt).

## Personalizar cores

As cores concretas vêm do teu tema do VS Code (não desta extensão). Se
quiseres afinar cores específicas para o ALGO, podes mapear os âmbitos
(`scope`) usados na gramática (ex: `keyword.control.algo`,
`storage.type.algo`, `support.function.algo`) nas definições
`editor.tokenColorCustomizations` do teu `settings.json`.
