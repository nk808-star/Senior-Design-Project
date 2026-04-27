"""
Downloads NHANES XPT files from the CDC across multiple survey cycles,
merges them on SEQN, bins continuous biomarkers into the same categories
the UI uses, infers binary disease labels from clinical thresholds, and writes:

    backend/data/nhanes_features.csv
    backend/data/nhanes_labels.csv

To add or remove cycles, edit the CYCLES list below.
Run once before training (or re-run whenever you change CYCLES):
    cd backend
    python build_dataset.py
    python train_knn.py
"""

import os
import numpy as np
import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ------------------------------------------------------------------ #
# Cycles to include — add or remove entries here.                    #
# year   : used in the CDC download URL                              #
# suffix : appended to every filename  (DEMO + suffix = DEMO_J)     #
# label  : human-readable name used in download messages            #
#                                                                    #
# Note: file naming is consistent for cycles 2009-2018.             #
# Going further back (pre-2009) some files use different names;     #
# missing files are skipped automatically with a warning.           #
# ------------------------------------------------------------------ #
CYCLES = [
    {"year": "2017", "suffix": "_J", "label": "2017-2018"},
    {"year": "2015", "suffix": "_I", "label": "2015-2016"},
    {"year": "2013", "suffix": "_H", "label": "2013-2014"},
    {"year": "2011", "suffix": "_G", "label": "2011-2012"},
    {"year": "2009", "suffix": "_F", "label": "2009-2010"},
    {"year": "2007", "suffix": "_E", "label": "2007-2008"},
    {"year": "2005", "suffix": "_D", "label": "2005-2006"},
    {"year": "2003", "suffix": "_C", "label": "2003-2004"},
    {"year": "2001", "suffix": "_B", "label": "2001-2002"},
    {"year": "1999", "suffix": "",   "label": "1999-2000"},  # no suffix in first cycle
]

# Base file names (suffix appended per cycle)
FILE_BASES = {
    "demo":   "DEMO",    # Demographics (age, sex, race, income-to-poverty)
    "bmx":    "BMX",     # Body measures (BMI, waist)
    "bpx":    "BPX",     # Blood pressure
    "tchol":  "TCHOL",   # Total cholesterol
    "trigly": "TRIGLY",  # Triglycerides + LDL
    "hdl":    "HDL",     # HDL cholesterol
    "glu":    "GLU",     # Fasting glucose
    "ghb":    "GHB",     # HbA1c
    "biopro": "BIOPRO",  # Creatinine, uric acid, BUN, ALT, GGT
    "hscrp":  "HSCRP",   # High-sensitivity CRP (named CRP in older cycles)
    "smq":    "SMQ",     # Smoking questionnaire
    "paq":    "PAQ",     # Physical activity questionnaire
    "alq":    "ALQ",     # Alcohol use
    "hiq":    "HIQ",     # Health insurance questionnaire
    "ocq":    "OCQ",     # Occupation / employment questionnaire
    "cbc":    "CBC",     # Complete blood count (hemoglobin, HCT, WBC)
    "ins":    "INS",     # Insulin (fasting subsample)
}

# CBC file was named L25_* in very early cycles — handled by graceful skip

# Some files use a different base name in older cycles
FILE_OVERRIDES = {
    # HSCRP file was named CRP (no HS prefix) before 2013
    ("hscrp", "2011"): "CRP_G",
    ("hscrp", "2009"): "CRP_F",
    ("hscrp", "2007"): "CRP_E",
    ("hscrp", "2005"): "CRP_D",
    ("hscrp", "2003"): "CRP_C",
    ("hscrp", "2001"): "CRP_B",
    ("hscrp", "1999"): "CRP",
}

# Older cycles (pre-2007) use a different CDC URL structure
LEGACY_URL_CYCLES = {
    "2007": "https://wwwn.cdc.gov/Nchs/Nhanes/2007-2008",
    "2005": "https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006",
    "2003": "https://wwwn.cdc.gov/Nchs/Nhanes/2003-2004",
    "2001": "https://wwwn.cdc.gov/Nchs/Nhanes/2001-2002",
    "1999": "https://wwwn.cdc.gov/Nchs/Nhanes/1999-2000",
}


