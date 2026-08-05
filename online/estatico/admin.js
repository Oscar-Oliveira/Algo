const corpoTabela = document.getElementById("corpo-tabela-pendentes");
const mensagemSemPendentes = document.getElementById("mensagem-sem-pendentes");
const mensagemErro = document.getElementById("mensagem-erro-admin");

function formatarData(iso) {
  return iso.replace("T", " ").slice(0, 16);
}

async function carregarPendentes() {
  mensagemErro.textContent = "";
  try {
    const resposta = await fetch("/api/admin/pendentes");
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErro.textContent = corpo.detail || "Não foi possível carregar as contas pendentes.";
      return;
    }
    const { pendentes } = await resposta.json();
    corpoTabela.innerHTML = "";
    mensagemSemPendentes.classList.toggle("escondido", pendentes.length > 0);
    pendentes.forEach((conta) => {
      const linha = document.createElement("tr");

      const celulaEmail = document.createElement("td");
      celulaEmail.textContent = conta.email;

      const celulaData = document.createElement("td");
      celulaData.textContent = formatarData(conta.criado_em);

      const celulaAcoes = document.createElement("td");
      const botaoAprovar = document.createElement("button");
      botaoAprovar.className = "botao-primario";
      botaoAprovar.textContent = "Aprovar";
      botaoAprovar.addEventListener("click", () => agir(conta.id, "aprovar"));

      const botaoRejeitar = document.createElement("button");
      botaoRejeitar.className = "botao-perigo";
      botaoRejeitar.textContent = "Rejeitar";
      botaoRejeitar.addEventListener("click", () => agir(conta.id, "rejeitar"));

      celulaAcoes.appendChild(botaoAprovar);
      celulaAcoes.appendChild(botaoRejeitar);

      linha.appendChild(celulaEmail);
      linha.appendChild(celulaData);
      linha.appendChild(celulaAcoes);
      corpoTabela.appendChild(linha);
    });
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

async function agir(idConta, acao) {
  mensagemErro.textContent = "";
  try {
    const resposta = await fetch(`/api/admin/${acao}/${idConta}`, { method: "POST" });
    if (!resposta.ok) {
      const corpo = await resposta.json();
      mensagemErro.textContent = corpo.detail || "Não foi possível concluir a ação.";
      return;
    }
    carregarPendentes();
  } catch (erro) {
    console.error(erro);
    mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
  }
}

carregarPendentes();
