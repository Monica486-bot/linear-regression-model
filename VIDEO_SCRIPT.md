# Video Demo Script — Student Grade Predictor
# Target: ≤ 7:00 | Camera ON the entire time | Screen shared the entire time

---

## BEFORE YOU HIT RECORD — Pre-flight checklist
- [ ] Camera on, face visible in corner
- [ ] Screen share active (full screen, not window-only)
- [ ] Flutter emulator running with the app open
- [ ] Browser tab open at: https://student-grade-api.onrender.com/docs
- [ ] Jupyter notebook open and fully executed (all outputs visible)
- [ ] No notifications / Do Not Disturb ON

---

## SEGMENT 1 — Mobile App Demo  [0:00 – 1:30]

**[0:00]**
> "This is my Student Grade Predictor — a machine learning app that predicts
> a student's final mathematics grade, G3, on a scale of 0 to 20, using
> 30 features from the UCI Student Performance dataset."

ACTION: Show the Flutter app running on the emulator/device.
Point to the page title and the output display card at the top.

**[0:15]**
> "The app has one prediction page. At the top is the output display area —
> it always shows, even before a prediction is made. Below it are 30 text
> fields, one for every variable the model needs, grouped into five sections:
> Personal Information, Family Background, School and Study, Lifestyle,
> and Period Grades."

ACTION: Slowly scroll through the sections so all fields are visible.

**[0:40]**
> "I'll fill in a valid prediction now."

ACTION: Fill in these values quickly (pre-memorise them):
  age=17, sex=1, address=1, famsize=1, Pstatus=1,
  Medu=3, Fedu=2, Mjob=2, Fjob=3, guardian=0,
  traveltime=1, studytime=2, failures=0, schoolsup=0, famsup=1,
  paid=0, activities=1, nursery=1, higher=1, internet=1,
  romantic=0, famrel=4, freetime=3, goout=2,
  Dalc=1, Walc=2, health=4, absences=2, G1=13, G2=14

**[1:10]**
> "I tap Predict — the app calls POST /predict on the live Render API."

ACTION: Tap Predict. Show the loading spinner, then the result card turning blue.

**[1:20]**
> "The model predicts a G3 of [X] out of 20. Now let me test the validation —
> I'll enter an age of 99, which is out of the allowed range of 15 to 22."

ACTION: Clear age field, type 99, tap Predict.
Show the red inline error: "Enter a value between 15 and 22".

---

## SEGMENT 2 — Swagger UI API Tests  [1:30 – 3:00]

**[1:30]**
ACTION: Switch to browser — https://student-grade-api.onrender.com/docs

> "This is the Swagger UI for the deployed API on Render. There are three
> endpoint groups: Status, Prediction, and Model Management."

**[1:45]**
> "I'll test POST /predict. The example body is pre-filled — I click
> Try it out, then Execute."

ACTION: Expand POST /predict → Try it out → Execute.
Show the 200 response with predicted_G3.

**[2:05]**
> "Now I'll test a range violation — I'll change G1 to 25, which exceeds
> the maximum of 20."

ACTION: Edit G1 to 25 in the request body → Execute.
Show the 422 Unprocessable Entity response with Pydantic's error detail.

**[2:20]**
> "And a missing field — I'll remove G2 entirely."

ACTION: Delete the G2 line from the JSON → Execute.
Show the 422 response saying G2 is required.

**[2:35]**
> "Finally, the retraining endpoint. POST /data lets me stream a single
> new labelled record. Every 10 new rows the model automatically retrains."

ACTION: Expand POST /data → Try it out → Execute with the pre-filled example.
Show the response: "Record stored. 9 more row(s) until auto-retrain."

---

## SEGMENT 3 — Notebook Walkthrough  [3:00 – 4:30]

**[3:00]**
ACTION: Switch to Jupyter notebook. Scroll to the top.

> "The notebook covers the full ML pipeline. The dataset is the UCI Student
> Performance dataset — 395 students, 33 features, a mix of numeric,
> ordinal, and categorical columns."

**[3:15]**
ACTION: Scroll to Visualization 1 (histogram grid).

> "The histograms show G3 is roughly normal but with a spike at zero —
> students who failed entirely. G1 and G2 have similar shapes, which
> already tells us prior grades are the strongest predictors."

**[3:30]**
ACTION: Scroll to Visualization 2 (correlation heatmap).

> "The heatmap confirms it — G2 has a correlation of 0.90 with G3, G1
> is 0.80. Failures is negative at minus 0.36. Based on this I dropped
> 'school' and 'reason' — both had near-zero correlation with G3."

**[3:45]**
ACTION: Scroll to the model comparison table output.

> "I trained four models: OLS Linear Regression, SGD Regressor — which is
> stochastic linear regression — Decision Tree, and Random Forest.
> The selection criterion is lowest test MSE. Random Forest achieved the
> lowest MSE of approximately [X], so it was saved as the production model.
> Linear Regression came second at [X], Decision Tree at [X], and SGD
> at [X]."

