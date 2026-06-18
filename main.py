import os
import re
import json
import google.generativeai as genai

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Physics Constants
KAPPA = 0.8e-9      # Joules per cycle
MU = 1.2e-9         # Joules per byte
CI_INDIA = 710      # mgCO2 / kWh
WUE = 1.8           # ml / Wh

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

# MODEL
model = genai.GenerativeModel("gemini-2.5-flash")


class CodePayload(BaseModel):
    code: str


def safe_float(value, default):
    try:
        if isinstance(value, (int, float)):
            return float(value)

        match = re.search(
            r"\d+(\.\d+)?",
            str(value)
        )

        if match:
            return float(match.group())

        return default

    except Exception:
        return default


@app.get("/")
def health_check():
    return {
        "status": "online",
        "model": "gemma-3-4b-it"
    }


@app.post("/analyze")
async def analyze_code(payload: CodePayload):
    prompt = f"""
You are an expert static code complexity analyzer.

Estimate the computational complexity score for Python code.

Use n = 1000.

VERY IMPORTANT RULES:
1. Code with sorted() = around 10000 cycles
2. Single loop = around 10000 cycles
3. Nested double loop = around 1000000 cycles
4. Triple nested loop = around 10000000 cycles
5. More loops means exponentially higher cycles
6. NEVER assign similar values to single and nested loops
7. Nested loops must be at least 50x higher than sorted()

Return ONLY valid JSON:
{{
    "T": integer,
    "S": integer
}}

CODE:
{payload.code}
"""

    try:
        response = model.generate_content(prompt)

        print("RAW MODEL RESPONSE:", response.text)

        match = re.search(
            r"\{[\s\S]*\}",
            response.text
        )

        if not match:
            raise ValueError(
                f"No JSON found: {response.text}"
            )

        data = json.loads(match.group())

        T = safe_float(data.get("T"), 5000)
        S = safe_float(data.get("S"), 256)

        # Safety clamps
        T = max(T, 100)
        S = max(S, 64)

        # Physics calculations
        energy_j = (KAPPA * T) + (MU * S)

        energy_wh = energy_j * 0.000277778

        water_ml = energy_wh * WUE
        carbon_mg = (energy_wh / 1000) * CI_INDIA

        # Better rating logic using T
        if T < 10000:
            rating = "A+ (Efficient)"
        elif T < 100000:
            rating = "B (Moderate)"
        else:
            rating = "D (Resource Heavy)"

        return {
            "energy_joules": round(energy_j, 8),
            "water_ml": round(water_ml, 8),
            "carbon_mg": round(carbon_mg, 8),
            "rating": rating,
            "raw_T": int(T),
            "raw_S": int(S)
        }

    except Exception as e:
        error_msg = str(e)

        if "RESOURCE_EXHAUSTED" in error_msg:
            raise HTTPException(
                status_code=429,
                detail="Quota exhausted"
            )

        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
