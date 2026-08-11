// FEAT-02: escolha de tema claro/escuro, persistida em localStorage,
// com deteção inicial por prefers-color-scheme. Carregado em <head>,
// antes do resto da página, para aplicar o tema já na primeira
// pintura -- sem isto, a página aparecia sempre no tema escuro por
// uma fração de segundo antes de trocar para o tema guardado.
(function () {
  const CHAVE = "algo-tema";

  function temaGuardadoOuPreferido() {
    const guardado = localStorage.getItem(CHAVE);
    if (guardado === "claro" || guardado === "escuro") return guardado;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "claro" : "escuro";
  }

  function aplicarTema(tema) {
    document.documentElement.dataset.theme = tema === "claro" ? "light" : "dark";
    window.dispatchEvent(new CustomEvent("algo-tema-mudou", { detail: tema }));
  }

  let temaAtual = temaGuardadoOuPreferido();
  aplicarTema(temaAtual);

  window.obterTema = () => temaAtual;

  document.addEventListener("DOMContentLoaded", () => {
    const botao = document.getElementById("botao-tema");
    if (!botao) return;
    const atualizarTitulo = () => {
      botao.title = temaAtual === "claro" ? "Mudar para tema escuro" : "Mudar para tema claro";
    };
    atualizarTitulo();
    botao.addEventListener("click", () => {
      temaAtual = temaAtual === "claro" ? "escuro" : "claro";
      localStorage.setItem(CHAVE, temaAtual);
      aplicarTema(temaAtual);
      atualizarTitulo();
    });
  });
})();
