using System;
using System.Collections.Generic;
using System.Linq;

// ============================================================
// Fill the bucket - find and fix the bugs
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
        var bucketsSorted = bucketsList.Distinct().OrderBy(x => x).ToList();
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

    [Theory]
    [MemberData(nameof(CanFillSimpleData))]
    public void TestCanFillSimple(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> CanFillSimpleData()
    {
        yield return new object[] { 10, new[] { 2 }, true, new Dictionary<int, int> { { 2, 5 } } };
        yield return new object[] { 8, new[] { 3, 5 }, true, new Dictionary<int, int> { { 3, 1 }, { 5, 1 } } };
        yield return new object[] { 11, new[] { 3, 2 }, true, new Dictionary<int, int> { { 3, 3 }, { 2, 1 } } };
        yield return new object[] { 11, new[] { 4, 3 }, true, new Dictionary<int, int> { { 4, 2 }, { 3, 1 } } };
        yield return new object[] { 11, new[] { 5, 3 }, true, new Dictionary<int, int> { { 5, 1 }, { 3, 2 } } };
    }

    [Theory]
    [MemberData(nameof(CanFillUnsortedData))]
    public void TestCanFillUnsortedSmallBuckets(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> CanFillUnsortedData()
    {
        yield return new object[] { 11, new[] { 2, 3 }, true, new Dictionary<int, int> { { 3, 3 }, { 2, 1 } } };
        yield return new object[] { 12, new[] { 3, 4 }, true, new Dictionary<int, int> { { 4, 3 } } };
        yield return new object[] { 111, new[] { 4, 5, 3, 200 }, true, new Dictionary<int, int> { { 5, 21 }, { 3, 2 } } };
    }

    [Theory]
    [MemberData(nameof(CanFillDuplicatesData))]
    public void TestCanFillDuplicatesSmallBuckets(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> CanFillDuplicatesData()
    {
        yield return new object[] { 11, new[] { 3, 3, 2 }, true, new Dictionary<int, int> { { 3, 3 }, { 2, 1 } } };
        yield return new object[] { 12, new[] { 3, 4, 3, 4 }, true, new Dictionary<int, int> { { 4, 3 } } };
        yield return new object[] { 111, new[] { 200, 3, 4, 5, 3, 200 }, true, new Dictionary<int, int> { { 5, 21 }, { 3, 2 } } };
    }

    [Theory]
    [MemberData(nameof(CanFillIgnoreZerosData))]
    public void TestCanFillIgnoreZeros(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> CanFillIgnoreZerosData()
    {
        yield return new object[] { 11, new[] { 3, 0, 2 }, true, new Dictionary<int, int> { { 3, 3 }, { 2, 1 } } };
        yield return new object[] { 12, new[] { 3, 4, 0 }, true, new Dictionary<int, int> { { 4, 3 } } };
        yield return new object[] { 111, new[] { 0, 3, 4, 5, 3, 200 }, true, new Dictionary<int, int> { { 5, 21 }, { 3, 2 } } };
    }

    [Theory]
    [MemberData(nameof(CannotFillSimpleData))]
    public void TestCannotFillSimple(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> CannotFillSimpleData()
    {
        yield return new object[] { 10, new[] { 3 }, false, new Dictionary<int, int>() };
        yield return new object[] { 11, new[] { 6, 3 }, false, new Dictionary<int, int>() };
    }

    [Theory]
    [MemberData(nameof(ZeroBigBucketData))]
    public void TestCanFillZeroBigBucket(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> ZeroBigBucketData()
    {
        yield return new object[] { 0, new[] { 3, 1 }, true, new Dictionary<int, int>() };
        yield return new object[] { 0, Array.Empty<int>(), true, new Dictionary<int, int>() };
    }

    [Theory]
    [MemberData(nameof(SmallestBucketTooBigData))]
    public void TestCannotFillSmallestBucketTooBig(int bigBucket, int[] smallBuckets,
        bool expectedCanFill, Dictionary<int, int> expectedPlan)
    {
        var (canFill, plan) = BucketFiller.CanFill(bigBucket, smallBuckets);
        AssertFillResult(expectedCanFill, expectedPlan, canFill, plan);
    }

    public static IEnumerable<object[]> SmallestBucketTooBigData()
    {
        yield return new object[] { 10, new[] { 13, 11 }, false, new Dictionary<int, int>() };
        yield return new object[] { 10, new[] { 13 }, false, new Dictionary<int, int>() };
    }

    [Fact]
    public void TestCannotFillNoSmallBuckets()
    {
        var (canFill, plan) = BucketFiller.CanFill(10, Array.Empty<int>());
        Assert.False(canFill);
        Assert.Empty(plan);
    }
}
