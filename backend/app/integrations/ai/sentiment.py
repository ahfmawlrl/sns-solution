"""Sentiment analysis — 4-class Korean text classification.

In production, uses fine-tuned KcELECTRA model.
Falls back to keyword-based heuristic when model is unavailable.
"""
import logging
import re

logger = logging.getLogger(__name__)

# Sentiment labels matching the CommentInbox.Sentiment enum
POSITIVE = "positive"
NEUTRAL = "neutral"
NEGATIVE = "negative"
CRISIS = "crisis"

# Simple keyword-based heuristic for fallback
_POSITIVE_KEYWORDS = {
    "좋아요", "감사", "최고", "추천", "좋다", "대박", "응원", "사랑", "멋져",
    "love", "great", "awesome", "amazing", "thanks", "good", "best", "nice",
}
_NEGATIVE_KEYWORDS = {
    "싫어", "별로", "최악", "불만", "실망", "짜증", "나쁘", "후회",
    "bad", "terrible", "worst", "hate", "disappointed", "awful", "poor",
}
_CRISIS_KEYWORDS = {
    "사기", "고소", "신고", "소송", "환불", "피해", "불법", "거짓",
    "fraud", "scam", "lawsuit", "illegal", "refund", "report", "fake",
}


class SentimentAnalyzer:
    """Analyze sentiment of text.

    Supports:
        - KcELECTRA model (when available)
        - Keyword-based heuristic (fallback)
    """

    def __init__(self, use_model: bool = False):
        self.use_model = use_model
        self._model = None

        if use_model:
            try:
                self._load_model()
            except Exception:
                logger.warning("Failed to load sentiment model, falling back to heuristic")
                self.use_model = False

    def _load_model(self):
        """Load KcELECTRA sentiment model. Placeholder for STEP 20."""
        # In production: load fine-tuned KcELECTRA from local path or HuggingFace
        # from transformers import pipeline
        # self._model = pipeline("text-classification", model="path/to/kcelectra-sentiment")
        raise NotImplementedError("KcELECTRA model not yet deployed")

    def analyze(self, text: str) -> tuple[str, float]:
        """Analyze text sentiment.

        Returns:
            (sentiment_label, confidence_score) where label is one of
            "positive", "neutral", "negative", "crisis"
            and score is 0.0 to 1.0
        """
        if self.use_model and self._model:
            return self._analyze_with_model(text)
        return self._analyze_heuristic(text)

    def _analyze_with_model(self, text: str) -> tuple[str, float]:
        """ML model-based analysis. Placeholder."""
        result = self._model(text[:512])  # type: ignore
        label = result[0]["label"]
        score = result[0]["score"]
        return label, score

    def _analyze_heuristic(self, text: str) -> tuple[str, float]:
        """Keyword-based heuristic sentiment analysis."""
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower))

        crisis_hits = len(words & _CRISIS_KEYWORDS)
        negative_hits = len(words & _NEGATIVE_KEYWORDS)
        positive_hits = len(words & _POSITIVE_KEYWORDS)

        if crisis_hits > 0:
            score = min(0.5 + crisis_hits * 0.15, 0.95)
            return CRISIS, score

        if negative_hits > positive_hits:
            score = min(0.5 + negative_hits * 0.1, 0.9)
            return NEGATIVE, score

        if positive_hits > negative_hits:
            score = min(0.5 + positive_hits * 0.1, 0.9)
            return POSITIVE, score

        return NEUTRAL, 0.5

    def analyze_batch(self, texts: list[str]) -> list[tuple[str, float]]:
        """Analyze multiple texts."""
        return [self.analyze(t) for t in texts]


# Global instance (heuristic mode by default)
sentiment_analyzer = SentimentAnalyzer(use_model=False)
