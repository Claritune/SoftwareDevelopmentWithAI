#include "expr.h"
#include <cmath>
#include <stdexcept>

static char op_symbol(OpType op) {
    switch (op) {
        case OpType::Sum:      return '+';
        case OpType::Mult:     return '*';
        case OpType::Div:      return '/';
        case OpType::Exponent: return '^';
    }
    throw std::logic_error("unknown op");
}

static int int_pow(int base, int exp) {
    if (exp < 0) throw std::domain_error("negative exponent not supported");
    int result = 1;
    for (int i = 0; i < exp; ++i)
        result *= base;
    return result;
}

int NumberExpr::evaluate() const {
    return value;
}

std::string NumberExpr::format() const {
    if (value < 0)
        return "(" + std::to_string(value) + ")";
    return std::to_string(value);
}

int BinaryOpExpr::evaluate() const {
    int l = left->evaluate();
    int r = right->evaluate();
    switch (op) {
        case OpType::Sum:      return l + r;
        case OpType::Mult:     return l * r;
        case OpType::Div:
            if (r == 0) throw std::domain_error("division by zero");
            return l / r;
        case OpType::Exponent: return int_pow(l, r);
    }
    throw std::logic_error("unknown op");
}

std::string BinaryOpExpr::format() const {
    return "(" + left->format() + " " + op_symbol(op) + " " + right->format() + ")";
}
