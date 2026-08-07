const abasAjuda = document.querySelectorAll(".aba-ajuda");

abasAjuda.forEach((aba) => {
  aba.addEventListener("click", () => {
    abasAjuda.forEach((a) => a.classList.remove("ativa"));
    aba.classList.add("ativa");
    document.querySelectorAll(".conteudo-aba-ajuda").forEach((secao) => secao.classList.add("escondido"));
    document.getElementById(`aba-conteudo-${aba.dataset.aba}`).classList.remove("escondido");
  });
});
