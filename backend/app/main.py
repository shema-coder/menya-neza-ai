from fastapi import FastAPI

app = FastAPI(
    title="MENYA NEZA AI",
    description="From Data to Early Action",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "project": "MENYA NEZA AI",
        "tagline": "From Data to Early Action",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "menya-neza-ai-backend",
    }
