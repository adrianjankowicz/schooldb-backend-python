from fastapi import APIRouter, HTTPException, Depends
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from typing import List
from utils.db import get_collection, get_database
from pydantic import BaseModel

router = APIRouter()

class ComplainModel(BaseModel):
    user: str  
    date: datetime
    complaint: str
    school: str 


@router.post("/ComplainCreate")
async def create_complain(complain_data: ComplainModel, db: MongoClient = Depends(get_database)):
    complain_collection = db.get_collection("complains")
    complain_data = complain_data.dict()
    complain_data["user"] = ObjectId(complain_data["user"])
    complain_data["school"] = ObjectId(complain_data["school"])
    result = complain_collection.insert_one(complain_data)
    return {"_id": str(result.inserted_id)}

@router.get("/ComplainList/{school_id}", response_model=List[ComplainModel])
async def list_complains(school_id: str, db: MongoClient = Depends(get_database)):
    complain_collection = db.get_collection("complains")
    students_collection = db.get_collection("students")
    complains = list(complain_collection.find({"school": ObjectId(school_id)}))
    for complain in complains:
        student = students_collection.find_one({"_id": complain["user"]})
        complain["user"] = student["name"] if student else "Unknown"
        complain["_id"] = str(complain["_id"])
        complain["user"] = str(complain["user"])
        complain["school"] = str(complain["school"])
    return complains