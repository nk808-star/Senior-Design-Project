"""
Loads pre-trained KNN models (seuclidean distance) from backend/models/
and uses them for disease risk prediction.

Feature encoding here must match build_dataset.py _bin_features exactly.

If a trained model file is not found (i.e. train_knn.py hasn't been run yet),
the engine falls back to an evidence-based logistic scoring function so the
API always returns something sensible.
"""

import os
import math
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

DISEASES = [
    ("gout",               "Gout"),
    ("diabetes",           "Type 2 Diabetes"),
    ("ckd",                "Chronic Kidney Disease"),
    ("hypertension",       "Hypertension"),
    ("cvd",                "Cardiovascular Disease"),
    ("metabolic_syndrome", "Metabolic Syndrome"),
]

DISEASE_DESCRIPTIONS = {
    "gout":               "Risk inferred from serum uric acid levels and metabolic profile.",
    "diabetes":           "Risk inferred from glucose metabolism, BMI, and lifestyle factors.",
    "ckd":                "Risk inferred from renal function markers and metabolic status.",
    "hypertension":       "Risk inferred from metabolic profile, lifestyle, and demographics.",
    "cvd":                "Risk inferred from lipid profile, metabolic markers, and lifestyle.",
    "metabolic_syndrome": "Risk inferred from combined metabolic risk factors (ATP III/IDF).",
}


