from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from typing import List
from utils.db import get_database, get_collection

class Notice(BaseModel):
    title: str
    details: str
    date: datetime
    adminID: str 

class NoticeList(BaseModel):
    title: str
    details: str
    date: datetime
    adminID: str
    school: str
    id: str = Field(..., alias='_id')


router = APIRouter()


@router.post("/NoticeCreate")
async def create_notice(notice_data: Notice, db: MongoClient = Depends(get_database)):
    notice_collection = db.get_collection("notices")
    notice_data = notice_data.dict()
    notice_data["school"] = ObjectId(notice_data["adminID"]) 
    result = notice_collection.insert_one(notice_data)
    return {"_id": str(result.inserted_id)}

@router.get("/NoticeList/{school_id}", response_model=List[NoticeList])
async def list_notices(school_id: str, db: MongoClient = Depends(get_database)):
    notice_collection = db.get_collection("notices")
    notices = list(notice_collection.find({"school": ObjectId(school_id)}))
    
    return [
        {
            "title": notice["title"],
            "details": notice["details"],
            "date": notice["date"],
            "adminID": school_id,
            "school": school_id,
            "_id": str(notice["_id"])
        } 
        for notice in notices
    ]

@router.put("/Notice/{notice_id}")
async def update_notice(notice_id: str, notice_data: Notice, db: MongoClient = Depends(get_database)):
    notice_collection = db.get_collection("notices")
    updated_data = {"$set": notice_data.dict()}
    result = notice_collection.update_one({"_id": ObjectId(notice_id)}, updated_data)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notice not found")
    return {"message": "Notice updated successfully"}

@router.delete("/Notice/{notice_id}")
async def delete_notice(notice_id: str, db: MongoClient = Depends(get_database)):
    notice_collection = db.get_collection("notices")
    result = notice_collection.delete_one({"_id": ObjectId(notice_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notice not found")
    return {"message": "Notice deleted successfully"}

@router.delete("/Notices/{school_id}")
async def delete_notices(school_id: str, db: MongoClient = Depends(get_database)):
    notice_collection = db.get_collection("notices")
    result = notice_collection.delete_many({"school": ObjectId(school_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No notices found to delete")
    return {"deleted_count": result.deleted_count}