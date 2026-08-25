function formatarData(iso) {
  return iso.replace("T", " ").slice(0, 16);
}

function formatarPercentagem(valor) {
  return valor === null || valor === undefined ? "-" : `${Math.round(valor * 100)}%`;
}

// Etiqueta de estado colorida (ver .badge* em estilo.css) -- usada em
// vez de texto simples sempre que uma célula representa um estado
// (ativo/inativo, aprovado/pendente/admin, tipo de evento no log).
function criarBadge(texto, variante) {
  const badge = document.createElement("span");
  badge.className = `badge badge-${variante}`;
  badge.textContent = texto;
  return badge;
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
  if (nomeAba === "grupos") carregarGrupos();
  if (nomeAba === "registoatividade") carregarLog();
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

let todosOsGruposParaSelect = [];
let idUtilizadorAtual = null;

function badgeEstadoDaConta(conta) {
  if (conta.admin) return criarBadge("Admin", "destaque");
  return conta.aprovado ? criarBadge("Aprovado", "sucesso") : criarBadge("Pendente", "aviso");
}

async function carregarUtilizadores() {
  mensagemErroUtilizadores.textContent = "";
  try {
    const [respostaUtilizadores, respostaGrupos, respostaEu] = await Promise.all([
      fetch("/api/admin/utilizadores"), fetch("/api/admin/grupos"), fetch("/api/eu"),
    ]);
    if (!respostaUtilizadores.ok) {
      const corpo = await respostaUtilizadores.json();
      mensagemErroUtilizadores.textContent = corpo.detail || "Não foi possível carregar os utilizadores.";
      return;
    }
    if (respostaGrupos.ok) {
      todosOsGruposParaSelect = (await respostaGrupos.json()).grupos;
    }
    if (respostaEu.ok) {
      idUtilizadorAtual = (await respostaEu.json()).id;
    }
    const { utilizadores } = await respostaUtilizadores.json();
    corpoTabelaUtilizadores.innerHTML = "";
    mensagemSemUtilizadores.classList.toggle("escondido", utilizadores.length > 0);
    utilizadores.forEach((conta) => {
      const linha = document.createElement("tr");

      const celulaEmail = document.createElement("td");
      celulaEmail.textContent = conta.email;

      const celulaEstado = document.createElement("td");
      celulaEstado.appendChild(badgeEstadoDaConta(conta));

      const celulaGrupo = document.createElement("td");
      const selectGrupo = document.createElement("select");
      selectGrupo.setAttribute("aria-label", `Grupo de ${conta.email}`);
      const opcaoSemGrupo = document.createElement("option");
      opcaoSemGrupo.value = "";
      opcaoSemGrupo.textContent = "Sem grupo";
      selectGrupo.appendChild(opcaoSemGrupo);
      todosOsGruposParaSelect.forEach((g) => {
        const opcao = document.createElement("option");
        opcao.value = g.id;
        opcao.textContent = g.nome;
        selectGrupo.appendChild(opcao);
      });
      selectGrupo.value = conta.grupo_id ? String(conta.grupo_id) : "";
      selectGrupo.addEventListener("change", () => mudarGrupoUtilizador(conta.id, selectGrupo.value));
      celulaGrupo.appendChild(selectGrupo);

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
      } else if (conta.admin) {
        if (conta.id === idUtilizadorAtual) {
          const notaPropriaConta = document.createElement("span");
          notaPropriaConta.className = "ajuda-campo";
          notaPropriaConta.textContent = "(a tua conta)";
          celulaAcoes.appendChild(notaPropriaConta);
        } else {
          const botaoRemoverAdmin = document.createElement("button");
          botaoRemoverAdmin.className = "botao-perigo";
          botaoRemoverAdmin.textContent = "Remover admin";
          botaoRemoverAdmin.addEventListener("click", () => agirSobreUtilizador(conta.id, "remover_admin"));
          celulaAcoes.appendChild(botaoRemoverAdmin);
        }
      } else {
        const botaoTornarAdmin = document.createElement("button");
        botaoTornarAdmin.className = "botao-secundario";
        botaoTornarAdmin.textContent = "Tornar admin";
        botaoTornarAdmin.addEventListener("click", () => agirSobreUtilizador(conta.id, "tornar_admin"));

        const botaoRevogar = document.createElement("button");
        botaoRevogar.className = "botao-perigo";
        botaoRevogar.textContent = "Revogar";
        botaoRevogar.addEventListener("click", () => agirSobreUtilizador(conta.id, "revogar"));

        celulaAcoes.appendChild(botaoTornarAdmin);
        celulaAcoes.appendChild(botaoRevogar);
      }

      linha.appendChild(celulaEmail);
      linha.appendChild(celulaEstado);
      linha.appendChild(celulaGrupo);
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

async function mudarGrupoUtilizador(idConta, grupoIdTexto) {
  mensagemErroUtilizadores.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/utilizadores/${idConta}/grupo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grupo_id: grupoIdTexto ? Number(grupoIdTexto) : null }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroUtilizadores.textContent = corpo.detail || "Não foi possível mudar o grupo.";
    }
  } catch (erro) {
    console.error(erro);
    mensagemErroUtilizadores.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  } finally {
    carregarUtilizadores();
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

// ---------- grupos ----------

const formCriarGrupo = document.getElementById("form-criar-grupo");
const campoNomeGrupoNovo = document.getElementById("grupo-novo-nome");
const corpoTabelaGrupos = document.getElementById("corpo-tabela-grupos");
const mensagemSemGrupos = document.getElementById("mensagem-sem-grupos");
const mensagemErroGrupos = document.getElementById("mensagem-erro-grupos");

async function carregarGrupos() {
  mensagemErroGrupos.textContent = "";
  try {
    const resposta = await fetch("/api/admin/grupos");
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível carregar os grupos.";
      return;
    }
    const { grupos } = await resposta.json();
    todosOsGruposParaSelect = grupos;
    corpoTabelaGrupos.innerHTML = "";
    mensagemSemGrupos.classList.toggle("escondido", grupos.length > 0);
    grupos.forEach((grupo) => {
      const linha = document.createElement("tr");

      const celulaNome = document.createElement("td");
      celulaNome.textContent = grupo.nome;

      const celulaEstado = document.createElement("td");
      celulaEstado.appendChild(grupo.ativo ? criarBadge("Ativo", "sucesso") : criarBadge("Inativo", "erro"));

      const celulaMembros = document.createElement("td");
      celulaMembros.className = "numero";
      celulaMembros.textContent = grupo.num_membros;

      const celulaCodigo = document.createElement("td");
      const botaoVerCodigo = document.createElement("button");
      botaoVerCodigo.className = "botao-secundario";
      botaoVerCodigo.textContent = "Ver código";
      botaoVerCodigo.addEventListener("click", () => verCodigoGrupo(grupo.id, celulaCodigo, botaoVerCodigo));
      celulaCodigo.appendChild(botaoVerCodigo);

      const celulaAcoes = document.createElement("td");
      const botaoAtivarDesativar = document.createElement("button");
      botaoAtivarDesativar.className = "botao-secundario";
      botaoAtivarDesativar.textContent = grupo.ativo ? "Desativar" : "Ativar";
      botaoAtivarDesativar.addEventListener("click", () => agirSobreGrupo(grupo.id, grupo.ativo ? "desativar" : "ativar"));

      const botaoRegenerar = document.createElement("button");
      botaoRegenerar.className = "botao-secundario";
      botaoRegenerar.textContent = "Regenerar código";
      botaoRegenerar.addEventListener("click", () => regenerarCodigoGrupo(grupo.id));

      const botaoExportar = document.createElement("a");
      botaoExportar.className = "botao-secundario";
      botaoExportar.textContent = "Exportar membros";
      botaoExportar.href = `/api/admin/grupos/${grupo.id}/membros.csv`;
      botaoExportar.target = "_blank";

      const botaoApagar = document.createElement("button");
      botaoApagar.className = "botao-perigo";
      botaoApagar.textContent = "Eliminar";
      botaoApagar.addEventListener("click", () => apagarGrupo(grupo.id));

      celulaAcoes.appendChild(botaoAtivarDesativar);
      celulaAcoes.appendChild(botaoRegenerar);
      celulaAcoes.appendChild(botaoExportar);
      celulaAcoes.appendChild(botaoApagar);

      linha.appendChild(celulaNome);
      linha.appendChild(celulaEstado);
      linha.appendChild(celulaMembros);
      linha.appendChild(celulaCodigo);
      linha.appendChild(celulaAcoes);
      corpoTabelaGrupos.appendChild(linha);
    });
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

formCriarGrupo.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensagemErroGrupos.textContent = "";
  try {
    const resposta = await fetch("/api/admin/grupos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: campoNomeGrupoNovo.value }),
    });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível criar o grupo.";
      return;
    }
    campoNomeGrupoNovo.value = "";
    alert(`Grupo "${corpo.nome}" criado. Código: ${corpo.codigo}\n\nAnota-o -- podes voltar a consultá-lo a qualquer momento com "Ver código".`);
    carregarGrupos();
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

async function verCodigoGrupo(grupoId, celula, botao) {
  try {
    const resposta = await fetch(`/api/admin/grupos/${grupoId}/codigo`);
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível obter o código.";
      return;
    }
    celula.textContent = corpo.codigo;
    celula.className = "texto-mono";
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function regenerarCodigoGrupo(grupoId) {
  if (!confirm("Gerar um código novo? O código antigo deixa de servir para novos registos (quem já está no grupo não é afetado).")) return;
  mensagemErroGrupos.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/grupos/${grupoId}/regenerar_codigo`, { method: "POST" });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível regenerar o código.";
      return;
    }
    alert(`Código novo: ${corpo.codigo}`);
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function agirSobreGrupo(grupoId, acao) {
  mensagemErroGrupos.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/grupos/${grupoId}/${acao}`, { method: "POST" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível concluir a ação.";
      return;
    }
    carregarGrupos();
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function apagarGrupo(grupoId) {
  if (!confirm("Eliminar este grupo definitivamente? Só é possível se não tiver membros.")) return;
  await agirSobreGrupo(grupoId, "apagar");
}

// ---------- registo geral de atividade ----------

const corpoTabelaLog = document.getElementById("corpo-tabela-log");
const mensagemSemLog = document.getElementById("mensagem-sem-log");
const mensagemErroLog = document.getElementById("mensagem-erro-log");
const selectLogUtilizador = document.getElementById("log-filtro-utilizador");
const selectLogGrupo = document.getElementById("log-filtro-grupo");
const selectLogTipo = document.getElementById("log-filtro-tipo");
const campoLogDataInicio = document.getElementById("log-filtro-data-inicio");
const campoLogDataFim = document.getElementById("log-filtro-data-fim");
const botaoLogAplicarFiltros = document.getElementById("log-aplicar-filtros");
const linkLogExportarCsv = document.getElementById("log-exportar-csv");
const checkboxLogSelecionarTudo = document.getElementById("log-selecionar-tudo");
const botaoLogApagarSelecionados = document.getElementById("log-apagar-selecionados");
const textoLogSelecionados = document.getElementById("log-texto-selecionados");
const botaoLogPaginaAnterior = document.getElementById("log-pagina-anterior");
const botaoLogPaginaSeguinte = document.getElementById("log-pagina-seguinte");
const textoLogPagina = document.getElementById("log-texto-pagina");

const TIPOS_LOG_CONHECIDOS = [
  "login", "login_falhado", "registo", "conta_aprovada", "conta_rejeitada", "conta_revogada",
  "admin_concedido", "admin_revogado", "grupo_criado", "grupo_editado", "grupo_ativado",
  "grupo_desativado", "grupo_eliminado", "grupo_reatribuido",
];

// Agrupa os tipos de evento por variante de badge, para se conseguir
// varrer a tabela visualmente à procura de falhas/remoções sem ler
// cada linha -- mesma convenção já usada noutros painéis de auditoria.
const TIPOS_LOG_ERRO = new Set([
  "login_falhado", "conta_rejeitada", "conta_revogada",
  "admin_revogado", "grupo_desativado", "grupo_eliminado",
]);
const TIPOS_LOG_SUCESSO = new Set([
  "login", "registo", "conta_aprovada", "admin_concedido", "grupo_criado", "grupo_ativado",
]);

function variantePorTipoLog(tipo) {
  if (TIPOS_LOG_ERRO.has(tipo)) return "erro";
  if (TIPOS_LOG_SUCESSO.has(tipo)) return "sucesso";
  return "neutro";
}

let paginaLog = 1;
let idsSelecionadosLog = new Set();

function construirQueryLog(incluirPagina) {
  const parametros = new URLSearchParams();
  if (selectLogUtilizador.value) parametros.set("estudante_id", selectLogUtilizador.value);
  if (selectLogGrupo.value) parametros.set("grupo_id", selectLogGrupo.value);
  if (selectLogTipo.value) parametros.set("tipo", selectLogTipo.value);
  if (campoLogDataInicio.value) parametros.set("data_inicio", campoLogDataInicio.value);
  if (campoLogDataFim.value) parametros.set("data_fim", campoLogDataFim.value);
  if (incluirPagina) parametros.set("pagina", String(paginaLog));
  return parametros;
}

async function popularFiltrosLog() {
  selectLogTipo.innerHTML = '<option value="">Todos os tipos</option>';
  TIPOS_LOG_CONHECIDOS.forEach((tipo) => {
    const opcao = document.createElement("option");
    opcao.value = tipo;
    opcao.textContent = tipo;
    selectLogTipo.appendChild(opcao);
  });

  try {
    const [respostaUtilizadores, respostaGrupos] = await Promise.all([
      fetch("/api/admin/utilizadores"), fetch("/api/admin/grupos"),
    ]);
    if (respostaUtilizadores.ok) {
      const { utilizadores } = await respostaUtilizadores.json();
      selectLogUtilizador.innerHTML = '<option value="">Todos os utilizadores</option>';
      utilizadores.forEach((conta) => {
        const opcao = document.createElement("option");
        opcao.value = conta.id;
        opcao.textContent = conta.email;
        selectLogUtilizador.appendChild(opcao);
      });
    }
    if (respostaGrupos.ok) {
      const { grupos } = await respostaGrupos.json();
      selectLogGrupo.innerHTML = '<option value="">Todos os grupos</option>';
      grupos.forEach((grupo) => {
        const opcao = document.createElement("option");
        opcao.value = grupo.id;
        opcao.textContent = grupo.nome;
        selectLogGrupo.appendChild(opcao);
      });
    }
  } catch (erro) {
    console.error(erro);
  }
}

function atualizarEstadoSelecaoLog() {
  botaoLogApagarSelecionados.disabled = idsSelecionadosLog.size === 0;
  textoLogSelecionados.textContent = idsSelecionadosLog.size > 0 ? `${idsSelecionadosLog.size} selecionado(s)` : "";
}

async function carregarLog() {
  mensagemErroLog.textContent = "";
  await popularFiltrosLog();
  await atualizarTabelaLog();
}

async function atualizarTabelaLog() {
  mensagemErroLog.textContent = "";
  idsSelecionadosLog = new Set();
  atualizarEstadoSelecaoLog();
  checkboxLogSelecionarTudo.checked = false;
  linkLogExportarCsv.href = `/api/admin/log.csv?${construirQueryLog(false).toString()}`;
  try {
    const resposta = await fetch(`/api/admin/log?${construirQueryLog(true).toString()}`);
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroLog.textContent = corpo.detail || "Não foi possível carregar o registo de atividade.";
      return;
    }
    const { eventos, total, pagina, por_pagina } = await resposta.json();
    corpoTabelaLog.innerHTML = "";
    mensagemSemLog.classList.toggle("escondido", eventos.length > 0);
    eventos.forEach((evento) => {
      const linha = document.createElement("tr");

      const celulaCheckbox = document.createElement("td");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) idsSelecionadosLog.add(evento.id);
        else idsSelecionadosLog.delete(evento.id);
        atualizarEstadoSelecaoLog();
      });
      celulaCheckbox.appendChild(checkbox);

      const celulaData = document.createElement("td");
      celulaData.textContent = formatarData(evento.criado_em);

      const celulaTipo = document.createElement("td");
      celulaTipo.appendChild(criarBadge(evento.tipo, variantePorTipoLog(evento.tipo)));

      const celulaAtor = document.createElement("td");
      celulaAtor.textContent = evento.ator_email || "-";

      const celulaAlvo = document.createElement("td");
      celulaAlvo.textContent = evento.alvo_email || "-";

      const celulaGrupoLog = document.createElement("td");
      celulaGrupoLog.textContent = evento.grupo_nome || "-";

      const celulaDetalhes = document.createElement("td");
      celulaDetalhes.className = "texto-mono";
      celulaDetalhes.textContent = evento.detalhes ? JSON.stringify(evento.detalhes) : "";

      linha.appendChild(celulaCheckbox);
      linha.appendChild(celulaData);
      linha.appendChild(celulaTipo);
      linha.appendChild(celulaAtor);
      linha.appendChild(celulaAlvo);
      linha.appendChild(celulaGrupoLog);
      linha.appendChild(celulaDetalhes);
      corpoTabelaLog.appendChild(linha);
    });

    const totalPaginas = Math.max(1, Math.ceil(total / por_pagina));
    textoLogPagina.textContent = `Página ${pagina} de ${totalPaginas} (${total} registos)`;
    botaoLogPaginaAnterior.disabled = pagina <= 1;
    botaoLogPaginaSeguinte.disabled = pagina >= totalPaginas;
  } catch (erro) {
    console.error(erro);
    mensagemErroLog.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

botaoLogAplicarFiltros.addEventListener("click", () => { paginaLog = 1; atualizarTabelaLog(); });
botaoLogPaginaAnterior.addEventListener("click", () => { paginaLog -= 1; atualizarTabelaLog(); });
botaoLogPaginaSeguinte.addEventListener("click", () => { paginaLog += 1; atualizarTabelaLog(); });

checkboxLogSelecionarTudo.addEventListener("change", () => {
  document.querySelectorAll("#corpo-tabela-log input[type=checkbox]").forEach((cb) => {
    cb.checked = checkboxLogSelecionarTudo.checked;
    cb.dispatchEvent(new Event("change"));
  });
});

botaoLogApagarSelecionados.addEventListener("click", async () => {
  if (idsSelecionadosLog.size === 0) return;
  if (!confirm(`Eliminar definitivamente ${idsSelecionadosLog.size} registo(s)? Esta ação não pode ser desfeita.`)) return;
  mensagemErroLog.textContent = "";
  try {
    const resposta = await fetch("/api/admin/log/apagar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [...idsSelecionadosLog] }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroLog.textContent = corpo.detail || "Não foi possível eliminar os registos selecionados.";
      return;
    }
    atualizarTabelaLog();
  } catch (erro) {
    console.error(erro);
    mensagemErroLog.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
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

carregarConteudoDaAba("grupos");
