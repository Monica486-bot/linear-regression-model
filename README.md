# Student Academic Performance Predictor

## Mission & Problem

Students' academic outcomes are shaped by a complex mix of social, family, and study-related factors. This project predicts a student's final mathematics grade (G3, scale 0–20) using 30 features — including study time, parental education, alcohol consumption, and prior period grades — to enable early identification of at-risk students before final exams.

**Dataset:** UCI Student Performance Dataset (`student-mat.csv`) — 395 students × 33 features (17 categorical + 16 numeric), covering demographics, family background, lifestyle, and academic history.
**Source:** P. Cortez & A. Silva, *Using Data Mining to Predict Secondary School Student Performance*, 2008. https://archive.ics.uci.edu/ml/datasets/Student+Performance

---

## Public API Endpoint (Swagger UI)

https://linear-regression-model-y8zs.onrender.com/docs

---

## Video Demo

> Insert your YouTube video link here

---

## Project Structure

```
linear_regression_model/
├── summative/
│   ├── linear_regression/
│   │   └── multivariate.ipynb      # EDA, model training, loss curve, scatter plot
│   ├── API/
│   │   ├── prediction.py           # FastAPI app
│   │   └── requirements.txt
│   └── FlutterApp/                 # Flutter mobile app
│       ├── lib/
│       │   ├── main.dart
│       │   └── prediction_page.dart
│       └── pubspec.yaml
├── pyproject.toml
└── README.md
```

---

## How to Run the Mobile App

### Prerequisites

- Flutter SDK ≥ 3.0 — https://docs.flutter.dev/get-started/install
- Android Studio or VS Code with the Flutter extension
- An Android emulator or physical device

### Steps

```bash
cd linear_regression_model/summative/FlutterApp
flutter pub get
flutter run
```

The app connects to the live deployed API. No local server setup is required.

---

## How to Run the API Locally

```bash
# Install uv
pip install uv

# Install dependencies
cd linear_regression_model
uv sync

# Start the API
cd summative/API
uv run uvicorn prediction:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the local Swagger UI.

---

## Deploying to Render

1. Push this repo to GitHub
2. Create a new **Web Service** on https://render.com
3. Set **Root Directory** to `linear_regression_model/summative/API`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn prediction:app --host 0.0.0.0 --port $PORT`
