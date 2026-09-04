const CODIGO_POR_OMISSAO = 'algoritmo "MeuPrograma"\ninicio\n    escrever("ola")\n';

// ---------- notificação flutuante (toast) ----------
// Confirmação visual de que uma ação foi guardada -- mesmo padrão do
// painel de admin (ver mostrarToast em admin.js): as mensagens de erro
// continuam inline, perto do formulário/lista em causa, mas uma ação
// bem-sucedida (guardar/apagar/escolher um LLM) não tinha, até aqui,
// nenhum sinal visual de que resultou em algo -- só o próprio efeito
// (a lista a mudar) indicava sucesso, facilmente perdido.
const elementoToast = document.getElementById("toast-notificacao");
const textoToast = document.getElementById("toast-notificacao-texto");
let timeoutToast = null;

function mostrarToast(texto) {
  textoToast.textContent = texto;
  clearTimeout(timeoutToast);
  elementoToast.classList.add("visivel");
  timeoutToast = setTimeout(() => elementoToast.classList.remove("visivel"), 2200);
}

// ---------- ligação entre o CodeMirror 6 (vendorizado, ver
// estatico/vendor/codemirror6/) e o resto de app.js -- devolve um
// objeto com a mesma superfície que o CodeMirror 5 antigo expunha
// (getValue/setValue/setOption/clearGutter/removeLineClass/
// setGutterMarker/addLineClass/scrollIntoView/on/refresh), para não
// ter de tocar em mais nenhum sítio deste ficheiro. ----------

function criarEditor() {
  const areaTexto = document.getElementById("area-codigo");
  areaTexto.value = CODIGO_POR_OMISSAO;
  try {
    if (typeof CM6 === "undefined" || typeof algoLanguage === "undefined") {
      throw new Error("CodeMirror não carregou -- a usar a área de texto simples.");
    }

    const compartimentoTema = new CM6.Compartment();
    // CM6 não vem com um "chrome" (fundo/gutters/cursor) claro por
    // omissão como o CM5 tinha embutido no seu codemirror.css -- só
    // syntaxHighlighting trata das cores dos tokens, não do fundo.
    const temaClaroChrome = CM6.EditorView.theme({
      "&": { backgroundColor: "#ffffff", color: "#1a1a1a" },
      ".cm-content": { caretColor: "#1a1a1a" },
      ".cm-gutters": { backgroundColor: "#f5f5f5", color: "#999", border: "none" },
      ".cm-activeLineGutter": { backgroundColor: "#e8e8e8" },
    }, { dark: false });
    const temaClaro = [temaClaroChrome, CM6.syntaxHighlighting(CM6.defaultHighlightStyle)];
    const temaEscuro = [CM6.oneDark, CM6.syntaxHighlighting(CM6.oneDarkHighlightStyle)];

    // ---- marcador de erro no gutter + fundo da linha (UX-15) ----
    const definirErroEfeito = CM6.StateEffect.define();
    const limparErroEfeito = CM6.StateEffect.define();

    class MarcadorErroGutter extends CM6.GutterMarker {
      constructor(elemento) { super(); this.elemento = elemento; }
      eq(outro) { return outro.elemento === this.elemento; }
      toDOM() { return this.elemento; }
    }

    const decoracaoLinhaErro = CM6.Decoration.line({ attributes: { class: "linha-com-erro" } });

    const campoErro = CM6.StateField.define({
      create() { return { linha: null, marcador: null }; },
      update(valor, tr) {
        for (const efeito of tr.effects) {
          if (efeito.is(definirErroEfeito)) valor = efeito.value;
          if (efeito.is(limparErroEfeito)) valor = { linha: null, marcador: null };
        }
        return valor;
      },
    });

    const decoracoesErro = CM6.EditorView.decorations.compute([campoErro], (state) => {
      const { linha } = state.field(campoErro);
      if (linha === null || linha >= state.doc.lines) return CM6.Decoration.none;
      return CM6.Decoration.set([decoracaoLinhaErro.range(state.doc.line(linha + 1).from)]);
    });

    const gutterErro = CM6.gutter({
      class: "gutter-erro",
      lineMarker(view, linhaInfo) {
        const { linha, marcador } = view.state.field(campoErro);
        if (linha === null || !marcador) return null;
        return linhaInfo.from === view.state.doc.line(linha + 1).from ? new MarcadorErroGutter(marcador) : null;
      },
      lineMarkerChange: (update) => update.state.field(campoErro) !== update.startState.field(campoErro),
    });

    const escutadoresDeMudanca = [];

    const view = new CM6.EditorView({
      doc: areaTexto.value,
      parent: areaTexto.parentNode,
      extensions: [
        CM6.lineNumbers(),
        gutterErro,
        campoErro,
        decoracoesErro,
        CM6.history(),
        CM6.keymap.of([CM6.indentWithTab, ...CM6.defaultKeymap, ...CM6.historyKeymap]),
        CM6.indentUnit.of("    "), // ARCH-06: tab converte sempre para 4 espaços, nunca insere '\t'
        CM6.highlightWhitespace(), // ARCH-06: espaços/tabs ficam visíveis (pontos/setas) -- ver estilo.css para o ajuste de opacidade
        // ARCH-06: indentWithTab só apanha a tecla Tab -- colar texto com
        // tabs literais (ex: copiado de outro editor) entra pela via do
        // clipboard, que não passa por ali. Convertemos aqui também, para
        // nunca sobrar um '\t' visível no documento.
        CM6.EditorView.domEventHandlers({
          paste(evento, view) {
            const texto = evento.clipboardData && evento.clipboardData.getData("text/plain");
            if (!texto || texto.indexOf("\t") === -1) return false;
            evento.preventDefault();
            view.dispatch(view.state.replaceSelection(texto.replace(/\t/g, "    ")));
            return true;
          },
        }),
        algoLanguage,
        compartimentoTema.of(window.obterTema && window.obterTema() === "claro" ? temaClaro : temaEscuro),
        CM6.EditorView.updateListener.of((update) => {
          if (update.docChanged) escutadoresDeMudanca.forEach((fn) => fn());
        }),
      ],
    });
    areaTexto.style.display = "none";

    return {
      getValue: () => view.state.doc.toString(),
      setValue: (v) => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: v } }),
      setOption: (nome, valor) => {
        if (nome !== "theme") return;
        view.dispatch({ effects: compartimentoTema.reconfigure(valor === "default" ? temaClaro : temaEscuro) });
      },
      clearGutter: () => view.dispatch({ effects: limparErroEfeito.of(null) }),
      removeLineClass: () => view.dispatch({ effects: limparErroEfeito.of(null) }),
      setGutterMarker: (linha, _gutterId, elementoDom) => {
        view.dispatch({ effects: definirErroEfeito.of({ linha, marcador: elementoDom }) });
      },
      addLineClass: () => {}, // já coberto por setGutterMarker acima, que despoleta a mesma decoração de linha
      scrollIntoView: (pos) => {
        const linha = view.state.doc.line(Math.min(pos.line + 1, view.state.doc.lines));
        view.dispatch({ effects: CM6.EditorView.scrollIntoView(linha.from + (pos.ch || 0), { y: "center" }) });
      },
      on: (evento, fn) => { if (evento === "change") escutadoresDeMudanca.push(fn); },
      refresh: () => view.requestMeasure(),
    };
  } catch (erro) {
    // Nunca deixar uma falha aqui impedir o resto da página de
    // funcionar (execução, Alguem, definições) -- só perdemos o
    // realce de sintaxe, não a aplicação inteira. Isto já aconteceu
    // de verdade: o CodeMirror vinha de um CDN externo que uma rede
    // escolar/institucional pode bloquear.
    console.warn(erro);
    return {
      getValue: () => areaTexto.value,
      setValue: (v) => { areaTexto.value = v; },
    };
  }
}

