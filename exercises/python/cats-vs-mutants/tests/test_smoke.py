from cats_vs_mutants.core.config import CatType, Config
from cats_vs_mutants.core.entities import PlaceResult, Status
from cats_vs_mutants.core.game import Game
from cats_vs_mutants.core.waves import default_waves


def test_smoke_place_cat_and_run_ticks():
    game = Game(Config(), default_waves())

    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK
    assert game.state.treats == 100
    assert len(game.state.cats) == 1

    for _ in range(5):
        game.tick()

    assert game.state.tick == 5
    assert game.status == Status.PLAYING
