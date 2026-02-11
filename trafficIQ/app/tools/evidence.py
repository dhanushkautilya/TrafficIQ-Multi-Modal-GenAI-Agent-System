"""Evidence packet builder for case documentation."""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.common.schemas import EvidencePacket, VehiclePrediction, PlateResult, BOLOMatch
from app.common.utils import generate_id
from app.common.config import get_config

logger = logging.getLogger(__name__)


class EvidencePacketBuilder:
    """Builder for evidence packets."""

    def __init__(self, config: Optional[object] = None):
        """Initialize evidence builder."""
        self.config = config or get_config()
        self.artifacts_dir = self.config.setup_artifacts_dir()

    def build(
        self,
        image_uri: str,
        vehicle_prediction: VehiclePrediction,
        plate_result: Optional[PlateResult] = None,
        bolo_match: Optional[BOLOMatch] = None,
        location: Optional[str] = None,
        notes: str = "",
    ) -> EvidencePacket:
        """
        Build and save evidence packet.
        
        Args:
            image_uri: Source image URI
            vehicle_prediction: Vehicle prediction result
            plate_result: Optional OCR plate result
            bolo_match: Optional BOLO match result
            location: Optional location information
            notes: Additional notes
            
        Returns:
            EvidencePacket with path to saved evidence
        """
        
        packet_id = generate_id("EV")
        timestamp = datetime.utcnow()
        
        # Prepare packet data
        packet_data = {
            "packet_id": packet_id,
            "timestamp": timestamp.isoformat(),
            "image_uri": image_uri,
            "location": location,
            "notes": notes,
            "vehicle_prediction": vehicle_prediction.model_dump(),
            "plate_result": plate_result.model_dump() if plate_result else None,
            "bolo_match": bolo_match.model_dump() if bolo_match else None,
        }
        
        # Save to file
        evidence_path = self._save_evidence(packet_id, packet_data)
        
        # Create packet object
        packet = EvidencePacket(
            packet_id=packet_id,
            image_uri=image_uri,
            vehicle_prediction=vehicle_prediction,
            plate_result=plate_result,
            bolo_match=bolo_match,
            location=location,
            notes=notes,
            evidence_path=evidence_path,
            metadata={
                "saved_at": timestamp.isoformat(),
                "saved_to_local": not self.config.use_gcs,
            },
        )
        
        logger.info(f"Evidence packet created: {packet_id} -> {evidence_path}")
        return packet

    def _save_evidence(self, packet_id: str, packet_data: dict) -> str:
        """Save evidence packet to storage."""
        
        if self.config.use_gcs:
            return self._save_to_gcs(packet_id, packet_data)
        else:
            return self._save_to_local(packet_id, packet_data)

    def _save_to_local(self, packet_id: str, packet_data: dict) -> str:
        """Save evidence packet locally."""
        filename = f"{packet_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.artifacts_dir / filename
        
        try:
            with open(filepath, "w") as f:
                json.dump(packet_data, f, indent=2, default=str)
            logger.info(f"Evidence saved locally: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save evidence locally: {str(e)}")
            raise

    def _save_to_gcs(self, packet_id: str, packet_data: dict) -> str:
        """Save evidence packet to GCS."""
        if not self.config.gcs_bucket:
            raise ValueError("GCS_BUCKET not configured")
        
        try:
            from google.cloud import storage
            
            client = storage.Client(project=self.config.gcp_project)
            bucket = client.bucket(self.config.gcs_bucket)
            
            filename = f"evidence/{packet_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            blob = bucket.blob(filename)
            
            blob.upload_from_string(
                json.dumps(packet_data, indent=2, default=str),
                content_type="application/json",
            )
            
            gcs_path = f"gs://{self.config.gcs_bucket}/{filename}"
            logger.info(f"Evidence saved to GCS: {gcs_path}")
            return gcs_path
            
        except ImportError:
            logger.error("google-cloud-storage not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to save evidence to GCS: {str(e)}")
            raise
