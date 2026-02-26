from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.course import Course, Module, Lesson, UserProgress
from app.schemas.course import CourseGenerateRequest, CourseResponse, LessonContentResponse
from app.core.llm import generate_course_syllabus, generate_lesson_content

router = APIRouter()

@router.post("/generate", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def generate_and_save_course(
    request: CourseGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Takes a topic, asks the LLM to generate a syllabus structure, and saves it to the database.
    """
    topic = request.topic
    
    # 1. Ask LLM to generate the syllabus
    try:
        generated_course = await generate_course_syllabus(topic)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Generation failed: {str(e)}")

    # 2. Save Course to DB
    new_course = Course(
        title=generated_course.title,
        description=generated_course.description,
        topic=topic,
        created_by=current_user.id
    )
    db.add(new_course)
    await db.flush() # flush to get the course ID

    # 3. Save Modules and Lessons to DB
    for g_module in generated_course.modules:
        new_module = Module(
            course_id=new_course.id,
            title=g_module.title,
            order_index=g_module.order_index
        )
        db.add(new_module)
        await db.flush()

        for g_lesson in g_module.lessons:
            new_lesson = Lesson(
                module_id=new_module.id,
                title=g_lesson.title,
                order_index=g_lesson.order_index
            )
            db.add(new_lesson)
            
    await db.commit()
    
    # Reload Course with relationships so we can return it
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
        .where(Course.id == new_course.id)
    )
    final_course = result.scalar_one_or_none()
    
    return final_course

@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch a course structure by ID.
    """
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
        .where(Course.id == course_id)
        .where(Course.created_by == current_user.id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    return course

@router.get("/user/courses", response_model=list[CourseResponse])
async def get_user_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all courses created by the current user.
    """
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
        .where(Course.created_by == current_user.id)
    )
    return result.scalars().all()

@router.get("/lessons/{lesson_id}", response_model=LessonContentResponse)
async def get_or_generate_lesson_content(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch a lesson's content. If it hasn't been generated yet, use the LLM to write the content
    and create a quiz, then save it and return it. JIT (Just-In-Time) Generation.
    """
    # Load Lesson along with Module and Course for context
    result = await db.execute(
        select(Lesson)
        .options(
            selectinload(Lesson.module).selectinload(Module.course)
        )
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    # Check if this course belongs to the user
    if lesson.module.course.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this course")

    # If content already exists, return it!
    if lesson.content:
        return lesson
        
    # Content does NOT exist. We need to generate it just in time!
    try:
        generated_data = await generate_lesson_content(
            course_title=lesson.module.course.title,
            module_title=lesson.module.title,
            lesson_title=lesson.title
        )
        
        # Save generated content to database
        lesson.content = generated_data.content_markdown
        # Quizzes come back as Pydantic objects, dump to dict to store in JSONB
        lesson.quiz_data = [q.model_dump() for q in generated_data.quiz]
        
        await db.commit()
        await db.refresh(lesson)
        
        return lesson
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Generation failed: {str(e)}")
