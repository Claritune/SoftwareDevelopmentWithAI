#!/bin/sh
# Rebuilds the reference output from the C++ implementation.
# Usage (from the project root): sh tests/golden/capture.sh [path/to/cats]
set -u
CATS="${1:-../../cpp/cats-vs-mutants/build/cats}"
OUT=tests/golden

run() {  # run <name> <script path>
    "$CATS" --headless "$2" > "$OUT/$1.stdout" 2> "$OUT/$1.stderr"
    echo $? > "$OUT/$1.exitcode"
}

run demo scripts/demo.txt
for script in "$OUT"/scripts/*.txt; do
    run "$(basename "$script" .txt)" "$script"
done
run missing_file "$OUT/scripts/does_not_exist.txt"
