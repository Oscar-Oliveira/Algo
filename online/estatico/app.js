const CODIGO_POR_OMISSAO = 'algoritmo "MeuPrograma"\ninicio\n    escrever("ola")\n';

function criarEditor() {
  const areaTexto = document.getElementById("area-codigo");
  areaTexto.value = CODIGO_POR_OMISSAO;
  try {
    if (typeof CodeMirror === "undefined") {
      throw new Error("CodeMirror não carregou -- a usar a área de texto simples.");
    }
    return CodeMirror.fromTextArea(areaTexto, {
      lineNumbers: true,
      theme: "material-darker",
      mode: "algo",
      indentUnit: 4,
      tabSize: 4,
      indentWithTabs: false,
    });
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


const formEntradaTerminal = document.getElementById("form-entrada-terminal");
const entradaTerminal = document.getElementById("entrada-terminal");

function escreverNoTerminal(texto, classe) {
  const linha = document.createElement("div");
  if (classe) linha.className = classe;
  linha.textContent = texto;
  terminal.appendChild(linha);
  terminal.scrollTop = terminal.scrollHeight;
}

let wsExecucao = null;

document.getElementById("botao-executar").addEventListener("click", () => {
  mostrarVistaPainelTerminal("execucao");
  document.querySelector(".painel-terminal").scrollIntoView({ behavior: "smooth", block: "start" });
  terminal.innerHTML = "";
  formEntradaTerminal.classList.add("escondido");
  if (wsExecucao) wsExecucao.close();

  const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
  wsExecucao = new WebSocket(`${protocolo}//${window.location.host}/ws/executar`);

  wsExecucao.addEventListener("open", () => {
    wsExecucao.send(JSON.stringify(obterTodosOsFicheiros()));
  });

  wsExecucao.addEventListener("message", (evento) => {
    const dados = JSON.parse(evento.data);
    if (dados.tipo === "erro_compilacao") {
      escreverNoTerminal(dados.mensagem, "linha-erro");
    } else if (dados.tipo === "compilado") {
      escreverNoTerminal("-- a executar --", "linha-sistema");
      formEntradaTerminal.classList.remove("escondido");
      entradaTerminal.focus();
    } else if (dados.tipo === "saida") {
      escreverNoTerminal(dados.texto);
    } else if (dados.tipo === "fim") {
      escreverNoTerminal(`-- terminou (código ${dados.codigo_saida}) --`, "linha-sistema");
      formEntradaTerminal.classList.add("escondido");
    } else if (dados.tipo === "erro") {
      escreverNoTerminal(dados.mensagem, "linha-erro");
      formEntradaTerminal.classList.add("escondido");
    }
  });

  wsExecucao.addEventListener("close", () => {
    formEntradaTerminal.classList.add("escondido");
  });
});

formEntradaTerminal.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const valor = entradaTerminal.value;
  escreverNoTerminal("> " + valor, "linha-sistema");
  if (wsExecucao && wsExecucao.readyState === WebSocket.OPEN) {
    wsExecucao.send(JSON.stringify({ tipo: "entrada", valor }));
  }
  entradaTerminal.value = "";
});

// ---------- Alguem ----------

const conversaAlguem = document.getElementById("conversa-alguem");
let wsAlguem = null;

