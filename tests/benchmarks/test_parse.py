"""Benchmark tests for filename parsing."""

from __future__ import annotations

import pytest

from anivault.core.parser.anime_parser import AnimeFilenameParser


@pytest.fixture
def parser() -> AnimeFilenameParser:
    """Create parser instance."""
    return AnimeFilenameParser()


@pytest.fixture
def test_filenames() -> list[str]:
    """Generate test filenames."""
    return [
        "[HorribleSubs] Attack on Titan - 01 [1080p].mkv",
        "[SubsPlease] Jujutsu Kaisen - 24 (1080p) [12345678].mkv",
        "Demon Slayer - Kimetsu no Yaiba - S01E01 - Cruelty.mkv",
        "My Hero Academia S05E12 1080p WEB x264-MiXED.mkv",
        "[Erai-raws] Spy x Family - 01 [1080p][Multiple Subtitle].mkv",
    ]


def test_benchmark_parse_filename(benchmark, parser, test_filenames) -> None:  # type: ignore[no-untyped-def]
    """Benchmark parsing single filename."""
    filename = test_filenames[0]
    result = benchmark(parser.parse, filename)

    # Verify result
    assert result is not None
    assert result.title is not None


def test_benchmark_parse_batch(benchmark, parser, test_filenames) -> None:  # type: ignore[no-untyped-def]
    """Benchmark parsing multiple filenames."""

    def parse_batch():  # type: ignore[no-untyped-def]
        return [parser.parse(fn) for fn in test_filenames]

    results = benchmark(parse_batch)
    assert len(results) == len(test_filenames)


def test_benchmark_parse_complex_filename(benchmark, parser) -> None:  # type: ignore[no-untyped-def]
    """Benchmark parsing complex filename with many elements."""
    complex_filename = (
        "[SubGroup] Anime Title - The Very Long Subtitle Part 2 - "
        "S03E24 - Episode Title [1080p][HEVC x265 10bit][AAC 2.0][Dual Audio][Eng Sub].mkv"
    )

    result = benchmark(parser.parse, complex_filename)
    assert result is not None
