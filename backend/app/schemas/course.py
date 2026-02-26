from pydantic import BaseModel, Field
from typing import List, Optional

# --- LangChain Structured Output Schemas ---

class GeneratedLessonSchema(BaseModel):
    title: str = Field(description="The title of the lesson")
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
    options: List[str] = Field(description="A list of 4 possible answers")
    correct_answer_index: int = Field(description="The index (0-3) of the correct answer in the options list")
    explanation: str = Field(description="Explanation of why the answer is correct")

class GeneratedLessonContentSchema(BaseModel):
    content_markdown: str = Field(description="The educational content of the lesson written in Markdown format. Should be extensive, engaging, and easy to read. Include code blocks if relevant.")
    quiz: List[QuizQuestionSchema] = Field(description="A short quiz of 3 questions to test the user's knowledge on this specific lesson content.")

# --- API Request/Response Schemas ---

class CourseGenerateRequest(BaseModel):
    topic: str

class LessonResponse(BaseModel):
    id: int
    title: str
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
    content: Optional[str]
    quiz_data: Optional[List[dict]]
    progress: Optional[List[UserProgressResponse]] = []
