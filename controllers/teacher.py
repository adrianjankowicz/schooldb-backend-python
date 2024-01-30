from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Collection, Optional, List
from pymongo import MongoClient
from bson import ObjectId
from utils.db import get_collection, get_database
from datetime import datetime

class Attendance(BaseModel):
    date: str
    presentCount: Optional[str]
    absentCount: Optional[str]

class Teacher(BaseModel):
    name: str
    email: str
    password: str
    role: str = "Teacher"
    school: str
    teachSubject: Optional[str]
    teachSclass: str
    attendance: List[Attendance] = []

class TeacherResponse(BaseModel):
    name: str
    email: str
    role: str = "Teacher"
    school: str
    teachSubject: Optional[str]
    teachSclass: str
    attendance: List[Attendance] = []

class SchoolInfo(BaseModel):
    id: str = Field(..., alias='_id')
    schoolName: str

class SubjectInfo(BaseModel):
    id: str = Field(..., alias='_id')
    subName: str
    sessions: Optional[str]

class SclassInfo(BaseModel):
    id: str = Field(..., alias='_id')
    sclassName: str

class TeacherList(BaseModel):
    id: str = Field(..., alias='_id')
    name: str
    email: str
    role: str
    school: str
    teachSubject: Optional[SubjectInfo]
    teachSclass: Optional[SclassInfo]
    attendance: List[str] = []
    createdAt: str
    updatedAt: str

class TeacherGet(BaseModel):
    id: str = Field(..., alias='_id')
    name: str
    email: str
    role: str
    school: Optional[SchoolInfo]
    teachSubject: Optional[SubjectInfo]
    teachSclass: Optional[SclassInfo]
    attendance: list
    createdAt: str
    updatedAt: str


class TeacherLogin(BaseModel):
    id: str = Field(..., alias='_id')
    name: str
    email: str
    role: str
    school: Optional[SchoolInfo]
    teachSubject: Optional[SubjectInfo]
    teachSclass: Optional[SclassInfo]
    attendance: List[str] = []
    createdAt: datetime
    updatedAt: datetime

class LoginData(BaseModel):
    email: str
    password: str


router = APIRouter()

