// Ícones SVG partilhados pelos botões montados em JS (linhas de tabela
// sobretudo) -- mesmo "kit" (viewBox 24x24, traço 1.8) dos ícones já
// escritos à mão no admin.html, só centralizado aqui para não repetir a
// mesma string em cada função que gera uma linha.
const ICONES = {
  olho: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>',
  olhoFechado: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a21.8 21.8 0 0 1 5.06-6.06M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a21.8 21.8 0 0 1-2.16 3.19" /><line x1="1" y1="1" x2="23" y2="23" /></svg>',
  energia: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0" /><line x1="12" y1="2" x2="12" y2="12" /></svg>',
  mensagem: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>',
  atualizar: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>',
  descarregar: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12" /><polyline points="7 10 12 15 17 10" /><path d="M4 19h16" /></svg>',
  apagar: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 20 7" /><path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" /><path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" /></svg>',
  check: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12" /></svg>',
  x: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>',
  escudo: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>',
  escudoRemover: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><line x1="9.5" y1="9.5" x2="14.5" y2="14.5" /><line x1="14.5" y1="9.5" x2="9.5" y2="14.5" /></svg>',
  trocar: '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9" /><path d="M3 11V9a4 4 0 0 1 4-4h14" /><polyline points="7 23 3 19 7 15" /><path d="M21 13v2a4 4 0 0 1-4 4H3" /></svg>',
};

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

// ---------- notificação flutuante (toast) ----------
// Confirmação visual partilhada por todo o painel de admin (Utilizadores,
// Definições, ...) de que uma ação foi guardada -- flutua sobre o
// conteúdo e desaparece sozinha, em vez de competir por espaço com as
// mensagens de erro (essas continuam inline, perto do formulário/tabela
// em causa, porque um erro pede mais atenção e pode precisar de ficar
// visível até o utilizador tentar de novo).
const elementoToast = document.getElementById("toast-notificacao");
const textoToast = document.getElementById("toast-notificacao-texto");
let timeoutToast = null;

function mostrarToast(texto) {
  textoToast.textContent = texto;
  clearTimeout(timeoutToast);
  elementoToast.classList.add("visivel");
  timeoutToast = setTimeout(() => elementoToast.classList.remove("visivel"), 2200);
  // Toda a ação bem-sucedida passa por aqui (ver chamadas por todo o
  // ficheiro) -- por isso é também o sítio certo, único, para invalidar
  // a cache de abas por carregar (conteudosCarregados, definida mais
  // abaixo): uma mudança feita numa aba (ex: mudar o grupo de um
  // estudante em Utilizadores) pode afetar o que outra aba mostra (ex:
  // a contagem de membros em Grupos, ou um evento novo em Registo de
  // Atividade), e sem isto essa outra aba só via a versão antiga até a
  // página ser recarregada por completo. Fica sempre tudo por
  // recarregar na próxima vez que essa aba for aberta -- nunca a atual,
  // que já trata da sua própria recarga logo a seguir à ação.
  Object.keys(conteudosCarregados).forEach((chave) => delete conteudosCarregados[chave]);
}

// ---------- abas ----------

const abas = document.querySelectorAll(".item-lateral-admin");
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
  if (nomeAba === "alguem") carregarDefinicoesAlguem();
  if (nomeAba === "llm") carregarConfiguracoesLlmAdmin();
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

// Subabas horizontais dentro de uma aba (ex: Investigação -> Dashboard/
// Relatório) -- só alternam visibilidade, os dados de ambas já vêm
// carregados juntos por atualizarInvestigacao().
document.querySelectorAll(".aba-secundaria-admin").forEach((subaba) => {
  subaba.addEventListener("click", () => {
    const grupo = subaba.closest(".conteudo-aba-admin");
    grupo.querySelectorAll(".aba-secundaria-admin").forEach((s) => s.classList.remove("ativa"));
    subaba.classList.add("ativa");
    grupo.querySelectorAll(".conteudo-subaba-admin").forEach((secao) => secao.classList.add("escondido"));
    document.getElementById(`subaba-conteudo-${subaba.dataset.subaba}`).classList.remove("escondido");
  });
});

// Abas só para admin global (ver online/main.py admin_global_atual) --
// esconder aqui é só cosmético, a proteção real é do lado do servidor
// (403 em cada rota destas abas para um admin de grupo).
const ABAS_RESTRITAS_A_ADMIN_GLOBAL = ["grupos", "utilizadores", "registoatividade", "relatorios", "alguem", "llm", "definicoes"];

// Guardado globalmente para gates client-side dentro de uma aba
// partilhada por admin global/de grupo (ex: painel de eliminação de
// execuções na aba Investigação) -- de novo, só cosmético, a proteção
// real é sempre do lado do servidor.
let EH_ADMIN_GLOBAL = false;

async function aplicarRestricoesDeAdmin() {
  try {
    const resposta = await fetch("/api/eu");
    if (!resposta.ok) return;
    const { admin_global } = await resposta.json();
    EH_ADMIN_GLOBAL = admin_global;
    if (admin_global) return;
    ABAS_RESTRITAS_A_ADMIN_GLOBAL.forEach((nomeAba) => {
      document.querySelector(`.item-lateral-admin[data-aba="${nomeAba}"]`)?.classList.add("escondido");
      document.getElementById(`aba-conteudo-${nomeAba}`)?.classList.add("escondido");
    });
  } catch (erro) {
    console.error(erro);
  }
}

aplicarRestricoesDeAdmin();

// ---------- utilizadores ----------

const corpoTabelaUtilizadores = document.getElementById("corpo-tabela-utilizadores");
const mensagemSemUtilizadores = document.getElementById("mensagem-sem-utilizadores");
const mensagemErroUtilizadores = document.getElementById("mensagem-erro-utilizadores");

let todosOsGruposParaSelect = [];
let idUtilizadorAtual = null;

