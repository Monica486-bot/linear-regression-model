import os
import io
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, SGDRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH    = os.path.join(BASE_DIR, "best_model.pkl")
SCALER_PATH   = os.path.join(BASE_DIR, "scaler.pkl")
FEATURE_PATH  = os.path.join(BASE_DIR, "feature_names.pkl")
DATA_PATH     = os.path.join(BASE_DIR, "training_data.csv")   # persistent data store
COUNTER_PATH  = os.path.join(BASE_DIR, "new_rows_counter.txt")

# Number of new streamed rows that triggers an automatic retrain
RETRAIN_THRESHOLD = 10

app = FastAPI(
    title="Student Grade Prediction API",
    description=(
        "Predicts a student's **final mathematics grade (G3, scale 0–20)** "
        "using 30 academic, demographic, and lifestyle features from the "
        "UCI Student Performance dataset.\n\n"
        "- `POST /predict`     — returns a predicted G3 grade given student features\n"
        "- `POST /data`        — stream a new labelled record; auto-retrains every "
        f"{RETRAIN_THRESHOLD} new rows\n"
        "- `GET  /data/status` — shows buffered row count and retrain countdown\n"
        "- `POST /retrain`     — manually upload a full CSV to retrain immediately\n"
        "- `GET  /health`      — confirms the API and loaded model are ready"
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — Cross-Origin Resource Sharing configuration
#
# WHY CORS IS NEEDED:
#   The Flutter mobile app and Swagger UI run on different origins than this
#   API server. Without CORS headers the browser/Flutter HTTP client blocks
#   the response. The middleware injects the correct Access-Control-* headers
#   on every response.
#
# allow_origins — EXPLICIT list, NOT "*":
#   Wildcard (*) is intentionally avoided for two reasons:
#   1. When allow_credentials=True, the CORS spec forbids wildcard origins —
#      the browser will reject the response entirely.
#   2. Restricting to known origins prevents any random third-party website
#      from making credentialed requests to this API.
#   Allowed:
#     - http://localhost:3000   → React/web tooling during local development
#     - http://localhost:8080   → Alternative local dev port
#     - http://localhost:52000  → Flutter web debug default port
#     - https://student-grade-api.onrender.com → Live production deployment
#   Blocked: every other origin (other deployed apps, scrapers, etc.)
#
# allow_credentials — True:
#   Allows the client to send cookies and Authorization headers cross-origin.
#   Required so the Flutter app can attach a Bearer token in future if auth
#   is added. Only safe because origins are explicitly listed above.
#
# allow_methods — ["GET", "POST"] only:
#   GET  → /health, /data/status, / (read-only status checks)
#   POST → /predict, /data, /retrain (all write/inference operations)
#   PUT, DELETE, PATCH are blocked — this API has no update-in-place or
#   delete operations, so exposing those methods would be unnecessary attack
#   surface.
#
# allow_headers — ["Content-Type", "Authorization"]:
#   Content-Type  → required for JSON POST bodies (application/json) and
#                   multipart/form-data uploads (/retrain CSV upload).
#   Authorization → reserved for future Bearer-token authentication without
#                   requiring a CORS config change.
#   All other headers (X-Custom-*, etc.) are blocked by default.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:52000",
        "https://student-grade-api.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class StudentFeatures(BaseModel):
    age:        int = Field(..., ge=15, le=22,  description="Student age in years (15–22)")
    sex:        int = Field(..., ge=0,  le=1,   description="Sex: 0 = Female, 1 = Male")
    address:    int = Field(..., ge=0,  le=1,   description="Home address: 0 = Rural, 1 = Urban")
    famsize:    int = Field(..., ge=0,  le=1,   description="Family size: 0 = ≤3 members, 1 = >3 members")
    Pstatus:    int = Field(..., ge=0,  le=1,   description="Parent cohabitation: 0 = Apart, 1 = Together")
    Medu:       int = Field(..., ge=0,  le=4,   description="Mother's education level (0 = none … 4 = higher)")
    Fedu:       int = Field(..., ge=0,  le=4,   description="Father's education level (0 = none … 4 = higher)")
    Mjob:       int = Field(..., ge=0,  le=4,   description="Mother's job encoded: 0=at_home,1=health,2=other,3=services,4=teacher")
    Fjob:       int = Field(..., ge=0,  le=4,   description="Father's job encoded: 0=at_home,1=health,2=other,3=services,4=teacher")
    guardian:   int = Field(..., ge=0,  le=2,   description="Student guardian: 0 = mother, 1 = father, 2 = other")
    traveltime: int = Field(..., ge=1,  le=4,   description="Home-to-school travel time: 1=<15min, 2=15–30min, 3=30min–1h, 4=>1h")
    studytime:  int = Field(..., ge=1,  le=4,   description="Weekly study time: 1=<2h, 2=2–5h, 3=5–10h, 4=>10h")
    failures:   int = Field(..., ge=0,  le=4,   description="Number of past class failures (0–4)")
    schoolsup:  int = Field(..., ge=0,  le=1,   description="Extra educational school support: 0 = No, 1 = Yes")
    famsup:     int = Field(..., ge=0,  le=1,   description="Family educational support: 0 = No, 1 = Yes")
    paid:       int = Field(..., ge=0,  le=1,   description="Extra paid classes in subject: 0 = No, 1 = Yes")
    activities: int = Field(..., ge=0,  le=1,   description="Extra-curricular activities: 0 = No, 1 = Yes")
    nursery:    int = Field(..., ge=0,  le=1,   description="Attended nursery school: 0 = No, 1 = Yes")
    higher:     int = Field(..., ge=0,  le=1,   description="Wants to pursue higher education: 0 = No, 1 = Yes")
    internet:   int = Field(..., ge=0,  le=1,   description="Internet access at home: 0 = No, 1 = Yes")
    romantic:   int = Field(..., ge=0,  le=1,   description="In a romantic relationship: 0 = No, 1 = Yes")
    famrel:     int = Field(..., ge=1,  le=5,   description="Quality of family relationships (1 = very bad … 5 = excellent)")
    freetime:   int = Field(..., ge=1,  le=5,   description="Free time after school (1 = very low … 5 = very high)")
    goout:      int = Field(..., ge=1,  le=5,   description="Going out with friends (1 = very low … 5 = very high)")
    Dalc:       int = Field(..., ge=1,  le=5,   description="Workday alcohol consumption (1 = very low … 5 = very high)")
    Walc:       int = Field(..., ge=1,  le=5,   description="Weekend alcohol consumption (1 = very low … 5 = very high)")
    health:     int = Field(..., ge=1,  le=5,   description="Current health status (1 = very bad … 5 = very good)")
    absences:   int = Field(..., ge=0,  le=93,  description="Number of school absences (0–93)")
    G1:         int = Field(..., ge=0,  le=20,  description="First period grade (0–20)")
    G2:         int = Field(..., ge=0,  le=20,  description="Second period grade (0–20)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "age": 17, "sex": 1, "address": 1, "famsize": 1,
                "Pstatus": 1, "Medu": 3, "Fedu": 2, "Mjob": 2,
                "Fjob": 3, "guardian": 0, "traveltime": 1, "studytime": 2,
                "failures": 0, "schoolsup": 0, "famsup": 1, "paid": 0,
                "activities": 1, "nursery": 1, "higher": 1, "internet": 1,
                "romantic": 0, "famrel": 4, "freetime": 3, "goout": 2,
                "Dalc": 1, "Walc": 2, "health": 4, "absences": 2,
                "G1": 13, "G2": 14
            }
        }
    }


