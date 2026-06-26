from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.generation import router as generation_router

app = FastAPI(title="RePlay City API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Branche le router de génération
app.include_router(generation_router)

@app.get("/")
def root():
    return {"message": "RePlay City API opérationnelle "}

@app.get("/health")
def health_check():
    return {"status": "ok"}