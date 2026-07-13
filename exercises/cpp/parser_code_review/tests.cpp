#include "parser.h"
#include <cassert>
#include <iostream>
#include <string>

static int tests_passed = 0;
static int tests_failed = 0;

static void check(const std::string& name, const std::string& input,
                  const std::string& expected_format, int expected_value) {
    try {
        Parser parser(input);
        auto expr = parser.parse();
        std::string fmt = expr->format();
        int val = expr->evaluate();
        if (fmt == expected_format && val == expected_value) {
            ++tests_passed;
        } else {
            ++tests_failed;
            std::cerr << "FAIL: " << name << "\n"
                      << "  input:           " << input << "\n"
                      << "  expected format:  " << expected_format << "\n"
                      << "  actual format:    " << fmt << "\n"
                      << "  expected value:   " << expected_value << "\n"
                      << "  actual value:     " << val << "\n";
        }
    } catch (const std::exception& e) {
        ++tests_failed;
        std::cerr << "FAIL: " << name << " (exception: " << e.what() << ")\n";
    }
}

static void check_parse_error(const std::string& name, const std::string& input) {
    try {
        Parser parser(input);
        parser.parse();
        ++tests_failed;
        std::cerr << "FAIL: " << name << " (expected ParseError, got none)\n";
    } catch (const ParseError&) {
        ++tests_passed;
    } catch (const std::exception& e) {
        ++tests_failed;
        std::cerr << "FAIL: " << name << " (expected ParseError, got: " << e.what() << ")\n";
    }
}

static void check_eval_error(const std::string& name, const std::string& input) {
    try {
        Parser parser(input);
        auto expr = parser.parse();
        expr->evaluate();
        ++tests_failed;
        std::cerr << "FAIL: " << name << " (expected evaluation error, got none)\n";
    } catch (const std::exception&) {
        ++tests_passed;
    }
}

int main() {
    // --- Examples from the README ---
    check("simple sum",       "Sum(3, 5)",                       "(3 + 5)",                       8);
    check("simple mult",      "Mult(4, 5)",                      "(4 * 5)",                       20);
    check("simple div",       "Div(10, 3)",                      "(10 / 3)",                      3);
    check("simple exponent",  "Exponent(2, 10)",                 "(2 ^ 10)",                      1024);
    check("nested sum+exp",   "Sum(Exponent(3, 2), -2)",         "((3 ^ 2) + (-2))",              7);
    check("nested exp+mult",  "Exponent(Mult(3, 2), 2)",         "((3 * 2) ^ 2)",                 36);
    check("nested sum+div",   "Sum(Mult(2, 3), Div(10, 2))",     "((2 * 3) + (10 / 2))",          11);
    check("nested mult+sums", "Mult(Sum(1, 2), Sum(3, 4))",      "((1 + 2) * (3 + 4))",           21);
    check("triple nested",    "Sum(Sum(Sum(1, 2), 3), 4)",       "(((1 + 2) + 3) + 4)",           10);

    // --- Edge cases: numbers ---
    check("zero",             "Sum(0, 0)",                       "(0 + 0)",                       0);
    check("negative numbers", "Sum(-3, -5)",                     "((-3) + (-5))",                 -8);
    check("large exponent",   "Exponent(2, 0)",                  "(2 ^ 0)",                       1);
    check("exponent base 0",  "Exponent(0, 5)",                  "(0 ^ 5)",                       0);
    check("mult by zero",     "Mult(42, 0)",                     "(42 * 0)",                      0);
    check("div truncation",   "Div(7, 2)",                       "(7 / 2)",                       3);
    check("negative div",     "Div(-7, 2)",                      "((-7) / 2)",                    -3);

    // --- Whitespace handling ---
    check("extra spaces",     "Sum( 3 , 5 )",                    "(3 + 5)",                       8);
    check("no spaces",        "Sum(3,5)",                        "(3 + 5)",                       8);
    check("tabs and spaces",  "Sum(\t3\t,\t5\t)",                "(3 + 5)",                       8);
    check("leading/trailing", "  Sum(3, 5)  ",                   "(3 + 5)",                       8);

    // --- Deep nesting ---
    check("deep nesting",
          "Sum(Sum(Sum(Sum(1, 2), 3), 4), 5)",
          "((((1 + 2) + 3) + 4) + 5)",
          15);

    check("mixed deep nesting",
          "Mult(Sum(1, 2), Exponent(Div(10, 5), 3))",
          "((1 + 2) * ((10 / 5) ^ 3))",
          24);

    // --- Error cases: parse errors ---
    check_parse_error("unknown function",       "Foo(1, 2)");
    check_parse_error("missing close paren",    "Sum(3, 5");
    check_parse_error("missing comma",          "Sum(3 5)");
    check_parse_error("missing argument",       "Sum(3,)");
    check_parse_error("empty input",            "");
    check_parse_error("trailing garbage",       "Sum(3, 5) hello");
    check_parse_error("unmatched paren",        "Sum(3, 5))");
    check_parse_error("bare minus",             "-");
    check_parse_error("only open paren",        "(");

    // --- Error cases: evaluation errors ---
    check_eval_error("division by zero",        "Div(10, 0)");
    check_eval_error("negative exponent",       "Exponent(2, -1)");

    // --- Summary ---
    std::cout << "\n" << tests_passed << " passed, " << tests_failed << " failed\n";
    return tests_failed > 0 ? 1 : 0;
}
