import os
import re
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Gemini Code Footprint Analyzer")

# ✅ CORS FIX for Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

class CodePayload(BaseModel):
    code: str

@app.post("/analyze")
async def analyze_code(payload: CodePayload):
    prompt = f"""
    Analyze the code for complexity. Return ONLY JSON with:
    "T": CPU cycles for n=1000, 
    "S": Memory bytes.
    CODE: {payload.code}
    """
    try:
        response = model.generate_content(prompt)
        match = re.search(r"\{.*\}", response.text, re.DOTALL)
        if not match:
            raise ValueError("Invalid AI response")
            
        data = json.loads(match.group())
        T, S = float(data.get("T", 5000)), float(data.get("S", 256))
        
        # Environmental physics
        energy_j = (0.8e-9 * T) + (1.2e-9 * S)
        water_ml = (energy_j / 3600000) * 1.8 * 1000
        
        return {
            "energy_joules": energy_j,
            "water_ml": water_ml,
            "rating": "A+ (Efficient)" if energy_j < 0.001 else "D (Resource Heavy)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))