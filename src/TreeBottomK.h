#ifndef TREEBOTTOMK_H
#define TREEBOTTOMK_H

#include <bits/stdc++.h>
#include "hash.cpp"
#include "Sketch.cpp"
#include "Utils.cpp"

using namespace std;

#define num uint32_t
#define NUM_MAX UINT32_MAX

/**
 * Fully dynamic bottom-k sketch.
 *
 * The sketch stores the l hash values in two ordered partitions:
 * bottom contains the k smallest values, while rest contains the remaining
 * l-k values. Only finite hash values are stored.
 */
class TreeBottomK : public Sketch
{
private:
    // Universe size used by the hash function configuration.
    num U;
    
    // Number of finite values exposed by getBottomK().
    int k;

    // Maximum number of finite hashes retained by the two partitions.
    int l;

    // The k smallest retained hashes.
    multiset<num> bottom;

    // The remaining retained hashes.
    multiset<num> rest;

    // Largest hash currently retained when the buffer is full.
    num delta = NUM_MAX;

    //First value of the current bottom-k; kept for Sketch compatibility.
    num signature = NUM_MAX;

    // Hash function used for every inserted element.
    Hash<num> *hashFunction;

    // Whether this object owns hashFunction and must delete it.
    bool doFreeHash;

    // Enables storage of original values for recovery after a fault.
    bool explicitSet;

    // Original values currently inserted, used by fault().
    unordered_set<num> elements;

public:
    TreeBottomK()
        : TreeBottomK(1, 1, 1, new TabulationHash<num>(), true, true)
    {
    }

    TreeBottomK(int k, int l, num U, bool explicitSet = true)
        : TreeBottomK(
              k,
              l,
              U,
              new TabulationHash<num>(),
              explicitSet,
              true)
    {
    }

    TreeBottomK(
        int k,
        int l,
        num U,
        Hash<num> *hashFunction,
        bool explicitSet = true,
        bool doFreeHash = false)
        : U(U),
          k(k),
          l(l),
          hashFunction(hashFunction),
          doFreeHash(doFreeHash),
          explicitSet(explicitSet)
    {
    }

    ~TreeBottomK()
    {
        if (doFreeHash)
            delete hashFunction;
    }

    num hash(num x) const
    {
        // The sketch stores hashes, not the original values.
        return (*hashFunction)(x);
    }

    void insert(num x)
    {
        insert(x, true);
    }

    void insert(num x, bool insertIntoSet)
    {
        // Keep the original value only when recovery is enabled.
        if (explicitSet && insertIntoSet)
            elements.insert(x);

        const num h = hash(x);
        const size_t retained = bottom.size() + rest.size();
        if (h > delta)
            return;

        // If the buffer is full, evict its largest value before inserting h.
        if (retained == static_cast<size_t>(l))
        {
            auto maximum = rest.empty() ? prev(bottom.end()) : prev(rest.end());
            if (rest.empty()) //case k == l
                bottom.erase(maximum);
            else
                rest.erase(maximum);
        }

        // Insert into the partition selected by the current boundary.
        if (bottom.empty() || h <= *bottom.rbegin())
            bottom.insert(h);
        else
            rest.insert(h);

        rebalancePartitions();

        // The minimum and maximum retained hashes are updated after insertion.
        UpdateDeltaAndSignature();
    }

    bool remove(num x)
    {
        // Removing an original value also removes it from the recovery set.
        if (explicitSet)
            elements.erase(x);

        const num h = hash(x);
        // When full, hashes larger than delta are not part of the sample.
        if (h > delta)
            return false;

        // find() is logarithmic and returns one occurrence when hashes repeat.
        auto element = bottom.find(h);
        if (element != bottom.end())
            bottom.erase(element);
        else
        {
            element = rest.find(h);
            if (element == rest.end())
                return false;
            rest.erase(element);
        }
        const size_t retained = bottom.size() + rest.size();
        if (retained < static_cast<size_t>(k) && delta != NUM_MAX)
        {
            // The retained sample is no longer sufficient to recover deletion.
            resetBuffer();
            if (explicitSet)
                fault();
            return true;
        }

        rebalancePartitions();
        UpdateDeltaAndSignature();
        return false;
    }

    void fault()
    {
        // Reinsert all known values without adding them a second time.
        for (num element : elements)
            insert(element, false);
    }

    num *getSignature()
    {
        // Return the address of the cached minimum hash.
        return &signature;
    }

    const multiset<num> *getBottomK() const
    {
        // Return the owned bottom-k partition without allowing modifications.
        return &bottom;
    }

    static double bottomKSimilarity(
        const TreeBottomK *A,
        const TreeBottomK *B)
    {
        const multiset<num> *bottomA = A->getBottomK();
        const multiset<num> *bottomB = B->getBottomK();
        multiset<num> intersectionSet;
        multiset<num> unionSet;


        // The standard algorithms preserve multiset multiplicities:
        // intersection keeps min(countA, countB), union keeps max(...).
        set_intersection(
            bottomA->begin(),
            bottomA->end(),
            bottomB->begin(),
            bottomB->end(),
            inserter(intersectionSet, intersectionSet.end()));

        const size_t intersectionSize = intersectionSet.size();
        const size_t unionSize = min((bottomA->size() + bottomB->size() - intersectionSize), 
            static_cast<size_t>(A->k));
        
        if (unionSize == 0)
            return 0.0;
        else
            return static_cast<double>(intersectionSize) / static_cast<double>(unionSize);
    }

    void resetBuffer()
    {
        // Empty both partitions; fault() repopulates them from elements.
        bottom.clear();
        rest.clear();
        delta = NUM_MAX;
        signature = NUM_MAX;
    }

private:
    void rebalancePartitions()
    {
        while (bottom.size() > static_cast<size_t>(k))
        {
            auto maximum = prev(bottom.end());
            rest.insert(*maximum);
            bottom.erase(maximum);
        }
        while (bottom.size() < static_cast<size_t>(k) && !rest.empty())
        {
            auto minimum = rest.begin();
            bottom.insert(*minimum);
            rest.erase(minimum);
        }
        while (!bottom.empty() && !rest.empty() &&
               *bottom.rbegin() > *rest.begin())
        {
            auto bottomMaximum = prev(bottom.end());
            auto restMinimum = rest.begin();
            const num lower = *restMinimum;
            const num higher = *bottomMaximum;
            bottom.erase(bottomMaximum);
            rest.erase(restMinimum);
            bottom.insert(lower);
            rest.insert(higher);
        }
    }

    void UpdateDeltaAndSignature()
    {
        signature = bottom.empty() ? NUM_MAX : *bottom.begin();
        const size_t retained = bottom.size() + rest.size();
        const auto maxValue = rest.empty() ? (bottom.empty() ? NUM_MAX : *bottom.rbegin()) : *rest.rbegin();
        if(retained == static_cast<size_t>(l)){
            delta = maxValue;
        }else{
            delta = delta == NUM_MAX ? NUM_MAX : maxValue;
        }         
    }
};

#endif
