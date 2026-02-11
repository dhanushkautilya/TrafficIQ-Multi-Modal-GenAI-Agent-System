"""BOLO (Be On Lookout) database client."""

import logging
from typing import Optional
from app.common.schemas import BOLOMatch
from app.common.utils import generate_id

logger = logging.getLogger(__name__)

# Mock BOLO watchlist
BOLO_WATCH_MAKES = ["Honda", "Toyota"]
BOLO_WATCH_PLATES_ENDING = ["7", "99"]
BOLO_WATCH_PLATE_PREFIX = ["ABC", "XYZ"]


class BOLOClient:
    """Client for BOLO database lookups."""

    def __init__(self):
        """Initialize BOLO client."""
        logger.info("BOLO client initialized in MOCK mode")

    def lookup(
        self,
        make: str,
        model: str,
        year_range: str,
        plate: Optional[str] = None,
        location: Optional[str] = None,
    ) -> BOLOMatch:
        """
        Lookup vehicle in BOLO database.
        
        Args:
            make: Vehicle make
            model: Vehicle model
            year_range: Year range
            plate: License plate (optional)
            location: Geographic location (optional)
            
        Returns:
            BOLOMatch indicating if a match was found
        """
        return self._lookup_mock(make, model, year_range, plate, location)

    def _lookup_mock(
        self,
        make: str,
        model: str,
        year_range: str,
        plate: Optional[str] = None,
        location: Optional[str] = None,
    ) -> BOLOMatch:
        """Mock BOLO lookup with deterministic matches."""
        
        is_match = False
        reason = ""
        match_confidence = 0.0
        bolo_id = None
        
        # Check make against watchlist
        if make in BOLO_WATCH_MAKES:
            is_match = True
            reason = f"Make '{make}' on watchlist"
            match_confidence = 0.85
            bolo_id = generate_id("BOLO-MAKE")
        
        # Check plate pattern
        if plate and not is_match:
            for ending in BOLO_WATCH_PLATES_ENDING:
                if plate.endswith(ending):
                    is_match = True
                    reason = f"Plate pattern match ({ending})"
                    match_confidence = 0.75
                    bolo_id = generate_id("BOLO-PLATE")
                    break
        
        # Check plate prefix (secondary check)
        if plate and not is_match:
            for prefix in BOLO_WATCH_PLATE_PREFIX:
                if plate.startswith(prefix):
                    is_match = True
                    reason = f"Plate prefix match ({prefix})"
                    match_confidence = 0.70
                    bolo_id = generate_id("BOLO-PREFIX")
                    break
        
        if not is_match:
            reason = "No match found"
        
        match = BOLOMatch(
            is_match=is_match,
            make=make if is_match else None,
            model=model if is_match else None,
            year_range=year_range if is_match else None,
            plate=plate if is_match else None,
            reason=reason,
            match_confidence=match_confidence,
            bolo_record_id=bolo_id,
        )
        
        logger.debug(
            f"BOLO lookup - Make: {make}, Plate: {plate}, Match: {is_match}, "
            f"Reason: {reason}"
        )
        return match
