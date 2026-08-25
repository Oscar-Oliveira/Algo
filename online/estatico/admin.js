function formatarData(iso) {
  return iso.replace("T", " ").slice(0, 16);
}

function formatarPercentagem(valor) {
  return valor === null || valor === undefined ? "-" : `${Math.round(valor * 100)}%`;
}

// ---------- abas ----------

const abas = document.querySelectorAll(".aba-admin");
const conteudosCarregados = {};

function carregarConteudoDaAba(nomeAba) {
  // Relatórios fica de fora deste cache: ao contrário de utilizadores/
  // atividade (que só mudam por ação do próprio admin, já tratada à
  // parte), novos relatórios podem chegar a qualquer momento de outra
  // sessão -- sem recarregar sempre, reabrir a aba depois de um
  // estudante (ou o próprio admin) reportar algo não mostrava o
  // relatório novo, porque o iframe do admin nunca é recarregado
  // enquanto o modal só é escondido/mostrado.
  if (nomeAba === "relatorios") { carregarRelatorios(); return; }
  if (conteudosCarregados[nomeAba]) return;
  conteudosCarregados[nomeAba] = true;
  if (nomeAba === "utilizadores") carregarUtilizadores();
  if (nomeAba === "atividade") carregarAtividade();
}

abas.forEach((aba) => {
  aba.addEventListener("click", () => {
    abas.forEach((a) => a.classList.remove("ativa"));
    aba.classList.add("ativa");
    document.querySelectorAll(".conteudo-aba-admin").forEach((secao) => secao.classList.add("escondido"));
    document.getElementById(`aba-conteudo-${aba.dataset.aba}`).classList.remove("escondido");
    carregarConteudoDaAba(aba.dataset.aba);
  });
});

// ---------- utilizadores ----------

const corpoTabelaUtilizadores = document.getElementById("corpo-tabela-utilizadores");
const mensagemSemUtilizadores = document.getElementById("mensagem-sem-utilizadores");
const mensagemErroUtilizadores = document.getElementById("mensagem-erro-utilizadores");

function estadoDaConta(conta) {
  if (conta.admin) return "Admin";
  return conta.aprovado ? "Aprovado" : "Pendente";
}

