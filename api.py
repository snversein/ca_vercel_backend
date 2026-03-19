from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return JSONResponse({"status": "ok", "message": "TaxPilot API Running"})

@app.get("/")
def root():
    return JSONResponse({"message": "TaxPilot API"})
