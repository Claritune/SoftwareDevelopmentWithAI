#include <map>
#include <vector>
#include <algorithm>
#include <ranges>

//============================================================
// Fill the bucket - find weak tests with mutation testing
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

//============================================================
// Test cases
//============================================================
#include <tuple>
#include <list>
#include "gtest/gtest.h"

using std::list;

using Buckets = list<Bucket>;

//------------------------------------------------------------
// Full tests - check both can_fill and fill_plan
//------------------------------------------------------------
class FillBucketTest :
    public testing::TestWithParam<
        std::tuple<Bucket, Buckets, bool, FillPlan>
    > {
};

TEST_P(FillBucketTest, test_fill_bucket) {
  auto [big_bucket, small_buckets, expected_can_fill, expected_fill_plan] = GetParam();
  auto [result_can_fill, result_fill_plan] = canFill(big_bucket, small_buckets);
  EXPECT_EQ(result_can_fill, expected_can_fill);
  EXPECT_EQ(result_fill_plan, expected_fill_plan);
}

INSTANTIATE_TEST_SUITE_P(CanFillBasic,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{10, Buckets{2}, true, FillPlan{{2, 5}}},
                             std::tuple{12, Buckets{3, 4}, true, FillPlan{{4, 3}}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CannotFillBasic,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{10, Buckets{3}, false, FillPlan{}},
                             std::tuple{10, Buckets{13, 11}, false, FillPlan{}}
                            )
                        );

//------------------------------------------------------------
// Weak tests - only check the boolean result, not the plan
//------------------------------------------------------------
class FillBucketCanFillOnlyTest :
    public testing::TestWithParam<
        std::tuple<Bucket, Buckets, bool>
    > {
};

TEST_P(FillBucketCanFillOnlyTest, test_can_fill_only) {
  auto [big_bucket, small_buckets, expected_can_fill] = GetParam();
  auto [result_can_fill, result_fill_plan] = canFill(big_bucket, small_buckets);
  EXPECT_EQ(result_can_fill, expected_can_fill);
}

INSTANTIATE_TEST_SUITE_P(CanFillMultiBucket,
                         FillBucketCanFillOnlyTest,
                         testing::Values(
                             std::tuple{8, Buckets{3, 5}, true},
                             std::tuple{11, Buckets{4, 3}, true},
                             std::tuple{11, Buckets{5, 3}, true},
                             std::tuple{111, Buckets{4, 5, 3, 200}, true}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CannotFillMultiBucket,
                         FillBucketCanFillOnlyTest,
                         testing::Values(
                             std::tuple{11, Buckets{6, 3}, false}
                            )
                        );

// Needed because we don't link with gtest_main
int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
