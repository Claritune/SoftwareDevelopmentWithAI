from gamer.games.base import Game
from gamer.games.othello import OTHELLO

GAMES: dict[str, Game] = {OTHELLO.id: OTHELLO}
