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
    
    structured_llm = llm.with_structured_output(GeneratedCourseSchema)
    
    system_prompt = """You are an expert curriculum designer and AI tutor with deep knowledge across all subjects.

Create a comprehensive, well-structured course syllabus that:

1. **Course Title**: Make it clear, engaging, and descriptive
   - Avoid generic titles
   - Include skill level if relevant (Beginner, Intermediate, Advanced)
   - Example: "Python for Data Science: From Zero to Hero" not just "Python Course"

2. **Course Description**: Write 2-5 sentences that:
   - Explain what the learner will master
   - Highlight practical outcomes and real-world applications
   - Create excitement about the learning journey

3. **Module Structure**: Create 4-7 logical modules that:
   - Follow a natural learning progression (basics → intermediate → advanced)
   - Each module focuses on one major concept or skill area
   - Build upon previous modules
   - Have clear, descriptive titles

4. **Lesson Structure**: Each module should have 3-7 lessons that:
   - Break down the module topic into digestible chunks
   - Progress from foundational to complex within the module
   - Have specific, actionable titles ("Understanding Variables" not "Introduction")
   - Cover one clear concept per lesson

Guidelines:
- Total course should have 30-60 lessons across all modules
- Ensure smooth progression: each lesson builds on previous knowledge
- Balance theory with practical application
- For technical topics: Include fundamentals, practical skills, and advanced concepts
- For non-technical topics: Include history/context, core principles, and applications"""
    
    user_prompt = """Topic: {topic}

Create a complete course syllabus following all guidelines above. Ensure the course is comprehensive enough to take a complete beginner to competency in this topic."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
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
    
    system_prompt = """You are an expert AI tutor specializing in creating clear, engaging, and comprehensive educational content.

Your lesson content MUST include:

1. **Clear Introduction**: Start with why this topic matters and what the learner will achieve

2. **Core Concepts**: Break down complex ideas into simple, digestible explanations
   - Use analogies and real-world comparisons
   - Define technical terms in plain language
   - Build from basics to advanced progressively

3. **Practical Examples**: ALWAYS include 2-3 concrete examples
   - For technical topics: Include well-commented code snippets with explanations
   - For non-technical topics: Use relatable scenarios, case studies, or step-by-step demonstrations
   - Show both correct and common mistake examples when relevant

4. **Visual Structure**: Use Markdown formatting effectively
   - Headers (##, ###) for sections
   - Bullet points for lists
   - Code blocks with language syntax highlighting (```python, ```javascript, etc.)
   - Bold for key terms, italic for emphasis
   - Blockquotes for important notes or tips

5. **Interactive Elements**:
   - "Try it yourself" sections
   - Practice exercises or thought experiments
   - Real-world applications

6. **Summary**: End with key takeaways

Format Guidelines:
- Write at a beginner-friendly level (assume no prior knowledge)
- Use conversational tone
- Keep paragraphs short (3-4 sentences max)
- Include code comments explaining each line for technical content
- Add emoji occasionally for engagement (✅ ❌ 💡 ⚠️)

"""
    
    user_prompt = """Course: {course_title}
Module: {module_title}
Lesson: {lesson_title}

Create comprehensive lesson content following all guidelines above. Then generate a 3-question multiple-choice quiz that tests understanding of the KEY concepts covered.

For code-heavy lessons: Include at least 2 complete, runnable code examples with detailed explanations.
For theory lessons: Include real-world examples, analogies, and practical applications."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({
        "course_title": course_title,
        "module_title": module_title,
        "lesson_title": lesson_title
    })
    
    return result
