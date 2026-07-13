#include "parser.h"
#include <iostream>
#include <string>

int main() {
    std::string line;
    if (!std::getline(std::cin, line)) {
        std::cerr << "Error: no input" << std::endl;
        return 1;
    }

    try {
        Parser parser(line);
        auto expr = parser.parse();
        std::cout << expr->format() << " = " << expr->evaluate() << std::endl;
    } catch (const ParseError& e) {
        std::cerr << "Parse error: " << e.what() << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