const editor = criarEditor();

// FEAT-02: mantém o tema do CodeMirror sincronizado com o resto da
// página quando o estudante alterna o tema depois do editor já estar criado.
window.addEventListener("algo-tema-mudou", (evento) => {
  if (!editor.setOption) return;
  editor.setOption("theme", evento.detail === "claro" ? "default" : "material-darker");
});

// ---------- gestão de vários ficheiros (para 'incluir') ----------

let ficheiros = [{ nome: "principal.algo", conteudo: CODIGO_POR_OMISSAO }];
let indiceFicheiroAtivo = 0;

function ficheiroAtivo() {
  return ficheiros[indiceFicheiroAtivo];
}

function guardarConteudoAtualNoFicheiro() {
  ficheiroAtivo().conteudo = editor.getValue();
}

function mudarParaFicheiro(indice) {
  guardarConteudoAtualNoFicheiro();
  indiceFicheiroAtivo = indice;
  editor.setValue(ficheiroAtivo().conteudo);
  renderizarSeparadoresDeFicheiros();
}

function renderizarSeparadoresDeFicheiros() {
  const lista = document.getElementById("lista-ficheiros");
  lista.innerHTML = "";
  ficheiros.forEach((ficheiro, indice) => {
    const separador = document.createElement("div");
    separador.className = "ficheiro-separador" + (indice === indiceFicheiroAtivo ? " ativo" : "");
    const nomeSpan = document.createElement("span");
    nomeSpan.textContent = ficheiro.nome + (indice === 0 ? " (principal)" : "");
    separador.appendChild(nomeSpan);
    separador.addEventListener("click", () => mudarParaFicheiro(indice));

    if (indice !== 0) {
      const botaoFechar = document.createElement("button");
      botaoFechar.className = "fechar-ficheiro";
      botaoFechar.textContent = "×";
      botaoFechar.title = "Remover este ficheiro";
      botaoFechar.addEventListener("click", (evento) => {
        evento.stopPropagation();
        ficheiros.splice(indice, 1);
        if (indiceFicheiroAtivo >= ficheiros.length) indiceFicheiroAtivo = ficheiros.length - 1;
        editor.setValue(ficheiroAtivo().conteudo);
        renderizarSeparadoresDeFicheiros();
      });
      separador.appendChild(botaoFechar);
    }
    lista.appendChild(separador);
  });
  atualizarBotaoAlternarFicheiros();
}

function atualizarBotaoAlternarFicheiros() {
  const lista = document.getElementById("lista-ficheiros");
  const botao = document.getElementById("botao-alternar-ficheiros");
  const estavaExpandida = lista.classList.contains("expandida");
  lista.classList.remove("expandida");
  const temFicheirosEscondidos = lista.scrollHeight > lista.clientHeight + 1;
  botao.classList.toggle("escondido", !temFicheirosEscondidos);
  if (estavaExpandida && temFicheirosEscondidos) {
    lista.classList.add("expandida");
  } else {
    botao.classList.remove("expandida");
    botao.title = "Mostrar todos os ficheiros";
  }
}

document.getElementById("botao-alternar-ficheiros").addEventListener("click", () => {
  const lista = document.getElementById("lista-ficheiros");
  const botao = document.getElementById("botao-alternar-ficheiros");
  const expandir = !lista.classList.contains("expandida");
  lista.classList.toggle("expandida", expandir);
  botao.classList.toggle("expandida", expandir);
  botao.title = expandir ? "Mostrar menos ficheiros" : "Mostrar todos os ficheiros";
});

new ResizeObserver(atualizarBotaoAlternarFicheiros).observe(document.getElementById("lista-ficheiros"));

document.getElementById("botao-novo-ficheiro").addEventListener("click", () => {
  let nome = prompt("Nome do ficheiro (ex: biblioteca.algo):", "biblioteca.algo");
  if (!nome) return;
  nome = nome.trim();
  if (!nome.endsWith(".algo")) nome += ".algo";
  if (ficheiros.some((f) => f.nome === nome)) {
    alert("Já existe um ficheiro com esse nome.");
    return;
  }
  guardarConteudoAtualNoFicheiro();
  ficheiros.push({ nome, conteudo: "" });
  mudarParaFicheiro(ficheiros.length - 1);
});

function obterTodosOsFicheiros() {
  guardarConteudoAtualNoFicheiro();
  return { ficheiros, principal: ficheiros[0].nome };
}

renderizarSeparadoresDeFicheiros();

// ---------- descarregar/abrir projeto (.zip, sem persistência em BD -- o
// próprio .zip descarregado é o "guardar", tanto para reabrir aqui como na
// consola, que já sabe abrir uma pasta normal de ficheiros .algo) ----------

document.getElementById("botao-descarregar-projeto").addEventListener("click", async () => {
  try {
    const resposta = await fetch("/api/projeto/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(obterTodosOsFicheiros()),
    });
    if (!resposta.ok) {
      const dados = await resposta.json();
      alert(dados.detail || "Não foi possível descarregar o projeto.");
      return;
    }
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const ligacao = document.createElement("a");
    ligacao.href = url;
    ligacao.download = "projeto.zip";
    ligacao.click();
    URL.revokeObjectURL(url);
  } catch (erro) {
    console.error(erro);
    alert("Não foi possível contactar o servidor.");
  }
});

const campoProjetoZip = document.getElementById("campo-projeto-zip");

document.getElementById("botao-abrir-projeto").addEventListener("click", () => {
  campoProjetoZip.value = "";
  campoProjetoZip.click();
});

campoProjetoZip.addEventListener("change", async () => {
  const ficheiro = campoProjetoZip.files[0];
  if (!ficheiro) return;
  if (!confirm("Isto substitui todos os ficheiros abertos no editor. Continuar?")) return;

  const dadosFormulario = new FormData();
  dadosFormulario.append("ficheiro", ficheiro);
  try {
    const resposta = await fetch("/api/projeto/upload", { method: "POST", body: dadosFormulario });
    const dados = await resposta.json();
    if (!resposta.ok) {
      alert(dados.detail || "Não foi possível abrir o projeto.");
      return;
    }
    ficheiros = dados.ficheiros;
    indiceFicheiroAtivo = 0;
    editor.setValue(ficheiroAtivo().conteudo);
    renderizarSeparadoresDeFicheiros();
  } catch (erro) {
    console.error(erro);
    alert("Não foi possível contactar o servidor.");
  }
});

// ---------- UX-15: marcador de erro no gutter do CodeMirror ----------
// Antes, um erro de compilação só aparecia como texto no terminal, sem
// nenhum apontador no próprio editor -- apesar do CodeMirror já estar
// carregado. As mensagens de erro do compilador seguem sempre o formato
// "Erro ... na linha N: ..." (ver lexer.py/parser.py/semantics.py), e um
// erro num ficheiro incluído vem prefixado com "Erro em '<nome>': ...".
let linhaComMarcadorDeErro = null;

