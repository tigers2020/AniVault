# 1 Introduction
You will be revising the chained hash table implementation of a map to instead implement a linked hash set. Sets, you may recall, are just maps without values. The "linked" adjective signifies that there is an additional ordering of the keys. When you iterate over the set, the keys are revealed in the order that they were added to the set.

First we will study some properties of hash functions.
In both open addressing and chaining, collisions degrade performance. Many keys mapping to the same location in a hash table result in a linear search. Clearly, good hash functions should minimize the number of collisions. How might the "goodness" or "badness" of a given hash function be measured by looking at the hash table after it has loaded its entries?

This may be best explained by an example. Look at Figure 1. A program entered 5 keys - A, B, C, D, and E into a hash table of length 10.

#### Bad Hash Function.
```
0
1 -> A C D
2
3
4 -> B E
5
...
```


#### Good Hash Function
```
0 -> A
1
2
3 -> D
4 -> B
5
6 -> C
...
9 -> E
```

`Figure 1: Two hypothetical hash functions applied to the same hash table array and the same stream of keys being put in the table.`

The figure shows the application of two different hash functions to this scenario. Clearly, the second function is better, but how can you quantify that based on what you can measure in the tables?

# 2 Activity 1: Problem Solving
1. Assume a chaining hash table of size 12 and a string-to-integer conversion function that simply adds their ordinal letter values together. (a=0, b=1, etc.) Draw what your hash table would look like after putting the following keys into it. As an example of the encoding, here is how the first key converts to a number.
```
'l', 'a', 'd'  -> 11 + 0 + 3 = 14
```

(a) "lad"
(b) "but"
(c) "is"
(d) "chin"

2. Show the order the keys would be displayed if following the chains from top to bottom and left to right.
3. Write code that implements a hash function that sums up the ordinal values of the characters scaled by 31 to the power of the index at which that character occurs in the string, e.g.:
```
'l','a','d' -> ord('l') + ord('a')*31 + ord('d')*31*31
```

4. Figure 2 in the implementation section illustrates the data structure design you will follow for implementing the linked hash table. Following this design:

    (a) Modify the left table in Figure 1 so that the insertion order is maintained.

    (b) Write pseudo-code for the remove(key) operation.


# 3. Activity 2: Implementation

Your data structure design is required to look like the diagram in Figure 2. That is, you build a chained hash table with keys only, no values, and the entry nodes have two additional references: previous and link(next) node links. This means that the ordering is done using the technique of a doubly linked list that overlays on top of the existing nodes needed for the bucket chains.

image.png
Figure 2: The linked hash table design. Structure shown is developed from entering the following words to the set:
```
batman has lots of gizmos on his belt.
```
