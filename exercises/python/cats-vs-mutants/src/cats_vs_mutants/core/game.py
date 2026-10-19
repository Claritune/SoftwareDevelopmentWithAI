"""The game rules. Pure and deterministic: no I/O, no clock, no randomness."""

import copy
from collections.abc import Iterable

from cats_vs_mutants.core.config import CatType, Config, MutantType
from cats_vs_mutants.core.entities import (
    Cat,
    GameState,
    Hairball,
    Mutant,
    PlaceResult,
    SpawnEvent,
    Status,
)


class Game:
    def __init__(self, config: Config, waves: Iterable[SpawnEvent]) -> None:
        # The game owns copies, like the C++ version taking both by value.
        self._config = copy.deepcopy(config)
        self._waves = sorted(waves, key=lambda e: e.tick)  # stable, like std::stable_sort
        self._state = GameState(
            treats=self._config.starting_treats, lives=self._config.starting_lives
        )

    @property
    def state(self) -> GameState:
        """The live game state. Read it; don't modify it."""
        return self._state

    @property
    def config(self) -> Config:
        return self._config

    @property
    def status(self) -> Status:
        return self._state.status

    def place(self, cat_type: CatType, lane: int, col: int) -> PlaceResult:
        if self._state.status != Status.PLAYING:
            return PlaceResult.GAME_OVER
        if not self._in_bounds(lane, col):
            return PlaceResult.OUT_OF_BOUNDS
        if self.cat_at(lane, col) is not None:
            return PlaceResult.CELL_OCCUPIED
        stats = self._config.cat(cat_type)
        if stats.cost > self._state.treats:
            return PlaceResult.NOT_ENOUGH_TREATS

        self._state.treats -= stats.cost
        self._state.cats.append(Cat(cat_type, lane, col, stats.health, stats.interval))
        return PlaceResult.OK

    def remove(self, lane: int, col: int) -> bool:
        if self._state.status != Status.PLAYING:
            return False
        for i, cat in enumerate(self._state.cats):
            if cat.lane == lane and cat.col == col:
                del self._state.cats[i]
                return True
        return False

    def tick(self) -> None:
        """One simulation step. The order of these steps is part of the game rules."""
        if self._state.status != Status.PLAYING:
            return

        self._state.tick += 1  # 1. Increment tick counter
        self._produce_resources()  # 2. Passive income and Rich Cat production
        self._spawn_mutants()  # 3. Spawn mutants scheduled for this tick
        self._fire_cats()  # 4. Cats fire (hairballs created, laser damage applied)
        self._move_hairballs()  # 5. Move hairballs...
        self._resolve_hits()  #    ...and resolve hits
        self._move_mutants()  # 6. Move mutants (respecting blocking and Hopper jumps)
        self._resolve_bites()  # 7. Resolve bites
        self._remove_dead()  # 8. Remove dead cats and dead mutants
        self._handle_mutants_at_home()  # 9. Handle mutants reaching home
        self._check_end_conditions()  # 10. Check win and lose conditions

    def current_wave(self) -> int:
        """Wave of the most recently spawned mutant (the first event's wave before any spawn)."""
        if self._state.next_spawn == 0:
            return self._waves[0].wave if self._waves else 0
        return self._waves[self._state.next_spawn - 1].wave

    def total_waves(self) -> int:
        return max((e.wave for e in self._waves), default=0)

    def cat_at(self, lane: int, col: int) -> Cat | None:
        for cat in self._state.cats:
            if cat.lane == lane and cat.col == col:
                return cat
        return None

    def cell_of(self, position: int) -> int:
        # C++ integer division truncates toward zero, so step -1 is still in cell 0.
        size = self._config.cell_size
        return position // size if position >= 0 else -(-position // size)

    # ---- Tick steps, in the order tick() runs them ------------------------------

    def _produce_resources(self) -> None:
        cfg, state = self._config, self._state
        if state.tick % cfg.passive_income_interval == 0:
            state.treats += cfg.passive_income
        for cat in state.cats:
            if cat.type != CatType.RICH:
                continue
            cat.cooldown -= 1
            if cat.cooldown == 0:
                cat.cooldown = cfg.rich.interval
                state.treats += cfg.rich_production

    def _spawn_mutants(self) -> None:
        cfg, state = self._config, self._state
        while (
            state.next_spawn < len(self._waves) and self._waves[state.next_spawn].tick <= state.tick
        ):
            e = self._waves[state.next_spawn]
            state.next_spawn += 1
            stats = cfg.mutant(e.type)
            state.mutants.append(
                Mutant(
                    e.type,
                    e.lane,
                    cfg.spawn_position(),
                    stats.health,
                    stats.move_interval,
                    cfg.bite_interval,
                    False,
                )
            )

    def _fire_cats(self) -> None:
        cfg, state = self._config, self._state
        for cat in state.cats:
            if cat.type not in (CatType.HISSING, CatType.LASER):
                continue
            cat.cooldown -= 1
            if cat.cooldown != 0:
                continue
            cat.cooldown = cfg.cat(cat.type).interval

            if cat.type == CatType.HISSING:
                if self._any_mutant_in_range(cat.lane, cat.col, cfg.cols):
                    state.hairballs.append(
                        Hairball(cat.lane, (cat.col + 1) * cfg.cell_size, cat.col)
                    )
            else:
                last = cat.col + cfg.laser_range
                if not self._any_mutant_in_range(cat.lane, cat.col, last):
                    continue
                for m in state.mutants:
                    cell = self.cell_of(m.position)
                    if m.lane == cat.lane and cat.col <= cell <= last:
                        self._damage(m, cfg.laser_damage)

    def _move_hairballs(self) -> None:
        for h in self._state.hairballs:
            h.position += self._config.hairball_speed

    def _resolve_hits(self) -> None:
        cfg, state = self._config, self._state
        remaining: list[Hairball] = []
        for h in state.hairballs:
            # The first mutant the hairball reaches is the one closest to its origin.
            target: Mutant | None = None
            for m in state.mutants:
                if m.lane != h.lane or m.health <= 0 or m.type == MutantType.EQUIVALENT:
                    continue
                if m.position > h.position or self.cell_of(m.position) < h.origin_col:
                    continue
                if target is None or m.position < target.position:
                    target = m
            if target is not None:
                self._damage(target, cfg.hairball_damage)
            elif h.position <= cfg.spawn_position():
                remaining.append(h)
        state.hairballs = remaining

    def _move_mutants(self) -> None:
        cfg = self._config
        for m in self._state.mutants:
            if m.health <= 0:
                continue
            blocker = self.cat_at(m.lane, self.cell_of(m.position))
            if blocker is not None:
                if m.type == MutantType.HOPPER and not m.has_jumped:
                    m.has_jumped = True
                    m.position = blocker.col * cfg.cell_size - 1
                    m.move_cooldown = cfg.hopper.move_interval
                continue
            m.move_cooldown -= 1
            if m.move_cooldown == 0:
                m.move_cooldown = cfg.mutant(m.type).move_interval
                m.position -= 1

    def _resolve_bites(self) -> None:
        cfg = self._config
        for m in self._state.mutants:
            if m.health <= 0:
                continue
            cat = self.cat_at(m.lane, self.cell_of(m.position))
            if cat is None:
                m.bite_cooldown = cfg.bite_interval
                continue
            m.bite_cooldown -= 1
            if m.bite_cooldown == 0:
                m.bite_cooldown = cfg.bite_interval
                cat.health -= cfg.bite_damage

    def _remove_dead(self) -> None:
        state = self._state
        state.cats = [c for c in state.cats if c.health > 0]
        state.mutants = [m for m in state.mutants if m.health > 0]

    def _handle_mutants_at_home(self) -> None:
        state = self._state
        remaining: list[Mutant] = []
        for m in state.mutants:
            if m.position >= 0:
                remaining.append(m)
            elif m.type != MutantType.EQUIVALENT:
                state.lives -= 1
        state.mutants = remaining

    def _check_end_conditions(self) -> None:
        state = self._state
        if state.lives <= 0:
            state.lives = 0
            state.status = Status.LOST
        elif state.next_spawn == len(self._waves) and not state.mutants:
            state.status = Status.WON

    # ---- Helpers -----------------------------------------------------------------

    def _in_bounds(self, lane: int, col: int) -> bool:
        return 0 <= lane < self._config.lanes and 0 <= col < self._config.cols

    def _any_mutant_in_range(self, lane: int, from_col: int, to_col: int) -> bool:
        return any(
            m.lane == lane and m.health > 0 and from_col <= self.cell_of(m.position) <= to_col
            for m in self._state.mutants
        )

    def _damage(self, mutant: Mutant, amount: int) -> None:
        if mutant.type == MutantType.EQUIVALENT:
            return
        mutant.health -= amount