function badgeEstadoDaConta(conta) {
  if (conta.admin) return criarBadge(conta.admin_global ? "Admin global" : "Admin de grupo", "destaque");
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

      // Uma só coluna, com significado diferente consoante o tipo de
      // conta (as três regras vivem todas na mesma relação --
      // estudante_grupo, ver grupos.py -- só a cardinalidade muda):
      // - estudante: pertence no máximo a um grupo -> dropdown único.
      // - admin global: não precisa de nenhum, já vê tudo -> só texto.
      // - admin de grupo: gere zero ou mais -> checkboxes (não um
      //   <select multiple>, que exige Ctrl/Cmd+clique e é fácil de
      //   confundir com "já vem tudo selecionado").
      const celulaGrupo = document.createElement("td");
      if (conta.admin && conta.admin_global) {
        celulaGrupo.className = "ajuda-campo";
        celulaGrupo.textContent = "Acesso a todos os grupos";
      } else if (conta.admin) {
        if (todosOsGruposParaSelect.length === 0) {
          celulaGrupo.className = "ajuda-campo";
          celulaGrupo.textContent = "Ainda não há grupos criados.";
        } else {
          const listaGruposGeridos = document.createElement("div");
          listaGruposGeridos.className = "lista-grupos-geridos";
          const idsGeridos = new Set(conta.grupos_geridos_ids || []);
          todosOsGruposParaSelect.forEach((g) => {
            const rotulo = document.createElement("label");
            rotulo.className = "opcao-grupo-gerido";
            const caixa = document.createElement("input");
            caixa.type = "checkbox";
            caixa.checked = idsGeridos.has(g.id);
            caixa.addEventListener("change", () => {
              const idsSelecionados = Array.from(listaGruposGeridos.querySelectorAll("input:checked"))
                .map((i) => Number(i.dataset.grupoId));
              definirGruposGeridosUtilizador(conta.id, idsSelecionados);
            });
            caixa.dataset.grupoId = g.id;
            rotulo.appendChild(caixa);
            rotulo.appendChild(document.createTextNode(g.nome));
            listaGruposGeridos.appendChild(rotulo);
          });
          celulaGrupo.appendChild(listaGruposGeridos);
        }
      } else {
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
      }

      const celulaData = document.createElement("td");
      celulaData.textContent = formatarData(conta.criado_em);

      const celulaAcoes = document.createElement("td");
      if (!conta.aprovado) {
        const botaoAprovar = document.createElement("button");
        botaoAprovar.className = "botao-primario botao-com-icone";
        botaoAprovar.innerHTML = ICONES.check + "<span>Aprovar</span>";
        botaoAprovar.addEventListener("click", () => agirSobreUtilizador(conta.id, "aprovar"));

        const botaoRejeitar = document.createElement("button");
        botaoRejeitar.className = "botao-perigo botao-com-icone";
        botaoRejeitar.innerHTML = ICONES.x + "<span>Rejeitar</span>";
        botaoRejeitar.addEventListener("click", () => {
          if (confirm(`Rejeitar e apagar definitivamente a conta de ${conta.email}?`)) agirSobreUtilizador(conta.id, "rejeitar");
        });

        celulaAcoes.appendChild(botaoAprovar);
        celulaAcoes.appendChild(botaoRejeitar);
      } else if (conta.admin) {
        if (conta.id === idUtilizadorAtual) {
          const notaPropriaConta = document.createElement("span");
          notaPropriaConta.className = "ajuda-campo";
          notaPropriaConta.textContent = "(a tua conta)";
          celulaAcoes.appendChild(notaPropriaConta);
        } else {
          const botaoAlternarGlobal = document.createElement("button");
          botaoAlternarGlobal.className = "botao-secundario botao-com-icone";
          botaoAlternarGlobal.innerHTML = ICONES.trocar + `<span>${conta.admin_global ? "Tornar admin de grupo" : "Tornar admin global"}</span>`;
          botaoAlternarGlobal.addEventListener("click", () => alternarAdminGlobal(conta.id, !conta.admin_global));

          const botaoRemoverAdmin = document.createElement("button");
          botaoRemoverAdmin.className = "botao-perigo botao-com-icone";
          botaoRemoverAdmin.innerHTML = ICONES.escudoRemover + "<span>Remover admin</span>";
          botaoRemoverAdmin.addEventListener("click", () => agirSobreUtilizador(conta.id, "remover_admin"));

          celulaAcoes.appendChild(botaoAlternarGlobal);
          celulaAcoes.appendChild(botaoRemoverAdmin);
        }
      } else {
        const botaoTornarAdmin = document.createElement("button");
        botaoTornarAdmin.className = "botao-sucesso botao-com-icone";
        botaoTornarAdmin.innerHTML = ICONES.escudo + "<span>Tornar admin</span>";
        botaoTornarAdmin.addEventListener("click", () => agirSobreUtilizador(conta.id, "tornar_admin"));

        const botaoRevogar = document.createElement("button");
        botaoRevogar.className = "botao-perigo botao-com-icone";
        botaoRevogar.innerHTML = ICONES.x + "<span>Revogar</span>";
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

async function alternarAdminGlobal(idConta, novoValor) {
  mensagemErroUtilizadores.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/utilizadores/${idConta}/admin_global`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ admin_global: novoValor }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroUtilizadores.textContent = corpo.detail || "Não foi possível concluir a ação.";
      return;
    }
    mostrarToast(novoValor ? "Agora é admin global." : "Agora é admin de grupo.");
    carregarUtilizadores();
  } catch (erro) {
    console.error(erro);
    mensagemErroUtilizadores.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function definirGruposGeridosUtilizador(idConta, grupoIds) {
  mensagemErroUtilizadores.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/utilizadores/${idConta}/grupos_geridos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grupo_ids: grupoIds }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroUtilizadores.textContent = corpo.detail || "Não foi possível atualizar os grupos geridos.";
      return;
    }
    mostrarToast("Grupos geridos atualizados.");
  } catch (erro) {
    console.error(erro);
    mensagemErroUtilizadores.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  } finally {
    carregarUtilizadores();
  }
}

const TEXTO_TOAST_POR_ACAO = {
  aprovar: "Conta aprovada.",
  rejeitar: "Conta rejeitada.",
  revogar: "Acesso revogado.",
  tornar_admin: "Promovido a admin.",
  remover_admin: "Privilégios de admin removidos.",
};

async function agirSobreUtilizador(idConta, acao) {
  mensagemErroUtilizadores.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/${acao}/${idConta}`, { method: "POST" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroUtilizadores.textContent = corpo.detail || "Não foi possível concluir a ação.";
      return;
    }
    mostrarToast(TEXTO_TOAST_POR_ACAO[acao] || "Ação concluída.");
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
      return;
    }
    mostrarToast("Grupo atualizado.");
  } catch (erro) {
    console.error(erro);
    mensagemErroUtilizadores.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  } finally {
    carregarUtilizadores();
  }
}

// ---------- Investigação (Fase 5) ----------
// Cada mudança de filtro volta a pedir ao servidor (ao contrário da
// antiga aba "Atividade", que pedia tudo uma vez e filtrava aqui) --
// o controlo de acesso por grupo (secção 15) é sempre do lado do
// servidor, por isso os filtros têm de ir com o pedido, não podem
// só esconder linhas de uma lista já carregada.

const corpoTabelaAtividade = document.getElementById("corpo-tabela-atividade");
const mensagemSemAtividade = document.getElementById("mensagem-sem-atividade");
const mensagemErroAtividade = document.getElementById("mensagem-erro-atividade");
const selectFiltroGrupo = document.getElementById("investigacao-filtro-grupo");
const campoFiltroDataInicio = document.getElementById("investigacao-filtro-data-inicio");
const campoFiltroDataFim = document.getElementById("investigacao-filtro-data-fim");
const selectFiltroFornecedor = document.getElementById("investigacao-filtro-fornecedor");
const selectFiltroApoioEscopo = document.getElementById("investigacao-filtro-apoio-escopo");
const selectFiltroGuardiaoEscopo = document.getElementById("investigacao-filtro-guardiao-escopo");
const botaoPaginaAnterior = document.getElementById("atividade-pagina-anterior");
const botaoPaginaSeguinte = document.getElementById("atividade-pagina-seguinte");
const textoPaginaAtividade = document.getElementById("atividade-texto-pagina");
const linkExportarCsv = document.getElementById("botao-exportar-csv");
const linkExportarJson = document.getElementById("botao-exportar-json");
const painelEliminarExecucoes = document.getElementById("painel-eliminar-execucoes");

const SESSOES_POR_PAGINA = 20;

let sessoesFiltradas = [];
let estadoAtividade = { pagina: 1, ordenarPor: null, ordemAscendente: true };

function construirQueryInvestigacao() {
  const parametros = new URLSearchParams();
  if (selectFiltroGrupo.value) parametros.set("grupo", selectFiltroGrupo.value);
  if (campoFiltroDataInicio.value) parametros.set("data_inicio", campoFiltroDataInicio.value);
  if (campoFiltroDataFim.value) parametros.set("data_fim", campoFiltroDataFim.value);
  if (selectFiltroFornecedor.value) parametros.set("fornecedor", selectFiltroFornecedor.value);
  if (selectFiltroApoioEscopo.value) parametros.set("apoio_escopo", selectFiltroApoioEscopo.value);
  if (selectFiltroGuardiaoEscopo.value) parametros.set("guardiao_escopo", selectFiltroGuardiaoEscopo.value);
  return parametros;
}

async function popularFiltrosInvestigacao() {
  try {
    const resposta = await fetch("/api/admin/investigacao/filtros");
    if (!resposta.ok) return;
    const opcoes = await resposta.json();
    const valorAtualGrupo = selectFiltroGrupo.value;
    selectFiltroGrupo.innerHTML = '<option value="">Todos os grupos</option>';
    opcoes.grupos.forEach((nome) => {
      const opcao = document.createElement("option");
      opcao.value = nome;
      opcao.textContent = nome;
      selectFiltroGrupo.appendChild(opcao);
    });
    selectFiltroGrupo.value = valorAtualGrupo;
    const valorAtualFornecedor = selectFiltroFornecedor.value;
    selectFiltroFornecedor.innerHTML = '<option value="">Todos os fornecedores</option>';
    opcoes.fornecedores.forEach((nome) => {
      const opcao = document.createElement("option");
      opcao.value = nome;
      opcao.textContent = nome;
      selectFiltroFornecedor.appendChild(opcao);
    });
    selectFiltroFornecedor.value = valorAtualFornecedor;
  } catch (erro) {
    console.error(erro);
  }
}

async function carregarAtividade() {
  painelEliminarExecucoes.classList.toggle("escondido", !EH_ADMIN_GLOBAL);
  await popularFiltrosInvestigacao();
  await atualizarInvestigacao();
}

