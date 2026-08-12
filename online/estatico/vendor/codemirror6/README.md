# CodeMirror 6 -- vendorizado

`codemirror6.js` é um bundle único, autocontido (IIFE, sem imports),
que expõe `window.CM6 = {...}`. Ao contrário do CM5 (`../codemirror/`),
o CM6 é distribuído pela CodeMirror como vários pacotes npm em ESM --
não há um build UMD "pronto a usar" para descarregar diretamente. Este
ficheiro é gerado uma única vez com `esbuild`, fora do projeto (não
existe `package.json`/`node_modules` aqui, de propósito, para não
introduzir Node como dependência de build do `online/`).

Pacotes incluídos (todos MIT, ver `LICENSE-codemirror6.txt`):

```
@codemirror/state@6.7.1
@codemirror/view@6.43.8
@codemirror/commands@6.10.4
@codemirror/language@6.12.4
@codemirror/theme-one-dark@6.1.3
@lezer/highlight@1.2.3
```

## Para reconstruir (ex: atualizar versão)

Num diretório fora do projeto:

```bash
npm init -y
npm install @codemirror/state @codemirror/view @codemirror/commands \
    @codemirror/language @codemirror/theme-one-dark @lezer/highlight esbuild
```

Criar `entry.js` a reexportar o necessário para `window.CM6` (ver o
início de `codemirror6.js` para a lista exata de nomes usados por
`app.js` e `modo_codemirror.py`), depois:

```bash
npx esbuild entry.js --bundle --format=iife --minify --outfile=codemirror6.js
```

E copiar o resultado para aqui.