# New-data submission schema — same as StudentFeatures plus the G3 label
class NewStudentRecord(BaseModel):
    age:        int = Field(..., ge=15, le=22)
    sex:        int = Field(..., ge=0,  le=1)
    address:    int = Field(..., ge=0,  le=1)
    famsize:    int = Field(..., ge=0,  le=1)
    Pstatus:    int = Field(..., ge=0,  le=1)
    Medu:       int = Field(..., ge=0,  le=4)
    Fedu:       int = Field(..., ge=0,  le=4)
    Mjob:       int = Field(..., ge=0,  le=4)
    Fjob:       int = Field(..., ge=0,  le=4)
    guardian:   int = Field(..., ge=0,  le=2)
    traveltime: int = Field(..., ge=1,  le=4)
    studytime:  int = Field(..., ge=1,  le=4)
    failures:   int = Field(..., ge=0,  le=4)
    schoolsup:  int = Field(..., ge=0,  le=1)
    famsup:     int = Field(..., ge=0,  le=1)
    paid:       int = Field(..., ge=0,  le=1)
    activities: int = Field(..., ge=0,  le=1)
    nursery:    int = Field(..., ge=0,  le=1)
    higher:     int = Field(..., ge=0,  le=1)
    internet:   int = Field(..., ge=0,  le=1)
    romantic:   int = Field(..., ge=0,  le=1)
    famrel:     int = Field(..., ge=1,  le=5)
    freetime:   int = Field(..., ge=1,  le=5)
    goout:      int = Field(..., ge=1,  le=5)
    Dalc:       int = Field(..., ge=1,  le=5)
    Walc:       int = Field(..., ge=1,  le=5)
    health:     int = Field(..., ge=1,  le=5)
    absences:   int = Field(..., ge=0,  le=93)
    G1:         int = Field(..., ge=0,  le=20)
    G2:         int = Field(..., ge=0,  le=20)
    G3:         int = Field(..., ge=0,  le=20, description="Actual final grade (target label)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "age": 16, "sex": 0, "address": 1, "famsize": 1,
                "Pstatus": 1, "Medu": 2, "Fedu": 2, "Mjob": 1,
                "Fjob": 2, "guardian": 0, "traveltime": 2, "studytime": 3,
                "failures": 0, "schoolsup": 1, "famsup": 0, "paid": 1,
                "activities": 0, "nursery": 1, "higher": 1, "internet": 1,
                "romantic": 0, "famrel": 3, "freetime": 2, "goout": 3,
                "Dalc": 1, "Walc": 1, "health": 5, "absences": 4,
                "G1": 11, "G2": 12, "G3": 12
            }
        }
    }