async function atualizarInvestigacao() {
  mensagemErroAtividade.textContent = "";
  const query = construirQueryInvestigacao();
  linkExportarCsv.href = `/api/admin/investigacao/exportar.csv?${query.toString()}`;
  linkExportarJson.href = `/api/admin/investigacao/exportar.json?${query.toString()}`;
  try {
    const [respostaRelatorio, respostaDashboard] = await Promise.all([
      fetch(`/api/admin/investigacao/relatorio?${query.toString()}`),
      fetch(`/api/admin/investigacao/dashboard?${query.toString()}`),
    ]);
    if (!respostaRelatorio.ok) {
      const corpo = await respostaRelatorio.json();
      mensagemErroAtividade.textContent = corpo.detail || "Não foi possível carregar o relatório.";
      return;
    }
    sessoesFiltradas = (await respostaRelatorio.json()).sessoes;
    atualizarCartoesMetricas(sessoesFiltradas);
    estadoAtividade.pagina = 1;
    atualizarTabelaAtividade();
    if (respostaDashboard.ok) desenharDashboard(await respostaDashboard.json());
  } catch (erro) {
    console.error(erro);
    mensagemErroAtividade.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

[selectFiltroGrupo, selectFiltroFornecedor, selectFiltroApoioEscopo, selectFiltroGuardiaoEscopo].forEach((el) =>
  el.addEventListener("change", atualizarInvestigacao));
[campoFiltroDataInicio, campoFiltroDataFim].forEach((el) =>
  el.addEventListener("change", atualizarInvestigacao));

function atualizarCartoesMetricas(sessoes) {
  document.getElementById("metrica-num-sessoes").textContent = sessoes.length;
  document.getElementById("metrica-num-estudantes").textContent =
    new Set(sessoes.map((s) => s.id_estudante).filter(Boolean)).size;
  const totalTentativas = sessoes.reduce((soma, s) => soma + (s.num_tentativas_totais || 0), 0);
  const totalRejeitadas = sessoes.reduce((soma, s) => soma + (s.num_tentativas_rejeitadas || 0), 0);
  document.getElementById("metrica-leakage-global").textContent =
    totalTentativas ? formatarPercentagem(totalRejeitadas / totalTentativas) : "-";
  document.getElementById("metrica-hint-dependency").textContent =
    sessoes.length ? (sessoes.reduce((soma, s) => soma + (s.num_turnos || 0), 0) / sessoes.length).toFixed(1) : "-";
}

function compararSessoes(a, b, campo, ascendente) {
  const va = a[campo];
  const vb = b[campo];
  if (va === null || va === undefined) return vb === null || vb === undefined ? 0 : 1;
  if (vb === null || vb === undefined) return -1;
  const resultado = va < vb ? -1 : va > vb ? 1 : 0;
  return ascendente ? resultado : -resultado;
}

function sessoesOrdenadas() {
  if (!estadoAtividade.ordenarPor) return sessoesFiltradas;
  return [...sessoesFiltradas].sort((a, b) =>
    compararSessoes(a, b, estadoAtividade.ordenarPor, estadoAtividade.ordemAscendente));
}

function atualizarTabelaAtividade() {
  const sessoes = sessoesOrdenadas();
  const totalPaginas = Math.max(1, Math.ceil(sessoes.length / SESSOES_POR_PAGINA));
  estadoAtividade.pagina = Math.min(estadoAtividade.pagina, totalPaginas);
  const inicio = (estadoAtividade.pagina - 1) * SESSOES_POR_PAGINA;
  const sessoesDaPagina = sessoes.slice(inicio, inicio + SESSOES_POR_PAGINA);

  corpoTabelaAtividade.innerHTML = "";
  mensagemSemAtividade.classList.toggle("escondido", sessoesDaPagina.length > 0);
  sessoesDaPagina.forEach((sessao) => {
    const linha = document.createElement("tr");
    const celulas = [
      sessao.id_estudante || "-",
      sessao.grupo || "-",
      sessao.num_turnos,
      formatarPercentagem(sessao.solution_leakage_rate),
      sessao.hint_escalation_maxima === null || sessao.hint_escalation_maxima === undefined ? "-" : sessao.hint_escalation_maxima,
      sessao.fornecedor ? `${sessao.fornecedor}/${sessao.modelo}` : "-",
      sessao.apoio_escopo || "-",
      sessao.guardiao_escopo || "-",
      sessao.num_recusas_seguras,
    ];
    celulas.forEach((valor) => {
      const celula = document.createElement("td");
      celula.textContent = valor;
      linha.appendChild(celula);
    });
    const celulaAcoes = document.createElement("td");
    if (sessao.estudante_id != null) {
      const botaoVer = document.createElement("button");
      botaoVer.type = "button";
      botaoVer.className = "botao-secundario botao-com-icone";
      botaoVer.innerHTML = ICONES.olho + "<span>Ver</span>";
      botaoVer.addEventListener("click", () => abrirVistaEstudante(sessao.estudante_id, sessao.id_estudante));
      celulaAcoes.appendChild(botaoVer);
    }
    linha.appendChild(celulaAcoes);
    corpoTabelaAtividade.appendChild(linha);
  });

  textoPaginaAtividade.textContent = `Página ${estadoAtividade.pagina} de ${totalPaginas} (${sessoes.length} sessões)`;
  botaoPaginaAnterior.disabled = estadoAtividade.pagina <= 1;
  botaoPaginaSeguinte.disabled = estadoAtividade.pagina >= totalPaginas;
}

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

// ---------- Investigação: gráficos (skill dataviz) ----------
// SVG desenhado à mão, sem biblioteca -- barras finas com topo
// arredondado, eixo/grelha recessivos (tokens do próprio tema),
// rótulo de valor direto em cada barra, e um <title> por barra como
// camada de hover mínima (sempre disponível, sem JS extra).

function criarGraficoBarras(elementoAlvo, itens, opcoes = {}) {
  const { chaveRotulo = "rotulo", chaveValor = "valor", formatarValor = (v) => String(v),
          serie2 = null } = opcoes;
  elementoAlvo.innerHTML = "";
  if (!itens.length) {
    elementoAlvo.innerHTML = '<div class="grafico-vazio">Sem dados para estes filtros.</div>';
    return;
  }

  const largura = 600;
  const altura = 160;
  const margemBaixo = 22;
  const margemCima = 16;
  const alturaUtil = altura - margemBaixo - margemCima;
  const maximo = Math.max(1, ...itens.map((i) => Math.max(i[chaveValor] || 0, serie2 ? (i[serie2] || 0) : 0)));
  const larguraGrupo = largura / itens.length;
  const numSeries = serie2 ? 2 : 1;
  const larguraBarra = Math.min(28, (larguraGrupo * 0.6) / numSeries);

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${largura} ${altura}`);
  svg.setAttribute("preserveAspectRatio", "none");

  const linhaBase = document.createElementNS("http://www.w3.org/2000/svg", "line");
  linhaBase.setAttribute("x1", "0");
  linhaBase.setAttribute("x2", String(largura));
  linhaBase.setAttribute("y1", String(altura - margemBaixo));
  linhaBase.setAttribute("y2", String(altura - margemBaixo));
  linhaBase.setAttribute("class", "grafico-eixo");
  svg.appendChild(linhaBase);

  function desenharBarra(x, valor, classe) {
    const alturaBarra = (valor / maximo) * alturaUtil;
    const y = altura - margemBaixo - alturaBarra;
    const retangulo = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    retangulo.setAttribute("x", String(x));
    retangulo.setAttribute("y", String(y));
    retangulo.setAttribute("width", String(larguraBarra));
    retangulo.setAttribute("height", String(Math.max(alturaBarra, valor > 0 ? 2 : 0)));
    retangulo.setAttribute("rx", "3");
    retangulo.setAttribute("class", classe);
    return retangulo;
  }

  itens.forEach((item, indice) => {
    const centroGrupo = indice * larguraGrupo + larguraGrupo / 2;
    const titulo1 = document.createElementNS("http://www.w3.org/2000/svg", "title");
    const valor1 = item[chaveValor] || 0;
    titulo1.textContent = `${item[chaveRotulo]}: ${formatarValor(valor1)}`;
    const x1 = serie2 ? centroGrupo - larguraBarra - 1 : centroGrupo - larguraBarra / 2;
    const barra1 = desenharBarra(x1, valor1, "grafico-barra");
    barra1.appendChild(titulo1);
    svg.appendChild(barra1);

    if (serie2) {
      const valor2 = item[serie2] || 0;
      const titulo2 = document.createElementNS("http://www.w3.org/2000/svg", "title");
      titulo2.textContent = `${item[chaveRotulo]} (${serie2}): ${formatarValor(valor2)}`;
      const barra2 = desenharBarra(centroGrupo + 1, valor2, "grafico-barra-serie-2");
      barra2.appendChild(titulo2);
      svg.appendChild(barra2);
    }

    // Rótulo do eixo -- só a cada N barras se houver muitas, para não
    // sobrepor texto (rótulos seletivos, ver marks-and-anatomy.md).
    const passo = Math.ceil(itens.length / 10);
    if (indice % passo === 0) {
      const rotulo = document.createElementNS("http://www.w3.org/2000/svg", "text");
      rotulo.setAttribute("x", String(centroGrupo));
      rotulo.setAttribute("y", String(altura - 6));
      rotulo.setAttribute("text-anchor", "middle");
      rotulo.setAttribute("class", "grafico-rotulo");
      rotulo.textContent = String(item[chaveRotulo]).slice(0, 10);
      svg.appendChild(rotulo);
    }
  });

  elementoAlvo.appendChild(svg);
}

function desenharDashboard(dashboard) {
  criarGraficoBarras(
    document.getElementById("grafico-sessoes-dia"),
    dashboard.sessoes_por_dia.map((d) => ({ rotulo: d.dia.slice(5), valor: d.sessoes })));

  criarGraficoBarras(
    document.getElementById("grafico-leakage-grupo"),
    dashboard.leakage_por_grupo.map((g) => ({ rotulo: g.grupo, valor: (g.solution_leakage_rate || 0) * 100 })),
    { formatarValor: (v) => `${Math.round(v)}%` });

  criarGraficoBarras(
    document.getElementById("grafico-nivel-maximo"),
    dashboard.distribuicao_nivel_maximo.map((n) => ({ rotulo: String(n.nivel), valor: n.sessoes })));

  criarGraficoBarras(
    document.getElementById("grafico-turnos"),
    dashboard.distribuicao_turnos.map((t) => ({ rotulo: String(t.turnos), valor: t.sessoes })));

  const porFornecedor = {};
  dashboard.sessoes_por_fornecedor_e_escopo.forEach((linha) => {
    const entrada = porFornecedor[linha.fornecedor_modelo] || { rotulo: linha.fornecedor_modelo, global: 0, pessoal: 0 };
    if (linha.escopo === "pessoal") entrada.pessoal += linha.sessoes;
    else entrada.global += linha.sessoes;
    porFornecedor[linha.fornecedor_modelo] = entrada;
  });
  criarGraficoBarras(
    document.getElementById("grafico-fornecedor-escopo"),
    Object.values(porFornecedor),
    { chaveValor: "global", serie2: "pessoal" });
  const legenda = document.getElementById("legenda-fornecedor-escopo");
  legenda.innerHTML = Object.keys(porFornecedor).length
    ? '<span class="legenda-item"><span class="legenda-cor" style="background:var(--grafico-serie-1)"></span>Global</span>'
      + '<span class="legenda-item"><span class="legenda-cor" style="background:var(--grafico-serie-2)"></span>Pessoal</span>'
    : "";
}

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

      const celulaAlguem = document.createElement("td");
      celulaAlguem.appendChild(grupo.alguem_ativo ? criarBadge("Permitido", "sucesso") : criarBadge("Bloqueado", "erro"));

      const celulaMembros = document.createElement("td");
      celulaMembros.className = "numero";
      celulaMembros.textContent = grupo.num_membros;

      const celulaCodigo = document.createElement("td");
      const textoCodigo = document.createElement("span");
      textoCodigo.className = "texto-mono texto-codigo-grupo";

      const botaoVerCodigo = document.createElement("button");
      botaoVerCodigo.className = "botao-secundario botao-com-icone";
      botaoVerCodigo.innerHTML = ICONES.olho + "<span>Ver código</span>";
      botaoVerCodigo.addEventListener("click", () => alternarCodigoGrupo(grupo.id, textoCodigo, botaoVerCodigo));

      const botaoRegenerar = document.createElement("button");
      botaoRegenerar.className = "botao-secundario botao-com-icone";
      botaoRegenerar.innerHTML = ICONES.atualizar + "<span>Regenerar</span>";
      botaoRegenerar.addEventListener("click", () => regenerarCodigoGrupo(grupo.id, textoCodigo, botaoVerCodigo));

      const grupoCodigo = document.createElement("div");
      grupoCodigo.className = "grupo-acoes-tabela";
      grupoCodigo.appendChild(textoCodigo);
      grupoCodigo.appendChild(botaoVerCodigo);
      grupoCodigo.appendChild(botaoRegenerar);
      celulaCodigo.appendChild(grupoCodigo);

      const celulaAcoes = document.createElement("td");
      const botaoAtivarDesativar = document.createElement("button");
      botaoAtivarDesativar.className = (grupo.ativo ? "botao-secundario" : "botao-sucesso") + " botao-com-icone";
      botaoAtivarDesativar.innerHTML = ICONES.energia + `<span>${grupo.ativo ? "Desativar" : "Ativar"}</span>`;
      botaoAtivarDesativar.addEventListener("click", () => agirSobreGrupo(grupo.id, grupo.ativo ? "desativar" : "ativar"));

      const botaoAlternarAlguem = document.createElement("button");
      botaoAlternarAlguem.className = (grupo.alguem_ativo ? "botao-secundario" : "botao-sucesso") + " botao-com-icone";
      botaoAlternarAlguem.innerHTML = ICONES.mensagem + `<span>${grupo.alguem_ativo ? "Bloquear Alguem" : "Permitir Alguem"}</span>`;
      botaoAlternarAlguem.addEventListener(
        "click", () => agirSobreGrupo(grupo.id, grupo.alguem_ativo ? "desativar_alguem" : "ativar_alguem"));

      const grupoEstado = document.createElement("div");
      grupoEstado.className = "grupo-acoes-tabela";
      grupoEstado.appendChild(botaoAtivarDesativar);
      grupoEstado.appendChild(botaoAlternarAlguem);

      const botaoExportar = document.createElement("a");
      botaoExportar.className = "botao-exportar botao-com-icone";
      botaoExportar.innerHTML = ICONES.descarregar + "<span>Exportar CSV</span>";
      botaoExportar.href = `/api/admin/grupos/${grupo.id}/membros.csv`;
      botaoExportar.target = "_blank";

      const botaoApagar = document.createElement("button");
      botaoApagar.className = "botao-perigo botao-com-icone";
      botaoApagar.innerHTML = ICONES.apagar + "<span>Apagar</span>";
      botaoApagar.addEventListener("click", () => apagarGrupo(grupo.id));

      const grupoDestrutivo = document.createElement("div");
      grupoDestrutivo.className = "grupo-acoes-tabela";
      grupoDestrutivo.appendChild(botaoExportar);
      grupoDestrutivo.appendChild(botaoApagar);

      celulaAcoes.appendChild(grupoEstado);
      celulaAcoes.appendChild(grupoDestrutivo);

      linha.appendChild(celulaNome);
      linha.appendChild(celulaEstado);
      linha.appendChild(celulaAlguem);
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
    mostrarToast(`Grupo "${corpo.nome}" criado -- usa "Ver código" para o consultar.`);
    carregarGrupos();
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

// Mostra/oculta o código de junção sem destruir os botões da célula
// (ver código, regenerar) -- textoCodigo é um <span> à parte, nunca o
// alvo de innerHTML/textContent direto da própria célula.
function mostrarBotaoVerCodigo(botao) {
  botao.innerHTML = ICONES.olho + "<span>Ver código</span>";
}

function mostrarBotaoOcultarCodigo(botao) {
  botao.innerHTML = ICONES.olhoFechado + "<span>Ocultar código</span>";
}

async function alternarCodigoGrupo(grupoId, textoCodigo, botao) {
  if (textoCodigo.textContent) {
    textoCodigo.textContent = "";
    mostrarBotaoVerCodigo(botao);
    return;
  }
  mensagemErroGrupos.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/grupos/${grupoId}/codigo`);
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível obter o código.";
      return;
    }
    textoCodigo.textContent = corpo.codigo;
    mostrarBotaoOcultarCodigo(botao);
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function regenerarCodigoGrupo(grupoId, textoCodigo, botaoVerCodigo) {
  if (!confirm("Gerar um código novo? O código antigo deixa de servir para novos registos (quem já está no grupo não é afetado).")) return;
  mensagemErroGrupos.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/grupos/${grupoId}/regenerar_codigo`, { method: "POST" });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível regenerar o código.";
      return;
    }
    textoCodigo.textContent = corpo.codigo;
    mostrarBotaoOcultarCodigo(botaoVerCodigo);
    mostrarToast("Código regenerado.");
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

const TEXTO_TOAST_POR_ACAO_GRUPO = {
  ativar: "Grupo ativado.",
  desativar: "Grupo desativado.",
  apagar: "Grupo apagado.",
  ativar_alguem: "Alguem permitido para este grupo.",
  desativar_alguem: "Alguem bloqueado para este grupo.",
};

async function agirSobreGrupo(grupoId, acao) {
  mensagemErroGrupos.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/grupos/${grupoId}/${acao}`, { method: "POST" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroGrupos.textContent = corpo.detail || "Não foi possível concluir a ação.";
      return;
    }
    mostrarToast(TEXTO_TOAST_POR_ACAO_GRUPO[acao] || "Ação concluída.");
    carregarGrupos();
  } catch (erro) {
    console.error(erro);
    mensagemErroGrupos.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function apagarGrupo(grupoId) {
  if (!confirm("Apagar este grupo definitivamente? Só é possível se não tiver membros.")) return;
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

const modalDetalhesLog = document.getElementById("modal-detalhes-log");
const conteudoDetalhesLog = document.getElementById("conteudo-detalhes-log");

function abrirDetalhesLog(detalhes) {
  conteudoDetalhesLog.textContent = JSON.stringify(detalhes, null, 2);
  modalDetalhesLog.classList.remove("escondido");
}

function fecharDetalhesLog() {
  modalDetalhesLog.classList.add("escondido");
}

document.getElementById("botao-fechar-detalhes-log").addEventListener("click", fecharDetalhesLog);
modalDetalhesLog.addEventListener("click", (evento) => {
  if (evento.target === modalDetalhesLog) fecharDetalhesLog();
});

const TIPOS_LOG_CONHECIDOS = [
  "login", "login_falhado", "registo", "conta_aprovada", "conta_rejeitada", "conta_revogada",
  "admin_concedido", "admin_revogado", "admin_global_alterado", "grupos_geridos_alterados",
  "grupo_criado", "grupo_editado", "grupo_ativado", "grupo_desativado", "grupo_eliminado",
  "grupo_reatribuido", "grupo_alguem_ativado", "grupo_alguem_desativado",
  "relatorio_apagado", "log_apagado", "definicao_alterada", "bd_descarregada",
];

// Agrupa os tipos de evento por variante de badge, para se conseguir
// varrer a tabela visualmente à procura de falhas/remoções sem ler
// cada linha -- mesma convenção já usada noutros painéis de auditoria.
const TIPOS_LOG_ERRO = new Set([
  "login_falhado", "conta_rejeitada", "conta_revogada",
  "admin_revogado", "grupo_desativado", "grupo_eliminado", "grupo_alguem_desativado",
  "relatorio_apagado", "log_apagado",
]);
const TIPOS_LOG_SUCESSO = new Set([
  "login", "registo", "conta_aprovada", "admin_concedido", "grupo_criado", "grupo_ativado",
  "grupo_alguem_ativado",
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
      if (evento.detalhes) {
        const botaoDetalhes = document.createElement("button");
        botaoDetalhes.type = "button";
        botaoDetalhes.className = "botao-secundario botao-com-icone";
        botaoDetalhes.innerHTML = ICONES.olho + "<span>Ver detalhes</span>";
        botaoDetalhes.addEventListener("click", () => abrirDetalhesLog(evento.detalhes));
        celulaDetalhes.appendChild(botaoDetalhes);
      } else {
        celulaDetalhes.textContent = "-";
      }

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
  if (!confirm(`Apagar definitivamente ${idsSelecionadosLog.size} registo(s)? Esta ação não pode ser desfeita.`)) return;
  mensagemErroLog.textContent = "";
  try {
    const resposta = await fetch("/api/admin/log/apagar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [...idsSelecionadosLog] }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroLog.textContent = corpo.detail || "Não foi possível apagar os registos selecionados.";
      return;
    }
    const { apagados } = await resposta.json();
    mostrarToast(apagados === 1 ? "1 registo apagado." : `${apagados} registos apagados.`);
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
const relatoriosNaoVistos = document.getElementById("relatorios-nao-vistos");
const relatoriosBadgeLateral = document.getElementById("relatorios-badge-lateral");

const RELATORIOS_POR_PAGINA = 20;

let todosOsRelatorios = [];
let paginaRelatorios = 1;

// Mostra a contagem de não vistos junto ao botão da aba na barra
// lateral, mesmo antes de o admin a abrir.
async function atualizarBadgeLateralRelatorios() {
  try {
    const resposta = await fetch("/api/admin/relatorios/nao_vistos");
    if (!resposta.ok) return;
    const { nao_vistos } = await resposta.json();
    relatoriosBadgeLateral.textContent = nao_vistos;
    relatoriosBadgeLateral.classList.toggle("escondido", nao_vistos === 0);
  } catch (erro) {
    console.error(erro);
  }
}

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
    // O servidor acabou de marcar tudo como visto (é o que abrir a
    // aba faz) -- por isso a contagem de não vistos vem da resposta
    // que ainda reflete o estado anterior, e o badge lateral zera.
    relatoriosNaoVistos.textContent = relatorios.filter((r) => !r.visto).length;
    relatoriosBadgeLateral.textContent = "";
    relatoriosBadgeLateral.classList.add("escondido");
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
    mostrarToast("Relatório apagado.");
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

// ---------- definições ----------

const checkboxAlguemAtivo = document.getElementById("definicao-alguem-ativo");
const checkboxUsarGuardiao = document.getElementById("definicao-usar-guardiao");
const selectNivelMaximoAjuda = document.getElementById("definicao-nivel-maximo-ajuda");
const descricaoNivelMaximoAjuda = document.getElementById("descricao-nivel-maximo-ajuda");
const mensagemErroDefinicoes = document.getElementById("mensagem-erro-definicoes");
const avisoAlguemSemLlm = document.getElementById("aviso-alguem-sem-llm");

// Preenchido a partir de /api/admin/definicoes (escada_ajuda) -- nunca
// escrito à mão aqui, para os nomes/descrições dos níveis nunca
// poderem divergir de alguem/nucleo/escada_de_ajuda.py (mesma
// ESCADA_DE_AJUDA que o próprio system prompt do Tutor usa).
let escadaAjuda = [];

async function carregarDefinicoesAlguem() {
  mensagemErroDefinicoes.textContent = "";
  try {
    const resposta = await fetch("/api/admin/definicoes");
    const dados = await resposta.json();
    checkboxAlguemAtivo.checked = !!dados.alguem_ativo;
    checkboxUsarGuardiao.checked = !!dados.usar_guardiao;
    escadaAjuda = dados.escada_ajuda;
    selectNivelMaximoAjuda.innerHTML = "";
    escadaAjuda.forEach((nivel) => {
      const opcao = document.createElement("option");
      opcao.value = nivel.numero;
      opcao.textContent = `${nivel.numero} -- ${nivel.nome}`;
      selectNivelMaximoAjuda.appendChild(opcao);
    });
    selectNivelMaximoAjuda.value = String(dados.nivel_maximo_ajuda);
    selectNivelMaximoAjuda.dataset.valorAnterior = String(dados.nivel_maximo_ajuda);
    atualizarDescricaoNivelMaximoAjuda();
  } catch (erro) {
    mensagemErroDefinicoes.textContent = "Não foi possível carregar as definições.";
  }
  carregarConfiguracoesLlmAdmin();
  carregarPrompts();
}

function atualizarDescricaoNivelMaximoAjuda() {
  const nivel = escadaAjuda.find((n) => String(n.numero) === selectNivelMaximoAjuda.value);
  descricaoNivelMaximoAjuda.textContent = nivel ? `${nivel.nome}: ${nivel.descricao}` : "";
}
selectNivelMaximoAjuda.addEventListener("change", atualizarDescricaoNivelMaximoAjuda);

checkboxUsarGuardiao.addEventListener("change", async () => {
  mensagemErroDefinicoes.textContent = "";
  const ativo = checkboxUsarGuardiao.checked;
  checkboxUsarGuardiao.disabled = true;
  try {
    const resposta = await fetch("/api/admin/definicoes/guardiao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ativo }),
    });
    if (!resposta.ok) throw new Error();
    mostrarToast(ativo ? "Guardião Pedagógico ativado." : "Guardião Pedagógico desativado.");
  } catch (erro) {
    checkboxUsarGuardiao.checked = !ativo;
    mensagemErroDefinicoes.textContent = "Não foi possível guardar. Tenta novamente.";
  } finally {
    checkboxUsarGuardiao.disabled = false;
  }
});

selectNivelMaximoAjuda.addEventListener("change", async () => {
  mensagemErroDefinicoes.textContent = "";
  const nivelAnterior = selectNivelMaximoAjuda.dataset.valorAnterior || selectNivelMaximoAjuda.value;
  const nivel = Number(selectNivelMaximoAjuda.value);
  selectNivelMaximoAjuda.disabled = true;
  try {
    const resposta = await fetch("/api/admin/definicoes/nivel-ajuda", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nivel }),
    });
    if (!resposta.ok) throw new Error();
    selectNivelMaximoAjuda.dataset.valorAnterior = String(nivel);
    mostrarToast("Nível máximo de ajuda atualizado.");
  } catch (erro) {
    selectNivelMaximoAjuda.value = nivelAnterior;
    mensagemErroDefinicoes.textContent = "Não foi possível guardar. Tenta novamente.";
  } finally {
    selectNivelMaximoAjuda.disabled = false;
  }
});

// Guarda logo ao mudar -- sem botão "Guardar" à parte: já não faz
// falta uma confirmação explícita agora que o toast dá feedback
// imediato de que ficou guardado.
checkboxAlguemAtivo.addEventListener("change", async () => {
  mensagemErroDefinicoes.textContent = "";
  const ativo = checkboxAlguemAtivo.checked;
  checkboxAlguemAtivo.disabled = true;
  try {
    const resposta = await fetch("/api/admin/definicoes/alguem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ativo }),
    });
    if (!resposta.ok) throw new Error();
    mostrarToast(ativo ? "Alguem ativado." : "Alguem desativado.");
  } catch (erro) {
    checkboxAlguemAtivo.checked = !ativo;
    mensagemErroDefinicoes.textContent = "Não foi possível guardar. Tenta novamente.";
  } finally {
    checkboxAlguemAtivo.disabled = false;
    atualizarAvisoAlguemSemLlm();
  }
});

// Ativar o Alguem sem NENHUM LLM disponível (nem uma configuração global
// de "apoio", nem permissão para os estudantes usarem a própria) deixa-o
// ligado só no nome -- todo o pedido acaba em ErroAlguemIndisponivel (ver
// alguem_ponte.construir_alguem). Sem este aviso, um admin só descobria
// isto ao ver estudantes a reportar o problema, sem perceber porquê.
function atualizarAvisoAlguemSemLlm() {
  const semLlm = checkboxAlguemAtivo.checked
    && !adminSelectPapelApoio.value
    && !adminPermissaoApoio.checked;
  avisoAlguemSemLlm.classList.toggle("escondido", !semLlm);
}

// ---------- configurações de LLM (globais) ----------

const mensagemErroDefinicoesLlm = document.getElementById("mensagem-erro-definicoes-llm");
const adminListaConfiguracoesLlm = document.getElementById("admin-lista-configuracoes-llm");
const adminVazioConfiguracoesLlm = document.getElementById("admin-vazio-configuracoes-llm");
const adminSelectPapelApoio = document.getElementById("admin-select-papel-apoio");
const adminSelectPapelGuardiao = document.getElementById("admin-select-papel-guardiao");
const adminPermissaoApoio = document.getElementById("admin-permissao-apoio");
const notaApoioGlobalManda = document.getElementById("nota-apoio-global-manda");
const modalConfiguracaoLlm = document.getElementById("modal-configuracao-llm");
const modalConfiguracaoLlmTitulo = document.getElementById("modal-configuracao-llm-titulo");
const adminCampoConfiguracaoId = document.getElementById("admin-campo-configuracao-id");
const adminCampoFornecedor = document.getElementById("admin-campo-fornecedor");
const adminRotuloApiKey = document.getElementById("admin-rotulo-api-key");
const adminRotuloHost = document.getElementById("admin-rotulo-host");

const ROTULOS_PAPEL_LLM_ADMIN = { apoio: "apoio", guardiao: "guardião" };

function atualizarCamposFornecedorAdmin() {
  const ollama = adminCampoFornecedor.value === "ollama";
  adminRotuloApiKey.classList.toggle("escondido", ollama);
  adminRotuloHost.classList.toggle("escondido", !ollama);
}
adminCampoFornecedor.addEventListener("change", atualizarCamposFornecedorAdmin);

async function carregarConfiguracoesLlmAdmin() {
  mensagemErroDefinicoesLlm.textContent = "";
  try {
    const resposta = await fetch("/api/admin/llm");
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroDefinicoesLlm.textContent = corpo.detail || "Não foi possível carregar as configurações.";
      return;
    }
    renderizarConfiguracoesLlmAdmin(await resposta.json());
  } catch (erro) {
    console.error(erro);
    mensagemErroDefinicoesLlm.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

function renderizarConfiguracoesLlmAdmin(dados) {
  const { configuracoes, selecao_global, permissoes } = dados;

  adminListaConfiguracoesLlm.innerHTML = "";
  adminVazioConfiguracoesLlm.classList.toggle("escondido", configuracoes.length > 0);
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

    const botaoTestar = document.createElement("button");
    botaoTestar.type = "button";
    botaoTestar.className = "botao-icone botao-icone-pequeno";
    botaoTestar.title = "Testar";
    botaoTestar.innerHTML = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      + '<polygon points="13 2 3 14 11 14 10 22 21 10 13 10 13 2" /></svg>';
    botaoTestar.addEventListener("click", () => testarConfiguracaoLlmAdmin(configuracao, botaoTestar));

    const botaoEditar = document.createElement("button");
    botaoEditar.type = "button";
    botaoEditar.className = "botao-icone botao-icone-pequeno";
    botaoEditar.title = "Editar";
    botaoEditar.innerHTML = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      + '<path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>';
    botaoEditar.addEventListener("click", () => abrirModalConfiguracaoLlm(configuracao));

    const botaoApagar = document.createElement("button");
    botaoApagar.type = "button";
    botaoApagar.className = "botao-icone botao-icone-pequeno botao-icone-perigo";
    botaoApagar.title = "Apagar";
    botaoApagar.innerHTML = '<svg class="icone-botao" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      + 'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
      + '<polyline points="4 7 20 7" /><path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" />'
      + '<path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" /></svg>';
    botaoApagar.addEventListener("click", () => apagarConfiguracaoLlmAdmin(configuracao));

    linha.appendChild(texto);
    linha.appendChild(botaoTestar);
    linha.appendChild(botaoEditar);
    linha.appendChild(botaoApagar);
    adminListaConfiguracoesLlm.appendChild(linha);
  });

  preencherSelectPapelAdmin(adminSelectPapelApoio, "apoio", configuracoes, selecao_global);
  preencherSelectPapelAdmin(adminSelectPapelGuardiao, "guardiao", configuracoes, selecao_global);
  adminPermissaoApoio.checked = !!permissoes.apoio;
  atualizarAvisoAlguemSemLlm();
  atualizarNotaApoioGlobalManda();
}

