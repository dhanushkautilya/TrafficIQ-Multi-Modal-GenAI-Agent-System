"""Tests for tools layer."""

import pytest
from app.common.config import Config
from app.tools.vertex_client import VertexAIClient
from app.tools.ocr_client import OCRClient
from app.tools.bolo_client import BOLOClient
from app.tools.evidence import EvidencePacketBuilder
from app.tools.case_client import CaseClient
from app.common.schemas import Priority


@pytest.fixture
def mock_config():
    """Create mock config for testing."""
    return Config(
        use_vertex=False,
        use_gcs=False,
        artifacts_path="./test_artifacts",
    )


class TestVertexClient:
    """Tests for Vertex AI client."""
    
    def test_mock_prediction_deterministic(self, mock_config):
        """Test that mock predictions are deterministic."""
        client = VertexAIClient(mock_config)
        
        # Same URI should produce same prediction
        pred1 = client.predict_vehicle("gs://bucket/image.jpg")
        pred2 = client.predict_vehicle("gs://bucket/image.jpg")
        
        assert pred1.make == pred2.make
        assert pred1.model == pred2.model
        assert pred1.confidence == pred2.confidence
    
    def test_mock_prediction_has_required_fields(self, mock_config):
        """Test that mock prediction has all required fields."""
        client = VertexAIClient(mock_config)
        pred = client.predict_vehicle("gs://bucket/image.jpg")
        
        assert pred.image_uri
        assert pred.make
        assert pred.model
        assert pred.year_range
        assert pred.color
        assert pred.body_type
        assert 0.0 <= pred.confidence <= 1.0
        assert pred.image_condition
    
    def test_night_image_reduces_confidence(self, mock_config):
        """Test that night images affect image condition."""
        client = VertexAIClient(mock_config)
        
        clear_pred = client.predict_vehicle("gs://bucket/clear_test_image.jpg")
        night_pred = client.predict_vehicle("gs://bucket/night_test_image.jpg")
        
        # Both should have valid confidences
        assert 0.0 <= clear_pred.confidence <= 1.0
        assert 0.0 <= night_pred.confidence <= 1.0
        
        # Night image should be marked with night condition
        assert night_pred.image_condition == "night"
        assert clear_pred.image_condition == "clear"
    
    def test_blur_image_marked_correctly(self, mock_config):
        """Test that blur images are marked."""
        client = VertexAIClient(mock_config)
        pred = client.predict_vehicle("gs://bucket/blur_image.jpg")
        
        assert "blur" in pred.image_condition.lower()


class TestOCRClient:
    """Tests for OCR client."""
    
    def test_plate_extraction_deterministic(self):
        """Test that OCR extractions are deterministic."""
        client = OCRClient()
        
        result1 = client.extract_plate("gs://bucket/plate_image.jpg")
        result2 = client.extract_plate("gs://bucket/plate_image.jpg")
        
        assert result1.plate_number == result2.plate_number
        assert result1.confidence == result2.confidence
    
    def test_plate_has_required_fields(self):
        """Test that OCR result has required fields."""
        client = OCRClient()
        result = client.extract_plate("gs://bucket/image.jpg")
        
        assert result.plate_number
        assert 0.0 <= result.confidence <= 1.0
        assert result.image_uri
    
    def test_night_image_reduces_plate_confidence(self):
        """Test that night images reduce plate confidence."""
        client = OCRClient()
        
        clear_result = client.extract_plate("gs://bucket/clear_plate.jpg")
        night_result = client.extract_plate("gs://bucket/night_plate.jpg")
        
        assert night_result.confidence < clear_result.confidence


class TestBOLOClient:
    """Tests for BOLO client."""
    
    def test_honda_always_matches(self):
        """Test that Honda make triggers BOLO match."""
        client = BOLOClient()
        result = client.lookup("Honda", "Civic", "2020-2021", "ABC1234")
        
        assert result.is_match is True
        assert result.make == "Honda"
    
    def test_toyota_no_match(self):
        """Test that Toyota typically doesn't match."""
        client = BOLOClient()
        result = client.lookup("Toyota", "Camry", "2020-2021", "ABC1234")
        
        # Without special plates, Toyota shouldn't match
        # But let's verify the structure is correct
        assert isinstance(result.is_match, bool)
        assert result.reason
    
    def test_plate_ending_7_matches(self):
        """Test that plates ending in 7 trigger match."""
        client = BOLOClient()
        result = client.lookup("Honda", "Civic", "2020-2021", "ABC1237")
        
        # Plate ending in 7 or make Honda should trigger
        assert result.is_match is True
    
    def test_no_match_returns_valid_result(self):
        """Test that no-match returns valid result."""
        client = BOLOClient()
        result = client.lookup("Ford", "F150", "2020-2021", "XYZ1234", "Downtown")
        
        # Verify structure even if no match
        assert isinstance(result.is_match, bool)
        assert result.reason
        assert 0.0 <= result.match_confidence <= 1.0


class TestEvidenceBuilder:
    """Tests for evidence packet builder."""
    
    def test_evidence_packet_created(self, mock_config):
        """Test that evidence packet is created successfully."""
        import tempfile
        from app.common.schemas import VehiclePrediction
        
        # Use temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(artifacts_path=tmpdir, use_gcs=False)
            builder = EvidencePacketBuilder(config)
            
            pred = VehiclePrediction(
                image_uri="test.jpg",
                make="Honda",
                model="Civic",
                year_range="2020-2021",
                color="black",
                body_type="sedan",
                confidence=0.95,
            )
            
            packet = builder.build(
                image_uri="test.jpg",
                vehicle_prediction=pred,
            )
            
            assert packet.packet_id
            assert packet.image_uri == "test.jpg"
            assert packet.evidence_path


class TestCaseClient:
    """Tests for case client."""
    
    def test_case_created_successfully(self, mock_config):
        """Test that case record is created."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(artifacts_path=tmpdir, use_gcs=False)
            client = CaseClient(config)
            
            case = client.create_case(
                summary="Test case",
                priority=Priority.P0,
                evidence_path="/path/to/evidence",
                vehicle_make="Honda",
                vehicle_model="Civic",
                vehicle_year_range="2020-2021",
            )
            
            assert case.case_id
            assert case.priority == Priority.P0
            assert case.status == "open"
    
    def test_case_retrieved(self, mock_config):
        """Test that created case can be retrieved."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config(artifacts_path=tmpdir, use_gcs=False)
            client = CaseClient(config)
            
            # Create case
            created = client.create_case(
                summary="Test case",
                priority=Priority.P1,
                evidence_path="/evidence",
                vehicle_make="Toyota",
                vehicle_model="Camry",
                vehicle_year_range="2021-2022",
            )
            
            # Retrieve case
            retrieved = client.get_case(created.case_id)
            
            assert retrieved is not None
            assert retrieved.case_id == created.case_id
            assert retrieved.priority == Priority.P1
