CXX = clang++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  SDKROOT := $(shell xcrun --show-sdk-path)
  CXXFLAGS += -isysroot $(SDKROOT) -I$(SDKROOT)/usr/include/c++/v1
endif

TARGET = expr_eval
SRCS = main.cpp parser.cpp expr.cpp
OBJS = $(SRCS:.cpp=.o)

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp expr.h parser.h
	$(CXX) $(CXXFLAGS) -c $<

clean:
	rm -f $(OBJS) $(TARGET)

test: $(TARGET)
	@echo "Sum(3, 5)" | ./$(TARGET)
	@echo "Mult(4, 5)" | ./$(TARGET)
	@echo "Div(10, 3)" | ./$(TARGET)
	@echo "Exponent(2, 10)" | ./$(TARGET)
	@echo "Sum(Exponent(3, 2), -2)" | ./$(TARGET)
	@echo "Exponent(Mult(3, 2), 2)" | ./$(TARGET)
	@echo "Sum(Mult(2, 3), Div(10, 2))" | ./$(TARGET)
	@echo "Mult(Sum(1, 2), Sum(3, 4))" | ./$(TARGET)
	@echo "Sum(Sum(Sum(1, 2), 3), 4)" | ./$(TARGET)
