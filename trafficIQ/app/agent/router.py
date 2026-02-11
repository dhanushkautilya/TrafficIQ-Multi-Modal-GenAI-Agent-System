"""Agent router and orchestration logic."""

import logging
import time
from datetime import datetime
from typing import Optional

from app.common.schemas import (
    VehiclePrediction,
    PlateResult,
    BOLOMatch,
    AgentResult,
    Priority,
)
from app.tools.vertex_client import VertexAIClient
from app.tools.ocr_client import OCRClient
from app.tools.bolo_client import BOLOClient
from app.tools.evidence import EvidencePacketBuilder
from app.tools.case_client import CaseClient
from app.agent.policy import PolicyConfig
from app.agent.prompts import Prompts
from app.common.config import get_config

logger = logging.getLogger(__name__)


class TrafficIQAgent:
    """Main orchestration agent that routes vehicle identification pipeline."""

    def __init__(
        self,
        config: Optional[object] = None,
        policy: Optional[PolicyConfig] = None,
    ):
        """
        Initialize agent with tools and policy.
        
        Args:
            config: Application configuration
            policy: Policy configuration for decision-making
        """
        self.config = config or get_config()
        self.policy = policy or PolicyConfig.default()
        
        # Initialize tools
        self.vertex_client = VertexAIClient(self.config)
        self.ocr_client = OCRClient()
        self.bolo_client = BOLOClient()
        self.evidence_builder = EvidencePacketBuilder(self.config)
        self.case_client = CaseClient(self.config)
        
        logger.info("TrafficIQAgent initialized")

    def run(
        self,
        image_uri: str,
        location: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> AgentResult:
        """
        Run complete vehicle identification and case creation pipeline.
        
        Args:
            image_uri: Image URI or path
            location: Optional location information
            timestamp: Optional timestamp
            
        Returns:
            AgentResult with all processing steps and outcomes
        """
        start_time = time.time()
        processing_steps = []
        ocr_fallback_used = False
        plate_result = None
        bolo_match = None
        
        try:
            logger.info(f"Starting agent run for {image_uri}")
            
            # Step 1: Vehicle prediction
            processing_steps.append("vehicle_prediction_request")
            logger.debug("Step 1: Requesting vehicle prediction from Vertex AI")
            
            vehicle_prediction = self.vertex_client.predict_vehicle(image_uri)
            processing_steps.append("vehicle_prediction_received")
            
            logger.info(
                f"Vehicle prediction: {vehicle_prediction.make} {vehicle_prediction.model} "
                f"(confidence: {vehicle_prediction.confidence:.2f})"
            )
            
            # Step 2: Conditional OCR fallback
            should_ocr = self.policy.should_use_ocr_fallback(
                vehicle_prediction.confidence,
                vehicle_prediction.image_condition,
            )
            
            if should_ocr:
                processing_steps.append("ocr_fallback_triggered")
                logger.debug(
                    f"Step 2: OCR fallback triggered (confidence: {vehicle_prediction.confidence:.2f}, "
                    f"condition: {vehicle_prediction.image_condition})"
                )
                
                plate_result = self.ocr_client.extract_plate(image_uri)
                ocr_fallback_used = True
                processing_steps.append("ocr_plate_extracted")
                
                logger.info(f"OCR plate extracted: {plate_result.plate_number} "
                           f"(confidence: {plate_result.confidence:.2f})")
            else:
                processing_steps.append("ocr_skipped")
                logger.debug("Step 2: OCR skipped (confidence sufficient)")
            
            # Step 3: BOLO database lookup
            processing_steps.append("bolo_lookup_started")
            logger.debug("Step 3: Checking BOLO database")
            
            bolo_match = self.bolo_client.lookup(
                make=vehicle_prediction.make,
                model=vehicle_prediction.model,
                year_range=vehicle_prediction.year_range,
                plate=plate_result.plate_number if plate_result else None,
                location=location,
            )
            processing_steps.append("bolo_lookup_completed")
            
            logger.info(f"BOLO lookup: match={bolo_match.is_match}, reason={bolo_match.reason}")
            
            # Step 4: Priority assignment
            processing_steps.append("priority_assignment")
            priority = self._assign_priority(vehicle_prediction, bolo_match)
            
            logger.info(f"Priority assigned: {priority}")
            
            # Step 5: Evidence packet building
            processing_steps.append("evidence_packet_building")
            logger.debug("Step 5: Building evidence packet")
            
            evidence_packet = self.evidence_builder.build(
                image_uri=image_uri,
                vehicle_prediction=vehicle_prediction,
                plate_result=plate_result,
                bolo_match=bolo_match,
                location=location,
                notes=f"OCR fallback used: {ocr_fallback_used}, BOLO match: {bolo_match.is_match}",
            )
            processing_steps.append("evidence_packet_created")
            
            # Step 6: Case creation
            processing_steps.append("case_creation")
            logger.debug("Step 6: Creating case record")
            
            case_summary = self._generate_case_summary(
                evidence_packet,
                priority,
                vehicle_prediction,
                bolo_match,
                ocr_fallback_used,
            )
            
            case_record = self.case_client.create_case(
                summary=case_summary,
                priority=priority,
                evidence_path=evidence_packet.evidence_path,
                vehicle_make=vehicle_prediction.make,
                vehicle_model=vehicle_prediction.model,
                vehicle_year_range=vehicle_prediction.year_range,
                plate_number=plate_result.plate_number if plate_result else None,
                location=location,
            )
            processing_steps.append("case_created")
            
            logger.info(f"Case created: {case_record.case_id}")
            
            # Build result
            elapsed_ms = (time.time() - start_time) * 1000
            
            result = AgentResult(
                image_uri=image_uri,
                vehicle_prediction=vehicle_prediction,
                ocr_fallback_used=ocr_fallback_used,
                plate_result=plate_result,
                bolo_match=bolo_match,
                priority=priority,
                case_record=case_record,
                processing_steps=processing_steps,
                total_processing_time_ms=elapsed_ms,
                location=location,
                metadata={
                    "model_version": vehicle_prediction.metadata.get("model_version"),
                    "steps_count": len(processing_steps),
                },
            )
            
            logger.info(f"Agent run completed in {elapsed_ms:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Agent run failed: {str(e)}", exc_info=True)
            raise

    def _assign_priority(
        self,
        vehicle_prediction: VehiclePrediction,
        bolo_match: BOLOMatch,
    ) -> Priority:
        """
        Assign priority based on policy.
        
        Args:
            vehicle_prediction: Vehicle prediction result
            bolo_match: BOLO database match result
            
        Returns:
            Priority level (P0, P1, or P2)
        """
        if bolo_match.is_match:
            # Use prediction confidence as primary factor
            if vehicle_prediction.confidence >= 0.70:
                return Priority.P0
            elif vehicle_prediction.confidence >= 0.50:
                return Priority.P1
            else:
                return Priority.P2
        else:
            return Priority.P2

    def _generate_case_summary(
        self,
        evidence_packet,
        priority: Priority,
        vehicle_prediction: VehiclePrediction,
        bolo_match: BOLOMatch,
        ocr_used: bool,
    ) -> str:
        """Generate case summary text."""
        return (
            f"Vehicle ID: {vehicle_prediction.make} {vehicle_prediction.model} "
            f"({vehicle_prediction.year_range}) - {vehicle_prediction.color} {vehicle_prediction.body_type}. "
            f"Confidence: {vehicle_prediction.confidence:.1%}. "
            f"BOLO Match: {bolo_match.is_match} ({bolo_match.reason}). "
            f"OCR used: {ocr_used}. "
            f"Priority: {priority}."
        )
