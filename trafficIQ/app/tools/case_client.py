"""Case management client."""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.common.schemas import CaseRecord, Priority
from app.common.utils import generate_id
from app.common.config import get_config

logger = logging.getLogger(__name__)


class CaseClient:
    """Client for case creation and management."""

    def __init__(self, config: Optional[object] = None):
        """Initialize case client."""
        self.config = config or get_config()
        self.artifacts_dir = self.config.setup_artifacts_dir()
        self.cases_file = self.artifacts_dir / "cases.jsonl"
        logger.info("Case client initialized in MOCK mode")

    def create_case(
        self,
        summary: str,
        priority: Priority,
        evidence_path: str,
        vehicle_make: str = "",
        vehicle_model: str = "",
        vehicle_year_range: str = "",
        plate_number: Optional[str] = None,
        location: Optional[str] = None,
    ) -> CaseRecord:
        """
        Create a new case record.
        
        Args:
            summary: Case summary
            priority: Priority level
            evidence_path: Path to evidence packet
            vehicle_make: Vehicle make
            vehicle_model: Vehicle model
            vehicle_year_range: Vehicle year range
            plate_number: License plate (optional)
            location: Location (optional)
            
        Returns:
            CaseRecord with case_id
        """
        
        case_id = generate_id("CASE")
        
        record = CaseRecord(
            case_id=case_id,
            priority=priority,
            summary=summary,
            evidence_path=evidence_path,
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            vehicle_year_range=vehicle_year_range,
            plate_number=plate_number,
            location=location,
            status="open",
        )
        
        # Save to local file
        self._save_case(record)
        
        logger.info(f"Case created: {case_id} (Priority: {priority})")
        return record

    def _save_case(self, case: CaseRecord) -> None:
        """Save case record to file."""
        try:
            with open(self.cases_file, "a") as f:
                f.write(case.model_dump_json() + "\n")
            logger.debug(f"Case saved to {self.cases_file}")
        except Exception as e:
            logger.error(f"Failed to save case: {str(e)}")
            raise

    def get_case(self, case_id: str) -> Optional[CaseRecord]:
        """Retrieve a case by ID."""
        try:
            if not self.cases_file.exists():
                return None
            
            with open(self.cases_file, "r") as f:
                for line in f:
                    case_data = json.loads(line)
                    if case_data.get("case_id") == case_id:
                        return CaseRecord(**case_data)
            
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve case: {str(e)}")
            return None

    def list_cases(self, limit: int = 100) -> list:
        """List recent cases."""
        try:
            cases = []
            if not self.cases_file.exists():
                return cases
            
            with open(self.cases_file, "r") as f:
                for line in f:
                    case_data = json.loads(line)
                    cases.append(CaseRecord(**case_data))
            
            return cases[-limit:]
        except Exception as e:
            logger.error(f"Failed to list cases: {str(e)}")
            return []
