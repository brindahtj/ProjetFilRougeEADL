from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Smart City API",
    description="API d'ingestion de données IoT",
    version="1.0.0"
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pollution")
def create_pollution(city: str, value: float):
    return {"city": city, "value": value}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)