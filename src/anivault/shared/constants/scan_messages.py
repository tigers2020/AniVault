"""Scan queue message kinds (shared between producer and consumer)."""


class ScanQueueMessageKind:
    """Message kinds for scan queue (producer: scan_use_case, consumer: scan_controller)."""

    STARTED = "started"
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    DONE = "done"
