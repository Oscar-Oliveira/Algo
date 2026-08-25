const abasAjuda = document.querySelectorAll(".aba-ajuda");

abasAjuda.forEach((aba) => {
  aba.addEventListener("click", () => {
    abasAjuda.forEach((a) => a.classList.remove("ativa"));
    aba.classList.add("ativa");
    document.querySelectorAll(".conteudo-aba-ajuda").forEach((secao) => secao.classList.add("escondido"));
    document.getElementById(`aba-conteudo-${aba.dataset.aba}`).classList.remove("escondido");
    if (aba.dataset.aba === "exemplos") {
      carregarExemplos();
    }
  });
});

// ---------- aba "Exemplos" ----------
//
// Um tema (pasta de exemplos/) de cada vez no painel direito: a barra
// lateral só lista os 10 temas -- os ficheiros e as suas descrições
// aparecem juntos, tema a tema, no painel direito (ver /api/exemplos,
// que já vem com o enunciado.md cortado em intro + blocos por
// _analisar_enunciado em main.py).

let dadosExemplos = null;

function escaparHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function formatarLinhaMarkdown(linha) {
  let texto = escaparHtml(linha);
  texto = texto.replace(/`([^`]+)`/g, "<code>$1</code>");
  texto = texto.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return texto;
}

// Um texto simples (intro/descrição de bloco, já sem cabeçalhos --
// esses vêm separados do backend) só precisa de parágrafos separados
// por linha em branco, com formatação inline de `código`/**negrito**.
function paragrafosHtml(texto) {
  if (!texto) {
    return "";
  }
  return texto
    .split(/\n\s*\n/)
    .map((paragrafo) => paragrafo.split("\n").map((l) => l.trim()).join(" ").trim())
    .filter((paragrafo) => paragrafo !== "")
    .map((paragrafo) => `<p>${formatarLinhaMarkdown(paragrafo)}</p>`)
    .join("");
}

async function carregarExemplos() {
  const indice = document.getElementById("indice-exemplos");
  if (dadosExemplos !== null) {
    return;
  }
  try {
    const resp = await fetch("/api/exemplos");
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    dadosExemplos = await resp.json();
  } catch (erro) {
    console.error("Falha ao carregar /api/exemplos:", erro);
    indice.innerHTML = "<p class=\"aviso-exemplo\">Não foi possível carregar os exemplos.</p>";
    return;
  }
  renderizarIndiceExemplos(dadosExemplos);
}

function renderizarIndiceExemplos(pastas) {
  const indice = document.getElementById("indice-exemplos");
  indice.innerHTML = "";
  if (pastas.length === 0) {
    indice.innerHTML = "<p class=\"aviso-exemplo\">Nenhum exemplo disponível.</p>";
    return;
  }
  pastas.forEach((pasta, indiceTema) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "item-tema-exemplo";
    item.textContent = pasta.titulo;
    item.addEventListener("click", () => {
      document.querySelectorAll(".item-tema-exemplo.ativo").forEach((el) => el.classList.remove("ativo"));
      item.classList.add("ativo");
      mostrarTema(pasta);
    });
    indice.appendChild(item);
    if (indiceTema === 0) {
      item.classList.add("ativo");
      mostrarTema(pasta);
    }
  });
}

function mostrarTema(pasta) {
  const conteudo = document.getElementById("conteudo-exemplo");
  const blocos = pasta.blocos || [];

  // índice do bloco (se algum) que contém cada ficheiro -- usado tanto
  // pela lista compacta como para saber se um bloco cobre mais do que
  // 1 ficheiro (caso do tema "Ficheiros e incluir", ver ACHADOS.md).
  const blocoDoFicheiro = (nome) => blocos.findIndex((b) => b.ficheiros.includes(nome));

  let html = `<h2>${escaparHtml(pasta.titulo)}</h2>`;
  if (pasta.intro) {
    html += `<div class="intro-exemplo">${paragrafosHtml(pasta.intro)}</div>`;
  }

  if (pasta.ficheiros.length > 0) {
    html += '<nav class="lista-ficheiros-exemplo">';
    html += pasta.ficheiros
      .map((ficheiro) => {
        const indiceBloco = blocoDoFicheiro(ficheiro.nome);
        const href = indiceBloco === -1 ? "#" : `#exemplo-bloco-${indiceBloco}`;
        return `<a href="${href}">${escaparHtml(ficheiro.nome)}</a>`;
      })
      .join("");
    html += "</nav>";
  }

  blocos.forEach((bloco, indice) => {
    html += `<div class="cartao-exemplo" id="exemplo-bloco-${indice}">`;
    html += `<h3>${formatarLinhaMarkdown(bloco.titulo)}</h3>`;
    html += paragrafosHtml(bloco.descricao);
    const mostrarNomeAntesDoCodigo = bloco.ficheiros.length > 1;
    bloco.ficheiros.forEach((nomeFicheiro) => {
      const ficheiro = pasta.ficheiros.find((f) => f.nome === nomeFicheiro);
      if (!ficheiro) {
        return;
      }
      if (mostrarNomeAntesDoCodigo) {
        html += `<p class="nome-ficheiro-exemplo">${escaparHtml(ficheiro.nome)}</p>`;
      }
      html += `<pre><code>${escaparHtml(ficheiro.codigo)}</code></pre>`;
    });
    html += "</div>";
  });

  conteudo.innerHTML = html;
}
