#pragma once

#include <memory>
#include <string>

#include "expr.h"

class Parser {
public:
    explicit Parser(std::string input);

    std::unique_ptr<Expression> parse();

private:
    void skipWhitespace();
    char peek() const;
    char consume();
    bool atEnd() const;

    std::unique_ptr<Expression> parseExpression();
    std::unique_ptr<Expression> parseNumber();
    std::unique_ptr<Expression> parseFunction();

    std::string input_;
    std::size_t pos_;
};
