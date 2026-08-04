using System;
using System.Collections.Generic;
using System.Linq;

// ============================================================
// Fill the bucket - add unit tests
// Goal: fill the big bucket with minimum fill operations
// a fill operation = using a small bucket of any size
// example: using 7 twice + 2 three times = 5 operations
// @Author: Amir Kirsh
// ============================================================

public static class BucketFiller
{
    private static (bool CanFill, Dictionary<int, int> Plan) CanFillRecursive(
        int bigBucket, List<int> smallBuckets, int index)
    {
        if (bigBucket < smallBuckets[^1])
            return (false, new Dictionary<int, int>());
        var curr = smallBuckets[index];
        if (bigBucket % curr == 0)
            return (true, new Dictionary<int, int> { { curr, bigBucket / curr } });
        if (index < smallBuckets.Count - 1)
        {
            var times = bigBucket / curr + 1;
            while (times > 0)
            {
                times--;
                var rest = bigBucket - times * curr;
                var (canFill, fillPlan) = CanFillRecursive(rest, smallBuckets, index + 1);
                if (canFill)
                {
                    if (times > 0) fillPlan[curr] = times;
                    return (true, fillPlan);
                }
            }
        }
        return (false, new Dictionary<int, int>());
    }

    public static (bool CanFill, Dictionary<int, int> Plan) CanFill(
        int bigBucket, IEnumerable<int> smallBuckets)
    {
        if (bigBucket == 0)
            return (true, new Dictionary<int, int>());
        var bucketsList = smallBuckets.ToList();
        if (!bucketsList.Any())
            return (false, new Dictionary<int, int>());
        var bucketsSorted = bucketsList.Distinct().OrderByDescending(x => x).ToList();
        if (bucketsSorted[^1] == 0) bucketsSorted.RemoveAt(bucketsSorted.Count - 1);
        return CanFillRecursive(bigBucket, bucketsSorted, 0);
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
