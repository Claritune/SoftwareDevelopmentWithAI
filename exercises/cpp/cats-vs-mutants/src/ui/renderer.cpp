#include "renderer.hpp"

#include <ncurses.h>

#include <cstdio>

namespace cvm::ui {

namespace {

constexpr int kCellWidth = 6;  // 5 character sprite plus a space
constexpr int kRowsPerLane = 3;  // cat row, mutant row, separator

enum ColorPair : short { kCatColor = 1, kMutantColor = 2, kHairballColor = 3 };

}  // namespace

const char* catSprite(CatType type) {
    switch (type) {
        case CatType::Rich: return "=$.$=";
        case CatType::Hissing: return "=^o^=";
        case CatType::Sleepy: return "=-.-=";
        case CatType::Laser: return "=O.O=";
    }
    return "?????";
}

const char* catName(CatType type) {
    switch (type) {
        case CatType::Rich: return "Rich Cat";
        case CatType::Hissing: return "Hissing Cat";
        case CatType::Sleepy: return "Sleepy Cat";
        case CatType::Laser: return "Laser Cat";
    }
    return "Cat";
}

const char* mutantSprite(MutantType type) {
    switch (type) {
        case MutantType::Blob: return "(x_x)";
        case MutantType::Runner: return "{@_@}";
        case MutantType::Brute: return "<O_O>";
        case MutantType::Hopper: return "(o_O)";
        case MutantType::Equivalent: return "( _ )";
    }
    return "?????";
}

const char* mutantName(MutantType type) {
    switch (type) {
        case MutantType::Blob: return "Blob";
        case MutantType::Runner: return "Runner";
        case MutantType::Brute: return "Brute";
        case MutantType::Hopper: return "Hopper";
        case MutantType::Equivalent: return "Equivalent Mutant";
    }
    return "Mutant";
}

const char* statusName(Status status) {
    switch (status) {
        case Status::Playing: return "Playing";
        case Status::Won: return "Won";
        case Status::Lost: return "Lost";
    }
    return "?";
}

const char* placeResultMessage(PlaceResult result) {
    switch (result) {
        case PlaceResult::Ok: return "";
        case PlaceResult::CellOccupied: return "That cell already has a cat.";
        case PlaceResult::NotEnoughTreats: return "Not enough treats!";
        case PlaceResult::OutOfBounds: return "Out of bounds.";
        case PlaceResult::GameOver: return "The game is over.";
    }
    return "";
}

std::string cellText(const Game& game, int lane, int col, int row) {
    if (row == 0) {
        const Cat* cat = game.catAt(lane, col);
        return cat != nullptr ? catSprite(cat->type) : "  .  ";
    }

    // The frontmost mutant in the cell wins; otherwise show a hairball.
    const Mutant* front = nullptr;
    for (const Mutant& m : game.state().mutants) {
        if (m.lane == lane && m.position >= 0 && game.cellOf(m.position) == col &&
            (front == nullptr || m.position < front->position)) {
            front = &m;
        }
    }
    if (front != nullptr) return mutantSprite(front->type);

    std::string text = "     ";
    const int cellSize = game.config().cellSize;
    for (const Hairball& h : game.state().hairballs) {
        if (h.lane == lane && game.cellOf(h.position) == col) {
            text[static_cast<std::size_t>((h.position % cellSize) * 5 / cellSize)] = 'o';
        }
    }
    return text;
}

std::string headerText(const Game& game) {
    char buf[128];
    std::snprintf(buf, sizeof buf, "TREATS: %d   WAVE %d/%d   LIVES: %d   TICK: %d",
                  game.state().treats, game.currentWave(), game.totalWaves(),
                  game.state().lives, game.state().tick);
    return buf;
}

Renderer::Renderer() {
    initscr();
    cbreak();
    noecho();
    keypad(stdscr, TRUE);
    nodelay(stdscr, TRUE);
    curs_set(0);
    if (has_colors()) {
        start_color();
        use_default_colors();
        init_pair(kCatColor, COLOR_YELLOW, -1);
        init_pair(kMutantColor, COLOR_GREEN, -1);
        init_pair(kHairballColor, COLOR_WHITE, -1);
        colors_ = true;
    }
}

Renderer::~Renderer() { endwin(); }

void Renderer::draw(const Game& game, const UiState& ui) {
    erase();
    if (game.status() != Status::Playing) {
        drawEndScreen(game);
        refresh();
        return;
    }

    std::string header = headerText(game);
    if (ui.paused) header += "   [PAUSED]";
    mvaddstr(0, 0, header.c_str());

    const int boardTop = 2;
    drawBoard(game, ui, boardTop);

    const Config& cfg = game.config();
    const int bottom = boardTop + cfg.lanes * kRowsPerLane + 1;
    mvprintw(bottom, 0, "Selected: %s %s   %s", catName(ui.selected), catSprite(ui.selected),
             ui.message.c_str());
    mvprintw(bottom + 1, 0, "1 Rich %d  2 Hissing %d  3 Sleepy %d  4 Laser %d", cfg.rich.cost,
             cfg.hissing.cost, cfg.sleepy.cost, cfg.laser.cost);
    mvaddstr(bottom + 2, 0, "Arrows move  Space/Enter place  x remove  p pause  q quit");
    refresh();
}

void Renderer::drawBoard(const Game& game, const UiState& ui, int top) {
    const Config& cfg = game.config();
    const int width = cfg.cols * kCellWidth;
    const int height = cfg.lanes * kRowsPerLane - 1;

    // Border
    mvaddch(top - 1, 0, '+');
    mvhline(top - 1, 1, '-', width);
    mvaddch(top - 1, width + 1, '+');
    mvaddch(top + height, 0, '+');
    mvhline(top + height, 1, '-', width);
    mvaddch(top + height, width + 1, '+');
    mvvline(top, 0, '|', height);
    mvvline(top, width + 1, '|', height);

    for (int lane = 0; lane < cfg.lanes; ++lane) {
        const int y = top + lane * kRowsPerLane;
        for (int col = 0; col < cfg.cols; ++col) {
            const int x = 1 + col * kCellWidth;
            const bool cursor = lane == ui.cursorLane && col == ui.cursorCol;
            for (int row = 0; row < 2; ++row) {
                const std::string text = cellText(game, lane, col, row);
                attr_t attr = A_NORMAL;
                if (colors_ && text != "  .  " && text != "     ") {
                    short pair = kCatColor;
                    // Sprites never start with a space; hairball rows always do.
                    if (row == 1) pair = text[0] == ' ' ? kHairballColor : kMutantColor;
                    attr |= COLOR_PAIR(pair) | A_BOLD;
                }
                if (cursor) attr |= A_REVERSE;
                attron(attr);
                mvprintw(y + row, x, "%s ", text.c_str());
                attroff(attr);
            }
        }
        if (lane + 1 < cfg.lanes) {
            attron(A_DIM);
            mvhline(y + 2, 1, '.', width);
            attroff(A_DIM);
        }
    }
}

void Renderer::drawEndScreen(const Game& game) {
    const bool won = game.status() == Status::Won;
    const char* title = won ? "*** THE CATS WIN! ***" : "*** THE MUTANTS GOT HOME ***";
    const char* line = won ? "Every mutant was killed. Your tests are strong."
                           : "Too many mutants survived. Time to write more tests.";
    const int y = LINES / 2 - 3;
    attron(A_BOLD);
    mvaddstr(y, 2, title);
    attroff(A_BOLD);
    mvaddstr(y + 2, 2, line);
    mvaddstr(y + 3, 2, headerText(game).c_str());
    mvaddstr(y + 5, 2, "press q to quit");
}

}  // namespace cvm::ui
