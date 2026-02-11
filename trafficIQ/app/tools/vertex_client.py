"""Vertex AI client for vehicle predictions."""

import logging
from typing import Optional
from app.common.schemas import VehiclePrediction
from app.common.utils import deterministic_hash, extract_image_uri_features
from app.common.config import get_config

logger = logging.getLogger(__name__)

MAKES = ["Honda", "Toyota", "Ford", "BMW", "Tesla", "Nissan", "Chevrolet"]
MODELS = ["Civic", "Camry", "F150", "3 Series", "Model 3", "Altima", "Silverado"]
YEARS = ["2020-2021", "2021-2022", "2022-2023", "2023-2024"]
COLORS = ["Black", "White", "Gray", "Silver", "Red", "Blue", "Green"]
BODY_TYPES = ["sedan", "SUV", "truck", "coupe", "wagon"]


class VertexAIClient:
    """Client for Vertex AI endpoint calls."""

    def __init__(self, config: Optional[object] = None):
        """Initialize client."""
        self.config = config or get_config()
        self.use_vertex = self.config.use_vertex
        self.project = self.config.gcp_project
        self.region = self.config.gcp_region
        self.endpoint_id = self.config.vertex_endpoint_id
        
        if self.use_vertex:
            try:
                import google.cloud.aiplatform as aiplatform
                self.aiplatform = aiplatform
                if self.project:
                    aiplatform.init(project=self.project, location=self.region)
                logger.info("Vertex AI client initialized in REAL mode")
            except ImportError:
                logger.error(
                    "google-cloud-aiplatform not installed. "
                    "Install with: pip install -e '.[gcp]' or set USE_VERTEX=false"
                )
                raise
        else:
            logger.info("Vertex AI client initialized in MOCK mode")

    def predict_vehicle(self, image_uri: str) -> VehiclePrediction:
        """
        Predict vehicle from image.
        
        Args:
            image_uri: Path or URL to image
            
        Returns:
            VehiclePrediction with vehicle details
        """
        if self.use_vertex:
            return self._predict_real(image_uri)
        else:
            return self._predict_mock(image_uri)

    def _predict_real(self, image_uri: str) -> VehiclePrediction:
        """Real Vertex AI prediction."""
        if not self.endpoint_id:
            raise ValueError("VERTEX_ENDPOINT_ID not configured")
        
        try:
            # This is pseudocode - actual implementation would use the SDK
            # endpoint = self.aiplatform.Endpoint(self.endpoint_id)
            # response = endpoint.predict(instances=[{"image_uri": image_uri}])
            # prediction = response.predictions[0]
            
            logger.info(f"Calling Vertex AI endpoint {self.endpoint_id} for {image_uri}")
            
            # Fallback to mock if real call would fail
            logger.warning("Real Vertex AI call not fully implemented, using mock")
            return self._predict_mock(image_uri)
            
        except Exception as e:
            logger.error(f"Vertex AI prediction failed: {str(e)}")
            raise

    def _predict_mock(self, image_uri: str) -> VehiclePrediction:
        """Deterministic mock prediction based on image URI hash."""
        features = extract_image_uri_features(image_uri)
        hash_val = features["hash_value"]
        
        # Use hash to select model characteristics deterministically
        make_idx = int(hash_val * len(MAKES))
        model_idx = int(hash_val * len(MODELS))
        year_idx = int(hash_val * len(YEARS))
        color_idx = int(hash_val * len(COLORS))
        body_idx = int(hash_val * len(BODY_TYPES))
        
        # Confidence - lower if night/blur/low_res
        base_confidence = deterministic_hash(image_uri + "_confidence")
        if features["is_night"] or features["is_blur"]:
            base_confidence *= 0.7
        if features["is_low_res"]:
            base_confidence *= 0.85
        
        image_condition = "clear"
        if features["is_night"]:
            image_condition = "night"
        elif features["is_blur"]:
            image_condition = "blur"
        elif features["is_rain"]:
            image_condition = "rain"
        
        prediction = VehiclePrediction(
            image_uri=image_uri,
            make=MAKES[make_idx % len(MAKES)],
            model=MODELS[model_idx % len(MODELS)],
            year_range=YEARS[year_idx % len(YEARS)],
            color=COLORS[color_idx % len(COLORS)],
            body_type=BODY_TYPES[body_idx % len(BODY_TYPES)],
            confidence=min(base_confidence, 1.0),
            image_condition=image_condition,
            metadata={
                "model_version": "gemma-3n-v1.0",
                "prediction_type": "mock",
            },
        )
        
        logger.debug(f"Mock prediction for {image_uri}: {prediction.make} {prediction.model}")
        return prediction
