from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import logging
from utils.db import get_collection, get_database
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date
from pymongo.collection import Collection, ReturnDocument
from pymongo import MongoClient

class ExamResult(BaseModel):
    subName: str  # ObjectId in MongoDB, ensure this is correctly referenced
    marksObtained: int = 0

class Attendance(BaseModel):
    subName: str
    status: str
    date: datetime

class Student(BaseModel):
    name: str
    rollNum: int
    password: str
    sclassName: Optional[str] = None
    adminID: str  # Renamed from school
    role: str = "Student"
    examResult: List[ExamResult] = []
    attendance: List[Attendance] = []

class StudentResponse(BaseModel):
    name: str
    rollNum: int
    sclassName: Optional[str] = None
    school: str
    role: str
    id: str = Field(..., alias='_id')

class SclassNameInfoX(BaseModel):
    id: str = Field(..., alias='_id')    
    sclassName: str

class ExamResultModelX(BaseModel):
    id: str = Field(..., alias='_id') 
    subName: str
    marksObtained: int

class AttendanceModelX(BaseModel):
    id: str = Field(..., alias='_id') 
    date: datetime
    status: str
    subName: str

class StudentResponseX(BaseModel):
    id: str = Field(..., alias='_id') 
    name: str
    rollNum: int
    sclassName: Optional[SclassNameInfoX]
    role: str
    examResult: List[ExamResultModelX]
    attendance: List[AttendanceModelX]
    school: str

class LoginData(BaseModel):
    studentName: str
    rollNum: str
    password: str

class SchoolObject(BaseModel):
    id: str

class UpdateStudentModel(BaseModel):
    name: Optional[str]
    rollNum: Optional[str]
    password: Optional[str]
    sclassName: Optional[str]
    school: Optional[str]
    role: Optional[str]

class AttendanceModel(BaseModel):
    subName: str
    status: str
    date: datetime

class AttendanceExam(BaseModel):
    id: str = Field(..., alias='_id')
    subName: str
    status: str
    date: datetime

class ExamResultModel(BaseModel):
    id: str = Field(None, alias='_id')
    subName: str
    marksObtained: int

class StudentExam(BaseModel):
    id: str = Field(..., alias='_id')
    name: str
    rollNum: int
    sclassName: str
    role: str
    examResult: List[ExamResultModel]
    attendance: List[AttendanceExam]
    school: str

class AttendanceRequest(BaseModel):
    id: Optional[str] = Field(None, alias='_id')
    subName: str
    status: str
    date: datetime

class StudentAttendance(BaseModel):
    id: str = Field(..., alias='_id')
    name: str
    rollNum: int
    sclassName: str
    role: str
    examResult: List[ExamResultModel]
    attendance: List[AttendanceExam]
    school: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()

def get_students_collection(db: MongoClient = Depends(get_database)):
    return db.get_collection('students')
def get_sclasses_collection(db: MongoClient = Depends(get_database)):
    return db.get_collection('sclasses')
def get_subjects_collection(db: MongoClient = Depends(get_database)):
    return db.get_collection('subjects')
def get_admins_collection(db: MongoClient = Depends(get_database)):
    return db.get_collection('admins')


