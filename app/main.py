from typing import Union
from fastapi import FastAPI
import json

app = FastAPI()


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}


@app.get("/data")
async def read_data():
    with open('data.json') as file:
        data = json.load(file)
    return data
