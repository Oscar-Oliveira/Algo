document.querySelectorAll(".alternador-botao").forEach((botao) => {
  botao.addEventListener("click", () => {
    document.querySelectorAll(".alternador-botao").forEach((b) => b.classList.remove("ativo"));
    botao.classList.add("ativo");
    const alvo = botao.dataset.alvo;
    document.getElementById("form-entrar").classList.toggle("escondido", alvo !== "entrar");
    document.getElementById("form-registar").classList.toggle("escondido", alvo !== "registar");
  });
});

async function submeter(formId, url) {
  const form = document.getElementById(formId);
  const mensagemErro = form.querySelector(".mensagem-erro");
  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagemErro.textContent = "";
    const dados = Object.fromEntries(new FormData(form));
    try {
      const resposta = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
      });
      const corpo = await resposta.json();
      if (!resposta.ok) {
        mensagemErro.textContent = corpo.detail || "Algo correu mal.";
        return;
      }
      if (corpo.pendente) {
        mensagemErro.style.color = "var(--sucesso)";
        mensagemErro.textContent = "A tua conta foi criada e está à espera de aprovação. Não precisas de fazer mais nada -- vais poder entrar assim que um administrador a aprovar. Se demorar mais do que esperavas, contacta o professor ou administrador responsável por este grupo.";
        return;
      }
      window.location.href = "/editor";
    } catch (erro) {
      console.error(erro);
      mensagemErro.textContent = "Não foi possível contactar o servidor: " + (erro && erro.message ? erro.message : erro);
    }
  });
}

submeter("form-entrar", "/api/entrar");
submeter("form-registar", "/api/registar");