// Um LLM global de Apoio manda sempre sobre a escolha pessoal do
// estudante (regra de precedência) -- sem isto, ligar a permissão
// "Estudantes podem usar o próprio LLM" com uma configuração global já
// escolhida parece dar-lhes uma opção real que na prática não existe.
function atualizarNotaApoioGlobalManda() {
  notaApoioGlobalManda.classList.toggle("escondido", !adminSelectPapelApoio.value);
}

function preencherSelectPapelAdmin(select, papel, configuracoes, selecaoGlobal) {
  select.innerHTML = "";
  const opcaoNenhuma = document.createElement("option");
  opcaoNenhuma.value = "";
  // Para 'guardiao' não há "critério do estudante" nenhum -- ele nunca
  // escolhe o próprio guardião (ver PAPEIS_PESSOAIS); sem seleção global,
  // a conversa simplesmente continua sem guardião.
  opcaoNenhuma.textContent = papel === "guardiao"
    ? "Nenhum -- conversa continua sem guardião"
    : "Nenhum -- deixar ao critério do estudante";
  select.appendChild(opcaoNenhuma);
  configuracoes.forEach((configuracao) => {
    const opcao = document.createElement("option");
    opcao.value = configuracao.id;
    opcao.textContent = configuracao.etiqueta;
    select.appendChild(opcao);
  });
  select.value = selecaoGlobal[papel] != null ? String(selecaoGlobal[papel]) : "";
}

