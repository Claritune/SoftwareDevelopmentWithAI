#pragma once

#include <string>

#include "../core/game.hpp"

namespace cvm::ui {

const char* catSprite(CatType type);
const char* catName(CatType type);
const char* mutantSprite(MutantType type);
const char* mutantName(MutantType type);
const char* statusName(Status status);
const char* placeResultMessage(PlaceResult result);

// Each lane is drawn as two text rows: cats on row 0, mutants and hairballs on row 1.
// Returns the 5 character content of one cell row. Shared by ncurses and headless output.
std::string cellText(const Game& game, int lane, int col, int row);

std::string headerText(const Game& game);

struct UiState {
    int cursorLane = 2;
    int cursorCol = 0;
    CatType selected = CatType::Rich;
    bool paused = false;
    std::string message;
};

// ncurses renderer. Only reads game state; never mutates it.
class Renderer {
public:
    Renderer();
    ~Renderer();
    Renderer(const Renderer&) = delete;
    Renderer& operator=(const Renderer&) = delete;

    void draw(const Game& game, const UiState& ui);

private:
    void drawBoard(const Game& game, const UiState& ui, int top);
    void drawEndScreen(const Game& game);

    bool colors_ = false;
};

}  // namespace cvm::ui
