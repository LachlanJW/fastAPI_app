from typing import Union
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_main():
    return {"msg": "Hello World"}