function limparMarcadorDeErro() {
  if (linhaComMarcadorDeErro === null) return;
  if (editor.clearGutter) editor.clearGutter("gutter-erro");
  if (editor.removeLineClass) editor.removeLineClass(linhaComMarcadorDeErro, "background", "linha-com-erro");
  linhaComMarcadorDeErro = null;
}

function marcarErroNoEditor(mensagem) {
  limparMarcadorDeErro();
  if (!editor.setGutterMarker) return; // CodeMirror não carregou -- a mensagem já aparece no terminal
  const linhaMatch = mensagem.match(/na linha (\d+)/);
  if (!linhaMatch) return;
  const ficheiroMatch = mensagem.match(/^Erro em '([^']+)':/);
  const nomeFicheiro = ficheiroMatch ? ficheiroMatch[1] : ficheiros[0].nome;
  const indice = ficheiros.findIndex((f) => f.nome === nomeFicheiro);
  if (indice === -1) return;
  if (indice !== indiceFicheiroAtivo) mudarParaFicheiro(indice);

  const linha = parseInt(linhaMatch[1], 10) - 1;
  const marcador = document.createElement("span");
  marcador.className = "gutter-marcador-erro";
  marcador.title = mensagem;
  marcador.textContent = "●";
  editor.setGutterMarker(linha, "gutter-erro", marcador);
  editor.addLineClass(linha, "background", "linha-com-erro");
  if (editor.scrollIntoView) editor.scrollIntoView({ line: linha, ch: 0 }, 80);
  linhaComMarcadorDeErro = linha;
}

if (editor.on) editor.on("change", limparMarcadorDeErro);

const formEntradaTerminal = document.getElementById("form-entrada-terminal");
const entradaTerminal = document.getElementById("entrada-terminal");

function escreverNoTerminal(texto, classe) {
  const linha = document.createElement("div");
  linha.className = !classe && /^\s*\[debug linha \d+\]/.test(texto) ? "linha-debug" : classe || "";
  linha.textContent = texto;
  terminal.appendChild(linha);
  terminal.scrollTop = terminal.scrollHeight;
}

// UX-15: clicar na mensagem de erro salta de volta para a linha
// marcada no editor (útil se o estudante já tiver deslocado o editor).
function escreverErroCompilacaoNoTerminal(mensagem) {
  const linha = document.createElement("div");
  linha.className = "linha-erro linha-erro-clicavel";
  linha.textContent = mensagem;
  linha.title = "Clica para ir para a linha no editor";
  linha.addEventListener("click", () => marcarErroNoEditor(mensagem));
  terminal.appendChild(linha);
  terminal.scrollTop = terminal.scrollHeight;
}

let wsExecucao = null;

// entradas escritas na execução interativa atual, por ordem -- null enquanto
// não houver uma execução terminada com sucesso (tipo "fim") para reproduzir
// em modo batch. Ver botaoDescarregarRastoExecucao mais abaixo.
let entradasExecucaoAtual = null;
let execucaoTerminadaComSucesso = false; // só true depois de "fim" -- ver atualizarBotaoDescarregarRastoExecucao
let modoExecucaoAtual = "Execução"; // "Execução" ou "Debug" -- título da vista-execucao, ver mostrarVistaPainelTerminal
let rastoExecucaoCache = null; // { chave, url } -- evita gerar de novo o mesmo rasto
const botaoDescarregarRastoExecucao = document.getElementById("botao-descarregar-rasto-execucao");

function invalidarRastoExecucaoCache() {
  if (rastoExecucaoCache) URL.revokeObjectURL(rastoExecucaoCache.url);
  rastoExecucaoCache = null;
}

function atualizarBotaoDescarregarRastoExecucao() {
  const naVistaExecucao = !vistaExecucao.classList.contains("escondido");
  botaoDescarregarRastoExecucao.classList.toggle("escondido", !naVistaExecucao);
  botaoDescarregarRastoExecucao.disabled = !execucaoTerminadaComSucesso;
  // botões "Rasto" (formulário clássico) e "Visualizador" só fazem
  // sentido em modo Debug -- na Execução normal só o download acima chega.
  const emDebug = naVistaExecucao && modoExecucaoAtual === "Debug";
  botaoAbrirRasto.classList.toggle("escondido", !emDebug);
  ligacaoAbrirVisualizador.classList.toggle("escondido", !emDebug);
}

