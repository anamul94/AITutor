from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import admin, auth, course

app = FastAPI(title="AITutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(course.router, prefix="/api/courses", tags=["courses"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

@app.get("/")
def root():
    return {"message": "Welcome to AITutor API"}
