from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# --- Shared literals ---

PreferredLevel = Literal["beginner", "intermediate", "advanced"]
CourseLanguage = Literal["english", "bengali", "hindi"]
ContentStyle = Literal["conceptual", "balanced", "practical"]
SpecializationMode = Literal["domain_first", "stack_constrained"]
CourseIntent = Literal["professional_capability"]
LessonType = Literal[
    "history",
    "motivation",
    "concept",
    "architecture",
    "internals",
    "implementation",
    "lab",
    "debugging",
    "comparison",
    "case_study",
    "performance",
    "production",
]
DepthStage = Literal[
    "foundation",
    "internals",
    "implementation",
    "debugging",
    "optimization",
    "production",
    "advanced",
]


# --- LangChain Structured Output Schemas ---

class CourseGenerationMetadata(BaseModel):
    normalized_domain: str = Field(description="Normalized technical domain or topic for the course.")
    stack_focus: Optional[str] = Field(
        default=None,
        description="Specific stack or constrained path when the topic names one explicitly.",
    )
    primary_implementation_language: Optional[str] = Field(
        default=None,
        description="Programming language that primary code examples must use when explicitly constrained.",
    )
    allowed_example_technologies: List[str] = Field(
        default_factory=list,
        description="Technologies that examples are allowed or expected to use across the course.",
    )
    specialization_mode: SpecializationMode = Field(
        description="Whether the course stays domain-first or follows an explicit stack constraint."
    )
    course_intent: CourseIntent = Field(
        default="professional_capability",
        description="Always optimize for professional capability rather than shallow tutorials.",
    )
    technical_focus_summary: str = Field(
        description="Short summary of what the course should emphasize and how it should specialize."
    )
    example_guardrails: str = Field(
        description="Rules that examples must follow, including when not to switch languages or stacks."
    )


class LessonGenerationMetadata(BaseModel):
    lesson_type: LessonType = Field(description="What kind of lesson this is.")
    depth_stage: DepthStage = Field(description="Where this lesson sits in the course depth progression.")
    requires_worked_example: bool = Field(
        description="Whether the lesson must include a concrete worked example."
    )
    requires_try_it_yourself: bool = Field(
        description="Whether the lesson must include a hands-on exercise or implementation task."
    )
    requires_common_mistakes: bool = Field(
        description="Whether the lesson must include pitfalls, troubleshooting, or mistakes."
    )
    stack_constraints: List[str] = Field(
        default_factory=list,
        description="Languages, frameworks, or environments that the lesson should stay anchored to.",
    )
    artifact_expectations: str = Field(
        description="Expected artifacts such as code, commands, configs, debugging steps, or reasoning outputs."
    )
    example_policy: str = Field(
        description="How examples should behave in this lesson, including whether comparisons are allowed."
    )


class GeneratedLessonSchema(BaseModel):
    title: str = Field(description="The title of the lesson")
    description: str = Field(
        description="A focused 1-3 sentence summary describing what this lesson must cover in detail."
    )
    order_index: int = Field(description="The order of the lesson in the module, starting at 1")
    generation_metadata: LessonGenerationMetadata = Field(
        description="Structured metadata used to keep lesson generation deep and consistent."
    )


class GeneratedModuleSchema(BaseModel):
    title: str = Field(description="The title of the module")
    order_index: int = Field(description="The order of the module in the course, starting at 1")
    lessons: List[GeneratedLessonSchema] = Field(description="List of lessons in this module")


class GeneratedCourseSchema(BaseModel):
    title: str = Field(description="A catchy, educational title for the course")
    description: str = Field(description="A short, engaging description of what the user will learn")
    generation_metadata: CourseGenerationMetadata = Field(
        description="Structured metadata used to keep the course consistent across syllabus and lesson generation."
    )
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
    content_generated_at: Optional[datetime] = None
    generation_metadata: Optional[LessonGenerationMetadata] = None


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
    generation_metadata: Optional[CourseGenerationMetadata] = None
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
    generation_metadata: Optional[LessonGenerationMetadata] = None
    progress: List[UserProgressResponse] = Field(default_factory=list)


class LessonQuizResponse(BaseModel):
    lesson_id: int
    module_id: int
    course_id: int
    quiz_data: List[QuizQuestionSchema]