function descarregarUrl(url, nomeFicheiro) {
  const a = document.createElement("a");
  a.href = url;
  a.download = nomeFicheiro;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Gera o rasto só quando pedido, correndo o programa de novo (em modo batch,
// com as mesmas entradas já escritas nesta execução interativa) apenas se
// ainda não tivermos um rasto em cache para essas entradas exatas.
botaoDescarregarRastoExecucao.addEventListener("click", async () => {
  if (!entradasExecucaoAtual) return;
  const chave = JSON.stringify(entradasExecucaoAtual);
  const nomeFicheiro = ficheiros[0].nome.replace(/\.algo$/, "") + "_trace.json";

  if (rastoExecucaoCache && rastoExecucaoCache.chave === chave) {
    descarregarUrl(rastoExecucaoCache.url, nomeFicheiro);
    return;
  }

  botaoDescarregarRastoExecucao.disabled = true;
  try {
    const resposta = await fetch("/api/rasto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...obterTodosOsFicheiros(), entradas: entradasExecucaoAtual }),
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      escreverNoTerminal(dados.detail || "Não foi possível gerar o rasto.", "linha-erro");
      return;
    }
    if (dados.erro) {
      escreverNoTerminal(
        `Não foi possível gerar o rasto: o programa terminou com um erro` +
        `${dados.erro.linha ? " na linha " + dados.erro.linha : ""} -- ${dados.erro.mensagem}`,
        "linha-erro");
      return;
    }
    if (dados.passos.length === 0) {
      escreverNoTerminal("O rasto não teve nenhum passo para descarregar.", "linha-erro");
      return;
    }
    const blob = new Blob([JSON.stringify(dados, null, 2)], { type: "application/json" });
    rastoExecucaoCache = { chave, url: URL.createObjectURL(blob) };
    descarregarUrl(rastoExecucaoCache.url, nomeFicheiro);
  } catch (erro) {
    console.error(erro);
    escreverNoTerminal("Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro), "linha-erro");
  } finally {
    botaoDescarregarRastoExecucao.disabled = false;
  }
});

document.getElementById("botao-executar").addEventListener("click", () => {
  modoExecucaoAtual = "Execução";
  mostrarVistaPainelTerminal("execucao");
  document.querySelector(".painel-terminal").scrollIntoView({ behavior: "smooth", block: "start" });
  terminal.innerHTML = "";
  limparMarcadorDeErro();
  formEntradaTerminal.classList.add("escondido");
  entradasExecucaoAtual = [];
  execucaoTerminadaComSucesso = false;
  invalidarRastoExecucaoCache();
  atualizarBotaoDescarregarRastoExecucao();
  if (wsExecucao) wsExecucao.close();

  const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
  wsExecucao = new WebSocket(`${protocolo}//${window.location.host}/ws/executar`);

  wsExecucao.addEventListener("open", () => {
    wsExecucao.send(JSON.stringify(obterTodosOsFicheiros()));
  });

  wsExecucao.addEventListener("message", (evento) => {
    const dados = JSON.parse(evento.data);
    if (dados.tipo === "erro_compilacao") {
      escreverErroCompilacaoNoTerminal(dados.mensagem);
      marcarErroNoEditor(dados.mensagem);
    } else if (dados.tipo === "compilado") {
      escreverNoTerminal("-- a executar --", "linha-sistema");
      formEntradaTerminal.classList.remove("escondido");
      entradaTerminal.focus();
    } else if (dados.tipo === "saida") {
      escreverNoTerminal(dados.texto);
    } else if (dados.tipo === "fim") {
      escreverNoTerminal(`-- terminou (código ${dados.codigo_saida}) --`, "linha-sistema");
      formEntradaTerminal.classList.add("escondido");
      execucaoTerminadaComSucesso = true;
      atualizarBotaoDescarregarRastoExecucao();
    } else if (dados.tipo === "erro") {
      escreverNoTerminal(dados.mensagem, "linha-erro");
      formEntradaTerminal.classList.add("escondido");
    }
  });

  wsExecucao.addEventListener("close", () => {
    formEntradaTerminal.classList.add("escondido");
  });
});

// ---------- Debug ao vivo (--debug interativo) ----------
// Peça isolada de propósito -- ver a nota no topo de
// online/executor.py:ExecucaoComDebugAoVivo. Reaproveita o mesmo painel/
// terminal e o mesmo formEntradaTerminal/wsExecucao que "Executar" já usa
// (o submit handler abaixo já manda a entrada para wsExecucao seja qual
// for a ligação aberta), só liga a um WebSocket diferente. "Rasto desta
// execução" (no painel de execução) descarrega o rasto desta execução ao
// vivo; o botão "Rasto" ali ao lado abre o formulário clássico (vista-rasto,
// mais abaixo) para gerar um rasto indicando as entradas à mão.

function iniciarDebug() {
  modoExecucaoAtual = "Debug";
  mostrarVistaPainelTerminal("execucao");
  document.querySelector(".painel-terminal").scrollIntoView({ behavior: "smooth", block: "start" });
  terminal.innerHTML = "";
  limparMarcadorDeErro();
  formEntradaTerminal.classList.add("escondido");
  entradasExecucaoAtual = []; // debug ao vivo também alimenta o "descarregar rasto", tal como a execução normal
  execucaoTerminadaComSucesso = false;
  invalidarRastoExecucaoCache();
  atualizarBotaoDescarregarRastoExecucao();
  if (wsExecucao) wsExecucao.close();

  const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
  wsExecucao = new WebSocket(`${protocolo}//${window.location.host}/ws/debug`);

  wsExecucao.addEventListener("open", () => {
    wsExecucao.send(JSON.stringify(obterTodosOsFicheiros()));
  });

  wsExecucao.addEventListener("message", (evento) => {
    const dados = JSON.parse(evento.data);
    if (dados.tipo === "erro_compilacao") {
      escreverErroCompilacaoNoTerminal(dados.mensagem);
      marcarErroNoEditor(dados.mensagem);
    } else if (dados.tipo === "compilado") {
      escreverNoTerminal("-- a executar em modo debug --", "linha-sistema");
      formEntradaTerminal.classList.remove("escondido");
      entradaTerminal.focus();
    } else if (dados.tipo === "saida") {
      escreverNoTerminal(dados.texto);
    } else if (dados.tipo === "fim") {
      escreverNoTerminal("-- terminou --", "linha-sistema");
      formEntradaTerminal.classList.add("escondido");
      execucaoTerminadaComSucesso = true;
      atualizarBotaoDescarregarRastoExecucao();
    } else if (dados.tipo === "erro") {
      escreverNoTerminal(dados.mensagem, "linha-erro");
      formEntradaTerminal.classList.add("escondido");
    }
  });

  wsExecucao.addEventListener("close", () => {
    formEntradaTerminal.classList.add("escondido");
  });
}

document.getElementById("botao-debug").addEventListener("click", iniciarDebug);

formEntradaTerminal.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const valor = entradaTerminal.value;
  escreverNoTerminal("> " + valor, "linha-sistema");
  if (wsExecucao && wsExecucao.readyState === WebSocket.OPEN) {
    wsExecucao.send(JSON.stringify({ tipo: "entrada", valor }));
  }
  if (entradasExecucaoAtual) entradasExecucaoAtual.push(valor);
  entradaTerminal.value = "";
});

// ---------- Alguem ----------

// Ligado/desligado pelo admin (aba Definições do painel de admin) --
// valor real só se conhece depois do fetch a /api/eu mais abaixo;
// começa false para nunca tentar ligar antes disso (e como falha
// segura se esse fetch falhar).
let ALGUEM_ATIVO = false;

const conversaAlguem = document.getElementById("conversa-alguem");
const entradaAlguem = document.getElementById("entrada-alguem");
const botaoEnviarAlguem = document.querySelector("#form-alguem button[type=submit]");
const avisoCredencialAlguem = document.getElementById("aviso-credencial-alguem");
const textoAvisoCredencialAlguem = document.getElementById("texto-aviso-credencial-alguem");
const botaoIrDefinicoes = document.getElementById("botao-ir-definicoes");
let wsAlguem = null;

// UX-14: se faltar (ou for inválida) a credencial LLM, o servidor envia
// "erro" e fecha o socket ANTES de mandar "pronto" -- sem isto, escrever e
// submeter no chat depois disso não fazia absolutamente nada, sem aviso.
let alguemPronto = false;

// 'acionavel' (enviado pelo servidor, ver alguem_ponte.ErroAlguemIndisponivel)
// diz se ir a Definições resolve alguma coisa -- quando não há NENHUM LLM
// disponível (nem global, nem permissão para um pessoal), Definições nem
// sequer mostra a opção de criar um, por isso o link fica escondido em vez
// de mandar o estudante para um sítio sem solução nenhuma.
function desativarEntradaAlguem(mensagem, acionavel) {
  entradaAlguem.disabled = true;
  botaoEnviarAlguem.disabled = true;
  textoAvisoCredencialAlguem.textContent = mensagem || "Ainda não configuraste um fornecedor de LLM.";
  botaoIrDefinicoes.classList.toggle("escondido", acionavel === false);
  avisoCredencialAlguem.classList.remove("escondido");
}

function ativarEntradaAlguem() {
  entradaAlguem.disabled = false;
  botaoEnviarAlguem.disabled = false;
  avisoCredencialAlguem.classList.add("escondido");
}

function ligarAlguem() {
  alguemPronto = false;
  const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
  wsAlguem = new WebSocket(`${protocolo}//${window.location.host}/ws/alguem`);

  wsAlguem.addEventListener("message", (evento) => {
    const dados = JSON.parse(evento.data);
    if (dados.tipo === "pronto" || dados.tipo === "resposta") {
      if (dados.tipo === "pronto") {
        alguemPronto = true;
        ativarEntradaAlguem();
      }
      esconderIndicadorAPensar();
      adicionarMensagem(dados.mensagem || dados.texto, "mensagem-alguem");
    } else if (dados.tipo === "erro") {
      esconderIndicadorAPensar();
      adicionarMensagem(dados.mensagem, "mensagem-erro-chat");
      if (!alguemPronto) desativarEntradaAlguem(dados.mensagem, dados.acionavel);
    }
  });
}

function adicionarMensagem(texto, classe) {
  const div = document.createElement("div");
  div.className = "mensagem " + classe;
  div.textContent = texto;
  conversaAlguem.appendChild(div);
  conversaAlguem.scrollTop = conversaAlguem.scrollHeight;
}

// UX-13: até 4-6 chamadas LLM encadeadas por turno (guardião a
// reclassificar/regenerar) podem levar vários segundos -- sem isto, o
// chat parecia parado, sem nenhum sinal de que o pedido foi recebido.
let indicadorAPensar = null;

function mostrarIndicadorAPensar() {
  if (indicadorAPensar) return;
  indicadorAPensar = document.createElement("div");
  indicadorAPensar.className = "mensagem mensagem-alguem indicador-a-pensar";
  indicadorAPensar.textContent = "A pensar…";
  conversaAlguem.appendChild(indicadorAPensar);
  conversaAlguem.scrollTop = conversaAlguem.scrollHeight;
}

function esconderIndicadorAPensar() {
  if (!indicadorAPensar) return;
  indicadorAPensar.remove();
  indicadorAPensar = null;
}

document.getElementById("form-alguem").addEventListener("submit", (evento) => {
  evento.preventDefault();
  const campo = document.getElementById("entrada-alguem");
  const texto = campo.value.trim();
  if (!texto || !wsAlguem || wsAlguem.readyState !== WebSocket.OPEN) return;
  adicionarMensagem(texto, "mensagem-estudante");
  wsAlguem.send(JSON.stringify({ texto }));
  campo.value = "";
  mostrarIndicadorAPensar();
});

document.getElementById("botao-mostrar-ficheiro").addEventListener("click", () => {
  if (!wsAlguem || wsAlguem.readyState !== WebSocket.OPEN) return;
  const { ficheiros: todosOsFicheiros } = obterTodosOsFicheiros();
  wsAlguem.send(JSON.stringify({ tipo: "ficheiro", ficheiros: todosOsFicheiros }));
  const nomes = todosOsFicheiros.map((f) => f.nome).join(", ");
  adicionarMensagem(`(mostrei-te o meu código atual: ${nomes})`, "mensagem-estudante");
});

// ---------- definições do LLM (vivem dentro do painel do Alguem) ----------
//
// Dois níveis dentro do mesmo painel (secção 5b de
// docs/interno/PlanoAlguemLLMInvestigacao.md): a lista de configurações
// guardadas (vista por omissão ao abrir) e o formulário para criar/editar
// uma delas.

const vistaConversaAlguem = document.getElementById("vista-conversa-alguem");
const vistaDefinicoesAlguem = document.getElementById("vista-definicoes-alguem");
const vistaDefinicoesLista = document.getElementById("vista-definicoes-lista");
const vistaDefinicoesFormulario = document.getElementById("vista-definicoes-formulario");
const botaoDefinicoesAlguem = document.getElementById("botao-definicoes-alguem");
const botaoMostrarFicheiro = document.getElementById("botao-mostrar-ficheiro");
const campoFornecedor = document.getElementById("campo-fornecedor");
const rotuloApiKey = document.getElementById("rotulo-api-key");
const rotuloHost = document.getElementById("rotulo-host");
const campoConfiguracaoId = document.getElementById("campo-configuracao-id");
const listaConfiguracoesLlm = document.getElementById("lista-configuracoes-llm");
const mensagemSemConfiguracoesLlm = document.getElementById("mensagem-sem-configuracoes-llm");
const selectConfiguracaoAtiva = document.getElementById("select-configuracao-ativa");

function atualizarCamposFornecedor() {
  const ollama = campoFornecedor.value === "ollama";
  rotuloApiKey.classList.toggle("escondido", ollama);
  rotuloHost.classList.toggle("escondido", !ollama);
}
campoFornecedor.addEventListener("change", atualizarCamposFornecedor);

// Só faz sentido "mostrar-lhe o meu código" durante uma conversa -- nas
// definições esconde-se, e o próprio botão de definições (engrenagem)
// passa a servir de "voltar à conversa" enquanto esta vista está aberta,
// em vez de haver dois botões a fazer praticamente a mesma coisa.
const ICONE_DEFINICOES_LLM = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
  + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="14" />'
  + '<line x1="4" y1="10" x2="4" y2="3" /><line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" />'
  + '<line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" /><line x1="1" y1="14" x2="7" y2="14" />'
  + '<line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" /></svg>';
const ICONE_VOLTAR_CONVERSA = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
  + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12" />'
  + '<polyline points="12 19 5 12 12 5" /></svg>';

async function abrirDefinicoes() {
  vistaConversaAlguem.classList.add("escondido");
  vistaDefinicoesAlguem.classList.remove("escondido");
  vistaDefinicoesFormulario.classList.add("escondido");
  vistaDefinicoesLista.classList.remove("escondido");
  botaoMostrarFicheiro.classList.add("escondido");
  botaoDefinicoesAlguem.innerHTML = ICONE_VOLTAR_CONVERSA;
  botaoDefinicoesAlguem.title = "Voltar à conversa";
  carregarConfiguracoesLlm();
}

function fecharDefinicoes() {
  vistaDefinicoesAlguem.classList.add("escondido");
  vistaConversaAlguem.classList.remove("escondido");
  botaoMostrarFicheiro.classList.remove("escondido");
  botaoDefinicoesAlguem.innerHTML = ICONE_DEFINICOES_LLM;
  botaoDefinicoesAlguem.title = "Definições do LLM";
}

function alternarPainelDefinicoes() {
  if (vistaDefinicoesAlguem.classList.contains("escondido")) {
    abrirDefinicoes();
  } else {
    fecharDefinicoes();
  }
}

botaoDefinicoesAlguem.addEventListener("click", alternarPainelDefinicoes);
document.getElementById("botao-ir-definicoes").addEventListener("click", abrirDefinicoes);

function abrirFormularioLlm(configuracao) {
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="definicoes"]');
  mensagemErro.textContent = "";
  const form = document.getElementById("form-definicoes");
  form.reset();
  campoConfiguracaoId.value = configuracao ? configuracao.id : "";
  if (configuracao) {
    document.getElementById("campo-etiqueta").value = configuracao.etiqueta;
    campoFornecedor.value = configuracao.fornecedor;
    document.getElementById("campo-modelo").value = configuracao.modelo;
    if (configuracao.host) document.getElementById("campo-host").value = configuracao.host;
  }
  atualizarCamposFornecedor();
  vistaDefinicoesLista.classList.add("escondido");
  vistaDefinicoesFormulario.classList.remove("escondido");
}

