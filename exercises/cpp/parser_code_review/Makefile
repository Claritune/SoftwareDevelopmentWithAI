CXX      := g++-15
CXXFLAGS := -std=c++17 -Wall -Wextra -Wpedantic

SRCS     := expr.cpp parser.cpp
OBJS     := $(SRCS:.cpp=.o)

.PHONY: all clean test

all: expr_eval

expr_eval: main.o $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

tests: tests.o $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

test: tests
	./tests

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -f *.o expr_eval tests
