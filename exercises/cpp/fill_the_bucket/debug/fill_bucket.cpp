#include <map>
#include <vector>
#include <algorithm>
#include <ranges>

//============================================================
// Fill the bucket - code to test
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
  std::ranges::sort(small_buckets_sorted); // sorted
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

class FillBucketTest :
    public testing::TestWithParam<
        std::tuple<Bucket, Buckets, bool, FillPlan>
    > {
    // the tuple is for:
    // - big bucket
    // - vector of small buckets
    // - bool - expected result for can fill
    // - map<size_t, size_t> - expected fill plan 
};

TEST_P(FillBucketTest, test_fill_bucket) {
  // Inside a test, access the test parameter with the GetParam() method
  // of the TestWithParam<T> class:
  auto [big_bucket, small_buckets, expected_can_fill, expected_fill_plan] = GetParam();
  auto [result_can_fill, result_fill_plan] = canFill(big_bucket, small_buckets);
  EXPECT_EQ(result_can_fill, expected_can_fill);
  EXPECT_EQ(result_fill_plan, expected_fill_plan);
}

INSTANTIATE_TEST_SUITE_P(CanFillSimple,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{10, Buckets{2}, true, FillPlan{{2, 5}}},
                             std::tuple{8, Buckets{3, 5}, true, FillPlan{{3, 1}, {5, 1}}},
                             std::tuple{11, Buckets{3, 2}, true, FillPlan{{3, 3}, {2, 1}}},
                             std::tuple{11, Buckets{4, 3}, true, FillPlan{{4, 2}, {3, 1}}},
                             std::tuple{11, Buckets{5, 3}, true, FillPlan{{5, 1}, {3, 2}}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CanFillUnsortedSmallBuckets,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{11, Buckets{2, 3}, true, FillPlan{{3, 3}, {2, 1}}},
                             std::tuple{12, Buckets{3, 4}, true, FillPlan{{4, 3}}},
                             std::tuple{111, Buckets{4, 5, 3, 200}, true, FillPlan{{5, 21}, {3, 2}}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CanFillUnsortedDuplicatesSmallBuckets,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{11, Buckets{3, 3, 2}, true, FillPlan{{3, 3}, {2, 1}}},
                             std::tuple{12, Buckets{3, 4, 3, 4}, true, FillPlan{{4, 3}}},
                             std::tuple{111, Buckets{200, 3, 4, 5, 3, 200}, true, FillPlan{{5, 21}, {3, 2}}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CanFillIgnoreZeroSmallBuckets,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{11, Buckets{3, 0, 2}, true, FillPlan{{3, 3}, {2, 1}}},
                             std::tuple{12, Buckets{3, 4, 0}, true, FillPlan{{4, 3}}},
                             std::tuple{111, Buckets{0, 3, 4, 5, 3, 200}, true, FillPlan{{5, 21}, {3, 2}}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CannotFillSimple,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{10, Buckets{3}, false, FillPlan{}},
                             std::tuple{11, Buckets{6, 3}, false, FillPlan{}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CanFillZeroBigBucket,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{0, Buckets{3, 1}, true, FillPlan{}},
                             std::tuple{0, Buckets{}, true, FillPlan{}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CannotFillSmallestBucketIsTooBig,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{10, Buckets{13, 11}, false, FillPlan{}},
                             std::tuple{10, Buckets{13}, false, FillPlan{}}
                            )
                        );

INSTANTIATE_TEST_SUITE_P(CannotFillNoSmallBuckets,
                         FillBucketTest,
                         testing::Values(
                             std::tuple{10, Buckets{}, false, FillPlan{}}
                            )
                        );

// Needed because we don't link with gtest_main
int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
