#include <map>
#include <vector>

using std::map, std::pair, std::vector;

pair<bool, map<size_t, size_t>>
canFill(size_t big_bucket, const vector<size_t>& small_buckets, size_t index = 0) {
  if(big_bucket == 0) return {true, {}};
  if(big_bucket < small_buckets.back()) return {false, {}};
  auto curr = small_buckets[index];
  if(big_bucket % curr == 0) return {true, { {curr, big_bucket / curr} }};
  if(index < small_buckets.size() - 1) {
    auto times = big_bucket / curr + 1;
    do {
      --times;
      auto rest = big_bucket - times * curr;
      auto result = canFill(rest, small_buckets, index + 1);
      if(result.first) {
        result.second[curr] = times;
        return result;
      }
    } while(times > 0);
  }
  return {false, {}};
}


#include <iostream>

int main() {
    auto result = canFill(12, {12});
    std::cout << result.first << '\n';
    for(const auto& p : result.second) {
        std::cout << p.first << ": " << p.second << '\n';        
    }
}
