from gamer.games.base import Game
from gamer.games.othello import OTHELLO

REGISTRY: dict[str, Game] = {OTHELLO.id: OTHELLO}
