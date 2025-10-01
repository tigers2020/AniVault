"""Property-based fuzzing tests for anime filename parser using Hypothesis."""

from __future__ import annotations

from hypothesis import given, strategies as st

from anivault.core.parser.anime_parser import AnimeFilenameParser
from anivault.core.parser.models import ParsingResult


# Define a composite strategy for generating plausible anime filenames
@st.composite
def filename_strategy(draw):
    """Generate plausible anime filename strings.

    This strategy creates random but structurally reasonable anime filenames
    to test the parser with realistic edge cases.

    Args:
        draw: Hypothesis draw function.

    Returns:
        Generated filename string.
    """
    # Generate components
    title = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
                min_codepoint=0x20,
                max_codepoint=0xD7FF,
            ),
            min_size=1,
            max_size=50,
        )
    )

    # Episode number (optional)
    has_episode = draw(st.booleans())
    episode = draw(st.integers(min_value=1, max_value=999)) if has_episode else None

    # Season number (optional)
    has_season = draw(st.booleans())
    season = draw(st.integers(min_value=1, max_value=10)) if has_season else None

    # Quality (optional)
    has_quality = draw(st.booleans())
    quality = (
        draw(st.sampled_from(["1080p", "720p", "480p", "2160p", "360p"]))
        if has_quality
        else None
    )

    # Release group (optional)
    has_group = draw(st.booleans())
    group = (
        draw(
            st.text(
                alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
                min_size=3,
                max_size=20,
            )
        )
        if has_group
        else None
    )

    # Extension
    extension = draw(st.sampled_from([".mkv", ".mp4", ".avi", ".webm", ".mov"]))

    # Build filename based on random format
    format_choice = draw(st.integers(min_value=0, max_value=4))

    if format_choice == 0 and group and episode:
        # Format: [Group] Title - Episode [Quality]
        filename = f"[{group}] {title} - {episode:02d}"
        if quality:
            filename += f" [{quality}]"
        filename += extension
    elif format_choice == 1 and season and episode:
        # Format: Title S##E##
        filename = f"{title} S{season:02d}E{episode:02d}"
        if quality:
            filename += f" [{quality}]"
        filename += extension
    elif format_choice == 2 and episode:
        # Format: Title - Episode
        filename = f"{title} - {episode}{extension}"
    elif format_choice == 3 and episode:
        # Format: Title EP##
        filename = f"{title} EP{episode:02d}{extension}"
    else:
        # Format: Simple title
        filename = f"{title}{extension}"

    return filename


class TestParserRobustness:
    """Property-based tests for parser robustness using Hypothesis."""

    @given(st.text(min_size=0, max_size=200))
    def test_parsing_never_crashes_on_arbitrary_text(self, text: str):
        """Test that parser never crashes on arbitrary text input.

        Property: Parser must handle any string without raising exceptions.
        """
        parser = AnimeFilenameParser()

        # Should not raise any exception
        result = parser.parse(text)

        # Result should always be a ParsingResult instance
        assert isinstance(result, ParsingResult)

    @given(filename_strategy())
    def test_parsing_never_crashes_on_plausible_filenames(self, filename: str):
        """Test that parser never crashes on plausible filename input.

        Property: Parser must handle structurally plausible filenames.
        """
        parser = AnimeFilenameParser()

        # Should not raise any exception
        result = parser.parse(filename)

        # Result should always be a ParsingResult instance
        assert isinstance(result, ParsingResult)

    @given(filename_strategy())
    def test_confidence_is_always_in_range(self, filename: str):
        """Test that confidence score is always within valid range.

        Property: Confidence must be between 0.0 and 1.0 (inclusive).
        """
        parser = AnimeFilenameParser()
        result = parser.parse(filename)

        assert (
            0.0 <= result.confidence <= 1.0
        ), f"Confidence {result.confidence} out of range for: {filename}"

    @given(filename_strategy())
    def test_parser_used_is_always_valid(self, filename: str):
        """Test that parser_used field always contains valid value.

        Property: parser_used must be one of the known parser names.
        """
        parser = AnimeFilenameParser()
        result = parser.parse(filename)

        valid_parsers = {"anitopy", "fallback", "unknown"}
        assert (
            result.parser_used in valid_parsers
        ), f"Invalid parser_used '{result.parser_used}' for: {filename}"

    @given(filename_strategy())
    def test_numeric_fields_have_valid_types(self, filename: str):
        """Test that numeric fields are always valid when present.

        Property: Episode and season must be positive integers when not None.
        """
        parser = AnimeFilenameParser()
        result = parser.parse(filename)

        # Episode must be int and positive if present
        if result.episode is not None:
            assert isinstance(
                result.episode, int
            ), f"Episode is not int: {type(result.episode)} for: {filename}"
            assert (
                result.episode >= 0
            ), f"Episode is negative: {result.episode} for: {filename}"

        # Season must be int and positive if present
        if result.season is not None:
            assert isinstance(
                result.season, int
            ), f"Season is not int: {type(result.season)} for: {filename}"
            assert (
                result.season >= 0
            ), f"Season is negative: {result.season} for: {filename}"

    @given(filename_strategy())
    def test_title_is_always_string(self, filename: str):
        """Test that title is always a string.

        Property: Title must always be a non-None string.
        """
        parser = AnimeFilenameParser()
        result = parser.parse(filename)

        assert isinstance(
            result.title, str
        ), f"Title is not string: {type(result.title)} for: {filename}"

    @given(filename_strategy())
    def test_result_is_always_valid_or_has_low_confidence(self, filename: str):
        """Test relationship between validity and confidence.

        Property: Invalid results should have low confidence.
        """
        parser = AnimeFilenameParser()
        result = parser.parse(filename)

        # If result is not valid, confidence should typically be low
        if not result.is_valid():
            # Allow some tolerance, but generally expect low confidence
            # for invalid results
            assert (
                result.confidence < 0.8
            ), f"Invalid result has high confidence {result.confidence} for: {filename}"

    @given(st.text(min_size=1, max_size=500))
    def test_other_info_is_always_dict(self, text: str):
        """Test that other_info is always a dictionary.

        Property: other_info must always be a dict.
        """
        parser = AnimeFilenameParser()
        result = parser.parse(text)

        assert isinstance(
            result.other_info, dict
        ), f"other_info is not dict: {type(result.other_info)} for: {text}"

    @given(filename_strategy())
    def test_string_fields_are_strings_or_none(self, filename: str):
        """Test that string fields are always strings or None.

        Property: Optional string fields must be str or None.
        """
        parser = AnimeFilenameParser()
        result = parser.parse(filename)

        string_fields = ["quality", "source", "codec", "audio", "release_group"]

        for field_name in string_fields:
            field_value = getattr(result, field_name)
            assert field_value is None or isinstance(field_value, str), (
                f"Field '{field_name}' is not str or None: "
                f"{type(field_value)} for: {filename}"
            )
