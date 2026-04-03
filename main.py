from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from simulation import simulate
app = FastAPI(title="Green Cloud Simulation Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run-simulation")
def run_sim(payload: dict):
    # Receives the 'code_impact' data from React
    return simulate(payload)