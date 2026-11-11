export function render(container, state, { mySeat, onMove }) {
  const myTurn = state.status === "playing" && state.current_player === mySeat;
  const legal = new Set(myTurn ? state.legal_moves.map((m) => `${m.row},${m.col}`) : []);
  const grid = document.createElement("div");
  grid.className = "othello-board";
  state.board.forEach((row, r) => row.forEach((cell, c) => {
    const sq = document.createElement("button");
    sq.className = "sq";
    if (cell !== null) {
      const disc = document.createElement("span");
      disc.className = `disc ${cell === 0 ? "black" : "white"}`;
      sq.append(disc);
    }
    if (legal.has(`${r},${c}`)) {
      sq.classList.add("legal");
      sq.addEventListener("click", () => onMove({ row: r, col: c }));
    } else {
      sq.disabled = true;
    }
    grid.append(sq);
  }));
  container.replaceChildren(grid);
}
