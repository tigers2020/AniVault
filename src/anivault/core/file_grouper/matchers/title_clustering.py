"""Title clustering module using DBSCAN.

This module provides functionality to cluster similar titles together
using density-based clustering (DBSCAN) algorithm.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sklearn.cluster import DBSCAN

from anivault.core.file_grouper.matchers.title_vectorizer import TitleVectorizer

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


class TitleClustering:
    """Clusters titles using DBSCAN algorithm.

    This class uses DBSCAN (Density-Based Spatial Clustering of Applications
    with Noise) to automatically group similar titles into clusters. Titles
    that are close together in the vector space (based on cosine distance)
    are grouped into the same cluster.

    Attributes:
        vectorizer: TitleVectorizer instance for converting titles to vectors.
        eps: Maximum distance between two samples for them to be considered
             as in the same neighborhood. Default 0.5 (cosine distance).
        min_samples: Minimum number of samples in a neighborhood for a point
                     to be considered a core point. Default 2.
        metric: Distance metric to use. Default 'cosine' (1 - cosine similarity).

    Example:
        >>> clustering = TitleClustering(eps=0.5, min_samples=2)
        >>> titles = ["Attack on Titan", "Attack on Titan S2", "Naruto"]
        >>> labels = clustering.fit_predict(titles)
        >>> labels
        array([0, 0, 1])  # First two in same cluster, third in different cluster
    """

    def __init__(
        self,
        eps: float = 0.5,
        min_samples: int = 2,
        metric: str = "cosine",
        vectorizer: TitleVectorizer | None = None,
    ) -> None:
        """Initialize TitleClustering.

        Args:
            eps: Maximum distance between two samples for them to be considered
                 as in the same neighborhood. For cosine distance, typical values
                 are 0.3-0.7. Lower values create more clusters, higher values
                 merge more titles. Default 0.5.
            min_samples: Minimum number of samples in a neighborhood for a point
                        to be considered a core point. Default 2 (allows pairs).
            metric: Distance metric to use. 'cosine' is recommended for TF-IDF
                   vectors. Default 'cosine'.
            vectorizer: Optional TitleVectorizer instance. If None, creates a
                       new one with default parameters.

        Example:
            >>> clustering = TitleClustering(eps=0.4, min_samples=3)
            >>> clustering.eps
            0.4
        """
        self.eps = eps
        self.min_samples = min_samples
        self.metric = metric

        # Initialize vectorizer if not provided
        self.vectorizer = vectorizer if vectorizer is not None else TitleVectorizer()

        # DBSCAN instance (will be created during fit)
        self._dbscan: DBSCAN | None = None
        self._fitted = False

        logger.debug(
            "TitleClustering initialized: eps=%.2f, min_samples=%d, metric=%s",
            eps,
            min_samples,
            metric,
        )

    def fit(self, titles: list[str]) -> TitleClustering:
        """Fit the clustering model to titles.

        This method vectorizes the titles and fits the DBSCAN model.
        Must be called before predict().

        Args:
            titles: List of title strings to cluster.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If titles list is empty.

        Example:
            >>> clustering = TitleClustering()
            >>> titles = ["Attack on Titan", "Attack on Titan S2"]
            >>> clustering.fit(titles)
            <TitleClustering object>
        """
        if not titles:
            msg = "Cannot fit clustering on empty title list"
            raise ValueError(msg)

        logger.debug("Fitting TitleClustering on %d titles", len(titles))

        # Vectorize titles
        vectors = self.vectorizer.fit_transform(titles)

        # Convert sparse matrix to dense if needed for DBSCAN
        vectors_dense = vectors.toarray() if hasattr(vectors, "toarray") else vectors

        # Initialize and fit DBSCAN
        # Note: DBSCAN with cosine metric requires precomputed distances
        # or we can use 'cosine' metric directly (sklearn handles it)
        self._dbscan = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric=self.metric,
            algorithm="auto",  # Let sklearn choose best algorithm
        )

        self._dbscan.fit(vectors_dense)
        self._fitted = True

        # Log clustering results
        n_clusters = len(set(self._dbscan.labels_)) - (1 if -1 in self._dbscan.labels_ else 0)
        n_noise = list(self._dbscan.labels_).count(-1)
        logger.info(
            "DBSCAN clustering completed: %d clusters, %d noise points (eps=%.2f, min_samples=%d)",
            n_clusters,
            n_noise,
            self.eps,
            self.min_samples,
        )

        return self

    def predict(self, titles: list[str]) -> np.ndarray:
        """Predict cluster labels for new titles.

        Note: DBSCAN doesn't support prediction for new points directly.
        This method fits the model on the new titles and returns labels.
        For true prediction, you would need to use a different approach
        (e.g., assign to nearest cluster).

        Args:
            titles: List of title strings to cluster.

        Returns:
            Array of cluster labels. -1 indicates noise (outlier).

        Raises:
            ValueError: If model has not been fitted yet.

        Example:
            >>> clustering = TitleClustering()
            >>> clustering.fit(["Attack on Titan", "Naruto"])
            >>> labels = clustering.predict(["Attack on Titan S2"])
            >>> labels
            array([0])  # Assigned to cluster 0
        """
        if not self._fitted:
            msg = "Clustering must be fitted before predict. Call fit() first."
            raise ValueError(msg)

        logger.debug("Predicting clusters for %d titles", len(titles))

        # DBSCAN doesn't support predict, so we need to refit or use approximate assignment
        # For now, we'll refit on the new data (this is a limitation of DBSCAN)
        # In practice, you might want to assign new points to nearest cluster
        logger.warning("DBSCAN doesn't support direct prediction. Refitting on new titles.")
        return self.fit(titles).labels_

    @property
    def labels_(self) -> np.ndarray:
        """Get cluster labels from the fitted model.

        Returns:
            Array of cluster labels. -1 indicates noise (outlier).

        Raises:
            ValueError: If model has not been fitted yet.

        Example:
            >>> clustering = TitleClustering()
            >>> clustering.fit(["Attack on Titan", "Naruto"])
            >>> labels = clustering.labels_
            >>> len(labels)
            2
        """
        if not self._fitted or self._dbscan is None:
            msg = "Clustering must be fitted before accessing labels. Call fit() first."
            raise ValueError(msg)

        return self._dbscan.labels_

    def fit_predict(self, titles: list[str]) -> np.ndarray:
        """Fit the model and predict cluster labels in one step.

        Args:
            titles: List of title strings to cluster.

        Returns:
            Array of cluster labels. -1 indicates noise (outlier).

        Example:
            >>> clustering = TitleClustering()
            >>> titles = ["Attack on Titan", "Attack on Titan S2", "Naruto"]
            >>> labels = clustering.fit_predict(titles)
            >>> labels
            array([0, 0, 1])
        """
        return self.fit(titles).labels_

    def get_cluster_info(self) -> dict[int, int]:
        """Get information about each cluster.

        Returns:
            Dictionary mapping cluster label to number of titles in that cluster.
            Label -1 represents noise points.

        Raises:
            ValueError: If model has not been fitted yet.

        Example:
            >>> clustering = TitleClustering()
            >>> clustering.fit(["Attack on Titan", "Attack on Titan S2", "Naruto"])
            >>> info = clustering.get_cluster_info()
            >>> info
            {0: 2, 1: 1}  # Cluster 0 has 2 titles, cluster 1 has 1 title
        """
        if not self._fitted:
            msg = "Clustering must be fitted before getting cluster info. Call fit() first."
            raise ValueError(msg)

        labels = self.labels_
        cluster_counts: dict[int, int] = {}
        for label in labels:
            cluster_counts[label] = cluster_counts.get(label, 0) + 1

        return cluster_counts
