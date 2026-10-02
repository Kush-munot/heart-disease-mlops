from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PatientFeatures(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "age": 57, "sex": 1, "cp": 4, "trestbps": 140, "chol": 241, "fbs": 0,
        "restecg": 0, "thalach": 123, "exang": 1, "oldpeak": 0.2, "slope": 2,
        "ca": 0, "thal": 7,
    }})

    age: int = Field(..., ge=18, le=100, description="Age in years")
    sex: Literal[0, 1] = Field(..., description="1 = male, 0 = female")
    cp: Literal[1, 2, 3, 4] = Field(..., description="Chest pain type (4 = asymptomatic)")
    trestbps: float = Field(..., ge=60, le=250, description="Resting blood pressure (mm Hg)")
    chol: float = Field(..., ge=80, le=700, description="Serum cholesterol (mg/dl)")
    fbs: Literal[0, 1] = Field(..., description="Fasting blood sugar > 120 mg/dl")
    restecg: Literal[0, 1, 2] = Field(..., description="Resting ECG result")
    thalach: float = Field(..., ge=50, le=250, description="Max heart rate achieved")
    exang: Literal[0, 1] = Field(..., description="Exercise induced angina")
    oldpeak: float = Field(..., ge=0, le=10, description="ST depression vs rest")
    slope: Literal[1, 2, 3] = Field(..., description="Slope of peak exercise ST segment")
    ca: Optional[Literal[0, 1, 2, 3]] = Field(None, description="Major vessels coloured (0-3)")
    thal: Optional[Literal[3, 6, 7]] = Field(None, description="3 normal, 6 fixed, 7 reversible")


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction: int
    label: str
    probability_disease: float
    confidence: float
    model_name: str
    model_version: str
