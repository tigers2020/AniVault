"""Tests for LinkedHashTable data structure."""

import pytest
from src.anivault.core.data_structures.linked_hash_table import LinkedHashTable


class TestLinkedHashTable:
    """Test cases for LinkedHashTable."""

    def test_empty_table(self):
        """Test empty table properties."""
        table = LinkedHashTable[str, int]()
        assert len(table) == 0
        assert table.size == 0
        assert list(table) == []

    def test_single_item(self):
        """Test table with single item."""
        table = LinkedHashTable[str, int]()
        table.put("key1", 42)

        assert len(table) == 1
        assert table.size == 1
        assert table.get("key1") == 42
        assert "key1" in table
        assert list(table) == [("key1", 42)]

    def test_multiple_items(self):
        """Test table with multiple items."""
        table = LinkedHashTable[str, int]()
        items = [("key1", 1), ("key2", 2), ("key3", 3)]

        for key, value in items:
            table.put(key, value)

        assert len(table) == 3
        assert table.size == 3

        # Test retrieval
        for key, expected_value in items:
            assert table.get(key) == expected_value
            assert key in table

        # Test iteration order (insertion order)
        assert list(table) == items

    def test_duplicate_keys(self):
        """Test overwriting existing keys."""
        table = LinkedHashTable[str, int]()
        table.put("key1", 1)
        table.put("key2", 2)

        # Overwrite existing key
        table.put("key1", 10)

        assert len(table) == 2  # Size should remain the same
        assert table.get("key1") == 10
        assert table.get("key2") == 2

        # Order should be preserved (key1 should still be first)
        assert list(table) == [("key1", 10), ("key2", 2)]

    def test_nonexistent_key(self):
        """Test accessing non-existent key."""
        table = LinkedHashTable[str, int]()
        table.put("key1", 1)

        assert table.get("nonexistent") is None
        assert "nonexistent" not in table

    def test_remove_existing(self):
        """Test removing existing items."""
        table = LinkedHashTable[str, int]()
        table.put("key1", 1)
        table.put("key2", 2)
        table.put("key3", 3)

        # Remove middle item
        removed = table.remove("key2")
        assert removed == 2
        assert len(table) == 2
        assert "key2" not in table
        assert table.get("key2") is None

        # Check remaining items
        assert table.get("key1") == 1
        assert table.get("key3") == 3

    def test_remove_nonexistent(self):
        """Test removing non-existent item."""
        table = LinkedHashTable[str, int]()
        table.put("key1", 1)

        removed = table.remove("nonexistent")
        assert removed is None
        assert len(table) == 1
        assert table.get("key1") == 1

    def test_clear(self):
        """Test clearing the table."""
        table = LinkedHashTable[str, int]()
        table.put("key1", 1)
        table.put("key2", 2)

        # Remove all items manually (no clear method)
        table.remove("key1")
        table.remove("key2")

        assert len(table) == 0
        assert table.size == 0
        assert list(table) == []

    def test_tuple_keys(self):
        """Test using tuple keys (for file organization)."""
        table = LinkedHashTable[tuple[str, int], str]()

        key1 = ("title1", 1)
        key2 = ("title2", 2)

        table.put(key1, "file1.mkv")
        table.put(key2, "file2.mkv")

        assert len(table) == 2
        assert table.get(key1) == "file1.mkv"
        assert table.get(key2) == "file2.mkv"
        assert key1 in table
        assert key2 in table

    def test_large_dataset(self):
        """Test with larger dataset to verify performance."""
        table = LinkedHashTable[int, str]()

        # Insert 1000 items
        for i in range(1000):
            table.put(i, f"value_{i}")

        assert len(table) == 1000

        # Test retrieval
        for i in range(1000):
            assert table.get(i) == f"value_{i}"
            assert i in table

        # Test iteration order
        items = list(table)
        assert len(items) == 1000
        for i, (key, value) in enumerate(items):
            assert key == i
            assert value == f"value_{i}"

    def test_mixed_types(self):
        """Test with mixed value types."""
        table = LinkedHashTable[str, object]()

        table.put("str", "string_value")
        table.put("int", 42)
        table.put("float", 3.14)
        table.put("bool", True)
        table.put("list", [1, 2, 3])

        assert len(table) == 5
        assert table.get("str") == "string_value"
        assert table.get("int") == 42
        assert table.get("float") == 3.14
        assert table.get("bool") is True
        assert table.get("list") == [1, 2, 3]

    def test_rehashing(self):
        """Test automatic rehashing when capacity is exceeded."""
        table = LinkedHashTable[str, int]()

        # Insert items to trigger rehashing
        # Initial capacity is typically small, so this should trigger rehash
        for i in range(20):  # More than initial capacity
            table.put(f"key_{i}", i)

        assert len(table) == 20

        # Verify all items are still accessible after rehashing
        for i in range(20):
            assert table.get(f"key_{i}") == i
            assert f"key_{i}" in table

    def test_iteration_consistency(self):
        """Test that iteration order is consistent."""
        table = LinkedHashTable[str, int]()

        # Insert items in specific order
        items = [("a", 1), ("b", 2), ("c", 3), ("d", 4), ("e", 5)]
        for key, value in items:
            table.put(key, value)

        # Multiple iterations should return same order
        iteration1 = list(table)
        iteration2 = list(table)
        assert iteration1 == iteration2 == items

        # Order should be preserved after modifications
        table.put("f", 6)
        expected_order = items + [("f", 6)]
        assert list(table) == expected_order

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        table = LinkedHashTable[str, int]()

        # Empty string key
        table.put("", 0)
        assert table.get("") == 0
        assert "" in table

        # Very long key
        long_key = "a" * 1000
        table.put(long_key, 999)
        assert table.get(long_key) == 999

        # Special characters in key
        special_key = "key with spaces and !@#$%^&*()"
        table.put(special_key, 123)
        assert table.get(special_key) == 123
