using System;
using System.Collections.Generic;
using System.Linq;

// ============================================================
// Fill the bucket - find weak tests with mutation testing
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

// ============================================================
// Test cases
// ============================================================
using Xunit;

public class FillBucketTests
{
    private static void AssertFillResult(
        bool expectedCanFill, Dictionary<int, int> expectedPlan,
        bool resultCanFill, Dictionary<int, int> resultPlan)
    {
        Assert.Equal(expectedCanFill, resultCanFill);
        Assert.Equal(expectedPlan.Count, resultPlan.Count);
        foreach (var (key, value) in expectedPlan)
        {
            Assert.True(resultPlan.ContainsKey(key), $"Missing bucket size {key}");
            Assert.Equal(value, resultPlan[key]);
        }
    }

    // Full tests - check both boolean and fill plan
    [Theory]
    [MemberData(nameof(CanFillBasicData))]
    public void TestCanFillBasic(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> CanFillBasicData()
    {
        yield return new object[] { 10, new[] { 2 }, true, new Dictionary<int, int> { { 2, 5 } } };
        yield return new object[] { 12, new[] { 3, 4 }, true, new Dictionary<int, int> { { 4, 3 } } };
    }

    [Theory]
    [MemberData(nameof(CannotFillBasicData))]
    public void TestCannotFillBasic(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> CannotFillBasicData()
    {
        yield return new object[] { 10, new[] { 3 }, false, new Dictionary<int, int>() };
        yield return new object[] { 10, new[] { 13, 11 }, false, new Dictionary<int, int>() };
    }

    // Weak tests - only check the boolean result, not the plan
    [Theory]
    [MemberData(nameof(CanFillMultiBucketData))]
    public void TestCanFillMultiBucket(int bigBucket, int[] smallBuckets, bool expectedCanFill)
    {
        var (canFill, _) = BucketFiller.CanFill(bigBucket, smallBuckets);
        Assert.Equal(expectedCanFill, canFill);
    }

    public static IEnumerable<object[]> CanFillMultiBucketData()
    {
        yield return new object[] { 8, new[] { 3, 5 }, true };
        yield return new object[] { 11, new[] { 4, 3 }, true };
        yield return new object[] { 11, new[] { 5, 3 }, true };
        yield return new object[] { 111, new[] { 4, 5, 3, 200 }, true };
    }

    [Theory]
    [MemberData(nameof(CannotFillMultiBucketData))]
    public void TestCannotFillMultiBucket(int bigBucket, int[] smallBuckets, bool expectedCanFill)
    {
        var (canFill, _) = BucketFiller.CanFill(bigBucket, smallBuckets);
        Assert.Equal(expectedCanFill, canFill);
    }

    public static IEnumerable<object[]> CannotFillMultiBucketData()
    {
        yield return new object[] { 11, new[] { 6, 3 }, false };
    }
}
