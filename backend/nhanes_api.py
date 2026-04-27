from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import pandas as pd
import patient_profile_builder, download_nhanes_file
from ml_model import RiskModelEngine

app = Flask(__name__)
CORS(app)

profile_builder = patient_profile_builder.PatientProfileBuilder(download_nhanes_file)
risk_model = RiskModelEngine()

# 1. Provide the dropdown options the UI expects
@app.route('/api/filters', methods=['GET'])
def get_filters():
    filters = {
        # Demographics & Socioeconomic
        "ageGroup":          ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
        "gender":            ["Male", "Female"],
        "ethnicity":         ["Mexican American", "Other Hispanic", "Non-Hispanic White", "Non-Hispanic Black", "Other"],
        "socioeconomicStatus": ["Low", "Middle", "High"],
        "income":            ["Low (<$35k)", "Middle ($35k-$75k)", "High (>=$75k)"],
        "insuranceStatus":   ["Insured", "Uninsured"],
        "employmentStatus":  ["Employed", "Unemployed", "Not in workforce"],
        # Lifestyle
        "smokingStatus":   ["Never", "Former", "Current"],
        "alcoholUse":      ["None", "Moderate", "Heavy"],
        "physicalActivity": ["Low", "Moderate", "High"],
        "diet":            ["Standard", "Vegetarian", "Vegan"],
        # Metabolic & Cardiovascular
        "bmi":          ["Underweight (<18.5)", "Normal (18.5-24.9)", "Overweight (25-29.9)", "Obese (>=30)"],
        "bloodGlucose": ["Normal (<100)", "Prediabetes (100-125)", "Diabetes (>=126)"],
        "hba1c":        ["Normal (<5.7%)", "Prediabetes (5.7-6.4%)", "Diabetes (>=6.5%)"],
        "HDL":          ["Low (<40)", "Normal (40-59)", "High (>=60)"],
        "LDL":          ["Optimal (<110)", "Borderline (110-159)", "High (>160)"],
        "triglycerides": ["Normal (<150)", "Borderline (150-199)", "High (>=200)"],
        "crp":          ["Low Risk (<1)", "Average (1-3)", "High Risk (>3)"],
        # Renal & Kidney Function
        "egfr":       [">90 (Normal)", "60-89 (Mild)", "<60 (Reduced)"],
        "creatinine": ["Normal", "High"],
        "BUN":        ["Normal (7-20)", "High (>20)"],
        "uricAcid":   ["Low (<3.5)", "Normal (3.5-7.2)", "High (>7.2)"],
        # Liver
        "alt": ["Normal", "Elevated"],
        "ast": ["Normal", "Elevated"],
        "ggt": ["Normal", "High"],
        # Blood & metabolic
        "albumin":    ["Low (<3.5)", "Normal (3.5-5.0)"],
        "insulin":    ["Normal (<25)", "Elevated (25-50)", "High (>50)"],
        "hemoglobin": ["Low", "Normal", "High"],
        "hct":        ["Low", "Normal", "High"],
        "wbc":        ["Low (<4.5)", "Normal (4.5-11.0)", "High (>11.0)"],
        # Electrolytes
        "sodium":     ["Low (<136)", "Normal (136-145)", "High (>145)"],
        "potassium":  ["Low (<3.5)", "Normal (3.5-5.0)", "High (>5.0)"],
        "calcium":    ["Low (<8.5)", "Normal (8.5-10.5)", "High (>10.5)"],
    }
    return jsonify(filters)

# 2. Run the ML model and return risk scores for all diseases
@app.route('/api/risk', methods=['GET'])
def get_risk():
    filters = request.args.to_dict()
    disease_risks = risk_model.predict(filters)

    from datetime import datetime, timezone
    return jsonify({
        "filters": filters,
        "diseaseRisks": disease_risks,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })

# 3. Keep your existing profile generation logic
@app.route('/profile', methods=['POST'])
def profile():
    data = request.get_json()
    selections = data.get("selections")
    cycles = data.get("cycles")
    
    if not selections or not cycles:
        return jsonify({'error': 'Please provide both "selections" and "cycles".'}), 400
    
    try:
        profile_df = profile_builder.build_profile(selections, cycles)
        temp_csv = os.path.abspath("patient_profile_temp.csv")
        profile_df.to_csv(temp_csv, index=False)
        return send_file(temp_csv, as_attachment=True, download_name="patient_profile.csv")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run on port 8000 to match the README requirements
    app.run(host='0.0.0.0', port=8000, debug=True)