class RiskModelEngine:

    def __init__(self):
        self._models: dict = {}
        self._load_models()

    # ------------------------------------------------------------------ #
    # Model loading                                                        #
    # ------------------------------------------------------------------ #

    def _load_models(self):
        try:
            import joblib
        except ImportError:
            print("  joblib not installed — trained models unavailable, using fallback scoring")
            return

        for disease_id, _ in DISEASES:
            path = os.path.join(MODELS_DIR, f"{disease_id}_knn.pkl")
            if os.path.exists(path):
                self._models[disease_id] = joblib.load(path)
                print(f"  Loaded KNN model: {disease_id}  (K={self._models[disease_id]['best_k']})")
            else:
                print(f"  No trained model for {disease_id} — using fallback scoring")

    # ------------------------------------------------------------------ #
    # Feature encoding  (must stay in sync with build_dataset.py)        #
    # ------------------------------------------------------------------ #

    def _encode(self, filters: dict) -> np.ndarray:
        """
        Convert UI string filter values to the same numeric feature vector
        used during training.  Order must match FEATURE_COLS in build_dataset.py.
        """
        f = []

        # f_age  (0-5)
        age_map = {"18-24": 0, "25-34": 1, "35-44": 2, "45-54": 3, "55-64": 4, "65+": 5}
        f.append(float(age_map.get(filters.get("ageGroup", ""), 2)))

        # f_gender  (0=Female, 1=Male)
        f.append(1.0 if filters.get("gender") == "Male" else 0.0)

        # f_ethnicity  (0-4)
        eth_map = {
            "Mexican American": 0, "Other Hispanic": 1,
            "Non-Hispanic White": 2, "Non-Hispanic Black": 3, "Other": 4,
        }
        f.append(float(eth_map.get(filters.get("ethnicity", ""), 2)))

        # f_ses  (0=Low, 1=Middle, 2=High)
        ses_map = {"Low": 0, "Middle": 1, "High": 2}
        f.append(float(ses_map.get(filters.get("socioeconomicStatus", ""), 1)))

        # f_smoking  (0=Never, 1=Former, 2=Current)
        smoke_map = {"Never": 0, "Former": 1, "Current": 2}
        f.append(float(smoke_map.get(filters.get("smokingStatus", ""), 0)))

        # f_alcohol  (0=None, 1=Moderate, 2=Heavy)
        alc_map = {"None": 0, "Moderate": 1, "Heavy": 2}
        f.append(float(alc_map.get(filters.get("alcoholUse", ""), 0)))

        # f_activity  (0=Low, 1=Moderate, 2=High)
        act_map = {"Low": 0, "Moderate": 1, "High": 2}
        f.append(float(act_map.get(filters.get("physicalActivity", ""), 1)))

        # f_bmi  (0=Underweight, 1=Normal, 2=Overweight, 3=Obese)
        bmi = filters.get("bmi", "")
        if "Underweight" in bmi:    bmi_v = 0
        elif "Normal"    in bmi:    bmi_v = 1
        elif "Overweight" in bmi:   bmi_v = 2
        elif "Obese"     in bmi:    bmi_v = 3
        else:                       bmi_v = 1
        f.append(float(bmi_v))

        # f_glucose  (0=Normal, 1=Prediabetes, 2=Diabetes)
        glc = filters.get("bloodGlucose", "")
        glc_v = 2 if "Diabetes (>=126)" in glc else 1 if "Prediabetes" in glc else 0
        f.append(float(glc_v))

        # f_hba1c  (0=Normal, 1=Prediabetes, 2=Diabetes)
        hba = filters.get("hba1c", "")
        hba_v = 2 if "Diabetes" in hba else 1 if "Prediabetes" in hba else 0
        f.append(float(hba_v))

        # f_hdl  (0=Low, 1=Normal, 2=High)
        hdl = filters.get("HDL", "")
        hdl_v = 0 if "Low" in hdl else 2 if "High" in hdl else 1
        f.append(float(hdl_v))

        # f_ldl  (0=Optimal, 1=Borderline, 2=High)
        ldl = filters.get("LDL", "")
        ldl_v = 2 if "High" in ldl else 1 if "Borderline" in ldl else 0
        f.append(float(ldl_v))

        # f_triglycerides  (0=Normal, 1=Borderline, 2=High)
        trig = filters.get("triglycerides", "")
        trig_v = 2 if "High" in trig else 1 if "Borderline" in trig else 0
        f.append(float(trig_v))

        # f_crp  (0=Low Risk, 1=Average, 2=High Risk)
        crp = filters.get("crp", "")
        crp_v = 2 if "High Risk" in crp else 1 if "Average" in crp else 0
        f.append(float(crp_v))

        # f_egfr  (0=Reduced <60, 1=Mild 60-89, 2=Normal >=90)
        egfr = filters.get("egfr", "")
        egfr_v = 0 if "<60" in egfr else 1 if "60-89" in egfr else 2
        f.append(float(egfr_v))

        # f_creatinine  (0=Normal, 1=High)
        f.append(1.0 if filters.get("creatinine") == "High" else 0.0)

        # f_bun  (0=Normal, 1=High)
        f.append(1.0 if "High" in filters.get("BUN", "") else 0.0)

        # f_uric_acid  (0=Low, 1=Normal, 2=High)
        ua = filters.get("uricAcid", "")
        ua_v = 0 if "Low" in ua else 2 if "High" in ua else 1
        f.append(float(ua_v))

        # f_alt  (0=Normal, 1=Elevated)
        f.append(1.0 if filters.get("alt") == "Elevated" else 0.0)

        # f_ggt  (0=Normal, 1=High)
        f.append(1.0 if filters.get("ggt") == "High" else 0.0)

        return np.array(f, dtype=float).reshape(1, -1)

    # ------------------------------------------------------------------ #
    # Fallback scoring (evidence-based logistic, used before training)    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def _fallback_score(self, disease_id: str, filters: dict) -> float:
        v = {}
        age_map = {"18-24": 0, "25-34": 1, "35-44": 2, "45-54": 3, "55-64": 4, "65+": 5}
        v["age"]             = age_map.get(filters.get("ageGroup", ""), 2)
        v["male"]            = 1 if filters.get("gender") == "Male" else 0
        sm                   = filters.get("smokingStatus", "")
        v["smoking_current"] = 1 if sm == "Current" else 0
        v["smoking_former"]  = 1 if sm == "Former"  else 0
        act                  = filters.get("physicalActivity", "")
        v["activity_low"]    = 1 if act == "Low" else 0
        bmi                  = filters.get("bmi", "")
        v["bmi_obese"]       = 1 if "Obese"      in bmi else 0
        v["bmi_overweight"]  = 1 if "Overweight" in bmi else 0
        glc                  = filters.get("bloodGlucose", "")
        v["glucose_diabetes"]    = 1 if "Diabetes (>=126)" in glc else 0
        v["glucose_prediabetes"] = 1 if "Prediabetes"      in glc else 0
        hba                  = filters.get("hba1c", "")
        v["hba1c_diabetes"]  = 1 if "Diabetes"    in hba else 0
        hdl                  = filters.get("HDL", "")
        v["hdl_low"]         = 1 if "Low"         in hdl else 0
        ldl                  = filters.get("LDL", "")
        v["ldl_high"]        = 1 if "High"        in ldl else 0
        v["ldl_borderline"]  = 1 if "Borderline"  in ldl else 0
        trig                 = filters.get("triglycerides", "")
        v["trig_high"]       = 1 if "High"        in trig else 0
        crp                  = filters.get("crp", "")
        v["crp_high"]        = 1 if "High Risk"   in crp else 0
        egfr                 = filters.get("egfr", "")
        v["egfr_reduced"]    = 1 if "<60"          in egfr else 0
        v["egfr_mild"]       = 1 if "60-89"        in egfr else 0
        v["creatinine_high"] = 1 if filters.get("creatinine") == "High" else 0
        v["bun_high"]        = 1 if "High" in filters.get("BUN", "") else 0
        ua                   = filters.get("uricAcid", "")
        v["uric_high"]       = 1 if "High"            in ua  else 0
        eth                  = filters.get("ethnicity", "")
        v["eth_black"]       = 1 if "Non-Hispanic Black" in eth else 0

        scores = {
            "gout": (
                -2.8
                + 2.5  * v["uric_high"]
                + 0.3  * v["age"]
                + 0.5  * v["male"]
                + 0.6  * v["bmi_obese"]
                + 0.4  * v["glucose_diabetes"]
                + 0.3  * v["creatinine_high"]
            ),
            "cvd": (
                -3.2
                + 0.45 * v["age"]
                + 0.35 * v["male"]
                + 1.3  * v["smoking_current"]
                + 0.45 * v["smoking_former"]
                + 0.85 * v["ldl_high"]
                + 0.35 * v["ldl_borderline"]
                + 0.95 * v["hdl_low"]
                + 0.7  * v["trig_high"]
                + 0.6  * v["activity_low"]
                + 0.75 * v["glucose_diabetes"]
                + 0.7  * v["crp_high"]
                + 0.4  * v["bmi_obese"]
                + 0.4  * v["eth_black"]
            ),
            "diabetes": (
                -3.5
                + 0.3  * v["age"]
                + 1.6  * v["bmi_obese"]
                + 0.75 * v["bmi_overweight"]
                + 2.0  * v["glucose_prediabetes"]
                + 3.5  * v["glucose_diabetes"]
                + 2.5  * v["hba1c_diabetes"]
                + 0.7  * v["activity_low"]
            ),
            "ckd": (
                -3.0
                + 3.2  * v["egfr_reduced"]
                + 1.6  * v["egfr_mild"]
                + 1.6  * v["creatinine_high"]
                + 1.1  * v["bun_high"]
                + 0.85 * v["uric_high"]
                + 1.2  * v["glucose_diabetes"]
                + 0.35 * v["age"]
            ),
            "hypertension": (
                -2.5
                + 0.42 * v["age"]
                + 1.05 * v["bmi_obese"]
                + 0.55 * v["bmi_overweight"]
                + 0.65 * v["activity_low"]
                + 0.55 * v["smoking_current"]
                + 0.65 * v["eth_black"]
                + 0.4  * v["glucose_diabetes"]
            ),
            "metabolic_syndrome": (
                -2.8
                + 1.55 * v["bmi_obese"]
                + 0.75 * v["bmi_overweight"]
                + 0.85 * v["glucose_prediabetes"]
                + 1.55 * v["glucose_diabetes"]
                + 0.85 * v["hdl_low"]
                + 0.85 * v["trig_high"]
                + 0.7  * v["activity_low"]
                + 0.6  * v["crp_high"]
            ),
        }
        return self._sigmoid(scores.get(disease_id, -2.0))

    # ------------------------------------------------------------------ #
    # Confidence & risk level                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _confidence(filters: dict) -> float:
        """Scales from 0.45 (no inputs) to 0.95 (all inputs filled)."""
        keys = [
            "ageGroup", "gender", "smokingStatus", "physicalActivity", "bmi",
            "bloodGlucose", "hba1c", "HDL", "LDL", "triglycerides", "crp",
            "egfr", "creatinine", "BUN", "uricAcid",
        ]
        filled = sum(1 for k in keys if filters.get(k))
        return round(0.45 + (filled / len(keys)) * 0.50, 2)

    @staticmethod
    def _level(score: float) -> str:
        if score < 0.20:
            return "low"
        if score < 0.45:
            return "moderate"
        return "high"

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def predict(self, filters: dict) -> list:
        conf = self._confidence(filters)
        x    = self._encode(filters)

        results = []
        for disease_id, disease_name in DISEASES:
            payload = self._models.get(disease_id)
            if payload is not None:
                clf   = payload["model"]
                proba = clf.predict_proba(x)       # shape (1, 2) → [P(0), P(1)]
                score = float(proba[0, 1])
            else:
                score = self._fallback_score(disease_id, filters)

            results.append({
                "diseaseId":   disease_id,
                "diseaseName": disease_name,
                "riskLevel":   self._level(score),
                "score":       round(score, 3),
                "confidence":  conf,
                "description": DISEASE_DESCRIPTIONS[disease_id],
            })

        return results