async function carregarUtilizadores() {
  mensagemErroUtilizadores.textContent = "";
  try {
    const resposta = await fetch("/api/admin/utilizadores");
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroUtilizadores.textContent = corpo.detail || "Não foi possível carregar os utilizadores.";
      return;
    }
    const { utilizadores } = await resposta.json();
    corpoTabelaUtilizadores.innerHTML = "";
    mensagemSemUtilizadores.classList.toggle("escondido", utilizadores.length > 0);
    utilizadores.forEach((conta) => {
      const linha = document.createElement("tr");

      const celulaEmail = document.createElement("td");
      celulaEmail.textContent = conta.email;

      const celulaEstado = document.createElement("td");
      celulaEstado.textContent = estadoDaConta(conta);

      const celulaData = document.createElement("td");
      celulaData.textContent = formatarData(conta.criado_em);

      const celulaAcoes = document.createElement("td");
      if (!conta.aprovado) {
        const botaoAprovar = document.createElement("button");
        botaoAprovar.className = "botao-primario";
        botaoAprovar.textContent = "Aprovar";
        botaoAprovar.addEventListener("click", () => agirSobreUtilizador(conta.id, "aprovar"));

        const botaoRejeitar = document.createElement("button");
        botaoRejeitar.className = "botao-perigo";
        botaoRejeitar.textContent = "Rejeitar";
        botaoRejeitar.addEventListener("click", () => agirSobreUtilizador(conta.id, "rejeitar"));

        celulaAcoes.appendChild(botaoAprovar);
        celulaAcoes.appendChild(botaoRejeitar);
      } else if (!conta.admin) {
        const botaoRevogar = document.createElement("button");
        botaoRevogar.className = "botao-perigo";
        botaoRevogar.textContent = "Revogar";
        botaoRevogar.addEventListener("click", () => agirSobreUtilizador(conta.id, "revogar"));

        celulaAcoes.appendChild(botaoRevogar);
      }

      linha.appendChild(celulaEmail);
      linha.appendChild(celulaEstado);
      linha.appendChild(celulaData);
      linha.appendChild(celulaAcoes);
      corpoTabelaUtilizadores.appendChild(linha);
    });
  } catch (erro) {
    console.error(erro);
    mensagemErroUtilizadores.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function agirSobreUtilizador(idConta, acao) {
  mensagemErroUtilizadores.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/${acao}/${idConta}`, { method: "POST" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroUtilizadores.textContent = corpo.detail || "Não foi possível concluir a ação.";
      return;
    }
    carregarUtilizadores();
  } catch (erro) {
    console.error(erro);
    mensagemErroUtilizadores.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

// ---------- atividade ----------
// A lista de sessões pode crescer bastante (uma por conversa com o
// Alguem) -- por isso pede-se o relatório completo uma vez só e
// filtra-se/pagina-se aqui no browser (nada disto volta a tocar no
// servidor), em vez de repetir o pedido a cada filtro ou página.

const corpoTabelaAtividade = document.getElementById("corpo-tabela-atividade");
const mensagemSemAtividade = document.getElementById("mensagem-sem-atividade");
const mensagemErroAtividade = document.getElementById("mensagem-erro-atividade");
const inputPesquisaAtividade = document.getElementById("atividade-pesquisa");
const selectFornecedorAtividade = document.getElementById("atividade-filtro-fornecedor");
const botaoPaginaAnterior = document.getElementById("atividade-pagina-anterior");
const botaoPaginaSeguinte = document.getElementById("atividade-pagina-seguinte");
const textoPaginaAtividade = document.getElementById("atividade-texto-pagina");

const SESSOES_POR_PAGINA = 20;

let todasAsSessoes = [];
let estadoAtividade = { pesquisa: "", fornecedor: "", pagina: 1, ordenarPor: null, ordemAscendente: true };

async function carregarAtividade() {
  mensagemErroAtividade.textContent = "";
  try {
    const resposta = await fetch("/api/admin/atividade");
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroAtividade.textContent = corpo.detail || "Não foi possível carregar a atividade.";
      return;
    }
    const relatorio = await resposta.json();
    const globais = relatorio.globais;
    document.getElementById("metrica-num-sessoes").textContent = globais.num_sessoes;
    document.getElementById("metrica-num-estudantes").textContent = globais.num_estudantes;
    document.getElementById("metrica-leakage-global").textContent = formatarPercentagem(globais.solution_leakage_rate_global);
    document.getElementById("metrica-hint-dependency").textContent =
      globais.hint_dependency_media === null || globais.hint_dependency_media === undefined
        ? "-" : globais.hint_dependency_media.toFixed(1);

    todasAsSessoes = relatorio.por_sessao;
    preencherFiltroFornecedor(todasAsSessoes);
    atualizarTabelaAtividade();
  } catch (erro) {
    console.error(erro);
    mensagemErroAtividade.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

function preencherFiltroFornecedor(sessoes) {
  const fornecedores = [...new Set(sessoes.map((s) => s.fornecedor).filter(Boolean))].sort();
  selectFornecedorAtividade.innerHTML = '<option value="">Todos os fornecedores</option>';
  fornecedores.forEach((fornecedor) => {
    const opcao = document.createElement("option");
    opcao.value = fornecedor;
    opcao.textContent = fornecedor;
    selectFornecedorAtividade.appendChild(opcao);
  });
}

function compararSessoes(a, b, campo, ascendente) {
  const va = a[campo];
  const vb = b[campo];
  if (va === null || va === undefined) return vb === null || vb === undefined ? 0 : 1;
  if (vb === null || vb === undefined) return -1;
  const resultado = va < vb ? -1 : va > vb ? 1 : 0;
  return ascendente ? resultado : -resultado;
}

function sessoesFiltradasEOrdenadas() {
  const pesquisa = estadoAtividade.pesquisa.trim().toLowerCase();
  let sessoes = todasAsSessoes.filter((s) => {
    if (estadoAtividade.fornecedor && s.fornecedor !== estadoAtividade.fornecedor) return false;
    if (!pesquisa) return true;
    return (s.id_sessao || "").toLowerCase().includes(pesquisa)
      || (s.id_estudante || "").toLowerCase().includes(pesquisa);
  });
  if (estadoAtividade.ordenarPor) {
    sessoes = [...sessoes].sort((a, b) =>
      compararSessoes(a, b, estadoAtividade.ordenarPor, estadoAtividade.ordemAscendente));
  }
  return sessoes;
}

function atualizarTabelaAtividade() {
  const sessoes = sessoesFiltradasEOrdenadas();
  const totalPaginas = Math.max(1, Math.ceil(sessoes.length / SESSOES_POR_PAGINA));
  estadoAtividade.pagina = Math.min(estadoAtividade.pagina, totalPaginas);
  const inicio = (estadoAtividade.pagina - 1) * SESSOES_POR_PAGINA;
  const sessoesDaPagina = sessoes.slice(inicio, inicio + SESSOES_POR_PAGINA);

  corpoTabelaAtividade.innerHTML = "";
  mensagemSemAtividade.classList.toggle("escondido", sessoesDaPagina.length > 0);
  sessoesDaPagina.forEach((sessao) => {
    const linha = document.createElement("tr");
    const celulas = [
      sessao.id_sessao ? sessao.id_sessao.slice(0, 8) : "-",
      sessao.id_estudante ? sessao.id_estudante.slice(0, 8) : "-",
      sessao.num_turnos,
      formatarPercentagem(sessao.solution_leakage_rate),
      sessao.hint_escalation_maxima === null || sessao.hint_escalation_maxima === undefined ? "-" : sessao.hint_escalation_maxima,
      sessao.fornecedor ? `${sessao.fornecedor}/${sessao.modelo}` : "-",
      sessao.num_recusas_seguras,
    ];
    celulas.forEach((valor) => {
      const celula = document.createElement("td");
      celula.textContent = valor;
      linha.appendChild(celula);
    });
    corpoTabelaAtividade.appendChild(linha);
  });

  textoPaginaAtividade.textContent = `Página ${estadoAtividade.pagina} de ${totalPaginas} (${sessoes.length} sessões)`;
  botaoPaginaAnterior.disabled = estadoAtividade.pagina <= 1;
  botaoPaginaSeguinte.disabled = estadoAtividade.pagina >= totalPaginas;
}

inputPesquisaAtividade.addEventListener("input", () => {
  estadoAtividade.pesquisa = inputPesquisaAtividade.value;
  estadoAtividade.pagina = 1;
  atualizarTabelaAtividade();
});

selectFornecedorAtividade.addEventListener("change", () => {
  estadoAtividade.fornecedor = selectFornecedorAtividade.value;
  estadoAtividade.pagina = 1;
  atualizarTabelaAtividade();
});

botaoPaginaAnterior.addEventListener("click", () => {
  estadoAtividade.pagina -= 1;
  atualizarTabelaAtividade();
});

botaoPaginaSeguinte.addEventListener("click", () => {
  estadoAtividade.pagina += 1;
  atualizarTabelaAtividade();
});

document.querySelectorAll("th.ordenavel").forEach((cabecalho) => {
  cabecalho.addEventListener("click", () => {
    const campo = cabecalho.dataset.ordenar;
    if (estadoAtividade.ordenarPor === campo) {
      estadoAtividade.ordemAscendente = !estadoAtividade.ordemAscendente;
    } else {
      estadoAtividade.ordenarPor = campo;
      estadoAtividade.ordemAscendente = true;
    }
    document.querySelectorAll("th.ordenavel").forEach((th) => th.classList.remove("ordenado-asc", "ordenado-desc"));
    cabecalho.classList.add(estadoAtividade.ordemAscendente ? "ordenado-asc" : "ordenado-desc");
    atualizarTabelaAtividade();
  });
});

// ---------- relatórios de problemas ----------

const corpoTabelaRelatorios = document.getElementById("corpo-tabela-relatorios");
const mensagemSemRelatorios = document.getElementById("mensagem-sem-relatorios");
const mensagemErroRelatorios = document.getElementById("mensagem-erro-relatorios");
const botaoRelatoriosPaginaAnterior = document.getElementById("relatorios-pagina-anterior");
const botaoRelatoriosPaginaSeguinte = document.getElementById("relatorios-pagina-seguinte");
const textoPaginaRelatorios = document.getElementById("relatorios-texto-pagina");
const relatoriosTotal = document.getElementById("relatorios-total");

const RELATORIOS_POR_PAGINA = 20;

let todosOsRelatorios = [];
let paginaRelatorios = 1;

async function carregarRelatorios() {
  mensagemErroRelatorios.textContent = "";
  try {
    const resposta = await fetch("/api/admin/relatorios");
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroRelatorios.textContent = corpo.detail || "Não foi possível carregar os relatórios.";
      return;
    }
    const { relatorios } = await resposta.json();
    todosOsRelatorios = relatorios;
    paginaRelatorios = 1;
    atualizarTabelaRelatorios();
  } catch (erro) {
    console.error(erro);
    mensagemErroRelatorios.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

function atualizarTabelaRelatorios() {
  const totalPaginas = Math.max(1, Math.ceil(todosOsRelatorios.length / RELATORIOS_POR_PAGINA));
  paginaRelatorios = Math.min(paginaRelatorios, totalPaginas);
  const inicio = (paginaRelatorios - 1) * RELATORIOS_POR_PAGINA;
  const relatoriosDaPagina = todosOsRelatorios.slice(inicio, inicio + RELATORIOS_POR_PAGINA);

  corpoTabelaRelatorios.innerHTML = "";
  mensagemSemRelatorios.classList.toggle("escondido", relatoriosDaPagina.length > 0);
  relatoriosDaPagina.forEach((relatorio) => {
    const linha = document.createElement("tr");

    const celulaEmail = document.createElement("td");
    celulaEmail.appendChild(document.createTextNode(relatorio.email));
    celulaEmail.appendChild(document.createElement("br"));
    const dataRelatorio = document.createElement("span");
    dataRelatorio.className = "ajuda-campo";
    dataRelatorio.textContent = formatarData(relatorio.criado_em);
    celulaEmail.appendChild(dataRelatorio);

    const celulaDescricao = document.createElement("td");
    const areaDescricao = document.createElement("textarea");
    areaDescricao.className = "descricao-relatorio";
    areaDescricao.readOnly = true;
    areaDescricao.value = relatorio.descricao;
    celulaDescricao.appendChild(areaDescricao);

    const celulaAcoes = document.createElement("td");
    const botaoApagar = document.createElement("button");
    botaoApagar.className = "botao-perigo botao-com-icone";
    botaoApagar.innerHTML = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      + '<polyline points="4 7 20 7" /><path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />'
      + '<path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" /></svg><span>Apagar</span>';
    botaoApagar.addEventListener("click", () => apagarRelatorio(relatorio.id));
    celulaAcoes.appendChild(botaoApagar);

    linha.appendChild(celulaEmail);
    linha.appendChild(celulaDescricao);
    linha.appendChild(celulaAcoes);
    corpoTabelaRelatorios.appendChild(linha);
  });

  relatoriosTotal.textContent = todosOsRelatorios.length;
  textoPaginaRelatorios.textContent = `Página ${paginaRelatorios} de ${totalPaginas}`;
  botaoRelatoriosPaginaAnterior.disabled = paginaRelatorios <= 1;
  botaoRelatoriosPaginaSeguinte.disabled = paginaRelatorios >= totalPaginas;
}

async function apagarRelatorio(idRelatorio) {
  if (!confirm("Apagar este relatório? Não é possível desfazer.")) return;
  mensagemErroRelatorios.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/relatorios/apagar/${idRelatorio}`, { method: "POST" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroRelatorios.textContent = corpo.detail || "Não foi possível apagar o relatório.";
      return;
    }
    todosOsRelatorios = todosOsRelatorios.filter((r) => r.id !== idRelatorio);
    atualizarTabelaRelatorios();
  } catch (erro) {
    console.error(erro);
    mensagemErroRelatorios.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

botaoRelatoriosPaginaAnterior.addEventListener("click", () => {
  paginaRelatorios -= 1;
  atualizarTabelaRelatorios();
});

botaoRelatoriosPaginaSeguinte.addEventListener("click", () => {
  paginaRelatorios += 1;
  atualizarTabelaRelatorios();
});

carregarConteudoDaAba("utilizadores");
