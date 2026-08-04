using System;
using System.Collections.Generic;
using System.Linq;

// ============================================================
// Fill the bucket - implement the solution
//
// Goal: fill the big bucket using small buckets with the
// minimum number of fill operations.
// A fill operation = using a small bucket of any size once.
// Example: using bucket 7 twice and bucket 2 three times
//          = 5 fill operations
//
// Requirements:
// - Handle unsorted input (sort internally)
// - Handle duplicate bucket sizes (treat as unique)
// - Handle zeros in small_buckets (ignore them)
// - big_bucket == 0 -> always fillable with empty plan
// - empty small_buckets with big_bucket > 0 -> not fillable
//
// Examples:
//   CanFill(10, [2])       -> (true,  {{2, 5}})
//   CanFill(8,  [3, 5])    -> (true,  {{3, 1}, {5, 1}})
//   CanFill(11, [3, 2])    -> (true,  {{3, 3}, {2, 1}})
//   CanFill(12, [3, 4])    -> (true,  {{4, 3}})
//   CanFill(10, [3])       -> (false, {})
//   CanFill(0,  [3, 1])    -> (true,  {})
//   CanFill(10, [])        -> (false, {})
// ============================================================

public static class BucketFiller
{
    public static (bool CanFill, Dictionary<int, int> Plan) CanFill(
        int bigBucket, IEnumerable<int> smallBuckets)
    {
        // TODO: implement
        return (false, new Dictionary<int, int>());
    }
}

class Program
{
    static void Main()
    {
        var examples = new (int Big, int[] Smalls)[]
        {
            (10, new[] { 2 }),
            (8, new[] { 3, 5 }),
            (11, new[] { 3, 2 }),
            (12, new[] { 3, 4 }),
            (10, new[] { 3 }),
            (0, new[] { 3, 1 }),
            (10, Array.Empty<int>()),
        };

        foreach (var (big, smalls) in examples)
        {
            var (canFill, plan) = BucketFiller.CanFill(big, smalls);
            var status = canFill ? "can fill" : "cannot fill";
            var planStr = string.Join(", ", plan.Select(kv => $"{kv.Key} x {kv.Value}"));
            Console.WriteLine($"{big} with [{string.Join(", ", smalls)}]: {status}"
                + (plan.Any() ? $" -> {{{planStr}}}" : ""));
        }
    }
}
