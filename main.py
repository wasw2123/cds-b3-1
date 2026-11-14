from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/")
def health_check1():
    return {"status": "OK"}


@app.get("/health")
def health_check2():
    return {"status": "OK"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)