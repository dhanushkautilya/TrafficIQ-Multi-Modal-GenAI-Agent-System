"""Tests for agent router."""

import pytest
import tempfile
from app.common.config import Config
from app.common.schemas import Priority
from app.agent.policy import PolicyConfig
from app.agent.router import TrafficIQAgent


@pytest.fixture
def test_config():
    """Create test config with temp artifacts."""
    tmpdir = tempfile.mkdtemp()
    return Config(
        use_vertex=False,
        use_gcs=False,
        artifacts_path=tmpdir,
    )


class TestPolicyConfig:
    """Tests for policy configuration."""
    
    def test_ocr_fallback_triggered_low_confidence(self):
        """Test OCR fallback triggered for low confidence."""
        policy = PolicyConfig()
        
        # Low confidence should trigger OCR
        assert policy.should_use_ocr_fallback(0.60, "clear") is True
        
        # High confidence should skip OCR
        assert policy.should_use_ocr_fallback(0.75, "clear") is False
    
    def test_ocr_fallback_triggered_poor_image_quality(self):
        """Test OCR fallback triggered for poor image quality."""
        policy = PolicyConfig()
        
        # Good confidence but night image should trigger OCR
        assert policy.should_use_ocr_fallback(0.80, "night") is True
        
        # Good confidence but blur should trigger OCR
        assert policy.should_use_ocr_fallback(0.80, "blur") is True
        
        # Good confidence and clear should skip OCR
        assert policy.should_use_ocr_fallback(0.80, "clear") is False
    
    def test_priority_assignment_p0(self):
        """Test P0 priority assignment."""
        policy = PolicyConfig()
        
        # BOLO match + high confidence = P0
        assert policy.assign_priority(bolo_match=True, confidence=0.75) == "P0"
        assert policy.assign_priority(bolo_match=True, confidence=0.95) == "P0"
    
    def test_priority_assignment_p1(self):
        """Test P1 priority assignment."""
        policy = PolicyConfig()
        
        # BOLO match + medium confidence = P1
        assert policy.assign_priority(bolo_match=True, confidence=0.65) == "P1"
        assert policy.assign_priority(bolo_match=True, confidence=0.55) == "P1"
    
    def test_priority_assignment_p2(self):
        """Test P2 priority assignment."""
        policy = PolicyConfig()
        
        # No BOLO match = P2
        assert policy.assign_priority(bolo_match=False, confidence=0.95) == "P2"
        
        # BOLO match but very low confidence = P2
        assert policy.assign_priority(bolo_match=True, confidence=0.40) == "P2"
    
    def test_default_config_created(self):
        """Test default configuration is created."""
        config = PolicyConfig.default()
        
        assert config.MIN_VEHICLE_CONFIDENCE_FOR_SKIP_OCR == 0.70
        assert config.MIN_PLATE_CONFIDENCE_FOR_BOLO == 0.60


class TestTrafficIQAgent:
    """Tests for main agent."""
    
    def test_agent_initialization(self, test_config):
        """Test agent initializes successfully."""
        agent = TrafficIQAgent(test_config)
        
        assert agent.config is not None
        assert agent.policy is not None
        assert agent.vertex_client is not None
        assert agent.ocr_client is not None
        assert agent.bolo_client is not None
        assert agent.evidence_builder is not None
        assert agent.case_client is not None
    
    def test_agent_run_complete(self, test_config):
        """Test agent runs complete pipeline."""
        agent = TrafficIQAgent(test_config)
        
        result = agent.run(
            image_uri="gs://bucket/test_image.jpg",
            location="Downtown",
        )
        
        # Verify result structure
        assert result.image_uri == "gs://bucket/test_image.jpg"
        assert result.vehicle_prediction is not None
        assert isinstance(result.priority, Priority)
        assert result.processing_steps
        assert result.total_processing_time_ms > 0
    
    def test_agent_run_with_timestamp(self, test_config):
        """Test agent run with custom timestamp."""
        from datetime import datetime
        
        agent = TrafficIQAgent(test_config)
        timestamp = datetime(2024, 1, 15, 14, 30, 0)
        
        result = agent.run(
            image_uri="gs://bucket/test_image.jpg",
            location="Highway",
            timestamp=timestamp,
        )
        
        assert result is not None
        assert result.case_record is not None
    
    def test_agent_ocr_fallback_path(self, test_config):
        """Test agent follows OCR fallback path for low confidence."""
        agent = TrafficIQAgent(test_config)
        
        # Use URI that triggers low confidence
        result = agent.run(
            image_uri="gs://bucket/low_confidence_image.jpg",
        )
        
        # Verify OCR was potentially used
        assert result.processing_steps
        if result.ocr_fallback_used:
            assert result.plate_result is not None
    
    def test_agent_priority_assignment(self, test_config):
        """Test agent assigns priority correctly."""
        agent = TrafficIQAgent(test_config)
        
        # Run with multiple URIs to test priority logic
        result = agent.run(image_uri="gs://bucket/test_priority.jpg")
        
        # If BOLO match found, priority should be P0 or P1
        if result.bolo_match and result.bolo_match.is_match:
            if result.vehicle_prediction.confidence >= 0.70:
                assert result.priority == Priority.P0
            else:
                # Could be P1 or P2 depending on confidence
                assert result.priority in [Priority.P1, Priority.P2]
        else:
            # No BOLO match means P2
            assert result.priority == Priority.P2
    
    def test_agent_case_creation(self, test_config):
        """Test agent creates case record."""
        agent = TrafficIQAgent(test_config)
        
        result = agent.run(image_uri="gs://bucket/test_image.jpg")
        
        assert result.case_record is not None
        assert result.case_record.case_id
        assert result.case_record.priority
        assert result.case_record.vehicle_make
        assert result.case_record.summary
    
    def test_agent_processing_steps_recorded(self, test_config):
        """Test agent records all processing steps."""
        agent = TrafficIQAgent(test_config)
        
        result = agent.run(image_uri="gs://bucket/test_image.jpg")
        
        expected_steps = [
            "vehicle_prediction_request",
            "vehicle_prediction_received",
        ]
        
        for step in expected_steps:
            assert step in result.processing_steps