function ligarAlguem() {
  const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
  wsAlguem = new WebSocket(`${protocolo}//${window.location.host}/ws/alguem`);

  wsAlguem.addEventListener("message", (evento) => {
    const dados = JSON.parse(evento.data);
    if (dados.tipo === "pronto" || dados.tipo === "resposta") {
      esconderIndicadorAPensar();
      adicionarMensagem(dados.mensagem || dados.texto, "mensagem-alguem");
    } else if (dados.tipo === "erro") {
      esconderIndicadorAPensar();
      adicionarMensagem(dados.mensagem, "mensagem-erro-chat");
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

ligarAlguem();

// ---------- definições do LLM (vivem dentro do painel do Alguem) ----------

const vistaConversaAlguem = document.getElementById("vista-conversa-alguem");
const vistaDefinicoesAlguem = document.getElementById("vista-definicoes-alguem");
const campoFornecedor = document.getElementById("campo-fornecedor");
const rotuloApiKey = document.getElementById("rotulo-api-key");
const rotuloHost = document.getElementById("rotulo-host");

function atualizarCamposFornecedor() {
  const ollama = campoFornecedor.value === "ollama";
  rotuloApiKey.classList.toggle("escondido", ollama);
  rotuloHost.classList.toggle("escondido", !ollama);
}
campoFornecedor.addEventListener("change", atualizarCamposFornecedor);

async function abrirDefinicoes() {
  vistaConversaAlguem.classList.add("escondido");
  vistaDefinicoesAlguem.classList.remove("escondido");
  try {
    const resposta = await fetch("/api/credencial");
    const dados = await resposta.json();
    if (dados.configurado) {
      campoFornecedor.value = dados.fornecedor;
      document.getElementById("campo-modelo").value = dados.modelo;
      if (dados.host) document.getElementById("campo-host").value = dados.host;
    }
  } catch (erro) { /* silencioso -- só um pré-preenchimento */ }
  atualizarCamposFornecedor();
}

function fecharDefinicoes() {
  vistaDefinicoesAlguem.classList.add("escondido");
  vistaConversaAlguem.classList.remove("escondido");
}

document.getElementById("botao-definicoes-alguem").addEventListener("click", abrirDefinicoes);
document.getElementById("botao-fechar-definicoes").addEventListener("click", fecharDefinicoes);

document.getElementById("form-definicoes").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="definicoes"]');
  mensagemErro.textContent = "";
  const dados = Object.fromEntries(new FormData(evento.target));
  try {
    const resposta = await fetch("/api/credencial", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErro.textContent = corpo.detail || "Algo correu mal.";
      return;
    }
    fecharDefinicoes();
    ligarAlguem();
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
  } catch (erro) { /* silencioso -- só uma ligação a mais */ }
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
const botaoVoltarExecucao = document.getElementById("botao-voltar-execucao");

const TITULOS_VISTA_PAINEL_TERMINAL = { execucao: "Execução", rasto: "Rasto", fluxograma: "Fluxograma", linter: "Verificador" };

function mostrarVistaPainelTerminal(nome) {
  vistaExecucao.classList.toggle("escondido", nome !== "execucao");
  vistaRasto.classList.toggle("escondido", nome !== "rasto");
  vistaFluxograma.classList.toggle("escondido", nome !== "fluxograma");
  vistaLinter.classList.toggle("escondido", nome !== "linter");
  tituloPainelExecucao.textContent = TITULOS_VISTA_PAINEL_TERMINAL[nome];
  botaoVoltarExecucao.classList.toggle("escondido", nome === "execucao");
  if (nome === "rasto") {
    document.getElementById("conteudo-rasto").classList.add("escondido");
    document.getElementById("form-entradas-rasto").classList.remove("escondido");
  }
  if (nome !== "rasto" && ultimoUrlRasto) { URL.revokeObjectURL(ultimoUrlRasto); ultimoUrlRasto = null; }
}

document.getElementById("botao-rasto").addEventListener("click", () => mostrarVistaPainelTerminal("rasto"));
botaoVoltarExecucao.addEventListener("click", () => mostrarVistaPainelTerminal("execucao"));

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
      mensagemErro.textContent = `${dados.erro.mensagem}${dados.erro.linha ? " (linha " + dados.erro.linha + ")" : ""}`;
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
  const ICONE_OLHO = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>';
  const ICONE_OLHO_FECHADO = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.9 17.9A10.4 10.4 0 0 1 12 20c-7 0-11-8-11-8a18.6 18.6 0 0 1 4.2-5.2M9.9 5.2A9.7 9.7 0 0 1 12 5c7 0 11 8 11 8a18.4 18.4 0 0 1-2.2 3.1M14.1 14.1a3 3 0 1 1-4.2-4.2"/><line x1="2" y1="2" x2="22" y2="22"/></svg>';
  botaoAlternarAlguem.innerHTML = escondido ? ICONE_OLHO : ICONE_OLHO_FECHADO;
  botaoAlternarAlguem.title = escondido ? "Mostrar Alguem" : "Esconder Alguem";
  if (editor.refresh) editor.refresh();
}

botaoAlternarAlguem.addEventListener("click", alternarPainelAlguem);
// UX-12: painel do Alguem visível por omissão -- antes começava
// escondido, só descoberto por um ícone pequeno no topo; um estudante
// novo na web podia nunca descobrir que o tutor existe (ao contrário
// da CLI, onde "?" é anunciado logo no banner inicial).

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
