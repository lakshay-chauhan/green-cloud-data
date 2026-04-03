import os
import re
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Gemini Physics-Based Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants for Physics Derivations
KAPPA = 0.8e-9  # Joules per CPU cycle
MU = 1.2e-9     # Joules per Byte-access
CI_INDIA = 710  # gCO2e/kWh (India Avg)
WUE = 1.8       # Liters/kWh (Water Usage Effectiveness)

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

class CodePayload(BaseModel):
    code: str

@app.post("/analyze")
async def analyze_code(payload: CodePayload):
    prompt = f"Analyze code complexity. Return ONLY JSON with 'T' (cycles n=1000) and 'S' (memory bytes). CODE: {payload.code}"
    try:
        response = model.generate_content(prompt)
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        data = json.loads(match.group())
        
        T = float(data.get("T", 5000))
        S = float(data.get("S", 256))

        # --- DERIVED VALUES (NO HALLUCINATION) ---
        # 1. Energy in Joules
        energy_j = (KAPPA * T) + (MU * S)
        
        # 2. Water in milliliters (ml)
        # Energy J -> kWh (1 J = 2.777e-7 kWh)
        energy_kwh = energy_j / 3600000
        water_ml = (energy_kwh * WUE) * 1000
        
        # 3. Carbon in milligrams (mg)
        carbon_mg = (energy_kwh * CI_INDIA) * 1000000

        # Rating Logic based on Energy Threshold
        rating = "A+ (Efficient)" if energy_j < 0.00005 else "D (Resource Heavy)"

        return {
            "energy_joules": energy_j,
            "water_ml": water_ml,
            "carbon_mg": carbon_mg,
            "rating": rating,
            "metrics": {"cycles": T, "memory": S}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))