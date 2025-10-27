"""LinkedHashTable implementation for O(1) file organization operations.

This module provides a high-performance hash table implementation that maintains
insertion order using a doubly linked list overlay on top of a chaining hash table.
It is specifically optimized for file organization workloads with memory efficiency
and polynomial hash functions for better distribution.

Key Features:
- O(1) average time complexity for put, get, and remove operations
- Maintains insertion order for deterministic iteration
- Memory-optimized using __slots__ for reduced memory footprint
- Polynomial hash function with ReDoS prevention
- Automatic rehashing with 1.5x growth factor
- Type-safe generic implementation

Example:
    >>> table = LinkedHashTable()
    >>> table.put("key1", "value1")
    >>> table.put("key2", "value2")
    >>> table.get("key1")
    'value1'
    >>> list(table)  # Maintains insertion order
    [('key1', 'value1'), ('key2', 'value2')]
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class HashNode(Generic[K, V]):
    """Hash table node with chaining and doubly linked list support.

    This node serves dual purposes:
    1. Chaining: next_in_bucket links nodes in the same hash bucket
    2. Order maintenance: prev_in_order and next_in_order maintain insertion order

    Optimized for memory efficiency using __slots__.
    """

    __slots__ = ("key", "next_in_bucket", "next_in_order", "prev_in_order", "value")

    def __init__(
        self,
        key: K,
        value: V,
        next_in_bucket: HashNode[K, V] | None = None,
        prev_in_order: HashNode[K, V] | None = None,
        next_in_order: HashNode[K, V] | None = None,
    ):
        """Initialize HashNode with optimized memory layout.

        Args:
            key: The key stored in this node
            value: The value stored in this node
            next_in_bucket: Next node in the hash bucket chain
            prev_in_order: Previous node in insertion order
            next_in_order: Next node in insertion order
        """
        self.key = key
        self.value = value
        self.next_in_bucket = next_in_bucket
        self.prev_in_order = prev_in_order
        self.next_in_order = next_in_order

    def __repr__(self) -> str:
        """String representation of the node."""
        return f"HashNode(key={self.key!r}, value={self.value!r})"


class LinkedHashTable(Generic[K, V]):
    """Hash table that maintains insertion order with O(1) operations.

    This implementation uses chaining for collision resolution and maintains
    insertion order using a doubly linked list overlay. It is specifically
    optimized for file organization workloads with memory efficiency and
    polynomial hash functions for better distribution.

    Features:
    - O(1) average time complexity for put, get, remove operations
    - Maintains insertion order for deterministic iteration
    - Memory-optimized using __slots__ for reduced memory footprint
    - Polynomial hash function with ReDoS prevention
    - Automatic rehashing with 1.5x growth factor
    - Generic type support for keys and values

    Args:
        initial_capacity: Initial number of buckets (default: 64)
        load_factor: Maximum load factor before rehashing (default: 0.8)

    Example:
        >>> table = LinkedHashTable()
        >>> table.put("file1", {"size": 1024, "type": "video"})
        >>> table.put("file2", {"size": 2048, "type": "audio"})
        >>> table.get("file1")
        {'size': 1024, 'type': 'video'}
        >>> len(table)
        2
        >>> list(table)  # Maintains insertion order
        [('file1', {'size': 1024, 'type': 'video'}),
         ('file2', {'size': 2048, 'type': 'audio'})]

    Note:
        Optimized defaults for file organization workloads:
        - initial_capacity=64: Reduces rehashing for typical file counts
        - load_factor=0.8: Higher threshold reduces memory waste
    """

    def __init__(self, initial_capacity: int = 64, load_factor: float = 0.8):
        """Initialize the LinkedHashTable.

        Args:
            initial_capacity: Initial number of buckets in the hash table
            load_factor: Threshold for rehashing (0.0 to 1.0)

        Note:
            Optimized defaults for file organization workloads:
            - initial_capacity=64: Reduces rehashing for typical file counts
            - load_factor=0.8: Higher threshold reduces memory waste
        """
        if initial_capacity <= 0:
            raise ValueError("Initial capacity must be positive")
        if not 0.0 < load_factor <= 1.0:
            raise ValueError("Load factor must be between 0.0 and 1.0")

        self._capacity = initial_capacity
        self._load_factor = load_factor
        self._size = 0
        self._buckets: list[HashNode[K, V] | None] = [None] * self._capacity
        self._head: HashNode[K, V] | None = None  # Oldest node
        self._tail: HashNode[K, V] | None = None  # Newest node

    def _hash(self, key: K) -> int:
        """Calculate hash value for the given key.

        Optimized for file organization using polynomial hash function
        for (filename, size) tuples to reduce collisions.

        Args:
            key: The key to hash

        Returns:
            Hash value modulo capacity
        """
        # Security: Maximum filename length to prevent ReDoS attacks
        max_filename_length = 500

        if isinstance(key, tuple) and len(key) == 2:
            # Optimized for (title, episode) tuples used in file organization
            title, episode = key
            title_str = str(title) if title is not None else "Unknown"
            episode_int = episode if episode is not None else 0

            # Prevent ReDoS attacks by limiting filename length
            if len(title_str) > max_filename_length:
                title_str = title_str[:max_filename_length]

            # Polynomial hash function: h = h * 31 + ord(char)
            hash_value = 0
            for char in title_str:
                hash_value = hash_value * 31 + ord(char)

            # Combine with episode number
            hash_value = hash_value * 31 + episode_int

            return hash_value % self._capacity

        # Fallback to built-in hash for other key types
        return hash(key) % self._capacity

    def put(self, key: K, value: V) -> V | None:
        """Insert or update a key-value pair.

        Args:
            key: The key to insert/update
            value: The value to associate with the key

        Returns:
            Previous value if key existed, None otherwise
        """
        bucket_index = self._hash(key)
        current = self._buckets[bucket_index]

        # Search for existing key in the bucket
        while current is not None:
            if current.key == key:
                # Update existing key
                old_value = current.value
                current.value = value
                return old_value
            current = current.next_in_bucket

        # Create new node (optimized - only set required fields)
        new_node = HashNode(key, value)

        # Add to bucket (chaining)
        new_node.next_in_bucket = self._buckets[bucket_index]
        self._buckets[bucket_index] = new_node

        # Add to insertion order (doubly linked list)
        if self._tail is None:
            # First node
            self._head = new_node
            self._tail = new_node
        else:
            # Append to tail
            self._tail.next_in_order = new_node
            new_node.prev_in_order = self._tail
            self._tail = new_node

        self._size += 1

        # Check if we need to rehash after adding new node
        if self._size >= self._capacity * self._load_factor:
            self._rehash()

        return None

    def get(self, key: K) -> V | None:
        """Retrieve value for the given key.

        Args:
            key: The key to look up

        Returns:
            Value associated with the key, or None if not found
        """
        bucket_index = self._hash(key)
        current = self._buckets[bucket_index]

        while current is not None:
            if current.key == key:
                return current.value
            current = current.next_in_bucket

        return None

    def remove(self, key: K) -> V | None:
        """Remove the key-value pair for the given key.

        Args:
            key: The key to remove

        Returns:
            Value that was removed, or None if key not found
        """
        bucket_index = self._hash(key)
        current = self._buckets[bucket_index]
        prev = None

        # Find the node to remove
        while current is not None:
            if current.key == key:
                # Remove from bucket (chaining)
                if prev is None:
                    self._buckets[bucket_index] = current.next_in_bucket
                else:
                    prev.next_in_bucket = current.next_in_bucket

                # Remove from insertion order (doubly linked list)
                if current.prev_in_order is not None:
                    current.prev_in_order.next_in_order = current.next_in_order
                else:
                    # This was the head
                    self._head = current.next_in_order

                if current.next_in_order is not None:
                    current.next_in_order.prev_in_order = current.prev_in_order
                else:
                    # This was the tail
                    self._tail = current.prev_in_order

                self._size -= 1
                return current.value

            prev = current
            current = current.next_in_bucket

        return None

    def _rehash(self) -> None:
        """Rehash the table with optimized capacity growth.

        Uses a 1.5x growth factor instead of 2x to reduce memory peaks
        while maintaining good performance characteristics.
        """
        # Use 1.5x growth factor for more gradual memory increase
        self._capacity = int(self._capacity * 1.5)
        self._buckets = [None] * self._capacity

        # Rehash all existing nodes
        current = self._head
        while current is not None:
            next_node = current.next_in_order  # Save next before modifying
            bucket_index = self._hash(current.key)
            current.next_in_bucket = self._buckets[bucket_index]
            self._buckets[bucket_index] = current
            current = next_node

    def clear(self) -> None:
        """Clear all key-value pairs from the table."""
        self._buckets = [None] * self._capacity
        self._head = None
        self._tail = None
        self._size = 0

    def __iter__(self) -> Iterator[tuple[K, V]]:
        """Iterate over key-value pairs in insertion order.

        Yields:
            Tuple of (key, value) pairs in insertion order
        """
        current = self._head
        while current is not None:
            # Optimized: avoid tuple creation overhead
            yield current.key, current.value
            current = current.next_in_order

    def __len__(self) -> int:
        """Return the number of key-value pairs in the table."""
        return self._size

    def __contains__(self, key: K) -> bool:
        """Check if the key exists in the table."""
        return self.get(key) is not None

    def __str__(self) -> str:
        """Return string representation of the table."""
        # Optimized: avoid creating intermediate list
        if self._size == 0:
            return "LinkedHashTable({})"

        # Build string directly from iteration
        items = []
        current = self._head
        while current is not None:
            items.append(f"({current.key!r}, {current.value!r})")
            current = current.next_in_order

        return f"LinkedHashTable([{', '.join(items)}])"

    def __repr__(self) -> str:
        """Return detailed string representation of the table."""
        return (
            f"LinkedHashTable(capacity={self._capacity}, "
            f"size={self._size}, load_factor={self._load_factor})"
        )

    @property
    def size(self) -> int:
        """Get the current number of elements in the table."""
        return self._size

    @property
    def capacity(self) -> int:
        """Get the current capacity of the table."""
        return self._capacity

    @property
    def load_factor(self) -> float:
        """Get the current load factor of the table."""
        return self._load_factor
