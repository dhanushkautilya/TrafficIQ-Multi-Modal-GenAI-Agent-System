"""Metrics and evaluation utilities."""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class ConfusionMatrix:
    """Confusion matrix for multi-class classification."""
    
    classes: List[str] = field(default_factory=list)
    matrix: List[List[int]] = field(default_factory=list)
    
    def __init__(self, classes: Optional[List[str]] = None):
        """Initialize confusion matrix."""
        self.classes = classes or []
        self.matrix = [[0 for _ in self.classes] for _ in self.classes] if self.classes else []
    
    def increment(self, true_idx: int, pred_idx: int):
        """Increment matrix cell."""
        if 0 <= true_idx < len(self.classes) and 0 <= pred_idx < len(self.classes):
            self.matrix[true_idx][pred_idx] += 1
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "classes": self.classes,
            "matrix": self.matrix,
        }
    
    def to_string(self) -> str:
        """Format as readable string."""
        if not self.matrix:
            return "Empty confusion matrix"
        
        lines = []
        lines.append("Confusion Matrix (True vs Predicted)")
        lines.append("-" * (12 + 12 * len(self.classes)))
        
        # Header row
        header = "True \\ Pred"
        for cls in self.classes:
            header += f" | {cls:<10}"
        lines.append(header)
        lines.append("-" * (12 + 12 * len(self.classes)))
        
        # Data rows
        for i, true_cls in enumerate(self.classes):
            row = f"{true_cls:<12}"
            for j in range(len(self.classes)):
                row += f" | {self.matrix[i][j]:<10}"
            lines.append(row)
        
        return "\n".join(lines)


@dataclass
class Metrics:
    """Evaluation metrics container."""
    
    accuracy: float = 0.0
    precision_macro: float = 0.0
    recall_macro: float = 0.0
    f1_macro: float = 0.0
    accuracy_by_class: Dict[str, float] = field(default_factory=dict)
    ece_confidence: float = 0.0  # Expected Calibration Error
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "accuracy": self.accuracy,
            "precision_macro": self.precision_macro,
            "recall_macro": self.recall_macro,
            "f1_macro": self.f1_macro,
            "accuracy_by_class": self.accuracy_by_class,
            "ece_confidence": self.ece_confidence,
        }
    
    def to_string(self) -> str:
        """Format as readable string."""
        lines = []
        lines.append("Evaluation Metrics")
        lines.append("-" * 50)
        lines.append(f"Overall Accuracy:     {self.accuracy:.4f}")
        lines.append(f"Precision (macro):    {self.precision_macro:.4f}")
        lines.append(f"Recall (macro):       {self.recall_macro:.4f}")
        lines.append(f"F1-Score (macro):     {self.f1_macro:.4f}")
        lines.append(f"ECE (Calibration):    {self.ece_confidence:.4f}")
        
        if self.accuracy_by_class:
            lines.append("\nPer-Class Accuracy:")
            for cls, acc in self.accuracy_by_class.items():
                lines.append(f"  {cls:<20}: {acc:.4f}")
        
        return "\n".join(lines)


class MetricsCalculator:
    """Calculate evaluation metrics."""
    
    @staticmethod
    def calculate_accuracy(true_labels: List[str], pred_labels: List[str]) -> float:
        """Calculate overall accuracy."""
        if not true_labels:
            return 0.0
        
        correct = sum(1 for t, p in zip(true_labels, pred_labels) if t == p)
        return correct / len(true_labels)
    
    @staticmethod
    def calculate_per_class_accuracy(
        true_labels: List[str],
        pred_labels: List[str],
    ) -> Dict[str, float]:
        """Calculate per-class accuracy."""
        per_class = {}
        unique_classes = set(true_labels)
        
        for cls in unique_classes:
            class_indices = [i for i, t in enumerate(true_labels) if t == cls]
            if class_indices:
                correct = sum(
                    1 for i in class_indices if true_labels[i] == pred_labels[i]
                )
                per_class[cls] = correct / len(class_indices)
        
        return per_class
    
    @staticmethod
    def confusion_matrix_from_labels(
        true_labels: List[str],
        pred_labels: List[str],
        classes: Optional[List[str]] = None,
    ) -> ConfusionMatrix:
        """Create confusion matrix from labels."""
        if classes is None:
            classes = sorted(set(true_labels) | set(pred_labels))
        
        cm = ConfusionMatrix(classes)
        class_to_idx = {cls: i for i, cls in enumerate(classes)}
        
        for true_label, pred_label in zip(true_labels, pred_labels):
            if true_label in class_to_idx and pred_label in class_to_idx:
                true_idx = class_to_idx[true_label]
                pred_idx = class_to_idx[pred_label]
                cm.increment(true_idx, pred_idx)
        
        return cm
    
    @staticmethod
    def calculate_ece(
        true_labels: List[str],
        pred_labels: List[str],
        confidences: List[float],
        n_bins: int = 10,
    ) -> float:
        """
        Calculate Expected Calibration Error (ECE).
        
        Measures gap between predicted confidence and actual accuracy.
        """
        if not true_labels or len(true_labels) != len(confidences):
            return 0.0
        
        # Bin confidences
        bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
        ece = 0.0
        
        for i in range(n_bins):
            lower = bin_boundaries[i]
            upper = bin_boundaries[i + 1]
            
            # Get samples in this bin
            in_bin = [
                j for j, conf in enumerate(confidences)
                if lower < conf <= upper
            ]
            
            if not in_bin:
                continue
            
            # Calculate accuracy in bin
            accuracy_in_bin = sum(
                1 for j in in_bin if true_labels[j] == pred_labels[j]
            ) / len(in_bin)
            
            # Calculate average confidence in bin
            avg_conf = sum(confidences[j] for j in in_bin) / len(in_bin)
            
            # Accumulate ECE
            ece += len(in_bin) / len(true_labels) * abs(avg_conf - accuracy_in_bin)
        
        return ece