def convert_objectid_to_str(data):
    """ Convert all ObjectId fields to strings """
    if isinstance(data, dict):
        return {k: (str(v) if isinstance(v, ObjectId) else convert_objectid_to_str(v)) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    else:
        return data

@router.post("/TeacherReg")
async def teacher_register(teacher: Teacher, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")
    subjects_collection = db.get_collection("subjects")

    if teachers_collection.find_one({"email": teacher.email}):
        raise HTTPException(status_code=400, detail="Email already exists")

    # Hash the password
    hashed_password = teacher.password
    
    teacher_data = teacher.dict(exclude={"password"})
    teacher_data["password"] = hashed_password

    # Set the creation and update timestamps
    now = datetime.now()
    teacher_data["createdAt"] = now
    teacher_data["updatedAt"] = now

    # Convert school, teachSubject, teachSclass to ObjectId if they are not None
    if teacher_data["school"]:
        teacher_data["school"] = ObjectId(teacher_data["school"])
    if teacher_data.get("teachSubject"):
        teacher_data["teachSubject"] = ObjectId(teacher_data["teachSubject"])
    if teacher_data.get("teachSclass"):
        teacher_data["teachSclass"] = ObjectId(teacher_data["teachSclass"])

    new_teacher = teachers_collection.insert_one(teacher_data)
    teacher_id = new_teacher.inserted_id

    # Update the subject with the teacher ID
    if teacher_data.get("teachSubject"):
        subjects_collection.update_one(
            {"_id": teacher_data["teachSubject"]},
            {"$set": {"teacher": teacher_id}}
        )

@router.post("/TeacherLogin", response_model=TeacherLogin)
async def teacher_login(login_data: LoginData, 
                        teachers_collection: Collection = Depends(lambda: get_collection('teachers')),
                        schools_collection: Collection = Depends(lambda: get_collection('admins')),
                        subjects_collection: Collection = Depends(lambda: get_collection('subjects')),
                        classes_collection: Collection = Depends(lambda: get_collection('sclasses'))):
  
    teacher = teachers_collection.find_one({"email": login_data.email})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    if login_data.password != teacher.get('password'):
        raise HTTPException(status_code=400, detail="Incorrect password")

    # Initialize response fields
    school_info = None
    subject_info = None
    class_info = None

    # Process school information if available
    if teacher.get('school'):
        school_data = schools_collection.find_one({"_id": ObjectId(teacher['school'])})
        if school_data:
            school_info = SchoolInfo(**convert_objectid_to_str(school_data))
    # Process subject information if available
    if teacher.get('teachSubject'):
        subject_data = subjects_collection.find_one({"_id": ObjectId(teacher['teachSubject'])})
        if subject_data:
            subject_info = SubjectInfo(**convert_objectid_to_str(subject_data))

    # Process class information if available
    if teacher.get('teachSclass'):
        class_data = classes_collection.find_one({"_id": ObjectId(teacher['teachSclass'])})
        if class_data:
            class_info = SclassInfo(**convert_objectid_to_str(class_data))
    print(teacher['teachSclass'])
    print(class_data)
    teacher_data = {
        "_id": str(teacher['_id']),
        "name": teacher['name'],
        "email": teacher['email'],
        "role": teacher['role'],
        "school": school_info,
        "teachSubject": subject_info,
        "teachSclass": class_info,
        "attendance": teacher.get('attendance', []),
        "createdAt": teacher['createdAt'].isoformat(),
        "updatedAt": teacher['updatedAt'].isoformat()
    }

    response = TeacherLogin(**teacher_data)

    return response


@router.get("/Teachers/{school_id}", response_model=List[TeacherList])
async def get_teachers(school_id: str, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")
    subjects_collection = db.get_collection("subjects")
    sclasses_collection = db.get_collection("sclasses")

    teachers = list(teachers_collection.find({"school": ObjectId(school_id)}))

    result = []
    for teacher in teachers:
        teacher.pop("password", None)  # Remove sensitive data

        # Convert ObjectId to string
        teacher['_id'] = str(teacher['_id'])
        teacher['school'] = str(teacher['school'])

        # Handle teachSubject
        subject_data = None
        if 'teachSubject' in teacher:
            subject = subjects_collection.find_one({"_id": teacher['teachSubject']})
            if subject:
                subject_data = {
                    "_id": str(subject['_id']),  # Renaming _id to id
                    "subName": subject['subName'],
                    "sessions": subject.get('sessions')
                }
        teacher['teachSubject'] = subject_data

        # Handle teachSclass
        sclass_data = None
        if 'teachSclass' in teacher:
            sclass = sclasses_collection.find_one({"_id": teacher['teachSclass']})
            if sclass:
                sclass_data = {
                    "_id": str(sclass['_id']),  # Renaming _id to id
                    "sclassName": sclass['sclassName']
                }
        teacher['teachSclass'] = sclass_data

        # Format dates
        teacher['createdAt'] = teacher['createdAt'].isoformat() if 'createdAt' in teacher else None
        teacher['updatedAt'] = teacher['updatedAt'].isoformat() if 'updatedAt' in teacher else None

        result.append(TeacherList(**teacher))

    if not result:
        raise HTTPException(status_code=404, detail="No teachers found")

    return result

@router.get("/Teacher/{teacher_id}", response_model=TeacherGet)
async def get_teacher_detail(teacher_id: str, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")
    subjects_collection = db.get_collection("subjects")
    sclasses_collection = db.get_collection("sclasses")
    schools_collection = db.get_collection("admins")

    teacher = teachers_collection.find_one({"_id": ObjectId(teacher_id)})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Convert ObjectId to string
    teacher['_id'] = str(teacher['_id'])

    # Handle the school field
    if 'school' in teacher:
        school = schools_collection.find_one({"_id": teacher['school']})
        teacher['school'] = SchoolInfo(
            _id=str(teacher['school']),
            schoolName=school['schoolName'] if school else "Unknown School"
        )

    # Handle the teachSubject field
    if 'teachSubject' in teacher:
        subject = subjects_collection.find_one({"_id": teacher['teachSubject']})
        teacher['teachSubject'] = SubjectInfo(
            _id=str(teacher['teachSubject']),
            subName=subject['subName'] if subject else "Unknown Subject",
            sessions=subject['sessions'] if subject else "Unknown Sessions"
        )

    # Handle the teachSclass field
    if 'teachSclass' in teacher:
        sclass = sclasses_collection.find_one({"_id": teacher['teachSclass']})
        teacher['teachSclass'] = SclassInfo(
            _id=str(teacher['teachSclass']),
            sclassName=sclass['sclassName'] if sclass else "Unknown Class"
        )
    
    if 'createdAt' in teacher:
        teacher['createdAt'] = teacher['createdAt'].isoformat() if teacher['createdAt'] else None

    if 'updatedAt' in teacher:
        teacher['updatedAt'] = teacher['updatedAt'].isoformat() if teacher['updatedAt'] else None


    teacher.pop("password", None)

    return TeacherGet(**teacher)

@router.put("/TeacherSubject")
async def update_teacher_subject(teacher_id: str, teach_subject: str, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")
    subjects_collection = db.get_collection("subjects")

    updated_teacher = teachers_collection.find_one_and_update(
        {"_id": ObjectId(teacher_id)},
        {"$set": {"teachSubject": ObjectId(teach_subject)}},
        return_document=True
    )

    if not updated_teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    subjects_collection.find_one_and_update(
        {"_id": ObjectId(teach_subject)},
        {"$set": {"teacher": updated_teacher["_id"]}}
    )

    return updated_teacher

@router.delete("/Teacher/{teacher_id}")
async def delete_teacher(teacher_id: str, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")
    subjects_collection = db.get_collection("subjects")

    deleted_teacher = teachers_collection.find_one_and_delete({"_id": ObjectId(teacher_id)})

    if not deleted_teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    subjects_collection.update_one(
        {"teacher": deleted_teacher["_id"]},
        {"$unset": {"teacher": ""}}
    )

    return {"message": "Teacher deleted successfully"}

@router.delete("/Teachers/{school_id}")
async def delete_teachers(school_id: str, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")
    subjects_collection = db.get_collection("subjects")

    deletion_result = teachers_collection.delete_many({"school": ObjectId(school_id)})

    if deletion_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No teachers found to delete")

    subjects_collection.update_many(
        {"school": ObjectId(school_id)},
        {"$unset": {"teacher": ""}}
    )

    return {"deleted_count": deletion_result.deleted_count}

@router.delete("/TeachersClass/{class_id}")
async def delete_teachers_by_class(class_id: str, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")
    subjects_collection = db.get_collection("subjects")

    deletion_result = teachers_collection.delete_many({"teachSclass": ObjectId(class_id)})

    if deletion_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No teachers found to delete")

    subjects_collection.update_many(
        {"teachSclass": ObjectId(class_id)},
        {"$unset": {"teacher": ""}}
    )

    return {"deleted_count": deletion_result.deleted_count}

@router.post("/TeacherAttendance/{teacher_id}")
async def teacher_attendance(teacher_id: str, status: str, date: datetime, db: MongoClient = Depends(get_database)):
    teachers_collection = db.get_collection("teachers")

    teacher = teachers_collection.find_one({"_id": ObjectId(teacher_id)})

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    date_string = date.strftime("%Y-%m-%d")

    attendance_updated = False
    for attendance in teacher.get("attendance", []):
        if attendance["date"].strftime("%Y-%m-%d") == date_string:
            attendance["status"] = status
            attendance_updated = True
            break

    if not attendance_updated:
        teacher["attendance"].append({"date": date, "status": status})

    teachers_collection.update_one({"_id": ObjectId(teacher_id)}, {"$set": {"attendance": teacher["attendance"]}})

    return {"message": "Attendance updated successfully"}