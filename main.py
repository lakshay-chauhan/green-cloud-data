import json
import re
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="EcoCode - Hardcoded Sustainability Analyzer")

# --- HARDCODED CONFIGURATION ---
# Paste your actual Gemini API key between the quotes below
HARDCODED_API_KEY = "AIzaSyAj_klWhDXv8x5uYpw4PEDCtuogVuPBYqk"
MODEL_NAME = "gemini-2.5-flash"

# Physics & Environmental Constants (2026 Standards)
CONSTANTS = {
    "WUE": 1.8,        # Liters per kWh (Water Usage Effectiveness)
    "CI": 710,         # gCO2e/kWh (Average Carbon Intensity for India)
    "P_BYTE": 8e-10,   # Watts per byte (RAM Idle/Refresh power)
    "KAPPA": 0.8e-9,   # Joules per CPU cycle
    "MU": 1.2e-9,      # Joules per Memory operation
}

# Initialize the Gemini Model immediately
try:
    genai.configure(api_key=HARDCODED_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    print(f"Failed to initialize Gemini: {e}")

class CodePayload(BaseModel):
    code: str

@app.get("/")
def home():
    return {"message": "Hardcoded Analyzer is Active", "docs": "/docs"}

@app.post("/analyze")
async def analyze_code(payload: CodePayload):
    # The Prompt: Instructing the LLM to extract the parameters for our equations
    prompt = f"""
    Analyze the following code for complexity.
    1. Estimate CPU Cycles (T) for an input size n=1000.
    2. Estimate Memory usage in Bytes (S).
    
    EXPECTED OUTPUT FORMAT (Strict JSON):
    {{"T": 5000, "S": 256}}

    CODE TO ANALYZE:
    {payload.code}
    
    Return ONLY the raw JSON object. No explanation or markdown backticks.
    """
    
    try:
        # Step 1: Call the LLM
        response = model.generate_content(prompt)
        
        # Step 2: Clean the response (Extracting only the {} part)
        json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if not json_match:
            raise ValueError("The AI did not return a valid JSON format.")
            
        data = json.loads(json_match.group())
        
        # Step 3: Ensure parameters are numbers (float)
        T = float(data.get("T", 0))
        S = float(data.get("S", 0))

        # --- APPLYING THE RESEARCH EQUATIONS ---
        
        # Equation 1: Energy Consumption (Joules)
        # E ≈ κ * T(n) + μ * S(n)
        energy_j = (CONSTANTS["KAPPA"] * T) + (CONSTANTS["MU"] * S)
        
        # Equation 2: Carbon Emissions from Memory (mg)
        # Carbon = (Total Bytes * Power per Byte) * Carbon Intensity
        carbon_mg = ((S * CONSTANTS["P_BYTE"]) * CONSTANTS["CI"]) * 1000
        
        # Equation 3: Water Consumption (ml)
        # Water = Energy_kWh * WUE
        energy_kwh = energy_j / 3600000
        water_ml = energy_kwh * CONSTANTS["WUE"] * 1000

        # --- SUSTAINABILITY RATING ---
        # Weighted score (scaled for small code snippets)
        score = (energy_j * 1000) + carbon_mg + (water_ml * 100)
        
        if score < 10:
            grade = "A+ (Planet Friendly)"
        elif score < 100:
            grade = "B (Efficient)"
        else:
            grade = "D (Resource Heavy)"

        return {
            "status": "success",
            "extracted_parameters": {
                "cpu_cycles_t": T,
                "memory_bytes_s": S
            },
            "environmental_impact": {
                "energy_joules": round(energy_j, 10),
                "carbon_mg": round(carbon_mg, 6),
                "water_ml": round(water_ml, 10)
            },
            "rating": grade
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # This runs the server on http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)