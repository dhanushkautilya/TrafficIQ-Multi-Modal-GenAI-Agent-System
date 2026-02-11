"""OCR client for license plate extraction."""

import logging
import re
from typing import Optional
from app.common.schemas import PlateResult
from app.common.utils import deterministic_hash

logger = logging.getLogger(__name__)

# Realistic license plate patterns
PLATE_PATTERNS = [
    "ABC{num}",
    "{num}XYZ",
    "{num}{upper}{num}",
    "{upper}{num}{upper}",
]

COLORS = ["white", "yellow", "red"]


class OCRClient:
    """Client for OCR-based plate extraction."""

    def __init__(self):
        """Initialize OCR client."""
        logger.info("OCR client initialized in MOCK mode")

    def extract_plate(self, image_uri: str) -> PlateResult:
        """
        Extract license plate from image using OCR.
        
        Args:
            image_uri: Path or URL to image
            
        Returns:
            PlateResult with plate number and confidence
        """
        return self._extract_plate_mock(image_uri)

    def _extract_plate_mock(self, image_uri: str) -> PlateResult:
        """Mock plate extraction with deterministic output."""
        # Generate deterministic plate based on URI
        hash_val = deterministic_hash(image_uri)
        
        # Pattern selection
        pattern_idx = int(hash_val * len(PLATE_PATTERNS))
        pattern = PLATE_PATTERNS[pattern_idx % len(PLATE_PATTERNS)]
        
        # Generate plate number
        plate = self._generate_plate(pattern, image_uri)
        
        # Confidence degradation for poor conditions
        confidence = hash_val * 0.95  # Mock confidence around 95%
        if "night" in image_uri.lower():
            confidence *= 0.8
        if "blur" in image_uri.lower():
            confidence *= 0.85
        if "rain" in image_uri.lower():
            confidence *= 0.9
        
        result = PlateResult(
            plate_number=plate,
            confidence=min(confidence, 1.0),
            image_uri=image_uri,
        )
        
        logger.debug(f"Mock plate extraction: {result.plate_number} (conf: {result.confidence:.2f})")
        return result

    def _generate_plate(self, pattern: str, seed: str) -> str:
        """Generate realistic plate number."""
        import random
        
        # Seed random for determinism
        hash_val = int(deterministic_hash(seed) * 10000)
        random.seed(hash_val)
        
        plate = pattern
        num_count = pattern.count("{num}")
        for _ in range(num_count):
            plate = plate.replace("{num}", str(random.randint(0, 9)), 1)
        
        upper_count = pattern.count("{upper}")
        for _ in range(upper_count):
            plate = plate.replace("{upper}", chr(65 + random.randint(0, 25)), 1)
        
        # US-style format typically 2-3 letters + 3-4 numbers
        if random.random() > 0.5:
            plate = f"{chr(65 + random.randint(0, 25))}{chr(65 + random.randint(0, 25))}{random.randint(1000, 9999)}"
        
        return plate.strip()
