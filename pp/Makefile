# =============================================================================
# Makefile for High-Performance Parallel Graph Analysis Framework
# Parallel BFS Benchmarks & Work-Stealing Memory Trace Logger
# Standard: C99
# =============================================================================

TARGET = graph_analyzer
SRCS = main.c graph.c
OBJS = $(SRCS:.c=.o)
HEADERS = graph.h

# Automatic OS and OpenMP Detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    # macOS: Use Clang with Homebrew libomp
    CC ?= clang
    OMP_FLAGS = -Xpreprocessor -fopenmp -isystem /opt/homebrew/opt/libomp/include
    OMP_LIBS  = -L/opt/homebrew/opt/libomp/lib -lomp
else
    # Linux: Use GCC with native OpenMP
    CC ?= gcc
    OMP_FLAGS = -fopenmp
    OMP_LIBS  = -fopenmp
endif

# Release compilation flags
CFLAGS = -std=c99 -Wall -Wextra -pedantic -O3 -march=native $(OMP_FLAGS)
LDFLAGS = $(OMP_LIBS)

# Debug and memory sanitization flags
DEBUG_FLAGS = -std=c99 -Wall -Wextra -pedantic -g -fsanitize=address,undefined -O1 $(OMP_FLAGS)

.PHONY: all run benchmark trace debug clean help

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $(TARGET) $(LDFLAGS)

%.o: %.c $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $@

# Run the default analyzer (loading, verification, and BFS benchmark)
run: $(TARGET)
	./$(TARGET) Amazon0302.txt

# Run pure timing benchmark for Strategies A, B, and C
benchmark: $(TARGET)
	./$(TARGET) Amazon0302.txt --benchmark

# Generate training_trace.txt and testing_trace.txt using Strategy C (Work-Stealing)
trace: $(TARGET)
	./$(TARGET) Amazon0302.txt --trace --root 0 --test-root 1

# Build with AddressSanitizer and debug symbols to guarantee zero memory leaks
debug: clean
	$(CC) $(DEBUG_FLAGS) $(SRCS) -o $(TARGET)_debug $(LDFLAGS)
	./$(TARGET)_debug Amazon0302.txt --benchmark

clean:
	rm -f $(OBJS) $(TARGET) $(TARGET)_debug
	rm -rf *.dSYM
	rm -f training_trace.txt testing_trace.txt

help:
	@echo "Available targets:"
	@echo "  make            - Build optimized release binary ($(TARGET))"
	@echo "  make run        - Build and execute default analysis & benchmarks"
	@echo "  make benchmark  - Run pure timing BFS benchmarks for Strategies A, B, and C"
	@echo "  make trace      - Generate training_trace.txt and testing_trace.txt using Strategy C"
	@echo "  make debug      - Build and test with AddressSanitizer and debug symbols"
	@echo "  make clean      - Remove object files, binaries, and trace files"
