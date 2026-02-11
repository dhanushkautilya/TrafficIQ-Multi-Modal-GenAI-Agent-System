"""Prompts and templates for TrafficIQ agent."""


class Prompts:
    """Collection of prompts for the agent."""

    SYSTEM_PROMPT = """You are TrafficIQ, an AI agent specialized in multi-modal vehicle identification from traffic camera imagery.

Your role is to:
1. Analyze vehicle images to identify make, model, year, color, and body type
2. Extract license plates when image quality allows
3. Cross-reference against known BOLO (Be On Lookout) databases
4. Generate priority-based case records for human investigators
5. Maintain high accuracy while managing uncertainty gracefully

Always:
- Acknowledge confidence levels honestly
- Use structured data formats (JSON)
- Provide clear reasoning for decisions
- Flag when image quality degrades model performance
"""

    ANALYZE_INSTRUCTION = """Analyze the following vehicle image and provide structured output:

Image URI: {image_uri}
Location: {location}
Timestamp: {timestamp}

Please identify:
1. Vehicle make (manufacturer)
2. Vehicle model
3. Approximate year range
4. Primary color
5. Body type (sedan, SUV, truck, etc.)
6. Your confidence level (0-1)
7. Notable features or damage

Format your response as JSON with fields: make, model, year_range, color, body_type, confidence, features.
"""

    OCR_INSTRUCTION = """Extract the license plate number from this image if visible:

Image URI: {image_uri}
Image Condition: {image_condition}

Provide:
1. Plate number (or "UNREADABLE")
2. Your confidence (0-1)
3. Plate region description

Format as JSON with fields: plate_number, confidence, region_description.
"""

    BOLO_INSTRUCTION = """Check the following vehicle against known watchlists:

Make: {make}
Model: {model}
Year: {year_range}
Plate: {plate}
Location: {location}

Determine:
1. Is there a match?
2. Match confidence (0-1)
3. Reason for match/no-match

Format as JSON with fields: is_match, match_confidence, reason.
"""

    PRIORITY_INSTRUCTION = """Assign priority to this case based on:

BOLO Match: {bolo_match}
Prediction Confidence: {pred_confidence}
BOLO Confidence: {bolo_confidence}
Image Quality: {image_quality}

Rules:
- P0: BOLO match + prediction_confidence >= 0.70
- P1: BOLO match + prediction_confidence < 0.70
- P2: No BOLO match

Return JSON with field: priority
"""

    CASE_SUMMARY_TEMPLATE = """Case Summary: {case_id}
================

Vehicle Identification:
- Make/Model/Year: {make}/{model}/{year_range}
- Color: {color}
- Body Type: {body_type}
- Confidence: {confidence:.1%}

License Plate: {plate}
Location: {location}
Timestamp: {timestamp}

BOLO Lookup Result:
- Match: {bolo_match}
- Reason: {bolo_reason}

Image Quality: {image_quality}

Priority: {priority}

Evidence Path: {evidence_path}

Notes: {notes}
"""

    @staticmethod
    def get_analyze_prompt(image_uri: str, location: str = "", timestamp: str = "") -> str:
        """Get vehicle analysis prompt."""
        return Prompts.ANALYZE_INSTRUCTION.format(
            image_uri=image_uri,
            location=location or "Unknown",
            timestamp=timestamp or "Unknown",
        )

    @staticmethod
    def get_ocr_prompt(image_uri: str, image_condition: str = "") -> str:
        """Get OCR extraction prompt."""
        return Prompts.OCR_INSTRUCTION.format(
            image_uri=image_uri,
            image_condition=image_condition or "Unknown",
        )

    @staticmethod
    def get_bolo_prompt(
        make: str,
        model: str,
        year_range: str,
        plate: str = "",
        location: str = "",
    ) -> str:
        """Get BOLO lookup prompt."""
        return Prompts.BOLO_INSTRUCTION.format(
            make=make,
            model=model,
            year_range=year_range,
            plate=plate or "Unknown",
            location=location or "Unknown",
        )

    @staticmethod
    def get_priority_prompt(
        bolo_match: bool,
        pred_confidence: float,
        bolo_confidence: float,
        image_quality: str,
    ) -> str:
        """Get priority assignment prompt."""
        return Prompts.PRIORITY_INSTRUCTION.format(
            bolo_match="Yes" if bolo_match else "No",
            pred_confidence=f"{pred_confidence:.2f}",
            bolo_confidence=f"{bolo_confidence:.2f}",
            image_quality=image_quality,
        )
