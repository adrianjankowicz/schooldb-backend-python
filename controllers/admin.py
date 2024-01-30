from fastapi import APIRouter, HTTPException, Depends, Request
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.collection import Collection
from bson import ObjectId
from pymongo.database import Database
from pydantic import BaseModel, ValidationError
from utils.db import  get_database, verify_google_token, get_collection
import json
import asyncio

router = APIRouter()


# Modele Pydantic
class GoogleLoginData(BaseModel):
    token: str

class AdminRegistrationData(BaseModel):
    email: str
    password: str
    schoolName: str = None
    token: str = None

class AdminLoginData(BaseModel):
    email: str
    password: str

class AdminDetailData(BaseModel):
    admin_id: str

class Admin(BaseModel):
    name: str
    email: str
    isGoogleAccount: bool
    role: str
    schoolName: str
    password: str


# def get_database(request: Request):
#     return request.state.db

@router.post("/AdminGoogleLogin")
async def google_login(data: GoogleLoginData, db: Database = Depends(get_database)):
    admins = db["admins"]
    google_user = verify_google_token(data.token)
    if google_user:
        admin = admins.find_one({'email': google_user['email']})
        if admin:
            admin['_id'] = str(admin['_id'])
            admin.pop('password', None)
            return admin
        else:
            raise HTTPException(status_code=404, detail='No user found with this Google account')
    else:
        raise HTTPException(status_code=400, detail='Invalid token')

# @router.post("/AdminReg")
# async def admin_register(data: AdminRegistrationData, db: Database = Depends(get_database)):
#     admins = db["admins"]
#     if 'token' in data:
#         google_user = verify_google_token(data['token'])
#         if google_user:
#             if admins.find_one({'email': google_user['email']}):
#                 raise HTTPException(status_code=400, detail='Email already exists')
#             admin = {
#                 'email': google_user['email'],
#                 'schoolName': data['schoolName'],
#                 'password': generate_password_hash('placeholder'),
#                 'isGoogleAccount': True
#             }
#         else:
#             raise HTTPException(status_code=400, detail='Invalid token')
#     else:
#         if admins.find_one({'email': data['email']}):
#             raise HTTPException(status_code=400, detail='Email already exists')
#         elif admins.find_one({'schoolName': data['schoolName']}):
#             raise HTTPException(status_code=400, detail='School name already exists')
#         admin = {
#             'email': data['email'],
#             'password': generate_password_hash(data['password']),
#             'schoolName': data.get('schoolName')
#         }

#     admins.insert_one(admin)
#     admin['_id'] = str(admin['_id'])
#     admin.pop('password', None)
#     return admin

@router.post("/AdminReg")
async def admin_register(request: Request, db: Database = Depends(get_database)):
    try:
        try:
            req_body = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format")

        admins_collection = get_collection("admins")
        admin_data = None
        print(admins_collection)
        if 'token' in req_body:

            google_user = await asyncio.to_thread(verify_google_token, req_body['token'])
            if not google_user:
                raise HTTPException(status_code=401, detail="Invalid Google token")



            existing_admin = admins_collection.find_one({'email': google_user['email']})
            if existing_admin:
                return {'message': 'Email already exists'}

            admin_data = Admin(
        **google_user,
        schoolName=req_body.get('schoolName', ''),
        password='placeholder',
        isGoogleAccount=True,
        role=req_body.get('role', 'Admin') 
    ).dict()
        else:
            existing_admin_by_email = admins_collection.find_one({'email': req_body['email']})
            existing_school = admins_collection.find_one({'schoolName': req_body['schoolName']})

            if existing_admin_by_email:
                return {'message': 'Email already exists'}
            elif existing_school:
                return {'message': 'School name already exists'}

            admin_data = Admin(**req_body).dict()

        result = admins_collection.insert_one(admin_data)
        admin_data.pop('password', None)  
        admin_data['_id'] = str(result.inserted_id)  
        return admin_data
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/AdminLogin")
async def admin_login(data: AdminLoginData, db: Database = Depends(get_database)):
    admins = db["admins"]
    email = data.email
    password = data.password
    admin = admins.find_one({'email': email})
    
    if admin and password == admin['password']:
        admin['_id'] = str(admin['_id'])
        admin.pop('password', None)
        return admin
    else:
        raise HTTPException(status_code=401, detail='Invalid email or password')


@router.get("/Admin/{admin_id}")
async def get_admin_detail(admin_id: str, db: Database = Depends(get_database)):
    admins = db["admins"]
    admin = admins.find_one({'_id': ObjectId(admin_id)})
    if admin:
        admin['_id'] = str(admin['_id'])
        admin.pop('password', None)
        return admin
    else:
        raise HTTPException(status_code=404, detail='No admin found')
