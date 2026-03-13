from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional

# --- LangChain Structured Output Schemas ---

class GeneratedLessonSchema(BaseModel):
    title: str = Field(description="The title of the lesson")
    description: str = Field(
        description="A focused 1-3 sentence summary describing what this lesson must cover in detail."
    )
    order_index: int = Field(description="The order of the lesson in the module, starting at 1")

class GeneratedModuleSchema(BaseModel):
    title: str = Field(description="The title of the module")
    order_index: int = Field(description="The order of the module in the course, starting at 1")
    lessons: List[GeneratedLessonSchema] = Field(description="List of lessons in this module")

class GeneratedCourseSchema(BaseModel):
    title: str = Field(description="A catchy, educational title for the course")
    description: str = Field(description="A short, engaging description of what the user will learn")
    modules: List[GeneratedModuleSchema] = Field(description="List of modules in the course")

class QuizQuestionSchema(BaseModel):
    question: str = Field(description="The quiz question text")
    options: List[str] = Field(description="A list of 4 possible answers", min_length=4, max_length=4)
    correct_answer_index: int = Field(description="The index (0-3) of the correct answer in the options list")
    explanation: str = Field(description="Explanation of why the answer is correct")

class GeneratedLessonQuizSchema(BaseModel):
    quiz: List[QuizQuestionSchema] = Field(
        description="A quiz of 5-10 multiple choice questions based on the lesson.",
        min_length=5,
        max_length=10,
    )

# --- API Request/Response Schemas ---

PreferredLevel = Literal["beginner", "intermediate", "advanced"]
CourseLanguage = Literal["english", "bengali", "hindi"]
ContentStyle = Literal["conceptual", "balanced", "practical"]


class CourseGenerateRequest(BaseModel):
    topic: str
    learning_goal: Optional[str] = None
    preferred_level: Optional[PreferredLevel] = None
    language: CourseLanguage = "english"
    content_style: ContentStyle = "balanced"

    @field_validator("learning_goal", mode="before")
    @classmethod
    def normalize_learning_goal(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            return value

        normalized = value.strip()
        if not normalized:
            return None
        if not 10 <= len(normalized) <= 300:
            raise ValueError("learning_goal must be between 10 and 300 characters")
        return normalized

class LessonResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    order_index: int

class ModuleResponse(BaseModel):
    id: int
    title: str
    order_index: int
    lessons: List[LessonResponse]

class CourseResponse(BaseModel):
    id: int
    title: str
    description: str
    topic: str
    learning_goal: Optional[str] = None
    preferred_level: Optional[PreferredLevel] = None
    language: CourseLanguage = "english"
    content_style: ContentStyle = "balanced"
    warnings: List[str] = Field(default_factory=list)
    progress_percentage: float = 0.0
    modules: List[ModuleResponse]

class UserProgressRequest(BaseModel):
    is_completed: bool = True
    quiz_score: Optional[int] = None

class UserProgressResponse(BaseModel):
    id: int
    lesson_id: int
    is_completed: bool
    quiz_score: Optional[int]
    
class LessonContentResponse(BaseModel):
    id: int
    module_id: int
    course_id: int
    title: str
    description: Optional[str] = None
    content: Optional[str]
    quiz_data: Optional[List[dict]]
    progress: List[UserProgressResponse] = Field(default_factory=list)


class LessonQuizResponse(BaseModel):
    lesson_id: int
    module_id: int
    course_id: int
    quiz_data: List[QuizQuestionSchema]
