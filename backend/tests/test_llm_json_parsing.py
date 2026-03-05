import unittest

from app.core.llm_json import extract_json_object_text, parse_pydantic_from_response
from app.schemas.course import GeneratedLessonQuizSchema


class _DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class LLMJsonParsingTests(unittest.TestCase):
    def test_extracts_json_from_markdown_fence(self) -> None:
        wrapped = """```json
{"a": 1, "b": 2}
```"""
        self.assertEqual(extract_json_object_text(wrapped), '{"a": 1, "b": 2}')

    def test_extracts_json_when_prefixed_text_exists(self) -> None:
        wrapped = "Here is the result:\n\n{\"a\": 1}\nThanks"
        self.assertEqual(extract_json_object_text(wrapped), '{"a": 1}')

    def test_parses_generated_quiz_schema_from_wrapped_json(self) -> None:
        content = """```json
{
  "quiz": [
    {
      "question": "Q1?",
      "options": ["A", "B", "C", "D"],
      "correct_answer_index": 0,
      "explanation": "Because"
    },
    {
      "question": "Q2?",
      "options": ["A", "B", "C", "D"],
      "correct_answer_index": 1,
      "explanation": "Because"
    },
    {
      "question": "Q3?",
      "options": ["A", "B", "C", "D"],
      "correct_answer_index": 2,
      "explanation": "Because"
    },
    {
      "question": "Q4?",
      "options": ["A", "B", "C", "D"],
      "correct_answer_index": 3,
      "explanation": "Because"
    },
    {
      "question": "Q5?",
      "options": ["A", "B", "C", "D"],
      "correct_answer_index": 1,
      "explanation": "Because"
    }
  ]
}
```"""
        parsed = parse_pydantic_from_response(_DummyResponse(content), GeneratedLessonQuizSchema)
        self.assertEqual(len(parsed.quiz), 5)


if __name__ == "__main__":
    unittest.main()
