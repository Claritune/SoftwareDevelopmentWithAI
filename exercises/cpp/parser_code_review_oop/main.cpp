#include <iostream>
#include <string>

#include "parser.h"

int main() {
    std::string line;
    if (!std::getline(std::cin, line)) {
        return 0;
    }

    Parser parser(line);
    auto expr = parser.parse();

    std::cout << expr->toString() << " = " << expr->evaluate() << '\n';
    return 0;
}