function fecharFormularioLlm() {
  vistaDefinicoesFormulario.classList.add("escondido");
  vistaDefinicoesLista.classList.remove("escondido");
  carregarConfiguracoesLlm();
}

document.getElementById("botao-nova-configuracao-llm").addEventListener("click", () => abrirFormularioLlm(null));
document.getElementById("botao-cancelar-formulario-llm").addEventListener("click", fecharFormularioLlm);

async function carregarConfiguracoesLlm() {
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="definicoes-lista"]');
  mensagemErro.textContent = "";
  try {
    const resposta = await fetch("/api/llm/configuracoes");
    const dados = await resposta.json();
    renderizarConfiguracoesLlm(dados);
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível carregar as configurações: " + (erro && erro.message ? erro.message : erro);
  }
}

function renderizarConfiguracoesLlm(dados) {
  const { configuracoes, configuracao_ativa_id, llm_pessoal_permitido, definido_pela_plataforma } = dados;

  listaConfiguracoesLlm.innerHTML = "";
  mensagemSemConfiguracoesLlm.classList.toggle("escondido", configuracoes.length > 0);
  configuracoes.forEach((configuracao) => {
    const linha = document.createElement("div");
    linha.className = "linha-configuracao-llm";

    const texto = document.createElement("div");
    texto.className = "texto-configuracao-llm";
    const etiqueta = document.createElement("strong");
    etiqueta.textContent = configuracao.etiqueta;
    const detalhe = document.createElement("span");
    detalhe.textContent = `${configuracao.fornecedor} · ${configuracao.modelo}`;
    texto.appendChild(etiqueta);
    texto.appendChild(detalhe);

    const botaoEditar = document.createElement("button");
    botaoEditar.type = "button";
    botaoEditar.className = "botao-icone botao-icone-pequeno";
    botaoEditar.title = "Editar";
    botaoEditar.innerHTML = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      + '<path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>';
    botaoEditar.addEventListener("click", () => abrirFormularioLlm(configuracao));

    const botaoApagar = document.createElement("button");
    botaoApagar.type = "button";
    botaoApagar.className = "botao-icone botao-icone-pequeno";
    botaoApagar.title = "Apagar";
    botaoApagar.innerHTML = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      + '<polyline points="4 7 20 7" /><path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />'
      + '<path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" /></svg>';
    botaoApagar.addEventListener("click", () => apagarConfiguracaoLlm(configuracao));

    linha.appendChild(texto);
    linha.appendChild(botaoEditar);
    linha.appendChild(botaoApagar);
    listaConfiguracoesLlm.appendChild(linha);
  });

  preencherSelecaoConfiguracaoAtiva(configuracoes, configuracao_ativa_id, llm_pessoal_permitido, definido_pela_plataforma);
}