# ------------------------------------------------------------------ #
# Download helpers                                                     #
# ------------------------------------------------------------------ #

def _download_xpt(year: str, filename: str) -> pd.DataFrame:
    """
    Download one XPT file, cache it locally.
    Tries the modern CDC URL first; falls back to the legacy URL
    for older cycles that predate the /Nchs/Data/Nhanes/Public/ structure.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{filename}.XPT")
    if not os.path.exists(path):
        urls = [
            f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{filename}.XPT",
        ]
        if year in LEGACY_URL_CYCLES:
            urls.append(f"{LEGACY_URL_CYCLES[year]}/{filename}.XPT")

        downloaded = False
        for url in urls:
            try:
                print(f"    Downloading {url} ...")
                r = requests.get(url, timeout=120)
                if r.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(r.content)
                    downloaded = True
                    break
            except requests.RequestException:
                continue
        if not downloaded:
            raise FileNotFoundError(f"Could not download {filename} for year {year}")
    return pd.read_sas(path, format="xport")


def _load_cycle(cycle: dict) -> dict[str, pd.DataFrame]:
    """Download all files for one cycle. Skips files that fail gracefully."""
    year   = cycle["year"]
    suffix = cycle["suffix"]
    label  = cycle["label"]
    print(f"\n  Cycle {label}:")

    dfs = {}
    for key, base in FILE_BASES.items():
        # Check for a known override (e.g. CRP vs HSCRP in older cycles)
        override = FILE_OVERRIDES.get((key, year))
        filename = override if override else base + suffix
        try:
            dfs[key] = _download_xpt(year, filename)
            print(f"    {filename}: {dfs[key].shape}")
        except Exception as e:
            print(f"    WARNING: {filename} not available — {e}")
    return dfs


# ------------------------------------------------------------------ #
# Derived variables                                                    #
# ------------------------------------------------------------------ #

def _ckd_epi_egfr(row) -> float:
    """CKD-EPI 2009 equation. Returns eGFR (mL/min/1.73 m²)."""
    scr = row.get("LBXSCR")
    age = row.get("RIDAGEYR")
    is_male = row.get("RIAGENDR") == 1
    if pd.isna(scr) or pd.isna(age):
        return np.nan
    if is_male:
        kappa, alpha, mult = 0.9, -0.411, 141
    else:
        kappa, alpha, mult = 0.7, -0.329, 144
    ratio = scr / kappa
    exp = alpha if ratio < 1 else -1.209
    return mult * (ratio ** exp) * (0.993 ** age)


def _pa_score(row) -> float:
    """
    MET-minute/week proxy.
    Vigorous activity ≈ 8 METs, moderate ≈ 4 METs.
    PAD615 / PAD630 are minutes per week.
    """
    vig = row.get("PAD615") if not pd.isna(row.get("PAD615", np.nan)) else 0.0
    mod = row.get("PAD630") if not pd.isna(row.get("PAD630", np.nan)) else 0.0
    return vig * 8 + mod * 4


# ------------------------------------------------------------------ #
# Feature binning  (must match ml_model.py _encode exactly)          #
# ------------------------------------------------------------------ #

def _bin_features(df: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=df.index)

    # f_age  0=18-24 … 5=65+
    f["f_age"] = pd.cut(
        df["RIDAGEYR"], bins=[0, 24, 34, 44, 54, 64, 200],
        labels=[0, 1, 2, 3, 4, 5]
    ).astype(float)

    # f_gender  0=Female, 1=Male
    f["f_gender"] = (df["RIAGENDR"] == 1).astype(float)

    # f_ethnicity  0=Mex-Am … 4=Other   (RIDRETH3: 1,2,3,4,6,7)
    eth_map = {1: 0, 2: 1, 3: 2, 4: 3, 6: 1, 7: 4}
    f["f_ethnicity"] = df["RIDRETH3"].map(eth_map).fillna(4).astype(float)

    # f_ses  income-to-poverty ratio → 0=Low 1=Middle 2=High
    f["f_ses"] = pd.cut(
        df["INDFMPIR"], bins=[-np.inf, 1.3, 3.5, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_smoking  0=Never 1=Former 2=Current
    # SMQ020=1 → ever smoked ≥100 cigs; SMQ040=1/2 → still smoking
    def _smoke(row):
        if row.get("SMQ020") != 1:
            return 0
        return 2 if row.get("SMQ040") in [1, 2] else 1
    f["f_smoking"] = df.apply(_smoke, axis=1).astype(float)

    # f_alcohol  0=None 1=Moderate 2=Heavy   (ALQ130 = avg drinks/day)
    def _alc(val):
        if pd.isna(val) or val == 0:
            return 0
        return 1 if val <= 2 else 2
    f["f_alcohol"] = df["ALQ130"].apply(_alc).astype(float)

    # f_activity  0=Low 1=Moderate 2=High  (MET-min/week)
    f["f_activity"] = pd.cut(
        df["pa_score"], bins=[-np.inf, 500, 1500, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_bmi  0=Underweight 1=Normal 2=Overweight 3=Obese
    f["f_bmi"] = pd.cut(
        df["BMXBMI"], bins=[-np.inf, 18.5, 25, 30, np.inf],
        labels=[0, 1, 2, 3]
    ).astype(float)

    # f_glucose  0=Normal(<100) 1=Prediabetes(100-125) 2=Diabetes(≥126)
    f["f_glucose"] = pd.cut(
        df["LBXGLU"], bins=[-np.inf, 100, 126, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_hba1c  0=Normal(<5.7) 1=Prediabetes(5.7-6.4) 2=Diabetes(≥6.5)
    f["f_hba1c"] = pd.cut(
        df["LBXGH"], bins=[-np.inf, 5.7, 6.5, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_hdl  0=Low 1=Normal 2=High  (gender-specific low threshold)
    def _hdl(row):
        hdl = row.get("LBDHDD")
        if pd.isna(hdl):
            return np.nan
        low = 40 if row.get("RIAGENDR") == 1 else 50
        if hdl < low:
            return 0
        return 1 if hdl < 60 else 2
    f["f_hdl"] = df.apply(_hdl, axis=1).astype(float)

    # f_ldl  0=Optimal(<110) 1=Borderline(110-159) 2=High(≥160)
    f["f_ldl"] = pd.cut(
        df["LBDLDL"], bins=[-np.inf, 110, 160, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_triglycerides  0=Normal(<150) 1=Borderline(150-199) 2=High(≥200)
    f["f_triglycerides"] = pd.cut(
        df["LBXTR"], bins=[-np.inf, 150, 200, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_crp  0=Low Risk(<1) 1=Average(1-3) 2=High Risk(>3)  mg/L
    f["f_crp"] = pd.cut(
        df["LBXHSCRP"], bins=[-np.inf, 1, 3, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_egfr  0=Reduced(<60) 1=Mild(60-89) 2=Normal(≥90)
    f["f_egfr"] = pd.cut(
        df["egfr"], bins=[-np.inf, 60, 90, np.inf],
        labels=[0, 1, 2]
    ).astype(float)

    # f_creatinine  0=Normal 1=High  (male >1.2, female >1.0 mg/dL)
    def _creat(row):
        scr = row.get("LBXSCR")
        if pd.isna(scr):
            return np.nan
        thresh = 1.2 if row.get("RIAGENDR") == 1 else 1.0
        return 1 if scr > thresh else 0
    f["f_creatinine"] = df.apply(_creat, axis=1).astype(float)

    # f_bun  0=Normal(7-20) 1=High(>20) mg/dL
    f["f_bun"] = (df["LBXSBU"] > 20).astype(float)

    # f_uric_acid  0=Low(<3.5) 1=Normal 2=High  (male >7.0, female >6.0)
    def _ua(row):
        ua = row.get("LBXSUA")
        if pd.isna(ua):
            return np.nan
        hi = 7.0 if row.get("RIAGENDR") == 1 else 6.0
        if ua < 3.5:
            return 0
        return 2 if ua >= hi else 1
    f["f_uric_acid"] = df.apply(_ua, axis=1).astype(float)

    # f_alt  0=Normal 1=Elevated  (male >40, female >31 U/L)
    def _alt(row):
        alt = row.get("LBXSATSI")
        if pd.isna(alt):
            return np.nan
        thresh = 40 if row.get("RIAGENDR") == 1 else 31
        return 1 if alt > thresh else 0
    f["f_alt"] = df.apply(_alt, axis=1).astype(float)

    # f_ggt  0=Normal 1=High  (male >55, female >38 U/L)
    def _ggt(row):
        ggt = row.get("LBXSGTSI")
        if pd.isna(ggt):
            return np.nan
        thresh = 55 if row.get("RIAGENDR") == 1 else 38
        return 1 if ggt > thresh else 0
    f["f_ggt"] = df.apply(_ggt, axis=1).astype(float)

    # f_ast  0=Normal 1=Elevated  (male >40, female >31 U/L)
    def _ast(row):
        ast = row.get("LBXSASSI")
        if pd.isna(ast):
            return np.nan
        thresh = 40 if row.get("RIAGENDR") == 1 else 31
        return 1 if ast > thresh else 0
    f["f_ast"] = df.apply(_ast, axis=1).astype(float)

    # f_albumin  0=Low(<3.5) 1=Normal(3.5-5.0)  g/dL
    if "LBXSAL" in df.columns:
        f["f_albumin"] = np.where(
            df["LBXSAL"].isna(), np.nan,
            np.where(df["LBXSAL"] < 3.5, 0.0, 1.0)
        )
    else:
        f["f_albumin"] = np.nan

    # f_insulin  0=Normal(<25) 1=Elevated(25-50) 2=High(>50)  µU/mL
    if "LBXIN" in df.columns:
        f["f_insulin"] = pd.cut(
            df["LBXIN"], bins=[-np.inf, 25, 50, np.inf],
            labels=[0, 1, 2]
        ).astype(float)
    else:
        f["f_insulin"] = np.nan

    # f_hemoglobin  0=Low 1=Normal 2=High  (gender-specific)
    def _hgb(row):
        hgb = row.get("LBXHGB")
        if pd.isna(hgb):
            return np.nan
        if row.get("RIAGENDR") == 1:
            if hgb < 13.5: return 0
            return 2 if hgb > 17.5 else 1
        else:
            if hgb < 12.0: return 0
            return 2 if hgb > 15.5 else 1
    if "LBXHGB" in df.columns:
        f["f_hemoglobin"] = df.apply(_hgb, axis=1).astype(float)
    else:
        f["f_hemoglobin"] = np.nan

    # f_hct  0=Low 1=Normal 2=High  (gender-specific, %)
    def _hct(row):
        hct = row.get("LBXHCT")
        if pd.isna(hct):
            return np.nan
        if row.get("RIAGENDR") == 1:
            if hct < 41: return 0
            return 2 if hct > 53 else 1
        else:
            if hct < 36: return 0
            return 2 if hct > 46 else 1
    if "LBXHCT" in df.columns:
        f["f_hct"] = df.apply(_hct, axis=1).astype(float)
    else:
        f["f_hct"] = np.nan

    # f_wbc  0=Low(<4.5) 1=Normal(4.5-11.0) 2=High(>11.0)  1000 cells/µL
    if "LBXWBCSI" in df.columns:
        f["f_wbc"] = pd.cut(
            df["LBXWBCSI"], bins=[-np.inf, 4.5, 11.0, np.inf],
            labels=[0, 1, 2]
        ).astype(float)
    else:
        f["f_wbc"] = np.nan

    # f_sodium  0=Low(<136) 1=Normal(136-145) 2=High(>145)  mmol/L
    if "LBXSNASI" in df.columns:
        f["f_sodium"] = pd.cut(
            df["LBXSNASI"], bins=[-np.inf, 136, 145, np.inf],
            labels=[0, 1, 2]
        ).astype(float)
    else:
        f["f_sodium"] = np.nan

    # f_potassium  0=Low(<3.5) 1=Normal(3.5-5.0) 2=High(>5.0)  mmol/L
    if "LBXSKSI" in df.columns:
        f["f_potassium"] = pd.cut(
            df["LBXSKSI"], bins=[-np.inf, 3.5, 5.0, np.inf],
            labels=[0, 1, 2]
        ).astype(float)
    else:
        f["f_potassium"] = np.nan

    # f_calcium  0=Low(<8.5) 1=Normal(8.5-10.5) 2=High(>10.5)  mg/dL
    if "LBXSCASI" in df.columns:
        f["f_calcium"] = pd.cut(
            df["LBXSCASI"], bins=[-np.inf, 8.5, 10.5, np.inf],
            labels=[0, 1, 2]
        ).astype(float)
    else:
        f["f_calcium"] = np.nan

    # f_income  0=Low(<$35k) 1=Middle($35k-$75k) 2=High(>=$75k)
    # INDHHIN2 / INDHHINC categories: 1-6=Low, 7-10=Middle, 11-12=High
    def _income(val):
        if pd.isna(val) or val in [13, 14, 15]:  # aggregated/ambiguous categories
            return np.nan
        if val <= 6:
            return 0
        if val <= 10:
            return 1
        return 2
    if "INCOME_CAT" in df.columns:
        f["f_income"] = df["INCOME_CAT"].apply(_income).astype(float)
    else:
        f["f_income"] = np.nan

    # f_insurance  0=Uninsured 1=Insured  (HIQ011: 1=Yes, 2=No)
    if "HIQ011" in df.columns:
        f["f_insurance"] = df["HIQ011"].map({1: 1, 2: 0}).astype(float)
    else:
        f["f_insurance"] = np.nan

    # f_employment  0=Not in workforce 1=Unemployed 2=Employed
    # OCQ150: 1=Working, 2=Has job but not at work, 3=Looking for work, 4=Not working
    def _emp(val):
        if pd.isna(val):
            return np.nan
        if val in [1, 2]:
            return 2
        if val == 3:
            return 1
        return 0
    if "OCQ150" in df.columns:
        f["f_employment"] = df["OCQ150"].apply(_emp).astype(float)
    else:
        f["f_employment"] = np.nan

    return f


# ------------------------------------------------------------------ #
# Disease label inference (clinical thresholds, not self-reported)   #
# ------------------------------------------------------------------ #

def _infer_labels(df: pd.DataFrame) -> pd.DataFrame:
    L = pd.DataFrame(index=df.index)

    is_male = (df["RIAGENDR"] == 1)

    # --- Gout: hyperuricemia (gender-specific serum uric acid threshold) ---
    ua_hi = np.where(is_male, 7.0, 6.0)
    L["label_gout"] = np.where(
        df["LBXSUA"].isna(), np.nan,
        (df["LBXSUA"].values >= ua_hi).astype(float)
    )

    # --- Diabetes: fasting glucose ≥126 OR HbA1c ≥6.5% ---
    both_missing = df["LBXGLU"].isna() & df["LBXGH"].isna()
    L["label_diabetes"] = np.where(
        both_missing, np.nan,
        ((df["LBXGLU"].fillna(0) >= 126) | (df["LBXGH"].fillna(0) >= 6.5)).astype(float)
    )

    # --- CKD: eGFR < 60 ---
    L["label_ckd"] = np.where(
        df["egfr"].isna(), np.nan,
        (df["egfr"] < 60).astype(float)
    )

    # --- Hypertension: SBP ≥130 OR DBP ≥80  (ACC/AHA 2017) ---
    bp_missing = df["BPXSY1"].isna() & df["BPXDI1"].isna()
    L["label_hypertension"] = np.where(
        bp_missing, np.nan,
        ((df["BPXSY1"].fillna(0) >= 130) | (df["BPXDI1"].fillna(0) >= 80)).astype(float)
    )

    # --- CVD risk: ≥3 of 7 major risk factors ---
    hdl_low = np.where(is_male, df["LBDHDD"] < 40, df["LBDHDD"] < 50)
    cvd_score = (
        (df["LBDLDL"].fillna(0) >= 160).astype(int)     # High LDL
        + hdl_low.astype(int)                            # Low HDL
        + (df["SMQ040"].isin([1, 2])).astype(int)        # Current smoker
        + (df["RIDAGEYR"] >= 55).astype(int)             # Age ≥55
        + (df["LBXGLU"].fillna(0) >= 126).astype(int)   # Diabetes
        + (df["LBXHSCRP"].fillna(0) > 3).astype(int)    # High CRP
        + (df["LBXTR"].fillna(0) >= 200).astype(int)    # High triglycerides
    )
    L["label_cvd"] = (cvd_score >= 3).astype(float)

    # --- Metabolic syndrome: ≥3 of 5 ATP III criteria ---
    waist_hi = np.where(is_male, df["BMXWAIST"] > 102, df["BMXWAIST"] > 88)
    ms_score = (
        waist_hi.astype(int)                              # Central obesity
        + (df["LBXTR"].fillna(0) >= 150).astype(int)     # High triglycerides
        + hdl_low.astype(int)                             # Low HDL
        + (df["BPXSY1"].fillna(0) >= 130).astype(int)    # High BP
        + (df["LBXGLU"].fillna(0) >= 100).astype(int)    # Elevated glucose
    )
    L["label_metabolic_syndrome"] = (ms_score >= 3).astype(float)

    return L


# ------------------------------------------------------------------ #
# Main build function                                                  #
# ------------------------------------------------------------------ #

FEATURE_COLS = [
    "f_age", "f_gender", "f_ethnicity", "f_ses",
    "f_smoking", "f_alcohol", "f_activity",
    "f_bmi", "f_glucose", "f_hba1c",
    "f_hdl", "f_ldl", "f_triglycerides", "f_crp",
    "f_egfr", "f_creatinine", "f_bun", "f_uric_acid",
    "f_alt", "f_ggt", "f_ast",
    "f_albumin", "f_insulin",
    "f_hemoglobin", "f_hct", "f_wbc",
    "f_sodium", "f_potassium", "f_calcium",
    "f_income", "f_insurance", "f_employment",
]

LABEL_COLS = [
    "label_gout", "label_diabetes", "label_ckd",
    "label_hypertension", "label_cvd", "label_metabolic_syndrome",
]


def _merge_cycle(dfs: dict) -> pd.DataFrame | None:
    """Merge all files for one cycle into a single flat DataFrame."""
    if "demo" not in dfs:
        return None

    demo = dfs["demo"]

    # RIDRETH3 (6-category) was introduced in 2007-2008.
    # Earlier cycles use RIDRETH1 (5-category) — remap it to RIDRETH3 column name
    # so downstream code is uniform. Categories 1-4 map directly; 5 → 7 (Other).
    if "RIDRETH3" not in demo.columns and "RIDRETH1" in demo.columns:
        demo = demo.copy()
        demo["RIDRETH3"] = demo["RIDRETH1"]

    # Income column changed names between cycles
    # INDHHIN2 = 2007+,  INDHHINC = 1999-2006
    if "INDHHIN2" in demo.columns:
        demo = demo.copy()
        demo["INCOME_CAT"] = demo["INDHHIN2"]
    elif "INDHHINC" in demo.columns:
        demo = demo.copy()
        demo["INCOME_CAT"] = demo["INDHHINC"]
    else:
        demo = demo.copy()
        demo["INCOME_CAT"] = np.nan

    df = demo[["SEQN", "RIDAGEYR", "RIAGENDR", "RIDRETH3", "INDFMPIR", "INCOME_CAT"]].copy()

    merges = [
        ("bmx",    ["SEQN", "BMXBMI", "BMXWAIST"]),
        ("bpx",    ["SEQN", "BPXSY1", "BPXDI1"]),
        ("tchol",  ["SEQN", "LBXTC"]),
        ("trigly", ["SEQN", "LBXTR", "LBDLDL"]),
        ("hdl",    ["SEQN", "LBDHDD"]),
        ("glu",    ["SEQN", "LBXGLU"]),
        ("ghb",    ["SEQN", "LBXGH"]),
        ("biopro", ["SEQN", "LBXSCR", "LBXSUA", "LBXSBU", "LBXSATSI", "LBXSGTSI",
                    "LBXSASSI",   # AST
                    "LBXSAL",     # Albumin
                    "LBXSNASI",   # Serum sodium
                    "LBXSKSI",    # Serum potassium
                    "LBXSCASI",   # Serum calcium
                    ]),
        ("hscrp",  ["SEQN", "LBXHSCRP"]),
        ("smq",    ["SEQN", "SMQ020", "SMQ040"]),
        ("paq",    ["SEQN", "PAQ605", "PAQ620", "PAD615", "PAD630"]),
        ("alq",    ["SEQN", "ALQ130"]),
        ("hiq",    ["SEQN", "HIQ011"]),
        ("ocq",    ["SEQN", "OCQ150"]),
        ("cbc",    ["SEQN", "LBXHGB", "LBXHCT", "LBXWBCSI"]),
        ("ins",    ["SEQN", "LBXIN"]),
    ]
    for key, cols in merges:
        if key not in dfs:
            continue
        avail = [c for c in cols if c in dfs[key].columns]
        df = df.merge(dfs[key][avail], on="SEQN", how="left")

    return df


def build():
    print(f"=== Building NHANES dataset ({len(CYCLES)} cycles) ===")

    # --- Download and merge each cycle independently, then stack ---
    cycle_frames = []
    for cycle in CYCLES:
        dfs      = _load_cycle(cycle)
        cycle_df = _merge_cycle(dfs)
        if cycle_df is not None:
            cycle_frames.append(cycle_df)
            print(f"  {cycle['label']} merged: {cycle_df.shape}")

    if not cycle_frames:
        raise RuntimeError("No cycle data could be loaded.")

    df = pd.concat(cycle_frames, ignore_index=True)
    print(f"\nCombined shape: {df.shape}  ({len(cycle_frames)} cycles)")

    # --- Numeric coercion ---
    num_cols = [
        "RIDAGEYR", "RIAGENDR", "RIDRETH3", "INDFMPIR", "INCOME_CAT",
        "BMXBMI", "BMXWAIST", "BPXSY1", "BPXDI1",
        "LBXTC", "LBXTR", "LBDLDL", "LBDHDD",
        "LBXGLU", "LBXGH", "LBXSCR", "LBXSUA", "LBXSBU",
        "LBXSATSI", "LBXSGTSI", "LBXHSCRP",
        "SMQ020", "SMQ040", "PAD615", "PAD630", "ALQ130",
        "HIQ011", "OCQ150",
        "LBXSASSI", "LBXSAL", "LBXSNASI", "LBXSKSI", "LBXSCASI",
        "LBXHGB", "LBXHCT", "LBXWBCSI", "LBXIN",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Replace NHANES refusal/don't-know sentinels with NaN
    for col in ["SMQ020", "SMQ040", "ALQ130", "INCOME_CAT", "HIQ011", "OCQ150"]:
        if col in df.columns:
            df.loc[df[col].isin([7, 9, 77, 99, 777, 999]), col] = np.nan

    # --- Derived variables ---
    df["egfr"]     = df.apply(_ckd_epi_egfr, axis=1)
    df["pa_score"] = df.apply(_pa_score, axis=1)

    # --- Bin features & infer labels ---
    features = _bin_features(df)
    labels   = _infer_labels(df)

    # Impute missing features with column median
    for col in FEATURE_COLS:
        median = features[col].median()
        features[col] = features[col].fillna(median)

    # --- Report ---
    print(f"\nFeature matrix: {features.shape}")
    print("Label summary:")
    for lc in LABEL_COLS:
        pos   = int(labels[lc].sum())
        total = int(labels[lc].notna().sum())
        pct   = 100.0 * pos / total if total > 0 else 0
        print(f"  {lc:35s}  {pos:4d} / {total:4d}  ({pct:.1f}%)")

    # --- Save ---
    os.makedirs(DATA_DIR, exist_ok=True)
    features[FEATURE_COLS].to_csv(os.path.join(DATA_DIR, "nhanes_features.csv"), index=False)
    labels[LABEL_COLS].to_csv(os.path.join(DATA_DIR, "nhanes_labels.csv"), index=False)
    print(f"\nSaved to {DATA_DIR}/")


if __name__ == "__main__":
    build()
