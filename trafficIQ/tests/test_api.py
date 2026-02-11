"""Tests for FastAPI endpoints."""

import pytest
import tempfile
from fastapi.testclient import TestClient
from datetime import datetime

# Setup test environment
import os
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_VERTEX"] = "false"

from app.api.main import app
from app.common.config import Config


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test health check returns ok."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"]
        assert data["environment"]
    
    def test_health_check_response_format(self, client):
        """Test health check response format."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "environment" in data


class TestAnalyzeEndpoint:
    """Tests for /analyze endpoint."""
    
    def test_analyze_vehicle_success(self, client):
        """Test vehicle analysis returns prediction."""
        response = client.post(
            "/analyze",
            json={"image_uri": "gs://bucket/test_image.jpg"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["image_uri"]
        assert data["make"]
        assert data["model"]
        assert data["confidence"]
    
    def test_analyze_vehicle_required_fields(self, client):
        """Test analyze endpoint returns all required fields."""
        response = client.post(
            "/analyze",
            json={"image_uri": "gs://bucket/image.jpg"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "image_uri",
            "make",
            "model",
            "year_range",
            "color",
            "body_type",
            "confidence",
            "image_condition",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_analyze_vehicle_confidence_range(self, client):
        """Test that confidence is in valid range."""
        response = client.post(
            "/analyze",
            json={"image_uri": "gs://bucket/test_image.jpg"},
        )
        
        data = response.json()
        assert 0.0 <= data["confidence"] <= 1.0
    
    def test_analyze_vehicle_missing_uri(self, client):
        """Test analyze endpoint with missing image_uri."""
        response = client.post("/analyze", json={})
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_analyze_deterministic(self, client):
        """Test analyze returns same result for same image."""
        uri = "gs://bucket/deterministic_test.jpg"
        
        response1 = client.post("/analyze", json={"image_uri": uri})
        response2 = client.post("/analyze", json={"image_uri": uri})
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["make"] == data2["make"]
        assert data1["model"] == data2["model"]
        assert data1["confidence"] == data2["confidence"]


class TestAgentRunEndpoint:
    """Tests for /agent/run endpoint."""
    
    def test_agent_run_success(self, client):
        """Test agent run completes successfully."""
        response = client.post(
            "/agent/run",
            json={"image_uri": "gs://bucket/test_image.jpg"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["image_uri"]
        assert data["priority"]
        assert "vehicle_prediction" in data
        assert "processing_steps" in data
    
    def test_agent_run_with_location(self, client):
        """Test agent run with location information."""
        response = client.post(
            "/agent/run",
            json={
                "image_uri": "gs://bucket/test_image.jpg",
                "location": "Downtown Intersection",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "Downtown Intersection"
    
    def test_agent_run_with_timestamp(self, client):
        """Test agent run with custom timestamp."""
        timestamp = "2024-01-15T14:30:00Z"
        
        response = client.post(
            "/agent/run",
            json={
                "image_uri": "gs://bucket/test_image.jpg",
                "timestamp": timestamp,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
    
    def test_agent_run_required_fields(self, client):
        """Test agent run returns all required fields."""
        response = client.post(
            "/agent/run",
            json={"image_uri": "gs://bucket/test_image.jpg"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "image_uri",
            "vehicle_prediction",
            "priority",
            "ocr_fallback_used",
            "processing_steps",
            "total_processing_time_ms",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_agent_run_creates_case(self, client):
        """Test agent run creates case record."""
        response = client.post(
            "/agent/run",
            json={"image_uri": "gs://bucket/test_image.jpg"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Case record should be created
        assert "case_record" in data
        if data["case_record"]:
            assert "case_id" in data["case_record"]
            assert "priority" in data["case_record"]
    
    def test_agent_run_missing_uri(self, client):
        """Test agent run with missing image_uri."""
        response = client.post("/agent/run", json={})
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_agent_run_priority_values(self, client):
        """Test agent run returns valid priority."""
        response = client.post(
            "/agent/run",
            json={"image_uri": "gs://bucket/test_image.jpg"},
        )
        
        data = response.json()
        assert data["priority"] in ["P0", "P1", "P2"]
    
    def test_agent_run_processing_time(self, client):
        """Test agent records processing time."""
        response = client.post(
            "/agent/run",
            json={"image_uri": "gs://bucket/test_image.jpg"},
        )
        
        data = response.json()
        assert data["total_processing_time_ms"] > 0
    
    def test_agent_run_with_all_optional_fields(self, client):
        """Test agent run with all optional fields."""
        response = client.post(
            "/agent/run",
            json={
                "image_uri": "gs://bucket/test_image.jpg",
                "location": "Test Location",
                "timestamp": "2024-01-15T14:30:00Z",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "Test Location"


class TestIntegration:
    """Integration tests."""
    
    def test_analyze_then_agent_run(self, client):
        """Test analyzing image then running full agent pipeline."""
        uri = "gs://bucket/integration_test.jpg"
        
        # First analyze
        analyze_response = client.post(
            "/analyze",
            json={"image_uri": uri},
        )
        assert analyze_response.status_code == 200
        
        # Then run agent
        agent_response = client.post(
            "/agent/run",
            json={"image_uri": uri},
        )
        assert agent_response.status_code == 200
        
        analyze_data = analyze_response.json()
        agent_data = agent_response.json()
        
        # Vehicle predictions should match
        assert analyze_data["make"] == agent_data["vehicle_prediction"]["make"]
        assert analyze_data["model"] == agent_data["vehicle_prediction"]["model"]
