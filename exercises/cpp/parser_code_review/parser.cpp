#include "parser.h"
#include <cctype>

Parser::Parser(std::string_view input) : input_(input) {}

ExprPtr Parser::parse() {
    skip_whitespace();
    auto expr = parse_expr();
    skip_whitespace();
    if (!at_end())
        throw ParseError("unexpected trailing characters at position " + std::to_string(pos_));
    return expr;
}

ExprPtr Parser::parse_expr() {
    skip_whitespace();
    if (at_end())
        throw ParseError("unexpected end of input");

    char c = peek();

    if (c == '-' || std::isdigit(static_cast<unsigned char>(c))) {
        // Could be a negative number or the start of a function name — digits confirm number
        if (c == '-') {
            // Look ahead: if next char is a digit, it's a negative number
            if (pos_ + 1 < input_.size() && std::isdigit(static_cast<unsigned char>(input_[pos_ + 1])))
                return parse_number();
            throw ParseError("unexpected '-' at position " + std::to_string(pos_));
        }
        return parse_number();
    }

    if (std::isalpha(static_cast<unsigned char>(c)))
        return parse_function_call();

    throw ParseError(std::string("unexpected character '") + c + "' at position " + std::to_string(pos_));
}

ExprPtr Parser::parse_number() {
    skip_whitespace();
    size_t start = pos_;
    if (peek() == '-')
        advance();
    if (at_end() || !std::isdigit(static_cast<unsigned char>(peek())))
        throw ParseError("expected digit at position " + std::to_string(pos_));
    while (!at_end() && std::isdigit(static_cast<unsigned char>(peek())))
        advance();
    std::string num_str(input_.substr(start, pos_ - start));
    return std::make_unique<NumberExpr>(std::stoi(num_str));
}

ExprPtr Parser::parse_function_call() {
    auto name = read_identifier();
    OpType op = identifier_to_op(name);

    skip_whitespace();
    expect('(');

    auto left = parse_expr();

    skip_whitespace();
    expect(',');

    auto right = parse_expr();

    skip_whitespace();
    expect(')');

    return std::make_unique<BinaryOpExpr>(op, std::move(left), std::move(right));
}

void Parser::skip_whitespace() {
    while (!at_end() && std::isspace(static_cast<unsigned char>(peek())))
        ++pos_;
}

char Parser::peek() const {
    if (at_end())
        throw ParseError("unexpected end of input");
    return input_[pos_];
}

char Parser::advance() {
    char c = peek();
    ++pos_;
    return c;
}

void Parser::expect(char c) {
    skip_whitespace();
    if (at_end())
        throw ParseError(std::string("expected '") + c + "' but reached end of input");
    if (peek() != c)
        throw ParseError(std::string("expected '") + c + "' but got '" + peek() + "' at position " + std::to_string(pos_));
    advance();
}

bool Parser::at_end() const {
    return pos_ >= input_.size();
}

std::string_view Parser::read_identifier() {
    skip_whitespace();
    size_t start = pos_;
    while (!at_end() && std::isalpha(static_cast<unsigned char>(peek())))
        advance();
    if (start == pos_)
        throw ParseError("expected identifier at position " + std::to_string(pos_));
    return input_.substr(start, pos_ - start);
}

OpType Parser::identifier_to_op(std::string_view name) const {
    if (name == "Sum")      return OpType::Sum;
    if (name == "Mult")     return OpType::Mult;
    if (name == "Div")      return OpType::Div;
    if (name == "Exponent") return OpType::Exponent;
    throw ParseError("unknown function: " + std::string(name));
}
