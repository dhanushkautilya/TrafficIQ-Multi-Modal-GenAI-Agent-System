"""API routes for TrafficIQ."""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from app.common.schemas import (
    AnalyzeRequest,
    AgentRunRequest,
    VehiclePrediction,
    AgentResult,
    HealthResponse,
)
from app.common.config import get_config
from app.tools.vertex_client import VertexAIClient
from app.agent.router import TrafficIQAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
config = get_config()
vertex_client = VertexAIClient(config)
agent = TrafficIQAgent(config)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=config.api_version,
        environment=config.environment,
    )


@router.post("/analyze", response_model=VehiclePrediction)
async def analyze_vehicle(request: AnalyzeRequest) -> VehiclePrediction:
    """
    Analyze a vehicle image and return predictions.
    
    Args:
        request: AnalyzeRequest containing image_uri
        
    Returns:
        VehiclePrediction with vehicle details
        
    Raises:
        HTTPException: If analysis fails
    """
    try:
        logger.info(f"Analyzing vehicle from {request.image_uri}")
        prediction = vertex_client.predict_vehicle(request.image_uri)
        return prediction
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/agent/run", response_model=AgentResult)
async def run_agent(request: AgentRunRequest) -> AgentResult:
    """
    Run complete agent orchestration pipeline.
    
    Args:
        request: AgentRunRequest containing image_uri and optional location/timestamp
        
    Returns:
        AgentResult with all processing steps and outcomes
        
    Raises:
        HTTPException: If agent execution fails
    """
    try:
        logger.info(f"Running agent for {request.image_uri}")
        
        timestamp = request.timestamp or datetime.utcnow()
        
        result = agent.run(
            image_uri=request.image_uri,
            location=request.location,
            timestamp=timestamp,
        )
        
        return result
    except Exception as e:
        logger.error(f"Agent run failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent run failed: {str(e)}")