async function definirSelecaoPapelAdmin(papel, select) {
  mensagemErroDefinicoesLlm.textContent = "";
  const configuracaoId = select.value ? Number(select.value) : null;
  try {
    const resposta = await fetch("/api/admin/llm/selecao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ papel, configuracao_id: configuracaoId }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroDefinicoesLlm.textContent = corpo.detail || "Não foi possível guardar a escolha.";
      return;
    }
    mostrarToast(`LLM ativo para ${ROTULOS_PAPEL_LLM_ADMIN[papel]} atualizado.`);
    atualizarAvisoAlguemSemLlm();
  } catch (erro) {
    console.error(erro);
    mensagemErroDefinicoesLlm.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

adminSelectPapelApoio.addEventListener("change", () => {
  definirSelecaoPapelAdmin("apoio", adminSelectPapelApoio);
  atualizarNotaApoioGlobalManda();
});
adminSelectPapelGuardiao.addEventListener("change", () => definirSelecaoPapelAdmin("guardiao", adminSelectPapelGuardiao));

async function definirPermissaoLlmAdmin(papel, checkbox) {
  mensagemErroDefinicoesLlm.textContent = "";
  const ativa = checkbox.checked;
  checkbox.disabled = true;
  try {
    const resposta = await fetch("/api/admin/llm/permissao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ papel, ativa }),
    });
    if (!resposta.ok) throw new Error();
    mostrarToast(ativa
      ? `Estudantes já podem usar o próprio LLM para ${ROTULOS_PAPEL_LLM_ADMIN[papel]}.`
      : `Estudantes já não podem usar o próprio LLM para ${ROTULOS_PAPEL_LLM_ADMIN[papel]}.`);
  } catch (erro) {
    checkbox.checked = !ativa;
    mensagemErroDefinicoesLlm.textContent = "Não foi possível guardar. Tenta novamente.";
  } finally {
    checkbox.disabled = false;
    atualizarAvisoAlguemSemLlm();
  }
}

adminPermissaoApoio.addEventListener("change", () => definirPermissaoLlmAdmin("apoio", adminPermissaoApoio));

function abrirModalConfiguracaoLlm(configuracao) {
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="configuracao-llm-admin"]');
  mensagemErro.textContent = "";
  const form = document.getElementById("form-configuracao-llm-admin");
  form.reset();
  adminCampoConfiguracaoId.value = configuracao ? configuracao.id : "";
  modalConfiguracaoLlmTitulo.textContent = configuracao ? "Editar configuração global" : "Nova configuração global";
  if (configuracao) {
    document.getElementById("admin-campo-etiqueta").value = configuracao.etiqueta;
    adminCampoFornecedor.value = configuracao.fornecedor;
    document.getElementById("admin-campo-modelo").value = configuracao.modelo;
    if (configuracao.host) document.getElementById("admin-campo-host").value = configuracao.host;
  }
  atualizarCamposFornecedorAdmin();
  modalConfiguracaoLlm.classList.remove("escondido");
}

