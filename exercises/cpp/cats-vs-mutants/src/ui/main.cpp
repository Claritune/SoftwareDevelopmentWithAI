#include <ncurses.h>

#include <chrono>
#include <csignal>
#include <iostream>
#include <string>

#include "../core/waves.hpp"
#include "headless.hpp"
#include "renderer.hpp"

namespace {

volatile std::sig_atomic_t g_interrupted = 0;

void onSigint(int) { g_interrupted = 1; }

using cvm::CatType;
using cvm::Game;
using cvm::ui::UiState;

// Translates one key press into UI state changes or core API calls.
// Returns false when the player wants to quit.
bool handleKey(int key, Game& game, UiState& ui) {
    const cvm::Config& cfg = game.config();
    if (key == 'q' || key == 'Q') return false;
    if (game.status() != cvm::Status::Playing) return true;

    switch (key) {
        case KEY_UP: if (ui.cursorLane > 0) ui.cursorLane--; break;
        case KEY_DOWN: if (ui.cursorLane < cfg.lanes - 1) ui.cursorLane++; break;
        case KEY_LEFT: if (ui.cursorCol > 0) ui.cursorCol--; break;
        case KEY_RIGHT: if (ui.cursorCol < cfg.cols - 1) ui.cursorCol++; break;
        case '1': ui.selected = CatType::Rich; break;
        case '2': ui.selected = CatType::Hissing; break;
        case '3': ui.selected = CatType::Sleepy; break;
        case '4': ui.selected = CatType::Laser; break;
        case 'p': case 'P': ui.paused = !ui.paused; break;
        case ' ': case '\n': case '\r': case KEY_ENTER:
            ui.message = cvm::ui::placeResultMessage(
                game.place(ui.selected, ui.cursorLane, ui.cursorCol));
            break;
        case 'x': case 'X':
            ui.message = game.remove(ui.cursorLane, ui.cursorCol) ? "" : "No cat there.";
            break;
        default: break;
    }
    return true;
}

int runInteractive() {
    using Clock = std::chrono::steady_clock;
    constexpr auto kTickLength = std::chrono::milliseconds(100);

    std::signal(SIGINT, onSigint);
    Game game(cvm::Config{}, cvm::defaultWaves());
    UiState ui;
    cvm::ui::Renderer renderer;

    auto nextTick = Clock::now() + kTickLength;
    while (!g_interrupted) {
        bool keepGoing = true;
        for (int key = getch(); key != ERR && keepGoing; key = getch()) {
            keepGoing = handleKey(key, game, ui);
        }
        if (!keepGoing) break;

        const auto now = Clock::now();
        if (now >= nextTick) {
            if (!ui.paused) game.tick();
            nextTick += kTickLength;
            if (nextTick < now) nextTick = now + kTickLength;  // don't spiral after a stall
        }
        renderer.draw(game, ui);
        napms(10);
    }
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc >= 2 && std::string(argv[1]) == "--headless") {
        if (argc < 3) {
            std::cerr << "usage: " << argv[0] << " --headless <script.txt>\n";
            return 2;
        }
        return cvm::ui::runHeadless(argv[2]);
    }
    if (argc >= 2) {
        std::cerr << "usage: " << argv[0] << " [--headless <script.txt>]\n";
        return 2;
    }
    return runInteractive();
}