// Um único LLM, usado para conversar -- o guardião é sempre transparente
// para o estudante (nunca uma escolha à parte dele, ver
// docs/interno/PlanoAlguemLLMInvestigacao.md e configuracao_llm.
// PAPEIS_PESSOAIS), por isso não há noção de "papel" aqui, ao contrário
// do painel de admin (que gere apoio/guardião como conceitos distintos).
const textoDefinidoPelaPlataforma = document.getElementById("texto-definido-pela-plataforma");

function preencherSelecaoConfiguracaoAtiva(configuracoes, configuracaoAtivaId, permitido, definidoPelaPlataforma) {
  const rotulo = selectConfiguracaoAtiva.closest("label");
  if (definidoPelaPlataforma || !permitido) {
    rotulo.classList.add("escondido");
    textoDefinidoPelaPlataforma.classList.remove("escondido");
    textoDefinidoPelaPlataforma.textContent = definidoPelaPlataforma
      ? "Definido pela plataforma."
      : "A plataforma não permite escolher o próprio LLM.";
    return;
  }
  rotulo.classList.remove("escondido");
  textoDefinidoPelaPlataforma.classList.add("escondido");
  selectConfiguracaoAtiva.innerHTML = "";
  const opcaoNenhuma = document.createElement("option");
  opcaoNenhuma.value = "";
  opcaoNenhuma.textContent = "Nenhuma";
  selectConfiguracaoAtiva.appendChild(opcaoNenhuma);
  configuracoes.forEach((configuracao) => {
    const opcao = document.createElement("option");
    opcao.value = configuracao.id;
    opcao.textContent = configuracao.etiqueta;
    selectConfiguracaoAtiva.appendChild(opcao);
  });
  selectConfiguracaoAtiva.value = configuracaoAtivaId != null ? String(configuracaoAtivaId) : "";
}