function fecharModalConfiguracaoLlm() {
  modalConfiguracaoLlm.classList.add("escondido");
}

document.getElementById("botao-nova-configuracao-llm-global").addEventListener(
  "click", () => abrirModalConfiguracaoLlm(null));
document.getElementById("botao-nova-configuracao-llm-global-vazio").addEventListener(
  "click", () => abrirModalConfiguracaoLlm(null));
document.getElementById("botao-fechar-configuracao-llm").addEventListener("click", fecharModalConfiguracaoLlm);
document.getElementById("botao-cancelar-configuracao-llm").addEventListener("click", fecharModalConfiguracaoLlm);
modalConfiguracaoLlm.addEventListener("click", (evento) => {
  if (evento.target === modalConfiguracaoLlm) fecharModalConfiguracaoLlm();
});

document.getElementById("form-configuracao-llm-admin").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const mensagemErro = document.querySelector('.mensagem-erro[data-form="configuracao-llm-admin"]');
  mensagemErro.textContent = "";
  const dados = Object.fromEntries(new FormData(evento.target));
  const configuracaoId = adminCampoConfiguracaoId.value;
  try {
    const resposta = await fetch(
      configuracaoId ? `/api/admin/llm/configuracoes/${configuracaoId}` : "/api/admin/llm/configuracoes",
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
    fecharModalConfiguracaoLlm();
    mostrarToast(configuracaoId ? "Configuração atualizada." : "Configuração criada.");
    carregarConfiguracoesLlmAdmin();
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

async function apagarConfiguracaoLlmAdmin(configuracao) {
  if (!confirm(`Apagar a configuração global "${configuracao.etiqueta}"?`)) return;
  mensagemErroDefinicoesLlm.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/llm/configuracoes/${configuracao.id}`, { method: "DELETE" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroDefinicoesLlm.textContent = corpo.detail || "Não foi possível apagar a configuração.";
      return;
    }
    mostrarToast("Configuração apagada.");
    carregarConfiguracoesLlmAdmin();
  } catch (erro) {
    console.error(erro);
    mensagemErroDefinicoesLlm.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function testarConfiguracaoLlmAdmin(configuracao, botao) {
  mensagemErroDefinicoesLlm.textContent = "";
  botao.disabled = true;
  try {
    const resposta = await fetch(`/api/admin/llm/configuracoes/${configuracao.id}/testar`, { method: "POST" });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroDefinicoesLlm.textContent = corpo.detail || "Não foi possível testar a configuração.";
      return;
    }
    if (corpo.ok) {
      mostrarToast(`"${configuracao.etiqueta}" respondeu -- configuração a funcionar.`);
    } else {
      mensagemErroDefinicoesLlm.textContent = corpo.detail || "A configuração não respondeu.";
    }
  } catch (erro) {
    console.error(erro);
    mensagemErroDefinicoesLlm.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  } finally {
    botao.disabled = false;
  }
}

// ---------- prompts editáveis (tutor, guardião) ----------

const mensagemErroPrompts = document.getElementById("mensagem-erro-prompts");
const CAMPOS_PROMPT = {
  tutor: {
    texto: document.getElementById("prompt-texto-tutor"),
    omissao: document.getElementById("prompt-omissao-tutor"),
    botaoGuardar: document.getElementById("botao-guardar-prompt-tutor"),
    botaoRepor: document.getElementById("botao-repor-prompt-tutor"),
  },
  guardiao: {
    texto: document.getElementById("prompt-texto-guardiao"),
    omissao: document.getElementById("prompt-omissao-guardiao"),
    botaoGuardar: document.getElementById("botao-guardar-prompt-guardiao"),
    botaoRepor: document.getElementById("botao-repor-prompt-guardiao"),
  },
};

async function carregarPrompts() {
  mensagemErroPrompts.textContent = "";
  try {
    const resposta = await fetch("/api/admin/prompts");
    if (!resposta.ok) throw new Error();
    const dados = await resposta.json();
    for (const [chave, campos] of Object.entries(CAMPOS_PROMPT)) {
      campos.texto.value = dados[chave].texto;
      campos.omissao.textContent = dados[chave].omissao;
    }
  } catch (erro) {
    mensagemErroPrompts.textContent = "Não foi possível carregar os prompts.";
  }
}

for (const [chave, campos] of Object.entries(CAMPOS_PROMPT)) {
  campos.botaoGuardar.addEventListener("click", async () => {
    mensagemErroPrompts.textContent = "";
    try {
      const resposta = await fetch(`/api/admin/prompts/${chave}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: campos.texto.value }),
      });
      if (!resposta.ok) {
        const corpo = await resposta.json();
        mensagemErroPrompts.textContent = corpo.detail || "Não foi possível guardar o prompt.";
        return;
      }
      mostrarToast("Prompt guardado.");
    } catch (erro) {
      mensagemErroPrompts.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
    }
  });

  campos.botaoRepor.addEventListener("click", async () => {
    if (!confirm("Repor este prompt para o valor por omissão?")) return;
    mensagemErroPrompts.textContent = "";
    try {
      const resposta = await fetch(`/api/admin/prompts/${chave}`, { method: "DELETE" });
      if (!resposta.ok) throw new Error();
      mostrarToast("Prompt reposto por omissão.");
      carregarPrompts();
    } catch (erro) {
      mensagemErroPrompts.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
    }
  });
}

