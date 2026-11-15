const css = document.createElement("link");
css.rel = "stylesheet"; css.href = new URL("./othello.css", import.meta.url);
document.head.append(css);

export function render(container, publicState, legalMoves, onMove) {
  const legal = new Set(legalMoves.map((m) => `${m.row},${m.col}`));
  container.className = "othello-board";
  container.replaceChildren(...publicState.board.flatMap((row, r) => row.map((cell, c) => {
    const sq = document.createElement("button");
    sq.className = "sq";
    if (cell) { const d = document.createElement("span"); d.className = `disc ${cell}`; sq.append(d); }
    if (onMove && legal.has(`${r},${c}`)) {
      sq.classList.add("legal");
      sq.addEventListener("click", () => onMove({ row: r, col: c }));
    } else sq.disabled = true;
    return sq;
  })));
}
