"""Policy configuration for TrafficIQ agent."""

from dataclasses import dataclass


@dataclass
class PolicyConfig:
    """Configuration for decision policies."""
    
    # Confidence thresholds
    MIN_VEHICLE_CONFIDENCE_FOR_SKIP_OCR: float = 0.70
    """Confidence needed to skip OCR fallback"""
    
    MIN_PLATE_CONFIDENCE_FOR_BOLO: float = 0.60
    """Minimum plate confidence required for BOLO lookup"""
    
    MIN_BOLO_CONFIDENCE_FOR_MATCH: float = 0.50
    """Minimum BOLO confidence to consider a match"""
    
    # Image quality thresholds
    NIGHT_QUALITY_PENALTY: float = 0.15
    """Confidence reduction for night-time images"""
    
    BLUR_QUALITY_PENALTY: float = 0.20
    """Confidence reduction for blurry images"""
    
    # Priority assignment
    P0_THRESHOLDS: dict = None
    """P0 (Critical): BOLO match + high confidence"""
    
    P1_THRESHOLDS: dict = None
    """P1 (Medium): BOLO match + lower confidence"""
    
    P2_THRESHOLDS: dict = None
    """P2 (Low): No BOLO match"""
    
    def __post_init__(self):
        """Set default threshold dicts."""
        if self.P0_THRESHOLDS is None:
            self.P0_THRESHOLDS = {
                "bolo_match": True,
                "min_confidence": 0.70,
            }
        if self.P1_THRESHOLDS is None:
            self.P1_THRESHOLDS = {
                "bolo_match": True,
                "min_confidence": 0.50,
            }
        if self.P2_THRESHOLDS is None:
            self.P2_THRESHOLDS = {
                "bolo_match": False,
            }

    def should_use_ocr_fallback(
        self, 
        vehicle_confidence: float,
        image_condition: str
    ) -> bool:
        """
        Determine if OCR fallback should be used.
        
        Returns True if:
        - Vehicle confidence is below threshold OR
        - Image quality is degraded (night, blur, etc.)
        """
        if vehicle_confidence < self.MIN_VEHICLE_CONFIDENCE_FOR_SKIP_OCR:
            return True
        
        degraded_conditions = ["night", "blur", "rain", "low_res"]
        if any(cond in image_condition.lower() for cond in degraded_conditions):
            return True
        
        return False

    def assign_priority(self, bolo_match: bool, confidence: float) -> str:
        """
        Assign priority based on BOLO match and confidence.
        
        Returns "P0", "P1", or "P2"
        """
        if bolo_match:
            if confidence >= self.P0_THRESHOLDS["min_confidence"]:
                return "P0"
            elif confidence >= self.P1_THRESHOLDS["min_confidence"]:
                return "P1"
            else:
                return "P2"
        else:
            return "P2"

    @staticmethod
    def default() -> "PolicyConfig":
        """Get default policy configuration."""
        return PolicyConfig()
