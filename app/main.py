from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
import json
import os
from dotenv import load_dotenv

# =============================================================================
#                                 Basic Setup
# =============================================================================

# Load environment variables
load_dotenv()

# Constants for JWT encoding and decoding
SECRET_KEY = os.getenv("SECRET_KEY")  # MUST BE IN CORRECT FORM
ALGORITHM = "HS256"
TOKEN_EXP = 30  # Expiration time in minutes

app = FastAPI()

# Path to the JSON data file
DATA_FILE = 'data.json'

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dummy user data for testing
fake_users_db = {
    "Me": {
        "username": "Me",
        "full_name": "Mr Me",
        "email": "me@email.com",
        "hashed_password": pwd_context.hash("password"),  # Hashed with bcrypt
        "disabled": False,
    }
}

# OAuth2 password instance for endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# =============================================================================
#                          Authentication Functions
# =============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against hashed password.
    True if password matches, otherwise False.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_user(db: Dict[str, Any], username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user from fake database.
    Returns user data if found, None otherwise.
    """
    return db.get(username)


def authenticate_user(fake_db: Dict[str, Any],
                      username: str, pswd: str) -> Optional[Dict[str, Any]]:
    """
    Args:
        fake_db (Dict[str, Any]): Database of users.
        username (str): Username of the user to authenticate.
        password (str): Plain text password of the user.

    Returns:
        Optional[Dict[str, Any]]: Authenticated user data or None.
    """
    user = get_user(fake_db, username)
    if not user or not verify_password(pswd, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict,
                        expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token.

    Args:
        data (dict): The data to encode.
        expires_delta (Optional[timedelta]): Expiration time delta.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta
                                           else timedelta(minutes=TOKEN_EXP))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# =============================================================================
#                               API Functions
# =============================================================================

def load_data() -> List[Dict[str, Any]]:
    """
    Returns:
        List[Dict[str, Any]]: List of items loaded from the JSON.
    """
    with open(DATA_FILE, 'r') as file:
        return json.load(file)


def save_data(data: List[Dict[str, Any]]) -> None:
    """
    Args:
        data (List[Dict[str, Any]]): List of items to be saved to the JSON.
    """
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get the current authenticated user based on the JWT token.

    Args:
        token (str): JWT token.

    Returns:
        Dict[str, Any]: User information if the token is valid.

    Raises:
        HTTPException: If the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token", response_model=Dict[str, str])
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, str]:
    """
    Endpoint to authenticate a user and return a JWT token.

    Args:
        form_data (OAuth2PasswordRequestForm): Containing username, password.

    Returns:
        Dict[str, str]: Access token and token type.
    """
    user = authenticate_user(fake_users_db,
                             form_data.username,
                             form_data.password)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=TOKEN_EXP)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/data", response_model=List[Dict[str, Any]])
async def get_data(current_user: Dict[str, Any] = Depends(get_current_user)
                   ) -> List[Dict[str, Any]]:
    """
    Endpoint to retrieve all data.

    Args:
        current_user (Dict[str, Any]): Current authenticated user.

    Returns:
        List[Dict[str, Any]]: List of all items.
    """
    return load_data()


@app.get("/data/{item_id}", response_model=Dict[str, Any])
async def get_item(item_id: int,
                   current_user: Dict[str, Any] = Depends(get_current_user)
                   ) -> Dict[str, Any]:
    """
    Endpoint to retrieve a single item by its ID.

    Args:
        item_id (int): ID of the item to be retrieved.
        current_user (Dict[str, Any]): Current authenticated user.

    Returns:
        Dict[str, Any]: Message and the item if found, or raises HTTPException.
    """
    data = load_data()
    for item in data:
        if item["id"] == item_id:
            return {"message": "Item obtained successfully", "item": item}
    raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/data/{item_id}", response_model=Dict[str, Any])
async def delete_item(item_id: int,
                      current_user: Dict[str, Any] = Depends(get_current_user)
                      ) -> Dict[str, Any]:
    """
    Endpoint to delete a single item by its ID.

    Args:
        item_id (int): ID of the item to be deleted.
        current_user (Dict[str, Any]): Current authenticated user.

    Returns:
        Dict[str, Any]: Message and deleted item if found, or HTTPException.
    """
    data = load_data()
    for index, item in enumerate(data):
        if item["id"] == item_id:
            deleted_item = data.pop(index)
            save_data(data)
            return {"message": "Item deleted", "item": deleted_item}
    raise HTTPException(status_code=404, detail="Item not found")