// ---------- referência da linguagem ALGO (só consulta) ----------

const referenciaAlgoTexto = document.getElementById("referencia-algo-texto");
const botaoCopiarReferenciaAlgo = document.getElementById("botao-copiar-referencia-algo");

async function carregarReferenciaAlgo() {
  try {
    const resposta = await fetch("/api/admin/referencia-algo");
    if (!resposta.ok) throw new Error();
    const dados = await resposta.json();
    referenciaAlgoTexto.textContent = dados.texto;
  } catch (erro) {
    referenciaAlgoTexto.textContent = "Não foi possível carregar a referência da linguagem.";
  }
}
carregarReferenciaAlgo();

botaoCopiarReferenciaAlgo.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(referenciaAlgoTexto.textContent);
    mostrarToast("Referência copiada.");
  } catch (erro) {
    mostrarToast("Não foi possível copiar -- seleciona o texto manualmente.");
  }
});

// ---------- Investigação: vista por estudante (secção 10) ----------

const modalVistaEstudante = document.getElementById("modal-vista-estudante");
const tituloVistaEstudante = document.getElementById("vista-estudante-titulo");
const linhaDoTempoVistaEstudante = document.getElementById("vista-estudante-linha-do-tempo");
const mensagemErroVistaEstudante = document.getElementById("mensagem-erro-vista-estudante");
const acoesExecucoesVistaEstudante = document.getElementById("vista-estudante-acoes-execucoes");
const botaoApagarExecucoesSelecionadas = document.getElementById("botao-apagar-execucoes-selecionadas");

