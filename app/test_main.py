import pytest
from fastapi.testclient import TestClient
import shutil
from .main import app, DATA_FILE
from typing import Dict

client = TestClient(app)

# Path to the backup file
DATA_FILE_BACKUP = 'data_backup.json'


@pytest.fixture(scope="module")
def backup_data_file():
    """
    Fixture to create a backup of the data file before any tests are run
    and restore the original data file after all tests have completed.
    """
    shutil.copyfile(DATA_FILE, DATA_FILE_BACKUP)
    yield
    shutil.copyfile(DATA_FILE_BACKUP, DATA_FILE)


@pytest.fixture
def reset_items():
    """
    Fixture to restore the original data before each test.
    """
    shutil.copyfile(DATA_FILE_BACKUP, DATA_FILE)


@pytest.fixture
def auth_token():
    response = client.post("/token", data={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 200, f"Failed to get token: {response.json()}"
    return response.json()["access_token"]


@pytest.fixture(scope="module", autouse=True)
def create_test_user():
    # Try to log in first
    login_response = client.post("/token", data={"username": "testuser", "password": "testpassword"})
    
    if login_response.status_code == 200:
        # User already exists, no need to create
        return

    # If login failed, try to create user
    response = client.post("/create_user", params={
        "username": "testuser",
        "password": "testpassword",
        "full_name": "Test User",
        "email": "testuser@example.com"
    })
    assert response.status_code == 200, f"Failed to create test user: {response.json()}"


def headers(auth_token: str) -> Dict[str, str]:
    """Give the headers dict given an auth token."""
    return {"Authorization": f"Bearer {auth_token}"}


def test_get_data(backup_data_file, reset_items, auth_token):
    """
    Test that the /data endpoint returns the data.
    """
    response = client.get("/data", headers=headers(auth_token))
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert isinstance(data, list)

    # Additional check: Ensure expected structure of the first item
    if data:
        item = data[0]
        assert "id" in item
        assert "price" in item
        assert "address" in item
        assert "features" in item
        assert "date" in item


def test_get_item(backup_data_file, reset_items, auth_token):
    """
    Test that the /data/{item_id} endpoint returns the correct item.
    """
    response = client.get("/data/2018724576", headers=headers(auth_token))
    assert response.status_code == 200
    item = response.json()["item"]
    assert item["id"] == 2018724576
    assert item["price"] == "$922,500"
    assert item["address"]["street"] == "54 Turbayne Crescent"

    # Additional checks for the full content
    assert item["features"]["beds"] == 3
    assert item["features"]["baths"] == 2
    assert item["features"]["parking"] == 2
    assert item["features"]["propertyType"] == "House"


def test_get_invalid_item_id(backup_data_file, reset_items, auth_token):
    """
    Test that attempting to retrieve item with an invalid ID returns 404 error.
    """
    response = client.get("/data/9999999999", headers=headers(auth_token))
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_delete_item(backup_data_file, reset_items, auth_token):
    """
    Test that the DELETE request removes the item correctly.
    """
    # Check length of data before
    original_response = client.get("/data", headers=headers(auth_token))
    original_length = len(original_response.json())

    # Complete the DELETE request
    delete_response = client.delete("/data/2018724576", headers=headers(auth_token))
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Item deleted"

    # Check length of data after request
    new_response = client.get("/data", headers=headers(auth_token))
    new_length = len(new_response.json())
    assert new_length == original_length - 1

    # Verify the deleted item no longer exists
    response = client.get("/data/2018724576", headers=headers(auth_token))
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_delete_non_existent_item(backup_data_file, reset_items, auth_token):
    """
    Test that attempting to delete a non-existent item returns a 404 error.
    """
    delete_response = client.delete("/data/9999999999", headers=headers(auth_token))
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Item not found"