async function definirConfiguracaoAtiva() {
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="definicoes-lista"]');
  mensagemErro.textContent = "";
  const configuracaoId = selectConfiguracaoAtiva.value ? Number(selectConfiguracaoAtiva.value) : null;
  try {
    const resposta = await fetch("/api/llm/selecao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ configuracao_id: configuracaoId }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErro.textContent = corpo.detail || "Não foi possível guardar a escolha.";
      return;
    }
    mostrarToast("LLM ativo atualizado.");
    if (ALGUEM_ATIVO) ligarAlguem();
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

selectConfiguracaoAtiva.addEventListener("change", definirConfiguracaoAtiva);

async function apagarConfiguracaoLlm(configuracao) {
  if (!confirm(`Apagar a configuração "${configuracao.etiqueta}"?`)) return;
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="definicoes-lista"]');
  mensagemErro.textContent = "";
  try {
    const resposta = await fetch(`/api/llm/configuracoes/${configuracao.id}`, { method: "DELETE" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErro.textContent = corpo.detail || "Não foi possível apagar a configuração.";
      return;
    }
    mostrarToast("Configuração apagada.");
    carregarConfiguracoesLlm();
    if (ALGUEM_ATIVO) ligarAlguem();
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

document.getElementById("form-definicoes").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="definicoes"]');
  mensagemErro.textContent = "";
  const dados = Object.fromEntries(new FormData(evento.target));
  const configuracaoId = campoConfiguracaoId.value;
  try {
    const resposta = await fetch(
      configuracaoId ? `/api/llm/configuracoes/${configuracaoId}` : "/api/llm/configuracoes",
      {
        method: configuracaoId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
      },
    );
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErro.textContent = corpo.detail || "Algo correu mal.";
      return;
    }
    mostrarToast(configuracaoId ? "Configuração atualizada." : "Configuração criada.");
    fecharFormularioLlm();
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

document.getElementById("botao-sair").addEventListener("click", async () => {
  await fetch("/api/sair", { method: "POST" });
  window.location.href = "/";
});

// ---------- ligação para o painel de admin ----------

// só mostra a ligação do painel de admin a quem realmente é admin --
// evita uma ação morta (403) para todos os outros estudantes
const botaoAdmin = document.getElementById("botao-admin");

(async () => {
  try {
    const resposta = await fetch("/api/eu");
    const dados = await resposta.json();
    if (dados.admin) botaoAdmin.classList.remove("escondido");
    ALGUEM_ATIVO = !!dados.alguem_ativo;
    // As Definições do LLM do estudante só fazem sentido se a plataforma
    // permitir escolher um LLM pessoal -- sem isso, o painel só geria
    // configurações que nunca podiam ficar ativas (ver rota_eu em
    // main.py e a regra de precedência em configuracao_llm.py).
    if (dados.llm_pessoal_permitido) botaoDefinicoesAlguem.classList.remove("escondido");
  } catch (erro) { /* silencioso -- só uma ligação a mais */ }
  if (ALGUEM_ATIVO) {
    ligarAlguem();
    botaoAlternarAlguem.classList.remove("escondido");
    botaoAlternarAlguem.addEventListener("click", alternarPainelAlguem);
  }
})();

// ---------- painel do meio: execução / rasto / fluxograma ----------
// As três vistas partilham o mesmo painel (nunca ao mesmo tempo) -- só
// uma fica visível de cada vez, tal como o rasto já fazia antes de
// existir um terceiro estado.

const vistaExecucao = document.getElementById("vista-execucao");
const vistaRasto = document.getElementById("vista-rasto");
const vistaFluxograma = document.getElementById("vista-fluxograma");
const vistaLinter = document.getElementById("vista-linter");
const tituloPainelExecucao = document.getElementById("titulo-painel-execucao");
const seletorRotinaFluxograma = document.getElementById("seletor-rotina-fluxograma");
const botaoVoltarExecucao = document.getElementById("botao-voltar-execucao");
const botaoAbrirRasto = document.getElementById("botao-rasto");
const ligacaoAbrirVisualizador = document.getElementById("ligacao-abrir-visualizador");

const TITULOS_VISTA_PAINEL_TERMINAL = { execucao: "Execução", rasto: "Rasto", fluxograma: "Fluxograma", linter: "Verificador" };

function mostrarVistaPainelTerminal(nome) {
  vistaExecucao.classList.toggle("escondido", nome !== "execucao");
  vistaRasto.classList.toggle("escondido", nome !== "rasto");
  vistaFluxograma.classList.toggle("escondido", nome !== "fluxograma");
  vistaLinter.classList.toggle("escondido", nome !== "linter");
  tituloPainelExecucao.textContent = nome === "execucao" ? modoExecucaoAtual : TITULOS_VISTA_PAINEL_TERMINAL[nome];
  seletorRotinaFluxograma.classList.toggle("escondido", nome !== "fluxograma");
  botaoVoltarExecucao.classList.toggle("escondido", nome === "execucao");
  atualizarBotaoDescarregarRastoExecucao();
  if (nome === "rasto") {
    document.getElementById("conteudo-rasto").classList.add("escondido");
    document.getElementById("form-entradas-rasto").classList.remove("escondido");
  }
  if (nome !== "rasto" && ultimoUrlRasto) { URL.revokeObjectURL(ultimoUrlRasto); ultimoUrlRasto = null; }
}

botaoVoltarExecucao.addEventListener("click", () => mostrarVistaPainelTerminal("execucao"));
botaoAbrirRasto.addEventListener("click", () => mostrarVistaPainelTerminal("rasto"));

// ---------- modal de ajuda: busca /ajuda e injeta só o <main> no modal
// (sem iframe -- corre no documento principal). Só na primeira abertura
// (evita um pedido a cada carregamento do editor); um <script> de topo
// não pode ser declarado duas vezes no mesmo documento, por isso não dá
// para simplesmente repetir isto em cada abertura ----------

function ligarModalFragmento(botaoId, modalId, containerId, fecharId, url, scriptUrl) {
  const modal = document.getElementById(modalId);
  const container = document.getElementById(containerId);
  let carregado = false;
  document.getElementById(botaoId).addEventListener("click", async () => {
    modal.classList.remove("escondido");
    if (carregado) return;
    carregado = true;
    try {
      const resposta = await fetch(url);
      const texto = await resposta.text();
      const doc = new DOMParser().parseFromString(texto, "text/html");
      const main = doc.querySelector("main");
      if (!main) throw new Error("resposta sem <main>");
      container.innerHTML = main.outerHTML;
      const script = document.createElement("script");
      script.src = scriptUrl;
      document.body.appendChild(script);
    } catch (erro) {
      console.error(erro);
      container.innerHTML = '<p class="mensagem-erro">Não foi possível contactar o servidor.</p>';
    }
  });
  document.getElementById(fecharId).addEventListener("click", () => modal.classList.add("escondido"));
  modal.addEventListener("click", (evento) => {
    if (evento.target === modal) modal.classList.add("escondido");
  });
}

ligarModalFragmento("botao-ajuda", "modal-ajuda", "conteudo-ajuda-embutido", "botao-fechar-ajuda", "/ajuda", "/estatico/ajuda.js");

// ---------- modal de reportar um problema ----------

const modalReportar = document.getElementById("modal-reportar");
const formReportar = document.getElementById("form-reportar");
const campoDescricaoReportar = document.getElementById("campo-descricao-reportar");
const mensagemErroReportar = document.querySelector('.mensagem-erro[data-form="reportar"]');

function abrirReportar() {
  mensagemErroReportar.textContent = "";
  modalReportar.classList.remove("escondido");
}

function fecharReportar() {
  modalReportar.classList.add("escondido");
  formReportar.reset();
  mensagemErroReportar.textContent = "";
}

document.getElementById("botao-reportar").addEventListener("click", abrirReportar);
document.getElementById("botao-cancelar-reportar").addEventListener("click", fecharReportar);
document.getElementById("botao-fechar-reportar").addEventListener("click", fecharReportar);
modalReportar.addEventListener("click", (evento) => {
  if (evento.target === modalReportar) fecharReportar();
});

formReportar.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensagemErroReportar.textContent = "";
  try {
    const resposta = await fetch("/api/relatorios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ descricao: campoDescricaoReportar.value }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroReportar.textContent = corpo.detail || "Algo correu mal.";
      return;
    }
    fecharReportar();
  } catch (erro) {
    console.error(erro);
    mensagemErroReportar.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

// ---------- fluxograma ----------

// ON-33: a mensagem de erro pode conter texto derivado do código do
// estudante (ex: um erro de compilação a citar um identificador) --
// nunca interpolar diretamente em innerHTML. textContent escapa
// sempre, independentemente do conteúdo.
function mostrarErroEm(elemento, mensagem) {
  elemento.innerHTML = "";
  const p = document.createElement("p");
  p.className = "mensagem-erro";
  p.textContent = mensagem;
  elemento.appendChild(p);
}

const campoRotinaFluxograma = document.getElementById("campo-rotina-fluxograma");

async function carregarFluxograma(nomeRotina) {
  const conteudo = document.getElementById("conteudo-fluxograma");
  conteudo.innerHTML = "<p>A gerar…</p>";
  try {
    const resposta = await fetch("/api/fluxograma", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...obterTodosOsFicheiros(), rotina: nomeRotina }),
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarErroEm(conteudo, dados.detail || "Não foi possível gerar o fluxograma.");
      return;
    }
    // ON-34: o servidor já sanitiza este SVG (ver
    // executor._sanitizar_svg) antes de o devolver -- mas continua a
    // ser HTML de terceiros (graphviz) inserido via innerHTML, por
    // isso não é tratado como texto simples como o resto desta função.
    conteudo.innerHTML = dados.svg;

    // só reconstrói o seletor se a lista de rotinas mudou (ex: 1ª vez,
    // ou o código foi alterado) -- evita perder a seleção ao trocar
    if (campoRotinaFluxograma.dataset.rotinas !== JSON.stringify(dados.rotinas)) {
      campoRotinaFluxograma.dataset.rotinas = JSON.stringify(dados.rotinas);
      campoRotinaFluxograma.innerHTML = "";
      dados.rotinas.forEach((nome) => {
        const opcao = document.createElement("option");
        opcao.value = nome;
        opcao.textContent = nome;
        campoRotinaFluxograma.appendChild(opcao);
      });
    }
    campoRotinaFluxograma.value = dados.rotina_atual;
  } catch (erro) {
    console.error(erro);
    mostrarErroEm(conteudo, "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro));
  }
}

document.getElementById("botao-fluxograma").addEventListener("click", () => {
  mostrarVistaPainelTerminal("fluxograma");
  carregarFluxograma(null);
});

campoRotinaFluxograma.addEventListener("change", () => {
  carregarFluxograma(campoRotinaFluxograma.value);
});

// ---------- linter ----------
// Corre mesmo que o programa não compile por erro semântico -- só um
// erro de sintaxe/inclusão (ErroCompilacao) impede a análise; ver a
// nota em executor.analisar_linter sobre porquê.

async function carregarLinter() {
  const conteudo = document.getElementById("conteudo-linter");
  conteudo.innerHTML = "<p>A analisar…</p>";
  try {
    const resposta = await fetch("/api/linter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(obterTodosOsFicheiros()),
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mostrarErroEm(conteudo, dados.detail || "Não foi possível correr o verificador.");
      return;
    }
    if (dados.avisos.length === 0) {
      conteudo.innerHTML = "<p>✔ Nenhum aviso — o verificador não encontrou nada a assinalar.</p>";
      return;
    }
    const lista = document.createElement("ul");
    lista.className = "lista-avisos-linter";
    dados.avisos.forEach((aviso) => {
      const item = document.createElement("li");
      item.textContent = `linha ${aviso.linha}: ${aviso.mensagem}`;
      lista.appendChild(item);
    });
    conteudo.innerHTML = "";
    conteudo.appendChild(lista);
  } catch (erro) {
    console.error(erro);
    mostrarErroEm(conteudo, "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro));
  }
}

document.getElementById("botao-linter").addEventListener("click", () => {
  mostrarVistaPainelTerminal("linter");
  carregarLinter();
});

// ---------- rasto: gera o JSON, oferece download + link para o visualizador autónomo ----------
// (a mesma ferramenta que já existia para uso com `algo executa --json`, não uma
// navegação passo-a-passo própria -- decisão explícita: reaproveitar o visualizador
// já existente e testado, em vez de reconstruir a mesma coisa aqui.)

let ultimoUrlRasto = null;

document.getElementById("form-entradas-rasto").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="rasto"]');
  mensagemErro.textContent = "";
  document.getElementById("conteudo-rasto").classList.add("escondido");
  const entradas = document.getElementById("campo-entradas-rasto").value
    .split(",").map((l) => l.trim()).filter((l) => l !== "");

  try {
    const resposta = await fetch("/api/rasto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...obterTodosOsFicheiros(), entradas }),
    });
    const dados = await resposta.json();
    if (!resposta.ok) {
      mensagemErro.textContent = dados.detail || "Não foi possível gerar o rasto.";
      return;
    }
    if (dados.erro) {
      mensagemErro.textContent =
        `Não foi possível gerar o rasto: o programa terminou com um erro` +
        `${dados.erro.linha ? " na linha " + dados.erro.linha : ""} -- ${dados.erro.mensagem}`;
      return;
    }
    if (dados.passos.length === 0) {
      mensagemErro.textContent = "O programa não chegou a executar nenhum passo.";
      return;
    }

    if (ultimoUrlRasto) URL.revokeObjectURL(ultimoUrlRasto);
    const blob = new Blob([JSON.stringify(dados, null, 2)], { type: "application/json" });
    ultimoUrlRasto = URL.createObjectURL(blob);

    document.getElementById("rasto-num-passos").textContent = dados.passos.length;
    const ligacaoDescarregar = document.getElementById("ligacao-descarregar-rasto");
    ligacaoDescarregar.href = ultimoUrlRasto;
    ligacaoDescarregar.download = ficheiros[0].nome.replace(/\.algo$/, "") + "_trace.json";

    document.getElementById("conteudo-rasto").classList.remove("escondido");
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

// ---------- esconder/mostrar o painel do Alguem ----------

const painelAlguem = document.querySelector(".painel-alguem");
const divisorAlguem = document.querySelector('.divisor[data-divisor="1"]');
const botaoAlternarAlguem = document.getElementById("botao-alternar-alguem");

let ultimasColunasComAlguem = null;

function alternarPainelAlguem() {
  const disposicao = document.getElementById("disposicao-editor");
  const escondido = !painelAlguem.classList.contains("escondido");
  painelAlguem.classList.toggle("escondido", escondido);
  divisorAlguem.classList.toggle("escondido", escondido);

  const colunas = getComputedStyle(disposicao).gridTemplateColumns.split(" ").map(parseFloat);
  if (escondido) {
    ultimasColunasComAlguem = colunas;
    disposicao.style.gridTemplateColumns = `${colunas[0]}fr 6px ${colunas[2]}fr`;
  } else {
    const restauradas = ultimasColunasComAlguem || colunas.concat(["6px", colunas[0]]);
    disposicao.style.gridTemplateColumns = restauradas.map((c, i) => i % 2 === 1 ? "6px" : `${c}fr`).join(" ");
  }
  // Mesmo balão-com-pontinhos usado como ícone do Alguem na barra
  // lateral do admin (identidade visual consistente) -- "esconder"
  // acrescenta um traço diagonal, no mesmo espírito de um ícone de
  // olho/olho-fechado, mas com a forma do Alguem em vez de um olho
  // genérico.
  const ICONE_ALGUEM_MOSTRAR = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="8" y1="9" x2="8.01" y2="9"/><line x1="12" y1="9" x2="12.01" y2="9"/><line x1="16" y1="9" x2="16.01" y2="9"/></svg>';
  const ICONE_ALGUEM_ESCONDER = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="8" y1="9" x2="8.01" y2="9"/><line x1="12" y1="9" x2="12.01" y2="9"/><line x1="16" y1="9" x2="16.01" y2="9"/><line x1="3" y1="3" x2="21" y2="19"/></svg>';
  botaoAlternarAlguem.innerHTML = escondido ? ICONE_ALGUEM_MOSTRAR : ICONE_ALGUEM_ESCONDER;
  botaoAlternarAlguem.title = escondido ? "Mostrar Alguem" : "Esconder Alguem";
  if (editor.refresh) editor.refresh();
}

// painel do Alguem escondido por omissão: editor e terminal a 50/50;
// ao mostrar o Alguem, os três painéis passam a dividir o espaço
// em partes iguais (ver alternarPainelAlguem).

// ---------- painéis redimensionáveis (arrastar os divisores) ----------

function tornarPaineisRedimensionaveis() {
  const disposicao = document.getElementById("disposicao-editor");
  const divisores = Array.from(document.querySelectorAll(".divisor"));
  const LARGURA_MINIMA_PX = 220;

  divisores.forEach((divisor) => {
    divisor.addEventListener("mousedown", (eventoInicial) => {
      eventoInicial.preventDefault();
      divisor.classList.add("a-arrastar");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      const colunas = getComputedStyle(disposicao).gridTemplateColumns.split(" ").map(parseFloat);
      const indiceDivisor = Number(divisor.dataset.divisor); // 0 ou 1
      const indicePainelAntes = indiceDivisor * 2;     // 0 -> painel 0; 1 -> painel 2
      const indicePainelDepois = indiceDivisor * 2 + 2; // 0 -> painel 2; 1 -> painel 4
      const larguraInicialAntes = colunas[indicePainelAntes];
      const larguraInicialDepois = colunas[indicePainelDepois];
      const xInicial = eventoInicial.clientX;

      function aoMover(eventoMover) {
        const deslocamento = eventoMover.clientX - xInicial;
        let novaLarguraAntes = larguraInicialAntes + deslocamento;
        let novaLarguraDepois = larguraInicialDepois - deslocamento;
        if (novaLarguraAntes < LARGURA_MINIMA_PX || novaLarguraDepois < LARGURA_MINIMA_PX) return;

        colunas[indicePainelAntes] = novaLarguraAntes;
        colunas[indicePainelDepois] = novaLarguraDepois;
        disposicao.style.gridTemplateColumns = colunas.map((c, i) =>
          i % 2 === 1 ? "6px" : `${c}px`).join(" ");

        if (editor.refresh) editor.refresh();
      }

      function aoLargar() {
        divisor.classList.remove("a-arrastar");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        document.removeEventListener("mousemove", aoMover);
        document.removeEventListener("mouseup", aoLargar);
      }

      document.addEventListener("mousemove", aoMover);
      document.addEventListener("mouseup", aoLargar);
    });
  });
}

tornarPaineisRedimensionaveis();
