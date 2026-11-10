export function render(container, publicState, legalMoves, onMove) {
  const legal = new Set(legalMoves.map((m) => m.cell));
  container.replaceChildren(...publicState.claims.map((claim, i) => {
    const b = document.createElement("button");
    b.textContent = claim || String(i);
    if (onMove && legal.has(i)) b.addEventListener("click", () => onMove({ cell: i }));
    else b.disabled = true;
    return b;
  }));
}
