#include "expr.h"

#include <cmath>
#include <sstream>

NumberExpr::NumberExpr(int value) : value_(value) {}

int NumberExpr::evaluate() const {
    return value_;
}

std::string NumberExpr::toString() const {
    if (value_ < 0) {
        return "(" + std::to_string(value_) + ")";
    }
    return std::to_string(value_);
}

BinaryExpr::BinaryExpr(std::unique_ptr<Expression> left, std::unique_ptr<Expression> right)
    : left_(std::move(left)), right_(std::move(right)) {}

int SumExpr::evaluate() const {
    return left_->evaluate() + right_->evaluate();
}

std::string SumExpr::toString() const {
    return "(" + left_->toString() + " + " + right_->toString() + ")";
}

int MultExpr::evaluate() const {
    return left_->evaluate() * right_->evaluate();
}

std::string MultExpr::toString() const {
    return "(" + left_->toString() + " * " + right_->toString() + ")";
}

int DivExpr::evaluate() const {
    return left_->evaluate() / right_->evaluate();
}

std::string DivExpr::toString() const {
    return "(" + left_->toString() + " / " + right_->toString() + ")";
}

int ExponentExpr::evaluate() const {
    return static_cast<int>(std::pow(left_->evaluate(), right_->evaluate()));
}

std::string ExponentExpr::toString() const {
    return "(" + left_->toString() + " ^ " + right_->toString() + ")";
}
