#pragma once

#include "expr.h"
#include <string>
#include <string_view>
#include <stdexcept>

struct ParseError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

class Parser {
public:
    explicit Parser(std::string_view input);
    ExprPtr parse();

private:
    std::string_view input_;
    size_t pos_ = 0;

    ExprPtr parse_expr();
    ExprPtr parse_number();
    ExprPtr parse_function_call();

    void skip_whitespace();
    char peek() const;
    char advance();
    void expect(char c);
    bool at_end() const;
    std::string_view read_identifier();
    OpType identifier_to_op(std::string_view name) const;
};
