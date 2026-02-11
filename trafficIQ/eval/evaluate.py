"""Evaluation pipeline for TrafficIQ."""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.common.config import get_config
from app.tools.vertex_client import VertexAIClient
from eval.metrics import Metrics, MetricsCalculator, ConfusionMatrix

logger = logging.getLogger(__name__)


class Evaluator:
    """Main evaluation pipeline."""
    
    def __init__(self, config: Optional[object] = None):
        """Initialize evaluator."""
        self.config = config or get_config()
        self.vertex_client = VertexAIClient(self.config)
        self.artifacts_dir = self.config.setup_artifacts_dir()
    
    def run_evaluation(
        self,
        dataset_path: str = "eval/sample_data.jsonl",
        output_path: Optional[str] = None,
    ) -> Metrics:
        """
        Run evaluation on dataset.
        
        Args:
            dataset_path: Path to JSONL evaluation dataset
            output_path: Optional path to save report (default: artifacts/eval_report.md)
            
        Returns:
            Metrics object with results
        """
        if output_path is None:
            output_path = str(self.artifacts_dir / "eval_report.md")
        
        logger.info(f"Starting evaluation on {dataset_path}")
        
        # Load dataset
        samples = self._load_dataset(dataset_path)
        logger.info(f"Loaded {len(samples)} samples")
        
        if not samples:
            logger.warning("No samples to evaluate")
            return Metrics()
        
        # Run predictions
        predictions = self._run_predictions(samples)
        
        # Calculate metrics
        metrics = self._calculate_metrics(samples, predictions)
        
        # Generate report
        report = self._generate_report(samples, predictions, metrics)
        
        # Save report
        self._save_report(report, output_path)
        
        logger.info(f"Evaluation complete. Report saved to {output_path}")
        return metrics
    
    def _load_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """Load evaluation dataset from JSONL."""
        samples = []
        try:
            with open(dataset_path, "r") as f:
                for line in f:
                    if line.strip():
                        samples.append(json.loads(line))
            logger.info(f"Loaded {len(samples)} samples from {dataset_path}")
        except FileNotFoundError:
            logger.error(f"Dataset file not found: {dataset_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in dataset: {str(e)}")
        
        return samples
    
    def _run_predictions(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run predictions on samples."""
        predictions = []
        
        for i, sample in enumerate(samples):
            try:
                image_uri = sample.get("image_uri", "")
                
                # Get prediction
                pred = self.vertex_client.predict_vehicle(image_uri)
                
                # Store prediction with true label
                predictions.append({
                    "image_uri": image_uri,
                    "true_make": sample.get("true_make"),
                    "pred_make": pred.make,
                    "pred_confidence": pred.confidence,
                    "true_model": sample.get("true_model"),
                    "pred_model": pred.model,
                    "true_year": sample.get("true_year_range"),
                    "pred_year": pred.year_range,
                })
                
                if (i + 1) % 5 == 0:
                    logger.debug(f"Processed {i + 1}/{len(samples)} samples")
            
            except Exception as e:
                logger.error(f"Prediction failed for {sample.get('image_uri')}: {str(e)}")
                continue
        
        logger.info(f"Predictions complete: {len(predictions)}/{len(samples)} successful")
        return predictions
    
    def _calculate_metrics(
        self,
        samples: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
    ) -> Metrics:
        """Calculate evaluation metrics."""
        if not predictions:
            return Metrics()
        
        true_makes = [p["true_make"] for p in predictions]
        pred_makes = [p["pred_make"] for p in predictions]
        confidences = [p["pred_confidence"] for p in predictions]
        
        # Overall accuracy
        accuracy = MetricsCalculator.calculate_accuracy(true_makes, pred_makes)
        
        # Per-class accuracy for makes
        accuracy_by_class = MetricsCalculator.calculate_per_class_accuracy(
            true_makes, pred_makes
        )
        
        # Confusion matrix (top makes)
        top_makes = sorted(set(true_makes), key=lambda x: true_makes.count(x), reverse=True)[:5]
        filtered_true = [m for m in true_makes if m in top_makes]
        filtered_pred = [p for t, p in zip(true_makes, pred_makes) if t in top_makes]
        
        cm = MetricsCalculator.confusion_matrix_from_labels(
            filtered_true, filtered_pred, top_makes
        )
        
        # ECE (calibration metric)
        ece = MetricsCalculator.calculate_ece(true_makes, pred_makes, confidences)
        
        metrics = Metrics(
            accuracy=accuracy,
            accuracy_by_class=accuracy_by_class,
            ece_confidence=ece,
        )
        
        logger.info(f"Metrics calculated: Accuracy={accuracy:.4f}, ECE={ece:.4f}")
        return metrics
    
    def _generate_report(
        self,
        samples: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        metrics: Metrics,
    ) -> str:
        """Generate markdown evaluation report."""
        lines = []
        
        lines.append("# TrafficIQ Evaluation Report\n")
        lines.append(f"Generated: {datetime.utcnow().isoformat()}\n")
        
        # Summary
        lines.append("## Summary\n")
        lines.append(f"- Dataset Size: {len(samples)} samples")
        lines.append(f"- Successful Predictions: {len(predictions)}/{len(samples)}")
        lines.append(f"- Evaluation Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Metrics
        lines.append("## Overall Metrics\n")
        lines.append(f"- **Accuracy**: {metrics.accuracy:.4f} ({metrics.accuracy*100:.2f}%)")
        lines.append(f"- **ECE (Calibration)**: {metrics.ece_confidence:.4f}")
        lines.append(f"- **Precision (macro)**: {metrics.precision_macro:.4f}")
        lines.append(f"- **Recall (macro)**: {metrics.recall_macro:.4f}")
        lines.append(f"- **F1-Score (macro)**: {metrics.f1_macro:.4f}\n")
        
        # Per-class accuracy
        if metrics.accuracy_by_class:
            lines.append("## Per-Class Accuracy (Vehicle Makes)\n")
            lines.append("| Make | Accuracy |")
            lines.append("|------|----------|")
            for make, acc in sorted(metrics.accuracy_by_class.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"| {make} | {acc:.4f} ({acc*100:.2f}%) |")
            lines.append()
        
        # Sample predictions
        lines.append("## Sample Predictions\n")
        lines.append("| Image | True Make | Predicted Make | Confidence |")
        lines.append("|-------|-----------|----------------|------------|")
        
        for pred in predictions[:10]:  # Show first 10
            true_make = pred["true_make"]
            pred_make = pred["pred_make"]
            conf = pred["pred_confidence"]
            match = "✓" if true_make == pred_make else "✗"
            lines.append(
                f"| {pred['image_uri'][-20:]:20} | {true_make:9} | {pred_make:14} | "
                f"{conf:.2f} {match} |"
            )
        lines.append()
        
        # Notes
        lines.append("## Notes\n")
        lines.append("- This is a mock evaluation using deterministic predictions")
        lines.append("- All predictions are based on image URI hash for reproducibility")
        lines.append("- ECE (Expected Calibration Error) measures confidence calibration")
        lines.append("- Lower ECE indicates better calibration (values near 0 are ideal)\n")
        
        return "\n".join(lines)
    
    def _save_report(self, report: str, output_path: str) -> None:
        """Save report to file."""
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(report)
            logger.info(f"Report saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}")
            raise


if __name__ == "__main__":
    import sys
    
    # Setup logging
    from app.common.logging import setup_logging
    setup_logging()
    
    # Run evaluation
    evaluator = Evaluator()
    evaluator.run_evaluation()
