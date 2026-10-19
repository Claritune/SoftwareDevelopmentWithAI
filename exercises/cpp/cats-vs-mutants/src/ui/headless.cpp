#include "headless.hpp"

#include <fstream>
#include <iostream>
#include <optional>
#include <sstream>

#include "../core/waves.hpp"
#include "renderer.hpp"

namespace cvm::ui {

namespace {

std::optional<CatType> parseCat(const std::string& name) {
    if (name == "rich") return CatType::Rich;
    if (name == "hissing") return CatType::Hissing;
    if (name == "sleepy") return CatType::Sleepy;
    if (name == "laser") return CatType::Laser;
    return std::nullopt;
}

}  // namespace

void printState(const Game& game, std::ostream& out) {
    const Config& cfg = game.config();
    const GameState& s = game.state();
    out << headerText(game) << "   STATUS: " << statusName(s.status) << '\n';

    const std::string border = "+" + std::string(static_cast<std::size_t>(cfg.cols) * 6, '-') + "+";
    out << border << '\n';
    for (int lane = 0; lane < cfg.lanes; ++lane) {
        for (int row = 0; row < 2; ++row) {
            out << '|';
            for (int col = 0; col < cfg.cols; ++col) out << cellText(game, lane, col, row) << ' ';
            out << "|\n";
        }
    }
    out << border << '\n';

    for (const Cat& c : s.cats) {
        out << "cat     " << catSprite(c.type) << " lane " << c.lane << " col " << c.col
            << " hp " << c.health << '\n';
    }
    for (const Mutant& m : s.mutants) {
        out << "mutant  " << mutantSprite(m.type) << " lane " << m.lane << " pos " << m.position
            << " hp " << m.health << '\n';
    }
    for (const Hairball& h : s.hairballs) {
        out << "hairball  o   lane " << h.lane << " pos " << h.position << '\n';
    }
}

int runHeadless(const std::string& path) {
    std::ifstream file(path);
    if (!file) {
        std::cerr << "cannot open script: " << path << '\n';
        return 1;
    }

    Game game(Config{}, defaultWaves());
    std::string line;
    int lineNo = 0;
    while (std::getline(file, line)) {
        ++lineNo;
        line = line.substr(0, line.find('#'));
        std::istringstream in(line);
        std::string cmd;
        if (!(in >> cmd)) continue;

        if (cmd == "place") {
            std::string name;
            int lane = 0;
            int col = 0;
            in >> name >> lane >> col;
            const std::optional<CatType> type = parseCat(name);
            if (!in || !type) {
                std::cerr << path << ':' << lineNo << ": bad place command\n";
                return 1;
            }
            const PlaceResult r = game.place(*type, lane, col);
            if (r != PlaceResult::Ok) {
                std::cout << "tick " << game.state().tick << ": place " << name << ' ' << lane
                          << ' ' << col << " failed: " << placeResultMessage(r) << '\n';
            }
        } else if (cmd == "remove") {
            int lane = 0;
            int col = 0;
            if (!(in >> lane >> col)) {
                std::cerr << path << ':' << lineNo << ": bad remove command\n";
                return 1;
            }
            game.remove(lane, col);
        } else if (cmd == "tick") {
            int n = 0;
            if (!(in >> n)) {
                std::cerr << path << ':' << lineNo << ": bad tick command\n";
                return 1;
            }
            for (int i = 0; i < n; ++i) game.tick();
        } else if (cmd == "print") {
            printState(game, std::cout);
            std::cout << '\n';
        } else {
            std::cerr << path << ':' << lineNo << ": unknown command '" << cmd << "'\n";
            return 1;
        }
    }

    std::cout << "=== FINAL STATE ===\n";
    printState(game, std::cout);
    return 0;
}

}  // namespace cvm::ui
