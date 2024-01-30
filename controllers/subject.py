from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
import logging
from utils.db import get_collection, get_database
from pymongo import MongoClient

# class TeacherInfo(BaseModel):
#     id: str = Field(..., alias='_id')
#     name: str

# class SclassInfo(BaseModel):
#     id: str = Field(..., alias='_id')
#     sclassName: str

# class SubjectResponse(BaseModel):
#     id: str = Field(..., alias='_id')
#     subName: str
#     subCode: str
#     sessions: str
#     sclassName: SclassInfo
#     school: str
#     teacher: Optional[TeacherInfo] = None
#     createdAt: Optional[str]
#     updatedAt: Optional[str]

router = APIRouter()

class Subject(BaseModel):
    subName: str
    subCode: str
    sessions: str
    sclassName: Optional[str] = None
    school: Optional[str] = None

class SubjectFree(BaseModel):
    id: str = Field(..., alias='_id')
    subName: str
    subCode: str
    sessions: str
    sclassName: Optional[str] = None
    school: Optional[str] = None

class SubjectCreate(BaseModel):
    subjects: List[Subject]
    adminID: str
    sclassName: str

class SclassNameInfo(BaseModel):
    id: str = Field(..., alias='_id')
    sclassName: str

class TeacherInfo(BaseModel):
    id: str = Field(..., alias='_id')
    name: str

class SubjectResponse(BaseModel):
    id: str = Field(..., alias='_id')
    subName: str
    subCode: str
    sessions: str
    sclassName: Optional[SclassNameInfo]
    school: str
    teacher: Optional[TeacherInfo] = None

def convert_objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    else:
        return obj
    