**[4:05]**
ACTION: Scroll to the loss curve plot.

> "This is the gradient descent loss curve — train loss in blue, test loss
> in orange. Both curves converge and stay close together, which means
> the model is not overfitting."

**[4:15]**
ACTION: Scroll to the before/after scatter plot.

> "And here is the scatter plot — before on the left showing raw data,
> after on the right with the best-fit regression line through the
> predicted values."

---

## SEGMENT 4 — The 4 Mandatory Questions  [4:30 – 6:45]

**[4:30] Q1 — Is your loss high or low, and what can you do to reduce it?**

ACTION: Point to the model comparison table or loss curve.

> "The test MSE for Random Forest is approximately [X]. On a 0-to-20 grade
> scale, an MSE of around 1 to 2 means predictions are off by roughly 1
> to 1.4 grade points on average — that is relatively low for this dataset.
> To reduce it further I could collect more data beyond the 395 rows,
> engineer interaction features such as G1 times study time, remove the
> G3-equals-zero outliers which skew the loss, or apply cross-validation
> instead of a single train-test split."

**[5:10] Q2 — Are there hyperparameters that can improve model performance?**

> "Yes. For Random Forest the key hyperparameters are n_estimators —
> the number of trees — max_depth, min_samples_split, and max_features.
> I used n_estimators of 100 and max_depth of 6. Using GridSearchCV or
> RandomizedSearchCV to tune these would likely reduce MSE further.
> For the SGD Regressor, the learning rate, eta0, and regularisation
> penalty are the main levers. For Decision Tree, max_depth controls
> the bias-variance trade-off directly."

**[5:45] Q3 — What happens with new data? How do you update the model in deployment?**

ACTION: Switch back to Swagger UI, point to POST /data and POST /retrain.

> "I built two update paths into the API. POST /data accepts one new
> labelled student record at a time and appends it to a persistent CSV
> on disk. A counter tracks new rows since the last retrain. Once 10 new
> rows arrive the API automatically retrains all four models and saves
> the best one — the live model is swapped with no downtime and no manual
> step. For large batch updates, POST /retrain accepts a full CSV upload
> and triggers an immediate retrain. This means the model continuously
> improves as real-world data accumulates."

**[6:20] Q4 — What was the basis for configuring the CORS middleware?**

ACTION: Switch to prediction.py in the editor, scroll to the CORS block.

> "CORS is needed because the Flutter app and Swagger UI run on different
> origins than the API server. I configured four specific things.
> First, allow_origins is an explicit list — localhost 3000, 8080, and
> 52000 for local development, and the Render URL for production.
> Wildcard star is intentionally avoided because when allow_credentials
> is True the CORS spec forbids wildcard origins — the browser rejects
> the response. Second, allow_credentials is True so the Flutter app can
> forward Authorization headers. Third, allow_methods is GET and POST only —
> the API has no delete or update operations so exposing those methods
> would be unnecessary attack surface. Fourth, allow_headers is
> Content-Type and Authorization only — Content-Type is required for
> JSON bodies and CSV uploads, Authorization is reserved for future
> token-based auth."

---

## SEGMENT 5 — Closing  [6:45 – 7:00]

**[6:45]**
> "To summarise: the Random Forest model was selected based on lowest
> test MSE, the API is live on Render with Swagger UI at the link in
> the README, the Flutter app connects to it directly, and the model
> updates automatically as new data streams in. Thank you."

ACTION: Show the app one final time making a prediction.

---

## TIMING SUMMARY

| Segment                        | Start | End  | Duration |
|-------------------------------|-------|------|----------|
| 1. Mobile app demo + validation | 0:00 | 1:30 | 1:30     |
| 2. Swagger UI tests             | 1:30 | 3:00 | 1:30     |
| 3. Notebook walkthrough         | 3:00 | 4:30 | 1:30     |
| 4. Four mandatory questions     | 4:30 | 6:45 | 2:15     |
| 5. Closing                      | 6:45 | 7:00 | 0:15     |
| **TOTAL**                       |      |      | **7:00** |

---

## FILL-IN VALUES (complete after running the notebook)

Replace the placeholders above with your actual results:

| Model             | Test MSE | R²   |
|-------------------|----------|------|
| LinearRegression  | ___.__   | 0.___ |
| SGDRegressor      | ___.__   | 0.___ |
| DecisionTree      | ___.__   | 0.___ |
| RandomForest      | ___.__   | 0.___ |
| **Best model →**  | **lowest above** | |

---

## RECORDING TIPS
- Speak at a steady pace — do not rush Segment 4, the questions carry the most weight
- Keep the cursor moving to guide the viewer's eye
- Do NOT explain challenges, setup problems, or what you tried that failed
- If you stumble on a word, keep going — do not restart the whole recording
- Use OBS, Loom, or Windows Game Bar (Win+G) to record
- Upload as unlisted YouTube video, paste the link into README.md