function fecharVistaEstudante() {
  modalVistaEstudante.classList.add("escondido");
}
document.getElementById("botao-fechar-vista-estudante").addEventListener("click", fecharVistaEstudante);
modalVistaEstudante.addEventListener("click", (evento) => {
  if (evento.target === modalVistaEstudante) fecharVistaEstudante();
});

async function abrirVistaEstudante(estudanteId, email) {
  mensagemErroVistaEstudante.textContent = "";
  tituloVistaEstudante.textContent = email || "Estudante";
  linhaDoTempoVistaEstudante.innerHTML = "";
  acoesExecucoesVistaEstudante.classList.add("escondido");
  modalVistaEstudante.classList.remove("escondido");
  try {
    const resposta = await fetch(`/api/admin/investigacao/estudante/${estudanteId}`);
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroVistaEstudante.textContent = corpo.detail || "Não foi possível carregar este estudante.";
      return;
    }
    const vista = await resposta.json();
    renderizarLinhaDoTempo(vista.linha_do_tempo, estudanteId);
  } catch (erro) {
    console.error(erro);
    mensagemErroVistaEstudante.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

function renderizarLinhaDoTempo(itens, estudanteId) {
  linhaDoTempoVistaEstudante.innerHTML = "";
  if (!itens.length) {
    linhaDoTempoVistaEstudante.innerHTML = '<p class="ajuda-campo">Sem sessões do Alguem nem execuções de código registadas.</p>';
    return;
  }
  const temExecucoes = itens.some((item) => item.tipo === "execucao_codigo");
  acoesExecucoesVistaEstudante.classList.toggle("escondido", !(EH_ADMIN_GLOBAL && temExecucoes));

  itens.forEach((item) => {
    const linha = document.createElement("div");
    const dados = item.dados;
    const cabecalho = document.createElement("div");
    cabecalho.className = "item-linha-do-tempo-cabecalho";
    const dataSpan = document.createElement("span");
    dataSpan.className = "item-linha-do-tempo-data";
    dataSpan.textContent = item.timestamp ? formatarData(item.timestamp) : "-";
    const corpo = document.createElement("div");
    corpo.className = "item-linha-do-tempo-corpo";

    if (item.tipo === "sessao_alguem") {
      linha.className = "item-linha-do-tempo item-linha-do-tempo-sessao";
      const titulo = document.createElement("span");
      titulo.textContent = `Sessão com o Alguem -- ${dados.num_turnos} turno(s)`;
      cabecalho.appendChild(titulo);
      cabecalho.appendChild(dataSpan);
      const detalhe = document.createElement("div");
      detalhe.className = "ajuda-campo";
      detalhe.textContent = `Modelo: ${dados.fornecedor ? `${dados.fornecedor}/${dados.modelo}` : "-"} -- `
        + `Leakage: ${formatarPercentagem(dados.solution_leakage_rate)} -- `
        + `Nível máx.: ${dados.hint_escalation_maxima ?? "-"} -- Grupo: ${dados.grupo || "-"}`;
      corpo.appendChild(cabecalho);
      corpo.appendChild(detalhe);
    } else {
      linha.className = "item-linha-do-tempo item-linha-do-tempo-execucao";
      if (EH_ADMIN_GLOBAL) {
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "checkbox-execucao-codigo";
        checkbox.dataset.id = dados.id;
        linha.appendChild(checkbox);
      }
      const titulo = document.createElement("span");
      titulo.textContent = `${dados.tipo === "debug" ? "Debug" : "Execução"} -- ${dados.nome_ficheiro_principal}`;
      cabecalho.appendChild(titulo);
      cabecalho.appendChild(dataSpan);
      const detalhe = document.createElement("div");
      detalhe.className = "ajuda-campo";
      detalhe.textContent = dados.resultado;
      corpo.appendChild(cabecalho);
      corpo.appendChild(detalhe);
    }
    linha.appendChild(corpo);
    linhaDoTempoVistaEstudante.appendChild(linha);
  });
}

botaoApagarExecucoesSelecionadas.addEventListener("click", async () => {
  const ids = [...document.querySelectorAll(".checkbox-execucao-codigo:checked")].map((c) => Number(c.dataset.id));
  if (!ids.length) {
    mensagemErroVistaEstudante.textContent = "Seleciona pelo menos uma execução para apagar.";
    return;
  }
  if (!confirm(`Apagar ${ids.length} execução(ões) de código, definitivamente?`)) return;
  mensagemErroVistaEstudante.textContent = "";
  try {
    const resposta = await fetch("/api/admin/execucoes/apagar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErroVistaEstudante.textContent = corpo.detail || "Não foi possível apagar.";
      return;
    }
    mostrarToast("Execuções apagadas.");
    fecharVistaEstudante();
  } catch (erro) {
    console.error(erro);
    mensagemErroVistaEstudante.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

// ---------- Investigação: eliminar histórico de código (secção 14) ----------

const mensagemErroEliminarExecucoes = document.getElementById("mensagem-erro-eliminar-execucoes");

document.getElementById("botao-apagar-execucoes-por-periodo").addEventListener("click", async () => {
  const dias = Number(document.getElementById("campo-dias-eliminar-execucoes").value);
  if (!confirm(`Apagar todo o histórico de código com mais de ${dias} dias, definitivamente?`)) return;
  mensagemErroEliminarExecucoes.textContent = "";
  try {
    const resposta = await fetch("/api/admin/execucoes/apagar-por-periodo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dias }),
    });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroEliminarExecucoes.textContent = corpo.detail || "Não foi possível apagar.";
      return;
    }
    mostrarToast(`${corpo.apagados} execução(ões) apagada(s).`);
  } catch (erro) {
    console.error(erro);
    mensagemErroEliminarExecucoes.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

document.getElementById("botao-apagar-todas-execucoes").addEventListener("click", async () => {
  if (!confirm("Apagar TODO o histórico de código de TODOS os estudantes, definitivamente? Esta ação não tem volta atrás.")) return;
  mensagemErroEliminarExecucoes.textContent = "";
  try {
    const resposta = await fetch("/api/admin/execucoes/apagar-tudo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmar: true }),
    });
    const corpo = await resposta.json();
    if (!resposta.ok) {
      mensagemErroEliminarExecucoes.textContent = corpo.detail || "Não foi possível apagar.";
      return;
    }
    mostrarToast(`${corpo.apagados} execução(ões) apagada(s).`);
  } catch (erro) {
    console.error(erro);
    mensagemErroEliminarExecucoes.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
});

carregarConteudoDaAba("grupos");
atualizarBadgeLateralRelatorios();
