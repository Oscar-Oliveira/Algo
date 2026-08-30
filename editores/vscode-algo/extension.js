// -*- coding: utf-8 -*-
// Diagnósticos (erros/avisos) para ficheiros .algo, via 'algo verifica
// --json' -- reaproveita o compilador real (parse/verificar) sem o tocar;
// ver algo_lang/cli.py:_cmd_verifica_json. Corre ao gravar e ao abrir um
// ficheiro .algo (não a cada tecla -- isso exigiria escrever o conteúdo
// não gravado num ficheiro temporário, o que partiria a resolução de
// 'incluir' contra ficheiros irmãos; fora do âmbito desta primeira versão).
"use strict";

const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");
const fs = require("fs");

const NOME_COLECAO = "algo";

let diagnosticos;
let canalSaida;
let avisoExecutavelMostrado = false;

function ativar(context) {
  diagnosticos = vscode.languages.createDiagnosticCollection(NOME_COLECAO);
  canalSaida = vscode.window.createOutputChannel("ALGO");
  context.subscriptions.push(diagnosticos, canalSaida);

  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(verificarDocumento),
    vscode.workspace.onDidOpenTextDocument(verificarDocumento),
    vscode.workspace.onDidCloseTextDocument((doc) => diagnosticos.delete(doc.uri))
  );

  for (const doc of vscode.workspace.textDocuments) {
    verificarDocumento(doc);
  }
}

function desativar() {
  if (diagnosticos) diagnosticos.dispose();
}

function verificarDocumento(doc) {
  if (doc.languageId !== "algo" || doc.uri.scheme !== "file") return;

  const executavel = encontrarExecutavelAlgo(doc.uri.fsPath);
  cp.execFile(
    executavel,
    ["verifica", "--json", doc.uri.fsPath],
    { timeout: 15000 },
    (erro, stdout, stderr) => {
      if (erro && erro.code === "ENOENT") {
        avisarExecutavelNaoEncontrado();
        return;
      }
      if (stderr) {
        canalSaida.appendLine(stderr);
      }
      let lista;
      try {
        lista = JSON.parse(stdout);
      } catch (e) {
        // Ficheiro com 'incluir' quebrado, codificação inválida, ou outro
        // erro que 'verifica --json' não converte em diagnóstico (ver
        // limitações conhecidas no README) -- mantém os diagnósticos
        // anteriores em vez de os apagar às cegas.
        canalSaida.appendLine(
          `[algo] não consegui interpretar 'verifica --json' para ${doc.uri.fsPath}`
        );
        return;
      }
      diagnosticos.set(doc.uri, lista.map((d) => paraDiagnosticoVSCode(doc, d)));
    }
  );
}

function paraDiagnosticoVSCode(doc, d) {
  const linha = Math.max(0, (d.linha || 1) - 1);
  let inicio, fim;
  if (d.coluna != null) {
    // Erro léxico/sintático com coluna exata: sublinha só essa posição --
    // o compilador não devolve o comprimento do token, por isso 1 caractere.
    inicio = Math.max(0, d.coluna - 1);
    fim = inicio + 1;
  } else {
    // Erro semântico/aviso, sem coluna: sublinha a linha inteira.
    inicio = 0;
    fim = linha < doc.lineCount ? doc.lineAt(linha).range.end.character : 1;
  }
  const intervalo = new vscode.Range(linha, inicio, linha, Math.max(fim, inicio + 1));
  const severidade =
    d.severidade === "aviso" ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error;
  const diagnostico = new vscode.Diagnostic(intervalo, d.mensagem, severidade);
  diagnostico.source = "algo";
  return diagnostico;
}

// Sem definição explícita (algo.caminhoExecutavel), procura um venv local
// no estilo de algo.sh/algo.bat (".venv" ao lado do ficheiro ou de algum
// antepassado), sem subir acima da pasta do workspace; falha para 'algo'
// simples, à espera de o encontrar no PATH.
function encontrarExecutavelAlgo(caminhoFicheiro) {
  const caminhoConfigurado = vscode.workspace
    .getConfiguration("algo")
    .get("caminhoExecutavel", "")
    .trim();
  if (caminhoConfigurado) return caminhoConfigurado;

  const nomeVenv =
    process.platform === "win32"
      ? path.join(".venv", "Scripts", "algo.exe")
      : path.join(".venv", "bin", "algo");

  const raizesWorkspace = (vscode.workspace.workspaceFolders || []).map((w) => w.uri.fsPath);
  let dir = path.dirname(caminhoFicheiro);
  for (let i = 0; i < 25; i++) {
    const candidato = path.join(dir, nomeVenv);
    if (fs.existsSync(candidato)) return candidato;
    if (raizesWorkspace.includes(dir)) break;
    const pai = path.dirname(dir);
    if (pai === dir) break;
    dir = pai;
  }
  return "algo";
}

function avisarExecutavelNaoEncontrado() {
  if (avisoExecutavelMostrado) return;
  avisoExecutavelMostrado = true;
  vscode.window
    .showWarningMessage(
      "ALGO: não encontrei o executável 'algo' (nem num .venv local, nem no PATH) -- " +
        "os diagnósticos de erros/avisos ao gravar ficam desligados até definires " +
        "'algo.caminhoExecutavel' nas definições.",
      "Abrir definições"
    )
    .then((escolha) => {
      if (escolha === "Abrir definições") {
        vscode.commands.executeCommand("workbench.action.openSettings", "algo.caminhoExecutavel");
      }
    });
}

module.exports = { activate: ativar, deactivate: desativar };
