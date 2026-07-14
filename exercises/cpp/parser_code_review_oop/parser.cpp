#include "parser.h"

#include <cctype>
#include <stdexcept>

Parser::Parser(std::string input) : input_(std::move(input)), pos_(0) {}

std::unique_ptr<Expression> Parser::parse() {
    auto expr = parseExpression();
    skipWhitespace();
    if (!atEnd()) {
        throw std::runtime_error("unexpected trailing input");
    }
    return expr;
}

void Parser::skipWhitespace() {
    while (!atEnd() && std::isspace(static_cast<unsigned char>(peek()))) {
        ++pos_;
    }
}

char Parser::peek() const {
    if (atEnd()) {
        return '\0';
    }
    return input_[pos_];
}

char Parser::consume() {
    if (atEnd()) {
        throw std::runtime_error("unexpected end of input");
    }
    return input_[pos_++];
}

bool Parser::atEnd() const {
    return pos_ >= input_.size();
}

std::unique_ptr<Expression> Parser::parseExpression() {
    skipWhitespace();

    if (std::isalpha(static_cast<unsigned char>(peek()))) {
        return parseFunction();
    }

    if (std::isdigit(static_cast<unsigned char>(peek())) ||
        (peek() == '-' && std::isdigit(static_cast<unsigned char>(input_[pos_ + 1])))) {
        return parseNumber();
    }

    throw std::runtime_error("expected number or function call");
}

std::unique_ptr<Expression> Parser::parseNumber() {
    skipWhitespace();

    bool negative = false;
    if (peek() == '-') {
        negative = true;
        consume();
    }

    if (!std::isdigit(static_cast<unsigned char>(peek()))) {
        throw std::runtime_error("expected integer literal");
    }

    int value = 0;
    while (std::isdigit(static_cast<unsigned char>(peek()))) {
        value = value * 10 + (peek() - '0');
        consume();
    }

    if (negative) {
        value = -value;
    }

    return std::make_unique<NumberExpr>(value);
}

std::unique_ptr<Expression> Parser::parseFunction() {
    skipWhitespace();

    std::string name;
    while (std::isalpha(static_cast<unsigned char>(peek()))) {
        name += consume();
    }

    skipWhitespace();
    if (consume() != '(') {
        throw std::runtime_error("expected '(' after function name");
    }

    auto left = parseExpression();

    skipWhitespace();
    if (consume() != ',') {
        throw std::runtime_error("expected ',' between arguments");
    }

    auto right = parseExpression();

    skipWhitespace();
    if (consume() != ')') {
        throw std::runtime_error("expected ')' to close function call");
    }

    if (name == "Sum") {
        return std::make_unique<SumExpr>(std::move(left), std::move(right));
    }
    if (name == "Mult") {
        return std::make_unique<MultExpr>(std::move(left), std::move(right));
    }
    if (name == "Div") {
        return std::make_unique<DivExpr>(std::move(left), std::move(right));
    }
    if (name == "Exponent") {
        return std::make_unique<ExponentExpr>(std::move(left), std::move(right));
    }

    throw std::runtime_error("unknown function: " + name);
}
