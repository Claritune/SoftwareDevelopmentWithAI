#pragma once

#include <memory>
#include <string>

enum class OpType { Sum, Mult, Div, Exponent };

struct Expr {
    virtual ~Expr() = default;
    virtual int evaluate() const = 0;
    virtual std::string format() const = 0;
};

using ExprPtr = std::unique_ptr<Expr>;

struct NumberExpr : Expr {
    int value;
    explicit NumberExpr(int v) : value(v) {}
    int evaluate() const override;
    std::string format() const override;
};

struct BinaryOpExpr : Expr {
    OpType op;
    ExprPtr left;
    ExprPtr right;
    BinaryOpExpr(OpType op, ExprPtr left, ExprPtr right)
        : op(op), left(std::move(left)), right(std::move(right)) {}
    int evaluate() const override;
    std::string format() const override;
};
