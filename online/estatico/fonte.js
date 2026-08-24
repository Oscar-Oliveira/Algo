// tamanho da fonte do editor, ajustável e persistido em localStorage.
// Carregado em <head>, tal como tema.js, para aplicar o tamanho já na
// primeira pintura -- evita o "salto" de tamanho depois do editor abrir.
(function () {
  const CHAVE = "algo-fonte-editor";
  const MINIMO = 0.7;
  const MAXIMO = 1.4;
  const PASSO = 0.05;
  const OMISSAO = 0.92;

  function tamanhoGuardado() {
    const guardado = parseFloat(localStorage.getItem(CHAVE));
    return Number.isFinite(guardado) ? guardado : OMISSAO;
  }

  function aplicarTamanho(remValor) {
    document.documentElement.style.setProperty("--fonte-editor-tamanho", remValor.toFixed(2) + "rem");
  }

  let tamanhoAtual = tamanhoGuardado();
  aplicarTamanho(tamanhoAtual);

  function ajustar(delta) {
    tamanhoAtual = Math.min(MAXIMO, Math.max(MINIMO, tamanhoAtual + delta));
    localStorage.setItem(CHAVE, tamanhoAtual);
    aplicarTamanho(tamanhoAtual);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const botaoMais = document.getElementById("botao-fonte-mais");
    const botaoMenos = document.getElementById("botao-fonte-menos");
    if (botaoMais) botaoMais.addEventListener("click", () => ajustar(PASSO));
    if (botaoMenos) botaoMenos.addEventListener("click", () => ajustar(-PASSO));
  });
})();
