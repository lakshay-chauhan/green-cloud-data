import os
import re
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# ✅ FIX: CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Physics Constants
KAPPA = 0.8e-9  # Joules/cycle
MU = 1.2e-9     # Joules/byte
CI_INDIA = 710  # mgCO2/kWh
WUE = 1.8       # ml/Wh (Water Usage Effectiveness)

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

class CodePayload(BaseModel):
    code: str

@app.post("/analyze")
async def analyze_code(payload: CodePayload):
    prompt = f"Analyze code complexity. Return ONLY JSON with 'T' (cycles n=1000) and 'S' (memory bytes). CODE: {payload.code}"
    try:
        response = model.generate_content(prompt)
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if not match: raise ValueError("No JSON found")
        
        data = json.loads(match.group())
        T, S = float(data.get("T", 5000)), float(data.get("S", 256))

        # --- Physical Derivations ---
        energy_j = (KAPPA * T) + (MU * S)
        # 1 Joule = 0.000277778 Watt-hours
        energy_wh = energy_j * 0.000277778
        
        water_ml = energy_wh * WUE
        carbon_mg = (energy_wh / 1000) * CI_INDIA

        return {
            "energy_joules": energy_j,
            "water_ml": water_ml,
            "carbon_mg": carbon_mg,
            "rating": "A+ (Efficient)" if energy_j < 0.00005 else "D (Resource Heavy)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))