class PredictionResponse(BaseModel):
    predicted_G3: float = Field(..., description="Predicted final grade on a 0–20 scale")


class DataResponse(BaseModel):
    message:           str  = Field(..., description="Status message")
    total_rows:        int  = Field(..., description="Total rows in the persistent data store")
    new_rows_pending:  int  = Field(..., description="New rows added since last retrain")
    retrain_triggered: bool = Field(..., description="Whether automatic retraining was triggered")
    retrain_threshold: int  = Field(..., description="Rows needed to trigger auto-retrain")


class DataStatusResponse(BaseModel):
    total_rows:         int = Field(..., description="Total rows stored")
    new_rows_pending:   int = Field(..., description="Rows added since last retrain")
    retrain_threshold:  int = Field(..., description="Threshold to trigger auto-retrain")
    rows_until_retrain: int = Field(..., description="Rows still needed before next auto-retrain")


class RetrainResponse(BaseModel):
    message:    str   = Field(..., description="Status message")
    best_model: str   = Field(..., description="Name of the best-performing algorithm")
    test_mse:   float = Field(..., description="MSE of the best model on the held-out test set")
    rows_used:  int   = Field(..., description="Number of rows used for retraining")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_artifacts():
    model    = joblib.load(MODEL_PATH)
    scaler   = joblib.load(SCALER_PATH)
    features = joblib.load(FEATURE_PATH)
    return model, scaler, features


def _get_new_row_count() -> int:
    if not os.path.exists(COUNTER_PATH):
        return 0
    with open(COUNTER_PATH) as f:
        return int(f.read().strip() or 0)


def _set_new_row_count(n: int):
    with open(COUNTER_PATH, "w") as f:
        f.write(str(n))


def _run_retrain(df: pd.DataFrame) -> RetrainResponse:
    """Core retraining logic shared by /retrain and the auto-retrain trigger."""
    for col in df.select_dtypes(include="object").columns:
        df[col] = LabelEncoder().fit_transform(df[col])

    drop_cols = [c for c in ["school", "reason", "G3"] if c in df.columns]
    X = df.drop(columns=drop_cols)
    y = df["G3"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train)
    X_te = scaler.transform(X_test)

    candidates = {
        "LinearRegression": LinearRegression(),
        "SGDRegressor":     SGDRegressor(max_iter=1000, random_state=42),
        "DecisionTree":     DecisionTreeRegressor(max_depth=5, random_state=42),
        "RandomForest":     RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42),
    }

    best_name, best_mse, best_model = None, float("inf"), None
    for name, m in candidates.items():
        m.fit(X_tr, y_train)
        mse = mean_squared_error(y_test, m.predict(X_te))
        if mse < best_mse:
            best_mse, best_name, best_model = mse, name, m

    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(scaler,     SCALER_PATH)
    joblib.dump(list(X.columns), FEATURE_PATH)
    _set_new_row_count(0)   # reset counter after every successful retrain

    return RetrainResponse(
        message="Model retrained successfully.",
        best_model=best_name,
        test_mse=round(best_mse, 4),
        rows_used=len(df),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Status"])
def root():
    """API root — confirms the service is running."""
    return {"message": "Student Grade Prediction API is running. Visit /docs for Swagger UI."}


@app.get("/health", tags=["Status"])
def health():
    """Health check — verifies the model artefacts are loaded and ready."""
    try:
        _load_artifacts()
        return {"status": "ok", "model": "loaded"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model artefacts not found. Run /retrain first.",
        )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Prediction"],
    summary="Predict a student's final grade (G3)",
    responses={
        200: {"description": "Successful prediction"},
        422: {"description": "Validation error — field missing, wrong type, or out of range"},
        503: {"description": "Model not yet trained — POST a CSV to /retrain first"},
    },
)
def predict(data: StudentFeatures):
    """
    Accept 30 student feature values and return the predicted **G3** final grade.

    - All fields are **required** and **typed** (integer).
    - Each field has a **range constraint** enforced by Pydantic — out-of-range
      values return HTTP 422 with a clear error message.
    - The prediction is clipped to [0, 20] to match the real grade scale.
    """
    try:
        model, scaler, features = _load_artifacts()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet. POST data to /retrain first.",
        )

    row    = pd.DataFrame([data.model_dump()])[features]
    row_sc = scaler.transform(row)
    pred   = float(np.clip(model.predict(row_sc)[0], 0, 20))
    return PredictionResponse(predicted_G3=round(pred, 2))