def convert_objectid_to_str(data):
    """ Convert all ObjectId fields to strings """
    if isinstance(data, dict):
        return {k: (str(v) if isinstance(v, ObjectId) else convert_objectid_to_str(v)) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    else:
        return data

# Utility function for password hashing
def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')  # Encoding the password to bytes
    hashed_password = pwd_context.hash(password_bytes)
    return hashed_password

@router.post("/StudentReg")
async def student_register(student: Student, students_collection: Collection = Depends(lambda: get_collection('students'))):
    existing_student = students_collection.find_one({"rollNum": student.rollNum, "school": ObjectId(student.adminID)})
    if existing_student:
        raise HTTPException(status_code=400, detail="Roll number already exists")


    # Convert fields to ObjectId where necessary
    student_dict = student.dict()
    student_dict['school'] = ObjectId(student_dict.pop('adminID', None))
    if student_dict.get('sclassName') and student_dict['sclassName'] != "undefined":
        student_dict['sclassName'] = ObjectId(student_dict['sclassName'])

    # Convert subName in examResult to ObjectId
    for exam in student_dict.get('examResult', []):
        if 'subName' in exam and exam['subName']:
            exam['subName'] = ObjectId(exam['subName'])

    # Hash the password (uncomment and implement this if you want hashed passwords)
    # student_dict['password'] = hash_password(student.password)

    result = students_collection.insert_one(student_dict)
    student_id = result.inserted_id
    return {"student_id": str(student_id)}

@router.post("/StudentLogin")
async def student_login(login_data: LoginData, students_collection: Collection = Depends(lambda: get_collection('students'))):
    # print(students_collection)
    rollNum = int(login_data.rollNum)
    # print(login_data)
    student = students_collection.find_one({"rollNum": rollNum, "name": login_data.studentName})
    # print(student)
    if not student or student["password"] != login_data.password:
        raise HTTPException(status_code=400, detail="Incorrect roll number or password")

    student_data = convert_objectid_to_str(student)
    del student_data["password"]
    return student_data

@router.get("/Students/{school_id}", response_model=List[StudentResponseX])
async def get_students(
    school_id: str, 
    students_collection: Collection = Depends(get_students_collection), 
    sclasses_collection: Collection = Depends(get_sclasses_collection),
    subjects_collection: Collection = Depends(get_subjects_collection)  # Add this
):
    try:
        oid = ObjectId(school_id)
        students_cursor = students_collection.find({"school": oid})

        student_list = []
        for student in students_cursor:
            student.pop('password', None)

            sclass_id = student.get('sclassName')
            sclass = sclasses_collection.find_one({"_id": sclass_id}) if sclass_id else None
            student['sclassName'] = SclassNameInfoX(_id=str(sclass['_id']), sclassName=sclass['sclassName']) if sclass else None

            exam_results = []
            for res in student.get('examResult', []):
                res_id = res.get('_id')
                if res_id is not None:
                    subject = subjects_collection.find_one({"_id": ObjectId(res['subName'])})
                    exam_results.append(ExamResultModelX(
                        _id=str(res['_id']),
                        subName=subject['subName'] if subject else 'Unknown',
                        marksObtained=res['marksObtained']
                    ))
            student['examResult'] = exam_results

            attendance_records = []
            for att in student.get('attendance', []):
                att_id = att.get('_id')
                if att_id is not None:
                    subject = subjects_collection.find_one({"_id": ObjectId(att['subName'])})
                    attendance_records.append(AttendanceModelX(
                        _id=str(att_id),
                        date=att['date'],
                        status=att['status'],
                        subName=subject['subName'] if subject else 'Unknown'
                    ))
            student['attendance'] = attendance_records

            student['_id'] = str(student['_id'])
            student['school'] = school_id

            student_list.append(StudentResponseX(**student))

        return student_list if student_list else HTTPException(status_code=404, detail="No students found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 


def convert_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """Converts an MongoDB document to ensure _id is a string."""
    document['_id'] = str(document['_id'])
    return document

@router.get("/Student/{student_id}")
async def get_student_detail(student_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    schools_collection = db.get_collection("admins")
    sclasses_collection = db.get_collection("sclasses")
    subjects_collection = db.get_collection("subjects")

    student = students_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student = convert_objectid_to_str(student)

    school = schools_collection.find_one({"_id": ObjectId(student['school'])})
    student['school'] = convert_objectid_to_str(school) if school else {"_id": student['school'], "schoolName": "Unknown School"}

    sclass = sclasses_collection.find_one({"_id": ObjectId(student['sclassName'])})
    student['sclassName'] = convert_objectid_to_str(sclass) if sclass else {"_id": student['sclassName'], "sclassName": "Unknown Class"}

    for result in student.get("examResult", []):
        subject = subjects_collection.find_one({"_id": ObjectId(result["subName"])})
        result["subName"] = convert_objectid_to_str(subject) if subject else {"_id": result["subName"], "subName": "Unknown Subject"}

    for record in student.get("attendance", []):
        subject = subjects_collection.find_one({"_id": ObjectId(record["subName"])})
        record["subName"] = convert_objectid_to_str(subject) if subject else {"_id": record["subName"], "subName": "Unknown Subject"}

    student.pop("password", None)

    return student

@router.delete("/Student/{student_id}")
async def delete_student(student_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    result = students_collection.delete_one({"_id": ObjectId(student_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}

@router.delete("/Students/{school_id}")
async def delete_students(school_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    result = students_collection.delete_many({"school": ObjectId(school_id)})
    if result.deleted_count == 0:
        return {"message": "No students found to delete"}
    return {"deleted_count": result.deleted_count}

@router.delete("/StudentsClass/{class_id}")
async def delete_students_by_class(class_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    result = students_collection.delete_many({"sclassName": ObjectId(class_id)})
    if result.deleted_count == 0:
        return {"message": "No students found to delete"}
    return {"deleted_count": result.deleted_count}

@router.put("/Students/{student_id}", response_model=UpdateStudentModel)
async def update_student(student_id: str, student_data: UpdateStudentModel = Body(...), db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")


    updated_student = students_collection.find_one_and_update(
        {"_id": ObjectId(student_id)},
        {"$set": student_data.dict(exclude_unset=True)},
        return_document=True
    )

    if not updated_student:
        raise HTTPException(status_code=404, detail="Student not found")

    updated_student.pop('password', None)  # Remove password from response
    return updated_student


@router.put("/UpdateExamResult/{student_id}", response_model=StudentExam)
async def update_exam_result(student_id: str, exam_data: ExamResultModel, students_collection: Collection = Depends(get_students_collection), sclasses_collection: Collection = Depends(get_sclasses_collection), schools_collection: Collection = Depends(get_admins_collection)):
    try:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Find the exam result if it already exists
        existing_result_index = next((index for (index, d) in enumerate(student.get("examResult", [])) if d["_id"] == ObjectId(exam_data.id)), -1)

        # Update the existing exam result or append a new one
        if existing_result_index != -1:
            student["examResult"][existing_result_index]["subName"] = ObjectId(exam_data.subName)
            student["examResult"][existing_result_index]["marksObtained"] = exam_data.marksObtained
        else:
            new_exam_result = {
                "_id": ObjectId(exam_data.id) if exam_data.id else ObjectId(),
                "subName": ObjectId(exam_data.subName),
                "marksObtained": exam_data.marksObtained
            }
            student["examResult"].append(new_exam_result)

        # Update the student document in the database
        students_collection.update_one({"_id": ObjectId(student_id)}, {"$set": {"examResult": student["examResult"]}})

        # Fetch updated student data
        student = students_collection.find_one({"_id": ObjectId(student_id)})


        # Convert ObjectIds to strings and fetch related objects
        student = convert_objectid_to_str(student)
        student['rollNum'] = student['rollNum']


        # Fetch and format sclassName details
        if student['sclassName']:
            sclass = sclasses_collection.find_one({"_id": ObjectId(student['sclassName'])})
            student['sclassName'] = sclass['sclassName']

        # Fetch and format school details
        if student['school']:
            school = schools_collection.find_one({"_id": ObjectId(student['school'])})
            student['school'] = school['schoolName']

        student.pop("password", None)  # Remove password from the response
        student.pop("adminID", None)  # Remove adminID if it's not needed in the response

        return StudentExam(**student)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put("/StudentAttendance/{student_id}", response_model=StudentAttendance)
async def update_student_attendance(student_id: str, attendance_data: AttendanceRequest, students_collection: Collection = Depends(get_students_collection), sclasses_collection: Collection = Depends(get_sclasses_collection), schools_collection: Collection = Depends(get_admins_collection)):
    try:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Find the attendance record if it already exists
        existing_attendance_index = next((index for (index, d) in enumerate(student.get("attendance", [])) if d["_id"] == ObjectId(attendance_data.id)), -1)

        # Update the existing attendance record or append a new one
        if existing_attendance_index != -1:
            student["attendance"][existing_attendance_index]["date"] = attendance_data.date
            student["attendance"][existing_attendance_index]["status"] = attendance_data.status
            student["attendance"][existing_attendance_index]["subName"] = ObjectId(attendance_data.subName)
        else:
            new_attendance_record = {
                "_id": ObjectId(attendance_data.id) if attendance_data.id else ObjectId(),
                "date": attendance_data.date,
                "status": attendance_data.status,
                "subName": ObjectId(attendance_data.subName)
            }
            student["attendance"].append(new_attendance_record)

        # Update the student document in the database
        students_collection.update_one({"_id": ObjectId(student_id)}, {"$set": {"attendance": student["attendance"]}})

        # Fetch updated student data
        student = students_collection.find_one({"_id": ObjectId(student_id)})

        # Convert ObjectIds to strings and fetch related objects
        student = convert_objectid_to_str(student)
        student['rollNum'] = student['rollNum']


        # Fetch and format sclassName details
        if student['sclassName']:
            sclass = sclasses_collection.find_one({"_id": ObjectId(student['sclassName'])})
            student['sclassName'] = sclass['sclassName']

        # Fetch and format school details
        if student['school']:
            school = schools_collection.find_one({"_id": ObjectId(student['school'])})
            student['school'] = school['schoolName']

        student.pop("password", None)  # Remove password from the response
        student.pop("adminID", None)  # Remove adminID if it's not needed in the response

        return StudentAttendance(**student)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint do aktualizacji obecności studenta
# @router.put("/StudentAttendance/{student_id}", response_model=ExamResultStudentModel)
# async def student_attendance(student_id: str, attendance_data: AttendanceStudentModel, db: MongoClient = Depends(get_database)):
#     students_collection = db.get_collection("students")
#     subjects_collection = db.get_collection("subjects")
#     sclasses_collection = db.get_collection("sclasses")

#     student = students_collection.find_one({"_id": ObjectId(student_id)})
#     if not student:
#         raise HTTPException(status_code=404, detail="Student not found")

#     subject = subjects_collection.find_one({"_id": ObjectId(attendance_data.subName)})
#     if not subject:
#         raise HTTPException(status_code=404, detail="Subject not found")

#     sclass_id = student.get("sclassName")
#     if sclass_id:
#         sclass_data = sclasses_collection.find_one({"_id": ObjectId(sclass_id)})
#         student["sclassName"] = sclass_id
    
#     # print(attendance_data)
#     attendance_id = ObjectId(attendance_data.id) if attendance_data.id else ObjectId()
#     attendance_entry = {
#         "_id": attendance_id,
#         "date": attendance_data.date,
#         "status": attendance_data.status,
#         "subName": ObjectId(attendance_data.subName)
#     }
#     # print(attendance_entry)
#     student["attendance"].append(attendance_entry)
#     students_collection.update_one({"_id": ObjectId(student_id)}, {"$set": {"attendance": student["attendance"]}})
#     print(student)
#     # Formatting the response
#     student["_id"] = str(student["_id"])
#     student["school"] = str(student["school"])
#     student["sclassName"] = str(student["sclassName"])

#     # Format exam results and attendance
#     student["examResult"] = [
#         {
#             "_id": str(result["_id"]),
#             "subName": str(result["subName"]),
#             "marksObtained": result["marksObtained"]
#         } for result in student.get("examResult", [])
#     ]

#     student["attendance"] = [
#         {
#             "_id": str(att["_id"]),
#             "date": att["date"],
#             "status": att["status"],
#             "subName": str(att["subName"])
#         } for att in student.get("attendance", [])
#     ]

#     student.pop("password", None)  # Remove sensitive information

#     return StudentAttendance(**student)

# Endpoint do usuwania obecności wszystkich studentów w szkole
@router.delete("/RemoveAllStudentsSubAtten/{school_id}")
async def clear_all_students_attendance(school_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    result = students_collection.update_many({"school": ObjectId(school_id)}, {"$set": {"attendance": []}})
    return {"modified_count": result.modified_count}

# Endpoint do usuwania obecności wszystkich studentów w danym przedmiocie
@router.delete("/RemoveAllStudentsAtten/{subject_id}")
async def clear_all_students_attendance_by_subject(subject_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    result = students_collection.update_many({"attendance.subName": ObjectId(subject_id)}, {"$pull": {"attendance": {"subName": ObjectId(subject_id)}}})
    return {"modified_count": result.modified_count}

@router.delete("/RemoveStudentSubAtten/{subject_id}")
async def remove_student_attendance_by_subject(student_id: str, subject_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    
    result = students_collection.update_one(
        {"_id": ObjectId(student_id)},
        {"$pull": {"attendance": {"subName": ObjectId(subject_id)}}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No attendance record found for the subject")
    return {"message": "Attendance record removed"}

# Usuwanie wszystkich obecności studenta
@router.delete("/RemoveStudentAtten/{student_id}")
async def remove_student_attendance(student_id: str, db: MongoClient = Depends(get_database)):
    students_collection = db.get_collection("students")
    
    result = students_collection.update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"attendance": []}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No attendance records found")
    return {"message": "All attendance records cleared"}

