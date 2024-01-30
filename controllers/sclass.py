from fastapi import APIRouter, HTTPException, Depends
from pymongo.collection import Collection
from utils.db import get_collection
from bson import ObjectId, errors
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

router = APIRouter()

class School(BaseModel):
    id: str = Field(..., alias='_id')
    schoolName: str

    class Config:
        allow_population_by_name = True

class Sclass(BaseModel):
    id: str = Field(..., alias='_id')
    sclassName: str
    school: School
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]


class SclassList(BaseModel):
    id: str = Field(..., alias='_id')
    sclassName: str
    adminID: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class SclassCreate(BaseModel):
    sclassName: str
    adminID: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

class Student(BaseModel):
    id: str = Field(..., alias='_id')
    name: str
    rollNum: int
    password: Optional[str] = None 
    sclassName: str
    school: str

@router.post("/SclassCreate", response_model=SclassCreate)
async def sclass_create(sclass_data: SclassCreate, sclass_collection: Collection = Depends(lambda: get_collection('sclasses'))):
    if not sclass_data.adminID or not ObjectId.is_valid(sclass_data.adminID):
        raise HTTPException(status_code=400, detail="Invalid school ID")

    school_id = ObjectId(sclass_data.adminID)
    
    existing_sclass = sclass_collection.find_one({"sclassName": sclass_data.sclassName, "school": school_id})
    print(existing_sclass)
    if existing_sclass:
        raise HTTPException(status_code=400, detail='Class with this name already exists in the school')
    print('here')
    new_sclass = {
        "sclassName": sclass_data.sclassName,
        "school": school_id,
        "createdAt": sclass_data.createdAt if sclass_data.createdAt else datetime.now(),
        "updatedAt": sclass_data.updatedAt if sclass_data.updatedAt else datetime.now()  
    }
    result = sclass_collection.insert_one(new_sclass)

    created_sclass = sclass_collection.find_one({"_id": result.inserted_id})


    response_data = {
        '_id': str(created_sclass['_id']),  # Use 'id' to match the alias in SclassList
        'sclassName': created_sclass['sclassName'],
        'school': str(created_sclass['school']),
        'createdAt': created_sclass['createdAt'].isoformat() if created_sclass.get('createdAt') else None,
        'updatedAt': created_sclass['updatedAt'].isoformat() if created_sclass.get('updatedAt') else None
    }

    return SclassList(**response_data)

@router.get("/SclassList/{id}", response_model=list[SclassList])
async def sclass_list(id: str, sclass_collection: Collection = Depends(lambda: get_collection('sclasses'))):
    sclasses = list(sclass_collection.find({"school": ObjectId(id)}))
    sclasses_list = []
    for sclass in sclasses:
        sclass_dict = {
            "_id": str(sclass['_id']),
            "sclassName": sclass['sclassName'],
            "adminID": str(sclass['school']),
            "createdAt": sclass.get('createdAt'),
            "updatedAt": sclass.get('updatedAt')
        }
        sclasses_list.append(SclassList(**sclass_dict))
    # print(sclasses_list)
    return sclasses_list

@router.get("/Sclass/{id}", response_model=Sclass)
async def get_sclass_detail(id: str, 
    sclass_collection: Collection = Depends(lambda: get_collection('sclasses')), 
    admin_collection: Collection = Depends(lambda: get_collection('admins'))):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid or missing ObjectId")
    
    valid_id = ObjectId(id)
    sclass = sclass_collection.find_one({"_id": valid_id})
    
    if not sclass:
        raise HTTPException(status_code=404, detail="No class found")

    admin_id = sclass.get("school")
    school_info = {}
    if admin_id:
        admin = admin_collection.find_one({"_id": admin_id})
        if admin:
            school_info = {
                "_id": str(admin_id),  # Explicitly converting ObjectId to string
                "schoolName": admin.get("schoolName", "Unknown School")
            }
        else:
            school_info = {"_id": str(admin_id), "schoolName": "Unknown School"}
    else:
        school_info = {"_id": "Unknown", "schoolName": "Unknown School"}

    return {
        "_id": str(sclass['_id']),
        "sclassName": sclass['sclassName'],
        "school": school_info,
        "createdAt": sclass.get('createdAt').isoformat() if sclass.get('createdAt') else None,
        "updatedAt": sclass.get('updatedAt').isoformat() if sclass.get('updatedAt') else None
    }
 

@router.get("/Sclass/Students/{id}", response_model=list[Student])
async def get_sclass_students(id: str, student_collection: Collection = Depends(lambda: get_collection('students'))):
    students = list(student_collection.find({"sclassName": ObjectId(id)}))
    for student in students:
        student['_id'] = str(student['_id']) 
        student['sclassName'] = str(student['sclassName']) 
        student['school'] = str(student['school']) 
        student.pop('password', None) 
    return [Student(**student) for student in students]

@router.delete("/Sclass/{id}")
async def delete_sclass(id: str, 
                        sclass_collection: Collection = Depends(lambda: get_collection('sclasses')), 
                        student_collection: Collection = Depends(lambda: get_collection('students')),
                        subject_collection: Collection = Depends(lambda: get_collection('subjects')),
                        teacher_collection: Collection = Depends(lambda: get_collection('teachers'))):
    deleted_class = sclass_collection.delete_one({"_id": ObjectId(id)})
    if deleted_class.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Class not found")

    student_collection.delete_many({"sclassName": id})
    subject_collection.delete_many({"sclassName": id})
    teacher_collection.delete_many({"teachSclass": id})

    return {"message": "Class deleted successfully"}

@router.delete("/Sclasses/{id}")
async def delete_sclasses(id: str, 
                          sclass_collection: Collection = Depends(lambda: get_collection('sclass')), 
                          student_collection: Collection = Depends(lambda: get_collection('student')),
                          subject_collection: Collection = Depends(lambda: get_collection('subject')),
                          teacher_collection: Collection = Depends(lambda: get_collection('teacher'))):
    deleted_classes = sclass_collection.delete_many({"school": id})
    if deleted_classes.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No classes found to delete")

    student_collection.delete_many({"school": id})
    subject_collection.delete_many({"school": id})
    teacher_collection.delete_many({"school": id})

    return {"message": "Classes deleted successfully"}

