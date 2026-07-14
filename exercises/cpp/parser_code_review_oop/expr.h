#pragma once

#include <memory>
#include <string>

class Expression {
public:
    virtual ~Expression() = default;
    virtual int evaluate() const = 0;
    virtual std::string toString() const = 0;
};

class NumberExpr : public Expression {
public:
    explicit NumberExpr(int value);

    int evaluate() const override;
    std::string toString() const override;

private:
    int value_;
};

class BinaryExpr : public Expression {
public:
    BinaryExpr(std::unique_ptr<Expression> left, std::unique_ptr<Expression> right);

protected:
    std::unique_ptr<Expression> left_;
    std::unique_ptr<Expression> right_;
};

class SumExpr : public BinaryExpr {
public:
    using BinaryExpr::BinaryExpr;

    int evaluate() const override;
    std::string toString() const override;
};

class MultExpr : public BinaryExpr {
public:
    using BinaryExpr::BinaryExpr;

    int evaluate() const override;
    std::string toString() const override;
};

class DivExpr : public BinaryExpr {
public:
    using BinaryExpr::BinaryExpr;

    int evaluate() const override;
    std::string toString() const override;
};

class ExponentExpr : public BinaryExpr {
public:
    using BinaryExpr::BinaryExpr;

    int evaluate() const override;
    std::string toString() const override;
};
