from fastapi import FastAPI, HTTPException
import json
from typing import List, Dict

app = FastAPI()

# Path to the JSON data file
DATA_FILE = 'data.json'


def load_data() -> List[Dict]:
    """
    Returns:
        List[Dict]: List of items loaded from the JSON file.
    """
    with open(DATA_FILE, 'r') as file:
        return json.load(file)


def save_data(data: List[Dict]) -> None:
    """
    Args:
        data (List[Dict]): List of items to be saved to the JSON file.
    """
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)


@app.get("/data")
async def get_data() -> List[Dict]:
    """
    Endpoint to retrieve all data.

    Returns:
        List[Dict]: List of all items.
    """
    data = load_data()
    return data


@app.get("/data/{item_id}", response_model=dict)
async def get_item(item_id: int) -> Dict:
    """
    Endpoint to retrieve a single item by its ID.

    Args:
        item_id (int): ID of the item to be retrieved.

    Returns:
        dict: Message and the item if found, or raises HTTPException.
    """
    data = load_data()
    for item in data:
        if item["id"] == item_id:
            return {"message": "Item obtained successfully", "item": item}
    raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/data/{item_id}", response_model=dict)
async def delete_item(item_id: int) -> Dict:
    """
    Endpoint to delete a single item by its ID.

    Args:
        item_id (int): ID of the item to be deleted.

    Returns:
        dict: Message and the deleted item if found, or raises HTTPException.
    """
    data = load_data()
    for index, item in enumerate(data):
        if item["id"] == item_id:
            deleted_item = data.pop(index)
            save_data(data)
            return {"message": "Item deleted successfully",
                    "item": deleted_item}
    raise HTTPException(status_code=404, detail="Item not found")
