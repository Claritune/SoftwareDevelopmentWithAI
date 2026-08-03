#include <map>
#include <vector>
#include <algorithm>
#include <ranges>

//============================================================
// Fill the bucket - implement the solution
//
// Goal: fill the big bucket using small buckets with the
// minimum number of fill operations.
// A fill operation = using a small bucket of any size once.
// Example: using bucket 7 twice and bucket 2 three times
//          = 5 fill operations
//
// Requirements:
// - Accept any range container for small_buckets (vector,
//   list, etc.)
// - Handle unsorted input (sort internally)
// - Handle duplicate bucket sizes (treat as unique)
// - Handle zeros in small_buckets (ignore them)
// - big_bucket == 0 -> always fillable with empty plan
// - empty small_buckets with big_bucket > 0 -> not fillable
//
// Examples:
//   canFill(10, {2})       -> {true,  {{2, 5}}}
//   canFill(8,  {3, 5})    -> {true,  {{3, 1}, {5, 1}}}
//   canFill(11, {3, 2})    -> {true,  {{3, 3}, {2, 1}}}
//   canFill(12, {3, 4})    -> {true,  {{4, 3}}}
//   canFill(10, {3})       -> {false, {}}
//   canFill(0,  {3, 1})    -> {true,  {}}
//   canFill(10, {})        -> {false, {}}
//============================================================

using std::map, std::pair, std::vector, std::ranges::range;

using FillPlan = map<size_t, size_t>;
using FillResult = pair<bool, FillPlan>;
using Bucket = size_t;

FillResult canFill(Bucket big_bucket, range auto&& small_buckets) {
  // TODO: implement
  return {false, {}};
}

#include <iostream>

int main() {
    auto print_result = [](Bucket big, const FillResult& result) {
        std::cout << big << ": " << (result.first ? "can fill" : "cannot fill") << '\n';
        for(const auto& [bucket, count] : result.second) {
            std::cout << "  bucket " << bucket << " x " << count << '\n';
        }
    };

    print_result(10, canFill(10, std::vector<Bucket>{2}));
    print_result(8,  canFill(8,  std::vector<Bucket>{3, 5}));
    print_result(11, canFill(11, std::vector<Bucket>{3, 2}));
    print_result(12, canFill(12, std::vector<Bucket>{3, 4}));
    print_result(10, canFill(10, std::vector<Bucket>{3}));
    print_result(0,  canFill(0,  std::vector<Bucket>{3, 1}));
    print_result(10, canFill(10, std::vector<Bucket>{}));
}
