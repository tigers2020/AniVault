Computational Problem Solving CSCI-603
Counting Words Using Hashing Lecture
10/15/2023
1 Problem
Suppose that we want to read a text file, count the number of times each word appears,
and provide clients with quick answers to whether or not a word appears and how many
times the word appears.
Let’s review what data structures might be candidate choices for solving this problem.
One choice would be to use linked lists of (word, count) pairs. As we read through the
text we could store a (word, count) pair in a linked list that is kept sorted by word. We
could use a linear search to look for each word, and then either insert a new entry if the
word is new, or update the count if the word is already in the list. The search for the
word’s entry is an O(N) operation. After the search operation, inserting or updating an
entry could be done in constant time(O(1)).
Another choice would be to use arrays to store the (word, count) pairs. An array has
efficient look-up; array access is an O(1) operation independent of the array size or number
of elements stored. If we could use a word as the index and keep the array sorted by word,
a binary search and update of an existing entry would require O(log(N)) time. However,
inserting a new word would require O(N) time to move existing entries. For example, to
add a word at the front of the array, all of the (word, count) pairs must be moved forward
one location to maintain the sorted order.
We would like to be able to quickly insert new words, update existing counts and search
for words. For search, we need a fast way to get from a string, the word to its associated
count. For insert or update, we need a fast way to add or change a (word, count) pair.
In the general case, we would like to be able to delete entries fast, but deletion is not a
capability required for a word counting program.
The type of data structure we want is known as a map, which stores a set of (key, value)
pairs. For our problem, the (key, value) pairs are (word, count) pairs, where each word in
the text is the unique key for a map entry, and count is the value that counts the word
occurrences.
1
2 Solution Design and Analysis
2.1 The Python Dictionary
You have already learned about the Python dict, or dictionary, class. The key for a
Python dictionary must be hashable. To be hashable, an element must be encodable to
an integer. Hashing, of course, is the main topic for this lecture. One consequence of
hashability is that the element must not be mutable; otherwise, its encoding will not be
constant.
The value in the (key, value) pair may be any value. Access, insertion, update and deletion
of a value requires use of the key associated with that value.
The hashing tables and hash maps we will create will have the same properties as dict.
However, we will not be using the indexing syntax. (The textbook does so by defining
methods getitem and setitem .
2.2 Hash Table Operations, Pseudo-code and Design Issues/Decisions
In its simplest form a hash table implements a set over its keys. A hash table can be the
basis of a map structure if there is storage for a value with each and every key in the
table.
In either case a hash table is an array that we access using strings or other
hashable objects. What makes a hash table’s design interesting is the way that it
converts objects into array indices. We define a hash function to produce a mapping from
keys to locations in an array, the hash table storage device. We convert words represented
as strings to hash codes that can be transformed into indices for the hash table array.
The hash table array has a fixed number of locations, all of which are initially ‘empty’.
These empty locations might be set to None or something else, depending on the specifics
of how the hash table works. Here are the major operations on a hash table used as a
map:
 put( table, key, value ) -> NoneType : Insert or update a (key,value) pair
into the hash table. The insertion operation updates and replaces any value that
previously may have been associated with the given key.
 get( table, key ) -> AnyType : Access a value by supplying its key to the hash
table.
 contains( table, key ) -> bool : Query whether or not a key exists in the
table.
 delete( table, key ) -> NoneType : Delete the entry for a given key. (The delete
operation may also be named remove.) (Note that our problem does not require implementing a delete operation.)
See the abstract class definition in map.py.
2
The next group of algorithms describe how hash tables in general implement maps. Each
one calls the provided hash function to obtain an integer hash code that specifies the
index location of the entry in the hash table. The only real difference between the algorithms is what they do when they have to deal with two keys being hashed to the same
place in the table. Pointing two keys to the same table index is called a collision.
Function contains( hashTable, key )
hashCode = hash_function( key )
if there is a Valid entry at hashTable[ hashCode ],
if the key matches the entry’s key,
return true
otherwise
Issue -- has there been a "collision"?
Special action required.
otherwise return false
Function get( hashTable, key )
hashCode = hash_function( key )
entry = hashTable[ hashCode ]
if there is a Valid entry at hashTable[ hashCode ],
if entry’s key matches key,
return entry’s value
otherwise
Issue -- has there been a "collision"?
Special action required.
otherwise
ERROR -- the requested key is not present
Function put( hashTable, key, value )
hashCode = hash_function( key )
if there is no Valid entry at the hashCode index in the hash table,
put a new entry( key,value ) at hashTable[ hashCode ]
otherwise
entry = hashTable[ hashCode ]
if entry’s key matches key
update entry’s value to value
otherwise
Special action required.
The purpose of the hashing function is to scatter the entries throughout the array and
decrease the need to handle collisions. Designing a hash table data structure involves
these activities: designing a hashing function that spreads out the data entries as evenly
as possible, and deciding how to handle the collisions that may occur when more than
one entry hashes to the same location.
3
2.3 Designing Hash Functions
2.3.1 Representing String Keys as Natural Numbers
Most hash functions are designed to produce members of the set of the natural numbers
N = {0, 1, 2, . . .}, and we need a way to convert our words to natural numbers. As an
example, let’s just consider words consisting of exactly three lower-case letters. If we use
the ordinal positions of the letters in the alphabet (’a’ is 0, ’z’ is 25), we can compute
hashes for our 3-letter words as follows using a function we will call numid.
String s numid(s)
aaa 0 × 262 + 0 × 261 + 0 × 260 = 0
aab 0 × 262 + 0 × 261 + 1 × 260 = 1
. . .
baa 1 × 262 + 0 × 261 + 0 × 260 = 676
bab 1 × 262 + 0 × 261 + 1 × 260 = 677
bac 1 × 262 + 0 × 261 + 2 × 260 = 678
. . .
caa 2 × 262 + 0 × 261 + 0 × 260 = 1352
cab 2 × 262 + 0 × 261 + 1 × 260 = 1353
. . .
zzz 25 × 262 + 25 × 261 + 25 × 260 = 17575
The three-letter key set may be understood as a base-26 numbering system. As shown in
the table above, we simply enumerate every possible string of three characters, increasing
letter values from the right end of the string:
aaa, aab, aac, aad, . . . , aba, abb, . . . , baa, bab, . . . , zzz
For words of maximum length W, the number of possible lower case words is 26W . For a
length of W = 10 characters, there are 141,167,095,653,376 possible identifiers; that’s 141
trillion!
If we use numid as the hash function with W = 10, the hash table needs one array
location for every possible lower-case, ten character string to obtain optimal O(1) search
performance. However, it is clearly infeasible to allocate a table with trillions of entries,
and it does not solve the problem of hashing a string of arbitrary length!
What if we generalize to strings of arbitrary length and choose a sub-sequence of three
letters on which to apply our conversion function? Computing a number based on the last
few letters would fail because many strings have the same last few letters. Using the first
few letters is also a problem because many strings start with the same prefix.
Consequently, many good string hash functions use all the letters. A long string generates
a very large number, and modular arithmetic limits values to the size of the table.
2.3.2 The Division Method for Hashing
One way to reduce storage needs is to shrink the capacity for the table, apply a function
to divide a key’s hash code by the capacity of the table, and produce the remainder as
4
the word index (location). Using the modulus operator, we process the return value of
hash( word ), the hash code, so that it will lie within the acceptable range of indices for
the smaller, hash table array.
For example, given the word ‘cab’ as a key, the numeric value is 1353. If we create a hash
table of capacity 1000, then:
hdiv(
0
cab0
) = numid(
0
cab0
) % 1000 = 1353 % 1000 = 353
and the entry for the key ‘cab’ would be stored at index 353 in the hash table.
2.4 Handling Collisions
The shrunken table in the preceding example works as long as no other key hashes to
location 353. If we insert an entry with the key value of ‘anp’ however, then
hdiv(
0
anp0
) = numid(
0
anp0
) % 1000 = (0 × 262 + 13 × 261 + 15 × 260
) % 1000 = 353
and we have a collision.
One way of handling the collision issue is to start searching through the array from the
hashed-to, collision point to the next available table location. This technique is called
open addressing. Here are some consequences relevant to the choice of open addressing
for collisions:
 If there are enough collisions in a region of the hash table, those collisions will
produce a cluster of occupied locations that later queries will have to examine while
searching for the desired entry.
 A call to contains with a non-existent key may take extra time before the function
reaches an empty location and is sure the key is not there. The search must cycle
back to the start of the array when it reaches the end and stop searching if the
search goes all the way through to the starting point of the search.
 If the application deletes entries from the table, a deletion operation must mark
a deleted entry location as “available”. Later contains/get operations will interpret “available” as “not here; continue searching”, and later put operations will
replace the “available” mark with a new entry. See the first example implementation, hashmap-open.py. The “not here” entry is named SKIP. (See Figure 2.)
 If the number of entries to store exceeds the capacity of the hash table array, a larger
table is required. While the array is initially fixed, we can grow the hash table by
rehashing. (See the Rehashing section.) See the first example implementation,
hashmap-open-resizable.py.
If we implement a hash table with a sparsely populated array, we can get good open
addressing performance with the trade-off of over-allocated memory.
A totally different approach is to put all the entries that hash to the same location at
that same location, using a linked list of entries. This is called “chaining”.
5
Object
Hash Table
Index into
bucket array
occupied
occupied
occupied
available!
Hash
Function
Figure 1: Open Addressing with linear probing examines each location in order until finding an
empty or “available” location.
2.5 Rehashing
As the size of a hash table with open addressing approaches its capacity, the probability
of collisions rises, and the hash table starts behaving poorly.
A common solution is to monitor the hash table’s load level. We calculate the load as the
number of keys already in the table divided by the table’s total capacity (i.e. number of
locations). When the load exceeds a certain threshold, the hash table data structure must
perform a rehash operation to enlarge the size of the hash table and repopulate a new
array with a rehashing of the existing entries.
Function rehash( hashtable )
allocate a larger array to use as new hash table storage
for each entry in the original hashtable
# put() uses new hash values based on a larger hash table capacity
put( new array, entry key, entry value )
change the hashtable’s array to be the new, larger array
The rehash operation is an O(N), linear time operation, because the loop executes once
for each entry in the original table.
6
2.6 Implementation
The word count.py program uses our hash map implementation to count word occurrences. Normally one imposes a hash function on a class by defining the special method
hash . However, to make the demonstrations more interesting the sample programs use
a hash function co-resident with the class code, so we can easily change it and observe
what happens.
3 Testing
We should test our hash function using various strings, e.g. using those shown in the table
above (‘aaa,’ ‘zzz’ and various others), checking that word counts are produced properly
at the different string positions.
We then need to test the contains, get and put functions. When putting new words and
existing words, check that when existing words are ‘put’ that their values are updated
appropriately. The has function should return true only if we provide a key that has
already been put in the table. For get, we need to check that existing words have their
count correctly returned.
To test the handling of collisions, we need to generate keys whose hashcodes are the same.
Unfortunately, that may be difficult to find keys whose hash function produce the same
hashcode.
Testing is easiest using small table capacities to start, as done in the code provided. A
function that prints the contents of these tables is helpful for debugging.
7
4 Presentation Notes
Concepts:
 Dictionaries as (key, value) sets
 Sets as sets of unique, hashable keys without values
 Hash function, table, and code for implementing maps
 Converting non-numeric data to numbers for use in hash tables
 Collisions
 Open addressing
 Load factor and resizing
 Chaining
8
pythonds
Saving and Logging are Disabled

Social
Search
User
Scratch Activecode
Help
This Chapter
6.5. Hashing
In previous sections we were able to make improvements in our search algorithms by taking advantage of information about where items are stored in the collection with respect to one another. For example, by knowing that a list was ordered, we could search in logarithmic time using a binary search. In this section we will attempt to go one step further by building a data structure that can be searched in
 time. This concept is referred to as hashing.

In order to do this, we will need to know even more about where the items might be when we go to look for them in the collection. If every item is where it should be, then the search can use a single comparison to discover the presence of an item. We will see, however, that this is typically not the case.

A hash table is a collection of items which are stored in such a way as to make it easy to find them later. Each position of the hash table, often called a slot, can hold an item and is named by an integer value starting at 0. For example, we will have a slot named 0, a slot named 1, a slot named 2, and so on. Initially, the hash table contains no items so every slot is empty. We can implement a hash table by using a list with each element initialized to the special Python value None. Figure 4 shows a hash table of size
. In other words, there are m slots in the table, named 0 through 10.

../_images/hashtable.png
Figure 4: Hash Table with 11 Empty Slots

The mapping between an item and the slot where that item belongs in the hash table is called the hash function. The hash function will take any item in the collection and return an integer in the range of slot names, between 0 and m-1. Assume that we have the set of integer items 54, 26, 93, 17, 77, and 31. Our first hash function, sometimes referred to as the “remainder method,” simply takes an item and divides it by the table size, returning the remainder as its hash value (
). Table 4 gives all of the hash values for our example items. Note that this remainder method (modulo arithmetic) will typically be present in some form in all hash functions, since the result must be in the range of slot names.

Table 4: Simple Hash Function Using Remainders
Item

Hash Value

54

10

26

4

93

5

17

6

77

0

31

9

Once the hash values have been computed, we can insert each item into the hash table at the designated position as shown in Figure 5. Note that 6 of the 11 slots are now occupied. This is referred to as the load factor, and is commonly denoted by

. For this example,

.

../_images/hashtable2.png
Figure 5: Hash Table with Six Items

Now when we want to search for an item, we simply use the hash function to compute the slot name for the item and then check the hash table to see if it is present. This searching operation is
, since a constant amount of time is required to compute the hash value and then index the hash table at that location. If everything is where it should be, we have found a constant time search algorithm.

You can probably already see that this technique is going to work only if each item maps to a unique location in the hash table. For example, if the item 44 had been the next item in our collection, it would have a hash value of 0 (
). Since 77 also had a hash value of 0, we would have a problem. According to the hash function, two or more items would need to be in the same slot. This is referred to as a collision (it may also be called a “clash”). Clearly, collisions create a problem for the hashing technique. We will discuss them in detail later.

6.5.1. Hash Functions
Given a collection of items, a hash function that maps each item into a unique slot is referred to as a perfect hash function. If we know the items and the collection will never change, then it is possible to construct a perfect hash function (refer to the exercises for more about perfect hash functions). Unfortunately, given an arbitrary collection of items, there is no systematic way to construct a perfect hash function. Luckily, we do not need the hash function to be perfect to still gain performance efficiency.

One way to always have a perfect hash function is to increase the size of the hash table so that each possible value in the item range can be accommodated. This guarantees that each item will have a unique slot. Although this is practical for small numbers of items, it is not feasible when the number of possible items is large. For example, if the items were nine-digit Social Security numbers, this method would require almost one billion slots. If we only want to store data for a class of 25 students, we will be wasting an enormous amount of memory.

Our goal is to create a hash function that minimizes the number of collisions, is easy to compute, and evenly distributes the items in the hash table. There are a number of common ways to extend the simple remainder method. We will consider a few of them here.

The folding method for constructing hash functions begins by dividing the item into equal-size pieces (the last piece may not be of equal size). These pieces are then added together to give the resulting hash value. For example, if our item was the phone number 436-555-4601, we would take the digits and divide them into groups of 2 (43,65,55,46,01). After the addition,
, we get 210. If we assume our hash table has 11 slots, then we need to perform the extra step of dividing by 11 and keeping the remainder. In this case
 is 1, so the phone number 436-555-4601 hashes to slot 1. Some folding methods go one step further and reverse every other piece before the addition. For the above example, we get
 which gives
.

Another numerical technique for constructing a hash function is called the mid-square method. We first square the item, and then extract some portion of the resulting digits. For example, if the item were 44, we would first compute
. By extracting the middle two digits, 93, and performing the remainder step, we get 5 (
). Table 5 shows items under both the remainder method and the mid-square method. You should verify that you understand how these values were computed.

Table 5: Comparison of Remainder and Mid-Square Methods
Item

Remainder

Mid-Square

54

10

3

26

4

7

93

5

9

17

6

8

77

0

4

31

9

6

We can also create hash functions for character-based items such as strings. The word “cat” can be thought of as a sequence of ordinal values.

ord('c')
99
ord('a')
97
ord('t')
116
We can then take these three ordinal values, add them up, and use the remainder method to get a hash value (see Figure 6). Listing 1 shows a function called hash that takes a string and a table size and returns the hash value in the range from 0 to tablesize-1.

../_images/stringhash.png
Figure 6: Hashing a String Using Ordinal Values

Listing 1

def hash(astring, tablesize):
    sum = 0
    for pos in range(len(astring)):
        sum = sum + ord(astring[pos])

    return sum%tablesize
It is interesting to note that when using this hash function, anagrams will always be given the same hash value. To remedy this, we could use the position of the character as a weight. Figure 7 shows one possible way to use the positional value as a weighting factor. The modification to the hash function is left as an exercise.

../_images/stringhash2.png
Figure 7: Hashing a String Using Ordinal Values with Weighting

You may be able to think of a number of additional ways to compute hash values for items in a collection. The important thing to remember is that the hash function has to be efficient so that it does not become the dominant part of the storage and search process. If the hash function is too complex, then it becomes more work to compute the slot name than it would be to simply do a basic sequential or binary search as described earlier. This would quickly defeat the purpose of hashing.

6.5.2. Collision Resolution
We now return to the problem of collisions. When two items hash to the same slot, we must have a systematic method for placing the second item in the hash table. This process is called collision resolution. As we stated earlier, if the hash function is perfect, collisions will never occur. However, since this is often not possible, collision resolution becomes a very important part of hashing.

One method for resolving collisions looks into the hash table and tries to find another open slot to hold the item that caused the collision. A simple way to do this is to start at the original hash value position and then move in a sequential manner through the slots until we encounter the first slot that is empty. Note that we may need to go back to the first slot (circularly) to cover the entire hash table. This collision resolution process is referred to as open addressing in that it tries to find the next open slot or address in the hash table. By systematically visiting each slot one at a time, we are performing an open addressing technique called linear probing.

Figure 8 shows an extended set of integer items under the simple remainder method hash function (54,26,93,17,77,31,44,55,20). Table 4 above shows the hash values for the original items. Figure 5 shows the original contents. When we attempt to place 44 into slot 0, a collision occurs. Under linear probing, we look sequentially, slot by slot, until we find an open position. In this case, we find slot 1.

Again, 55 should go in slot 0 but must be placed in slot 2 since it is the next open position. The final value of 20 hashes to slot 9. Since slot 9 is full, we begin to do linear probing. We visit slots 10, 0, 1, and 2, and finally find an empty slot at position 3.

../_images/linearprobing1.png
Figure 8: Collision Resolution with Linear Probing

Once we have built a hash table using open addressing and linear probing, it is essential that we utilize the same methods to search for items. Assume we want to look up the item 93. When we compute the hash value, we get 5. Looking in slot 5 reveals 93, and we can return True. What if we are looking for 20? Now the hash value is 9, and slot 9 is currently holding 31. We cannot simply return False since we know that there could have been collisions. We are now forced to do a sequential search, starting at position 10, looking until either we find the item 20 or we find an empty slot.

A disadvantage to linear probing is the tendency for clustering; items become clustered in the table. This means that if many collisions occur at the same hash value, a number of surrounding slots will be filled by the linear probing resolution. This will have an impact on other items that are being inserted, as we saw when we tried to add the item 20 above. A cluster of values hashing to 0 had to be skipped to finally find an open position. This cluster is shown in Figure 9.

../_images/clustering.png
Figure 9: A Cluster of Items for Slot 0

One way to deal with clustering is to extend the linear probing technique so that instead of looking sequentially for the next open slot, we skip slots, thereby more evenly distributing the items that have caused collisions. This will potentially reduce the clustering that occurs. Figure 10 shows the items when collision resolution is done with a “plus 3” probe. This means that once a collision occurs, we will look at every third slot until we find one that is empty.

../_images/linearprobing2.png
Figure 10: Collision Resolution Using “Plus 3”

The general name for this process of looking for another slot after a collision is rehashing. With simple linear probing, the rehash function is
 where
. The “plus 3” rehash can be defined as
. In general,
. It is important to note that the size of the “skip” must be such that all the slots in the table will eventually be visited. Otherwise, part of the table will be unused. To ensure this, it is often suggested that the table size be a prime number. This is the reason we have been using 11 in our examples.

A variation of the linear probing idea is called quadratic probing. Instead of using a constant “skip” value, we use a rehash function that increments the hash value by 1, 3, 5, 7, 9, and so on. This means that if the first hash value is h, the successive values are
,
,
,
, and so on. In general, the i will be i^2
. In other words, quadratic probing uses a skip consisting of successive perfect squares. Figure 11 shows our example values after they are placed using this technique.

../_images/quadratic.png
Figure 11: Collision Resolution with Quadratic Probing

An alternative method for handling the collision problem is to allow each slot to hold a reference to a collection (or chain) of items. Chaining allows many items to exist at the same location in the hash table. When collisions happen, the item is still placed in the proper slot of the hash table. As more and more items hash to the same location, the difficulty of searching for the item in the collection increases. Figure 12 shows the items as they are added to a hash table that uses chaining to resolve collisions.

../_images/chaining.png
Figure 12: Collision Resolution with Chaining

When we want to search for an item, we use the hash function to generate the slot where it should reside. Since each slot holds a collection, we use a searching technique to decide whether the item is present. The advantage is that on the average there are likely to be many fewer items in each slot, so the search is perhaps more efficient. We will look at the analysis for hashing at the end of this section.

Self Check

Q-1: In a hash table of size 13 which index positions would the following two keys map to? 27, 130

A. 1, 10
B. 13, 0
C. 1, 0
D. 2, 3

Activity: 6.5.2.1 Multiple Choice (HASH_1)

Q-2: Suppose you are given the following set of keys to insert into a hash table that holds exactly 11 values: 113 , 117 , 97 , 100 , 114 , 108 , 116 , 105 , 99 Which of the following best demonstrates the contents of the hash table after all the keys have been inserted using linear probing?

A. 100, __, __, 113, 114, 105, 116, 117, 97, 108, 99
B. 99, 100, __, 113, 114, __, 116, 117, 105, 97, 108
C. 100, 113, 117, 97, 14, 108, 116, 105, 99, __, __
D. 117, 114, 108, 116, 105, 99, __, __, 97, 100, 113

Activity: 6.5.2.2 Multiple Choice (HASH_2)

6.5.3. Implementing the Map Abstract Data Type
One of the most useful Python collections is the dictionary. Recall that a dictionary is an associative data type where you can store key–data pairs. The key is used to look up the associated data value. We often refer to this idea as a map.

The map abstract data type is defined as follows. The structure is an unordered collection of associations between a key and a data value. The keys in a map are all unique so that there is a one-to-one relationship between a key and a value. The operations are given below.

Map() Create a new, empty map. It returns an empty map collection.

put(key,val) Add a new key-value pair to the map. If the key is already in the map then replace the old value with the new value.

get(key) Given a key, return the value stored in the map or None otherwise.

del Delete the key-value pair from the map using a statement of the form del map[key].

len() Return the number of key-value pairs stored in the map.

in Return True for a statement of the form key in map, if the given key is in the map, False otherwise.

One of the great benefits of a dictionary is the fact that given a key, we can look up the associated data value very quickly. In order to provide this fast look up capability, we need an implementation that supports an efficient search. We could use a list with sequential or binary search but it would be even better to use a hash table as described above since looking up an item in a hash table can approach
 performance.

In Listing 2 we use two lists to create a HashTable class that implements the Map abstract data type. One list, called slots, will hold the key items and a parallel list, called data, will hold the data values. When we look up a key, the corresponding position in the data list will hold the associated data value. We will treat the key list as a hash table using the ideas presented earlier. Note that the initial size for the hash table has been chosen to be 11. Although this is arbitrary, it is important that the size be a prime number so that the collision resolution algorithm can be as efficient as possible.

Listing 2

class HashTable:
    def __init__(self):
        self.size = 11
        self.slots = [None] * self.size
        self.data = [None] * self.size
hashfunction implements the simple remainder method. The collision resolution technique is linear probing with a “plus 1” rehash function. The put function (see Listing 3) assumes that there will eventually be an empty slot unless the key is already present in the self.slots. It computes the original hash value and if that slot is not empty, iterates the rehash function until an empty slot occurs. If a nonempty slot already contains the key, the old data value is replaced with the new data value. Dealing with the situation where there are no empty slots left is an exercise.

Listing 3

def put(self,key,data):
  hashvalue = self.hashfunction(key,len(self.slots))

  if self.slots[hashvalue] == None:
    self.slots[hashvalue] = key
    self.data[hashvalue] = data
  else:
    if self.slots[hashvalue] == key:
      self.data[hashvalue] = data  #replace
    else:
      nextslot = self.rehash(hashvalue,len(self.slots))
      while self.slots[nextslot] != None and \
                      self.slots[nextslot] != key:
        nextslot = self.rehash(nextslot,len(self.slots))

      if self.slots[nextslot] == None:
        self.slots[nextslot]=key
        self.data[nextslot]=data
      else:
        self.data[nextslot] = data #replace

def hashfunction(self,key,size):
     return key%size

def rehash(self,oldhash,size):
    return (oldhash+1)%size
Likewise, the get function (see Listing 4) begins by computing the initial hash value. If the value is not in the initial slot, rehash is used to locate the next possible position. Notice that line 15 guarantees that the search will terminate by checking to make sure that we have not returned to the initial slot. If that happens, we have exhausted all possible slots and the item must not be present.

The final methods of the HashTable class provide additional dictionary functionality. We overload the __getitem__ and __setitem__ methods to allow access using``[]``. This means that once a HashTable has been created, the familiar index operator will be available. We leave the remaining methods as exercises.

Listing 4

def get(self,key):
  startslot = self.hashfunction(key,len(self.slots))

  data = None
  stop = False
  found = False
  position = startslot
  while self.slots[position] != None and  \
                       not found and not stop:
     if self.slots[position] == key:
       found = True
       data = self.data[position]
     else:
       position=self.rehash(position,len(self.slots))
       if position == startslot:
           stop = True
  return data

def __getitem__(self,key):
    return self.get(key)

def __setitem__(self,key,data):
    self.put(key,data)
The following session shows the HashTable class in action. First we will create a hash table and store some items with integer keys and string data values.

H=HashTable()
H[54]="cat"
H[26]="dog"
H[93]="lion"
H[17]="tiger"
H[77]="bird"
H[31]="cow"
H[44]="goat"
H[55]="pig"
H[20]="chicken"
H.slots
[77, 44, 55, 20, 26, 93, 17, None, None, 31, 54]
H.data
['bird', 'goat', 'pig', 'chicken', 'dog', 'lion',
       'tiger', None, None, 'cow', 'cat']
Next we will access and modify some items in the hash table. Note that the value for the key 20 is being replaced.

H[20]
'chicken'
H[17]
'tiger'
H[20]='duck'
H[20]
'duck'
H.data
['bird', 'goat', 'pig', 'duck', 'dog', 'lion',
       'tiger', None, None, 'cow', 'cat']
>> print(H[99])
None
The complete hash table example can be found in ActiveCode 1.

Activity: 6.5.3.1 Complete Hash Table Example (hashtablecomplete)

6.5.4. Analysis of Hashing
We stated earlier that in the best case hashing would provide a
, constant time search technique. However, due to collisions, the number of comparisons is typically not so simple. Even though a complete analysis of hashing is beyond the scope of this text, we can state some well-known results that approximate the number of comparisons necessary to search for an item.

The most important piece of information we need to analyze the use of a hash table is the load factor,
. Conceptually, if
 is small, then there is a lower chance of collisions, meaning that items are more likely to be in the slots where they belong. If
 is large, meaning that the table is filling up, then there are more and more collisions. This means that collision resolution is more difficult, requiring more comparisons to find an empty slot. With chaining, increased collisions means an increased number of items on each chain.

As before, we will have a result for both a successful and an unsuccessful search. For a successful search using open addressing with linear probing, the average number of comparisons is approximately


 and an unsuccessful search gives


 If we are using chaining, the average number of comparisons is

 for the successful case, and simply
 comparisons if the search is unsuccessful.

You have attempted 1 of 4 activities on this page
user not logged in
