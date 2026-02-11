# TrafficIQ Evaluation Dataset Schema

## Overview
The evaluation dataset is stored as JSONL (JSON Lines), with one record per line. Each record represents a labeled vehicle image for model evaluation.

## Record Format

```json
{
  "image_uri": "gs://bucket/images/traffic_cam_001.jpg",
  "true_make": "Honda",
  "true_model": "Civic",
  "true_year_range": "2020-2021",
  "true_color": "black",
  "true_body_type": "sedan",
  "true_plate": "ABC1234",
  "location": "Downtown Intersection A",
  "timestamp": "2024-01-15T14:30:00Z",
  "image_quality": "clear",
  "notes": "Minor occlusion from utility pole"
}
```

## Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image_uri` | string | Yes | Path or URL to traffic camera image |
| `true_make` | string | Yes | Ground truth vehicle make (Honda, Toyota, Ford, etc.) |
| `true_model` | string | Yes | Ground truth vehicle model (Civic, Camry, F150, etc.) |
| `true_year_range` | string | Yes | Ground truth year range (e.g., "2020-2021") |
| `true_color` | string | No | Ground truth vehicle color |
| `true_body_type` | string | No | Ground truth body type (sedan, SUV, truck, etc.) |
| `true_plate` | string | No | Ground truth license plate |
| `location` | string | No | Geographic location of camera |
| `timestamp` | string | No | ISO 8601 timestamp of image capture |
| `image_quality` | string | No | Image quality indicator (clear, night, blur, rain, low_res) |
| `notes` | string | No | Additional annotation notes |

## Data Split Recommendations

- **Training**: 70% of dataset
- **Validation**: 15% of dataset
- **Test**: 15% of dataset

## Format Examples

### Clear daytime image
```json
{"image_uri": "traffic/cam_001_clear.jpg", "true_make": "Toyota", "true_model": "Camry", "true_year_range": "2021-2022", "true_color": "silver", "true_body_type": "sedan", "image_quality": "clear"}
```

### Night image with partial occlusion
```json
{"image_uri": "traffic/cam_002_night_occluded.jpg", "true_make": "Honda", "true_model": "Civic", "true_year_range": "2020-2021", "true_color": "black", "image_quality": "night", "notes": "50% occluded by tree"}
```

### Blurry image
```json
{"image_uri": "traffic/cam_003_blur.jpg", "true_make": "Ford", "true_model": "F150", "true_year_range": "2022-2023", "true_body_type": "truck", "image_quality": "blur"}
```
