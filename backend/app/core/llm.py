import os
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.course import GeneratedCourseSchema, GeneratedLessonContentSchema
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# We need an initialized Bedrock Client for Langchain
# Make sure your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_DEFAULT_REGION are set in .env
def get_llm():
    # Use inference profile IDs or Foundation Model IDs rather than ARNs
    model_id = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
    region_name = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    
    # If the model_id is an ARN, we need to extract the provider name (e.g. 'anthropic') 
    # and pass it explicitly so Langchain knows how to format the messages.
    provider = None
    if model_id and model_id.startswith("arn:aws:bedrock"):
        # ARNs usually look like: arn:aws:bedrock:region::foundation-model/provider.model-name
        # or arn:aws:bedrock:region:account:inference-profile/provider.model-name
        parts = model_id.split("/")
        if len(parts) > 1:
            provider = parts[-1].split(".")[0]
            
    kwargs = {
        "model_id": model_id,
        "region_name": region_name,
        "temperature": 0.5
    }
    
    if provider:
        kwargs["provider"] = provider
    
    return ChatBedrockConverse(**kwargs)

async def generate_course_syllabus(topic: str) -> GeneratedCourseSchema:
    """
    Generates a structured outline for a course based on a topic.
    """
    llm = get_llm()
    
    # We use LangChain's structured output to ensure we get a clean JSON matching our Pydantic schema
    structured_llm = llm.with_structured_output(GeneratedCourseSchema)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert curriculum designer and AI tutor. Your job is to create highly engaging, comprehensive, and well-structured course outlines."),
        ("user", "Create a detailed course syllabus for the following topic: {topic}. The course should be broken down into logical modules, and each module should have multiple sequential lessons. Provide a catchy title and a short description for the course.")
    ])
    
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({"topic": topic})
    return result

async def generate_lesson_content(course_title: str, module_title: str, lesson_title: str) -> GeneratedLessonContentSchema:
    """
    Generates the actual Markdown content and Quiz for a specific lesson.
    """
    llm = get_llm()
    
    structured_llm = llm.with_structured_output(GeneratedLessonContentSchema)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert AI tutor. Your job is to write the educational content for a specific lesson within a broader course. The content should be written in Markdown, be highly engaging, easy to read, and explain concepts clearly. If applicable, include examples or code snippets. Afterwards, generate a 3-question multiple-choice quiz to test the user's understanding of this specific lesson."),
        ("user", "Course: {course_title}\nModule: {module_title}\nLesson: {lesson_title}\n\nPlease write the educational content for this lesson and create the quiz.")
    ])
    
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({
        "course_title": course_title,
        "module_title": module_title,
        "lesson_title": lesson_title
    })
    
    return result
