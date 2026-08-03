#include <map>
#include <vector>
#include <algorithm>
#include <ranges>

//============================================================
// Fill the bucket - add unit tests
// Goal: fill the big bucket with minimum fill operations
// a fill operation = using a small bucket of any size
// example: using 7 twice + 2 three times = 5 operations
// @Author: Amir Kirsh
//============================================================

using std::map, std::pair, std::vector, std::ranges::range;

using FillPlan = map<size_t, size_t>;
using FillResult = pair<bool, FillPlan>;
using Bucket = size_t;

FillResult canFillRecursive(Bucket big_bucket, const vector<Bucket>& small_buckets, size_t index) {
  if(big_bucket < small_buckets.back()) return {false, {}};
  auto curr = small_buckets[index];
  if(big_bucket % curr == 0) return {true, { {curr, big_bucket / curr} }};
  if(index < small_buckets.size() - 1) {
    auto times = big_bucket / curr + 1;
    do {
      --times;
      auto rest = big_bucket - times * curr;
      auto [can_fill, fill_plan] = canFillRecursive(rest, small_buckets, index + 1);
      if(can_fill) {
        if(times > 0) fill_plan[curr] = times;
        return {true, fill_plan};
      }
    } while(times > 0);
  }
  return {false, {}};
}

FillResult canFill(Bucket big_bucket, range auto&& small_buckets) {
  if(big_bucket == 0) return {true, {}};
  if(small_buckets.empty()) return {false, {}};
  // sort a copied vector of the small buckets container
  auto small_buckets_sorted = std::vector(small_buckets.begin(), small_buckets.end());
  std::ranges::sort(small_buckets_sorted, std::greater<>()); // sorted descending
  // remove duplicates
  auto [new_end, end] = std::ranges::unique(small_buckets_sorted);
  // erase the duplicates from the container
  small_buckets_sorted.erase(new_end, end);
  // remove trailing zero if exists
  if(small_buckets_sorted.back() == 0) small_buckets_sorted.pop_back();
  // call the recursive helper function, starting from index 0
  return canFillRecursive(big_bucket, small_buckets_sorted, 0);
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
