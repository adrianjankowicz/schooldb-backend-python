from pymongo import MongoClient
from fastapi import HTTPException
from dotenv import load_dotenv
import os
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()

# MongoDB client setup
MONGO_URL = os.environ.get("MONGO_URL")
GOOGLE_API = os.environ.get("GOOGLE_API")

client = MongoClient(MONGO_URL)
db = client.test

def verify_google_token(token):
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_API)
        return idinfo
    except ValueError:
        return None

def get_database():
    return db

def get_collection(collection_name: str):
    try:
        return db[collection_name]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")