# ---------------------------------------------------------------------------
# Streaming / incremental data ingestion
#
# POST /data accepts one new labelled student record at a time.
# Each row is appended to training_data.csv (the persistent data store).
# A plain-text counter tracks how many new rows have arrived since the last
# retrain.  Once that counter reaches RETRAIN_THRESHOLD the model is
# automatically retrained on the FULL accumulated dataset and the counter
# resets to 0.
#
# This satisfies "trigger a model update when new data is seen" — the system
# reacts to incoming data without any manual intervention.
# ---------------------------------------------------------------------------
@app.post(
    "/data",
    response_model=DataResponse,
    tags=["Model Management"],
    summary="Stream a new labelled record — auto-retrains every 10 new rows",
    responses={
        200: {"description": "Row stored; retraining triggered if threshold met"},
    },
)
def add_data(record: NewStudentRecord):
    """
    Submit **one new labelled student record** (all features + actual G3 grade).

    **Auto-retraining logic:**
    - The row is appended to `training_data.csv` on disk.
    - A counter tracks rows added since the last retrain.
    - When the counter reaches **10 rows**, all four candidate models are
      retrained on the full accumulated dataset and the best one (lowest MSE)
      replaces the live model automatically.
    - The counter resets to 0 after every successful retrain.

    This means the deployed model continuously improves as new real-world
    data arrives, with no manual intervention required.
    """
    new_row = pd.DataFrame([record.model_dump()])
    write_header = not os.path.exists(DATA_PATH)
    new_row.to_csv(DATA_PATH, mode="a", header=write_header, index=False)

    pending = _get_new_row_count() + 1
    _set_new_row_count(pending)
    total = len(pd.read_csv(DATA_PATH))

    retrain_triggered = False
    if pending >= RETRAIN_THRESHOLD:
        df = pd.read_csv(DATA_PATH)
        if len(df) >= 20:   # minimum rows needed for a meaningful train/test split
            _run_retrain(df)
            retrain_triggered = True
            pending = 0

    suffix = (
        " Model retrained automatically."
        if retrain_triggered
        else f" {RETRAIN_THRESHOLD - pending} more row(s) until auto-retrain."
    )
    return DataResponse(
        message="Record stored." + suffix,
        total_rows=total,
        new_rows_pending=pending,
        retrain_triggered=retrain_triggered,
        retrain_threshold=RETRAIN_THRESHOLD,
    )


@app.get(
    "/data/status",
    response_model=DataStatusResponse,
    tags=["Model Management"],
    summary="Check buffered row count and next auto-retrain countdown",
)
def data_status():
    """Returns the current state of the data buffer and retraining counter."""
    total   = len(pd.read_csv(DATA_PATH)) if os.path.exists(DATA_PATH) else 0
    pending = _get_new_row_count()
    return DataStatusResponse(
        total_rows=total,
        new_rows_pending=pending,
        retrain_threshold=RETRAIN_THRESHOLD,
        rows_until_retrain=max(0, RETRAIN_THRESHOLD - pending),
    )


@app.post(
    "/retrain",
    response_model=RetrainResponse,
    tags=["Model Management"],
    summary="Manually retrain by uploading a full CSV dataset",
    responses={
        200: {"description": "Retraining completed — best model saved"},
        400: {"description": "Invalid CSV file or missing G3 column"},
    },
)
async def retrain(
    file: UploadFile = File(
        ...,
        description="CSV file with the same columns as student-mat.csv, including the G3 target column",
    )
):
    """
    **Manual bulk retrain** — upload a full CSV to replace the training data
    and immediately retrain all four candidate models.

    Use this for large batch updates.
    For row-by-row streaming updates use `POST /data` instead.

    The CSV must:
    - Use `;` or `,` as delimiter
    - Contain a `G3` target column
    - Follow the same column schema as the original UCI dataset
    """
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    if "G3" not in df.columns:
        raise HTTPException(
            status_code=400, detail="CSV must contain a 'G3' target column."
        )

    # Persist as the new training store so /data rows append on top of it
    df.to_csv(DATA_PATH, index=False)

    return _run_retrain(df)
