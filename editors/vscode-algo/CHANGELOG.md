# Changelog

Todas as alterações notáveis desta extensão são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/).

## [0.3.1]

### Added
- Contacto de suporte (`author`/`bugs` em `package.json`, secção
  "Problemas / contacto" no README).

## [0.3.0]

### Added
- Diagnósticos (erros/avisos) no editor ao gravar/abrir um ficheiro
  `.algo`, via `algo verifica --json` (novo em `algo_lang/cli.py`) --
  `extension.js`, primeiro código executável da extensão.
- Definição `algo.caminhoExecutavel` para apontar explicitamente para o
  executável `algo`; sem ela, procura um `.venv` local ou o `algo` no PATH.

## [0.2.0]

### Added
- Ícone da extensão (`images/icon.png`).
- Tema de ícones de ficheiro mínimo (`Algo Minimal`) que dá um ícone
  distinto a ficheiros `.algo` no explorador de ficheiros.
- Licença MIT (`LICENSE`).

## [0.1.0]

### Added
- Realce de sintaxe (gramática TextMate) para ficheiros `.algo`.
- Configuração de linguagem: comentários, emparelhamento de
  parênteses/chavetas, auto-indentação.
