"""Pydantic schemas for TrafficIQ API and data models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class VehicleConfidence(str, Enum):
    """Confidence levels for vehicle predictions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Priority(str, Enum):
    """Priority levels for cases."""
    P0 = "P0"  # Critical match, high confidence
    P1 = "P1"  # Match but lower confidence
    P2 = "P2"  # No match


class VehiclePrediction(BaseModel):
    """Vehicle prediction from Vertex AI model."""
    image_uri: str
    make: str = Field(..., description="Vehicle make (Honda, Toyota, etc.)")
    model: str = Field(..., description="Vehicle model (Civic, Camry, etc.)")
    year_range: str = Field(..., description="Year range (2020-2023, etc.)")
    color: str = Field(..., description="Vehicle color")
    body_type: str = Field(..., description="Body type (sedan, SUV, truck, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    image_condition: str = Field(default="clear", description="Image quality (clear, night, blur, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PlateResult(BaseModel):
    """OCR plate extraction result."""
    plate_number: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    image_uri: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BOLOMatch(BaseModel):
    """BOLO (Be On Lookout) database match result."""
    is_match: bool
    make: Optional[str] = None
    model: Optional[str] = None
    year_range: Optional[str] = None
    plate: Optional[str] = None
    reason: str = Field(default="", description="Reason for match or no-match")
    match_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bolo_record_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EvidencePacket(BaseModel):
    """Structured evidence packet for case creation."""
    packet_id: str
    image_uri: str
    vehicle_prediction: VehiclePrediction
    plate_result: Optional[PlateResult] = None
    bolo_match: Optional[BOLOMatch] = None
    location: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: str = ""
    evidence_path: str = Field(..., description="Local or GCS path to saved evidence")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseRecord(BaseModel):
    """Case management record."""
    case_id: str
    priority: Priority
    summary: str
    evidence_path: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year_range: str
    plate_number: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="open")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    """Request for /analyze endpoint."""
    image_uri: str


class AgentRunRequest(BaseModel):
    """Request for /agent/run endpoint."""
    image_uri: str
    location: Optional[str] = None
    timestamp: Optional[datetime] = None


class AgentResult(BaseModel):
    """Complete result from agent orchestration."""
    image_uri: str
    vehicle_prediction: VehiclePrediction
    ocr_fallback_used: bool
    plate_result: Optional[PlateResult] = None
    bolo_match: Optional[BOLOMatch] = None
    priority: Priority
    case_record: Optional[CaseRecord] = None
    processing_steps: List[str] = Field(default_factory=list, description="Steps taken")
    total_processing_time_ms: float = Field(...)
    location: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str
