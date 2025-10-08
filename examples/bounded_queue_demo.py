"""
Demonstration of BoundedQueue usage.
"""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.anivault import BoundedQueue


def producer(queue: BoundedQueue, items: list, delay: float = 0.1) -> None:
    """Producer function that adds items to the queue."""
    for item in items:
        print(f"Producer: Adding {item}")
        queue.put(item)
        time.sleep(delay)
    print("Producer: Finished adding items")


def consumer(queue: BoundedQueue, expected_count: int, delay: float = 0.1) -> None:
    """Consumer function that removes items from the queue."""
    consumed = 0
    while consumed < expected_count:
        item = queue.get()
        if item:
            print(f"Consumer: Got {item}")
            consumed += 1
        time.sleep(delay)
    print("Consumer: Finished consuming items")


def main() -> None:
    """Demonstrate BoundedQueue functionality."""
    print("=== BoundedQueue Demonstration ===\n")

    # Create a bounded queue with capacity 3
    queue = BoundedQueue(capacity=3)
    print(f"Created queue with capacity: {queue.capacity()}")
    print(f"Initial size: {queue.size()}")
    print(f"Is empty: {queue.is_empty()}")
    print()

    # Test basic operations
    print("=== Basic Operations ===")
    queue.put("item1")
    queue.put("item2")
    print(f"After adding 2 items - Size: {queue.size()}, Is full: {queue.is_full()}")

    # Peek at the first item
    first_item = queue.peek()
    print(f"First item (peek): {first_item}")

    # Get items
    item1 = queue.get()
    item2 = queue.get()
    print(f"Retrieved items: {item1}, {item2}")
    print(f"After retrieval - Size: {queue.size()}, Is empty: {queue.is_empty()}")
    print()

    # Test capacity limits
    print("=== Capacity Limits ===")
    for i in range(5):
        success = queue.put_nowait(f"item{i}")
        print(f"Added item{i}: {success}")
    print(f"Final size: {queue.size()}")
    print()

    # Test statistics
    print("=== Queue Statistics ===")
    stats = queue.get_stats()
    print(f"Total added: {stats.total_added}")
    print(f"Total removed: {stats.total_removed}")
    print(f"Max size reached: {stats.max_size_reached}")
    print()

    # Test producer-consumer pattern
    print("=== Producer-Consumer Pattern ===")
    queue.clear()
    items = [f"task_{i}" for i in range(5)]

    # Start producer and consumer threads
    producer_thread = threading.Thread(target=producer, args=(queue, items, 0.2))
    consumer_thread = threading.Thread(target=consumer, args=(queue, len(items), 0.3))

    producer_thread.start()
    consumer_thread.start()

    # Wait for completion
    producer_thread.join()
    consumer_thread.join()

    print(f"Final queue size: {queue.size()}")
    print("Demonstration completed!")


if __name__ == "__main__":
    main()
