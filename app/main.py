from fastapi import FastAPI

app = FastAPI(title="RePlay City API")

@app.get("/")
def root():
    return {"message": "RePlay City API opérationnelle"}