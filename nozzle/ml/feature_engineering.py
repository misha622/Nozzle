"""Feature extraction from alerts for ML clustering."""

import re
from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class AlertFeatureExtractor:
    """Extracts numerical features from alert fields for ML models."""

    def __init__(self, max_features: int = 500):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            ngram_range=(1, 2),
            analyzer="char_wb",
        )
        self._fitted = False

    def fit(self, descriptions: List[str]) -> "AlertFeatureExtractor":
        """Fit TF-IDF vectorizer on alert descriptions."""
        self.vectorizer.fit(descriptions)
        self._fitted = True
        return self

    def transform(self, descriptions: List[str]) -> np.ndarray:
        """Transform descriptions to TF-IDF matrix."""
        if not self._fitted:
            raise ValueError("Vectorizer not fitted. Call fit() first.")
        return self.vectorizer.transform(descriptions).toarray()

    def fit_transform(self, descriptions: List[str]) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(descriptions)
        return self.transform(descriptions)

    @staticmethod
    def extract_numerical_features(alert) -> np.ndarray:
        """Extract hand-crafted numerical features from a NormalizedAlert."""
        features = [
            alert.severity or 0,
            1 if alert.agent_name else 0,
            1 if alert.source_ip else 0,
            1 if alert.destination_ip else 0,
            len(alert.description) if alert.description else 0,
            len(alert.full_log) if alert.full_log else 0,
            alert.severity / 15.0,  # Normalized severity
        ]
        return np.array(features, dtype=np.float32)

    @staticmethod
    def clean_description(desc: str) -> str:
        """Clean alert description for better text matching."""
        if not desc:
            return ""
        # Remove IP addresses
        desc = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "<IP>", desc)
        # Remove port numbers
        desc = re.sub(r"port \d+", "port <PORT>", desc)
        # Remove timestamps
        desc = re.sub(r"\d{2}:\d{2}:\d{2}", "<TIME>", desc)
        # Remove hex strings
        desc = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", desc)
        return desc.lower().strip()
