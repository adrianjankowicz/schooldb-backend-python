from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from controllers.admin import router as admin_router
from controllers.sclass import router as sclass_router
from controllers.subject import router as subject_router
from controllers.student import router as student_router
from controllers.complain import router as complain_router
from controllers.teacher import router as teacher_router
from controllers.notice import router as notice_router

from utils.db import db, get_database

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def db_middleware(request: Request, call_next):
    request.state.db = db
    response = await call_next(request)
    return response

# Include routers
app.include_router(admin_router, dependencies=[Depends(get_database)])
app.include_router(sclass_router, dependencies=[Depends(get_database)])
app.include_router(subject_router, dependencies=[Depends(get_database)])
app.include_router(student_router, dependencies=[Depends(get_database)])
app.include_router(complain_router, dependencies=[Depends(get_database)])
app.include_router(teacher_router, dependencies=[Depends(get_database)])
app.include_router(notice_router, dependencies=[Depends(get_database)])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)