"""Title vectorization module for DBSCAN clustering.

This module provides functionality to convert title strings into
high-dimensional vectors suitable for clustering algorithms like DBSCAN.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from sklearn.feature_extraction.text import TfidfVectorizer

if TYPE_CHECKING:
    import numpy as np
    from scipy.sparse import csr_matrix

logger = logging.getLogger(__name__)


class TitleVectorizer:
    """Vectorizes titles for clustering using TF-IDF.

    This class converts a list of title strings into a vector matrix
    where each row represents a title and each column represents a feature
    (word/term). The TF-IDF (Term Frequency-Inverse Document Frequency)
    weighting scheme is used to emphasize important words while downplaying
    common words.

    The vectorizer is designed to be extensible, allowing future integration
    with Sentence Transformer models for semantic embeddings.

    Attributes:
        vectorizer: TfidfVectorizer instance for text vectorization.
        _fitted: Whether the vectorizer has been fitted to data.

    Example:
        >>> vectorizer = TitleVectorizer()
        >>> titles = ["Attack on Titan", "Attack on Titan Season 2"]
        >>> vectors = vectorizer.fit_transform(titles)
        >>> vectors.shape
        (2, n_features)
    """

    def __init__(
        self,
        max_features: int = 1000,
        ngram_range: tuple[int, int] = (1, 2),
        min_df: int = 1,
        max_df: float = 0.95,
    ) -> None:
        """Initialize the TitleVectorizer.

        Args:
            max_features: Maximum number of features (terms) to keep.
                         Default 1000 (good balance for title length).
            ngram_range: Range of n-grams to extract. (1, 2) means unigrams
                        and bigrams. Default (1, 2).
            min_df: Minimum document frequency for a term to be included.
                   Default 1 (include all terms that appear at least once).
            max_df: Maximum document frequency. Terms that appear in more than
                   this fraction of documents are ignored. Default 0.95.

        Example:
            >>> vectorizer = TitleVectorizer(max_features=500)
            >>> vectorizer.max_features
            500
        """
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df

        # Initialize TF-IDF vectorizer
        # Note: max_df must be >= min_df in terms of document count
        # We'll adjust max_df dynamically in fit() for small datasets
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=max_df,
            lowercase=True,  # Normalize to lowercase
            strip_accents="unicode",  # Remove accents
            analyzer="word",  # Word-level tokenization
            token_pattern=r"(?u)\b\w+\b",  # noqa: S106  # Word boundary pattern (regex for word matching)
        )

        self._fitted = False
        logger.debug(
            "TitleVectorizer initialized: max_features=%d, ngram_range=%s",
            max_features,
            ngram_range,
        )

    def fit(self, titles: list[str]) -> TitleVectorizer:
        """Fit the vectorizer to a list of titles.

        This method learns the vocabulary and IDF (Inverse Document Frequency)
        values from the input titles. Must be called before transform().

        Args:
            titles: List of title strings to fit the vectorizer on.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If titles list is empty.

        Example:
            >>> vectorizer = TitleVectorizer()
            >>> titles = ["Attack on Titan", "Naruto"]
            >>> vectorizer.fit(titles)
            <TitleVectorizer object>
        """
        if not titles:
            msg = "Cannot fit vectorizer on empty title list"
            raise ValueError(msg)

        logger.debug("Fitting TitleVectorizer on %d titles", len(titles))

        # Adjust max_df for small datasets to avoid conflicts with min_df
        num_docs = len(titles)
        if isinstance(self.vectorizer.max_df, float) and self.vectorizer.max_df < 1.0:
            max_df_docs = int(self.vectorizer.max_df * num_docs)
            if max_df_docs < self.vectorizer.min_df:
                # Adjust max_df to be at least min_df
                # Use 1.0 (all documents) if dataset is too small
                adjusted_max_df = 1.0 if num_docs <= self.vectorizer.min_df else max((self.vectorizer.min_df + 1) / num_docs, 0.95)
                logger.debug(
                    "Adjusting max_df from %.2f to %.2f for small dataset (n=%d, min_df=%d)",
                    self.vectorizer.max_df,
                    adjusted_max_df,
                    num_docs,
                    self.vectorizer.min_df,
                )
                # Create new vectorizer with adjusted max_df
                self.vectorizer = TfidfVectorizer(
                    max_features=self.max_features,
                    ngram_range=self.ngram_range,
                    min_df=self.min_df,
                    max_df=adjusted_max_df,
                    lowercase=True,
                    strip_accents="unicode",
                    analyzer="word",
                    token_pattern=r"(?u)\b\w+\b",  # noqa: S106
                )

        self.vectorizer.fit(titles)
        self._fitted = True
        logger.debug("TitleVectorizer fitted successfully")
        return self

    def transform(self, titles: list[str]) -> np.ndarray | csr_matrix:
        """Transform titles into vector matrix.

        This method converts a list of titles into a vector matrix where
        each row is a title and each column is a feature (term).

        Args:
            titles: List of title strings to vectorize.

        Returns:
            Vector matrix of shape (n_titles, n_features).
            Returns sparse matrix (csr_matrix) for efficiency, which can be
            converted to dense array with .toarray() if needed.

        Raises:
            ValueError: If vectorizer has not been fitted yet.

        Example:
            >>> vectorizer = TitleVectorizer()
            >>> vectorizer.fit(["Attack on Titan", "Naruto"])
            >>> vectors = vectorizer.transform(["Attack on Titan Season 2"])
            >>> vectors.shape[0]
            1
        """
        if not self._fitted:
            msg = "Vectorizer must be fitted before transform. Call fit() first."
            raise ValueError(msg)

        logger.debug("Transforming %d titles to vectors", len(titles))
        vectors = self.vectorizer.transform(titles)
        logger.debug("Transformed to matrix shape: %s", vectors.shape)
        return vectors

    def fit_transform(self, titles: list[str]) -> np.ndarray | csr_matrix:
        """Fit the vectorizer and transform titles in one step.

        This is a convenience method that combines fit() and transform().

        Args:
            titles: List of title strings to fit and transform.

        Returns:
            Vector matrix of shape (n_titles, n_features).

        Example:
            >>> vectorizer = TitleVectorizer()
            >>> titles = ["Attack on Titan", "Attack on Titan Season 2"]
            >>> vectors = vectorizer.fit_transform(titles)
            >>> vectors.shape[0]
            2
        """
        return self.fit(titles).transform(titles)

    def get_feature_names(self) -> list[str]:
        """Get the feature names (terms) learned during fitting.

        Returns:
            List of feature names (terms) in the order they appear in vectors.

        Raises:
            ValueError: If vectorizer has not been fitted yet.

        Example:
            >>> vectorizer = TitleVectorizer()
            >>> vectorizer.fit(["Attack on Titan"])
            >>> features = vectorizer.get_feature_names()
            >>> "attack" in features
            True
        """
        if not self._fitted:
            msg = "Vectorizer must be fitted before getting feature names. Call fit() first."
            raise ValueError(msg)

        return cast(list[str], self.vectorizer.get_feature_names_out().tolist())

    def get_vocabulary_size(self) -> int:
        """Get the size of the learned vocabulary.

        Returns:
            Number of unique features (terms) in the vocabulary.

        Raises:
            ValueError: If vectorizer has not been fitted yet.

        Example:
            >>> vectorizer = TitleVectorizer()
            >>> vectorizer.fit(["Attack on Titan", "Naruto"])
            >>> vocab_size = vectorizer.get_vocabulary_size()
            >>> vocab_size > 0
            True
        """
        if not self._fitted:
            msg = "Vectorizer must be fitted before getting vocabulary size. Call fit() first."
            raise ValueError(msg)

        return len(self.vectorizer.vocabulary_)