@router.post("/SubjectCreate")
async def subject_create(subject_data: SubjectCreate):
    subjects_collection = get_collection('subjects')

    for subject in subject_data.subjects:
        existing_subject = subjects_collection.find_one({
            'subCode': subject.subCode,
            'school': ObjectId(subject_data.adminID)
        })

        if existing_subject:
            raise HTTPException(status_code=400, detail=f'Subject with subCode {subject.subCode} already exists')

    new_subjects = [{
        'subName': subject.subName,
        'subCode': subject.subCode,
        'sessions': subject.sessions,
        'sclassName': ObjectId(subject_data.sclassName),
        'school': ObjectId(subject_data.adminID)
    } for subject in subject_data.subjects]

    try:
        inserted_ids = subjects_collection.insert_many(new_subjects).inserted_ids
        # Convert ObjectId fields to strings for response
        converted_ids = [convert_objectid_to_str(id) for id in inserted_ids]
        return {"inserted_ids": converted_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/AllSubjects/{school_id}")
async def all_subjects(school_id: str, db: MongoClient = Depends(get_database)) -> List[SubjectResponse]:
    subjects_collection = db.get_collection('subjects')
    sclasses_collection = db.get_collection('sclasses')
    teachers_collection = db.get_collection('teachers')

    subjects_cursor = subjects_collection.find({'school': ObjectId(school_id)})
    enhanced_subjects = []

    for subject in subjects_cursor:
        subject_dict = convert_objectid_to_str(subject)

        # Fetch and embed sclassName details
        sclass_id = subject.get('sclassName')
        if sclass_id and ObjectId.is_valid(sclass_id):
            sclass = sclasses_collection.find_one({'_id': ObjectId(sclass_id)})
            subject_dict['sclassName'] = SclassNameInfo(**convert_objectid_to_str(sclass)) if sclass else None

        # Fetch and embed teacher details
        teacher_id = subject.get('teacher')
        if teacher_id and ObjectId.is_valid(teacher_id):
            teacher = teachers_collection.find_one({'_id': ObjectId(teacher_id)})
            subject_dict['teacher'] = TeacherInfo(**convert_objectid_to_str(teacher)) if teacher else None

        enhanced_subjects.append(SubjectResponse(**subject_dict))

    if not enhanced_subjects:
        raise HTTPException(status_code=404, detail="No subjects found")

    return enhanced_subjects

@router.get("/ClassSubjects/{class_id}")
async def class_subjects(class_id: str) -> List[Subject]:
    subjects_collection = get_collection('subjects')
    subjects = list(subjects_collection.find({'sclassName': ObjectId(class_id)}))
    if subjects:
        return [convert_objectid_to_str(subject) for subject in subjects]
    else:
        raise HTTPException(status_code=404, detail="No subjects found")
    
def get_teacher_name(teacher_id):
    teachers_collection = get_collection('teachers')
    teacher = teachers_collection.find_one({'_id': teacher_id})
    return teacher['name'] if teacher else "Unknown"

@router.get("/FreeSubjectList/{sclass_id}", response_model=List[SubjectFree])
async def free_subject_list(sclass_id: str, db: MongoClient = Depends(get_database)):
    subjects_collection = db.get_collection("subjects")

    try:
        subjects = list(subjects_collection.find({"sclassName": ObjectId(sclass_id), "teacher": {"$exists": False}}))

        # Convert ObjectId fields to strings
        print(subjects)
        for subject in subjects:
            subject['_id'] = str(subject['_id'])
            subject['sclassName'] = str(subject['sclassName'])
            subject['school'] = str(subject['school'])

        if subjects:
            return subjects
        else:
            raise HTTPException(status_code=404, detail="No subjects found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/Subject/{subject_id}", response_model=SubjectResponse)
async def get_subject_detail(subject_id: str):
    # Validate the subject_id
    try:
        valid_subject_id = ObjectId(subject_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid subject ID")

    subjects_collection = get_collection('subjects')
    sclasses_collection = get_collection('sclasses')
    teachers_collection = get_collection('teachers')

    subject = subjects_collection.find_one({'_id': valid_subject_id})
    if subject:
        # Populate class name details
        if 'sclassName' in subject and subject['sclassName']:
            sclass = sclasses_collection.find_one({'_id': ObjectId(subject['sclassName'])})
            subject['sclassName'] = {
                '_id': str(sclass['_id']),
                'sclassName': sclass['sclassName']
            } if sclass else {'_id': str(subject['sclassName']), 'sclassName': 'Unknown'}

        # Populate teacher name details
        if 'teacher' in subject and subject['teacher']:
            teacher = teachers_collection.find_one({'_id': ObjectId(subject['teacher'])})
            subject['teacher'] = {
                '_id': str(teacher['_id']),
                'name': teacher['name']
            } if teacher else {'_id': str(subject['teacher']), 'name': 'Unknown'}

        return convert_objectid_to_str(subject)
    else:
        raise HTTPException(status_code=404, detail="No subject found")

@router.delete("/Subject/{subject_id}")
async def delete_subject(subject_id: str):
    subjects_collection = get_collection('subjects')
    teachers_collection = get_collection('teachers')
    students_collection = get_collection('students')

    deleted_subject = subjects_collection.find_one_and_delete({'_id': ObjectId(subject_id)})
    if not deleted_subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Update related teachers and students
    teachers_collection.update_one({'teachSubject': ObjectId(subject_id)}, {'$unset': {'teachSubject': ''}})
    students_collection.update_many({}, {'$pull': {'examResult': {'subName': ObjectId(subject_id)}}})
    students_collection.update_many({}, {'$pull': {'attendance': {'subName': ObjectId(subject_id)}}})

    return {"message": "Subject deleted successfully"}

@router.delete("/Subjects/{school_id}")
async def delete_subjects(school_id: str):
    subjects_collection = get_collection('subjects')
    teachers_collection = get_collection('teachers')
    students_collection = get_collection('students')

    # Delete subjects and get deleted subject IDs
    deleted_subjects = subjects_collection.delete_many({'school': school_id})
    deleted_ids = [subject['_id'] for subject in deleted_subjects]

    # Update related teachers
    teachers_collection.update_many(
        {'teachSubject': {'$in': deleted_ids}},
        {'$unset': {'teachSubject': 1}}
    )

    # Update students
    students_collection.update_many(
        {},
        {'$set': {'examResult': None, 'attendance': None}}
    )

    return {"message": f"Subjects deleted successfully for school {school_id}"}

@router.delete("/SubjectsClass/{class_id}")
async def delete_subjects_by_class(class_id: str):
    subjects_collection = get_collection('subjects')
    teachers_collection = get_collection('teachers')
    students_collection = get_collection('students')

    # Delete subjects and get deleted subject IDs
    deleted_subjects = subjects_collection.delete_many({'sclassName': class_id})
    deleted_ids = [subject['_id'] for subject in deleted_subjects]

    # Update related teachers
    teachers_collection.update_many(
        {'teachSubject': {'$in': deleted_ids}},
        {'$unset': {'teachSubject': 1}}
    )

    # Update students
    students_collection.update_many(
        {},
        {'$set': {'examResult': None, 'attendance': None}}
    )

    return {"message": f"Subjects deleted successfully for class {class_id}"}