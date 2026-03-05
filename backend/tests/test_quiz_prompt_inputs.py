import unittest

from app.agents import lesson_quiz_agent


class LessonQuizPromptInputTests(unittest.TestCase):
    def test_quiz_prompt_inputs_include_lesson_content_and_context(self) -> None:
        result = lesson_quiz_agent.build_lesson_quiz_prompt_inputs(
            course_title="Backend Engineering",
            module_title="Auth",
            lesson_title="JWT Access Tokens",
            lesson_content="Token structure and signature verification",
            lesson_description="Covers token structure, signing, and verification flow.",
            learning_goal="Design secure JWT auth with rotation.",
            preferred_level="Advanced",
            language="english",
        )
        self.assertEqual(result["course_title"], "Backend Engineering")
        self.assertEqual(result["lesson_content"], "Token structure and signature verification")
        self.assertEqual(result["preferred_level_context"], "advanced")
        self.assertEqual(result["learning_goal_context"], "Design secure JWT auth with rotation.")

    def test_quiz_prompt_contract_markers_exist(self) -> None:
        self.assertIn("Generate between 5 and 10", lesson_quiz_agent.LESSON_QUIZ_SYSTEM_PROMPT)
        self.assertIn("Generate only JSON", lesson_quiz_agent.LESSON_QUIZ_USER_PROMPT)
        self.assertIn("must contain 5 to 10", lesson_quiz_agent.LESSON_QUIZ_JSON_RULES)


if __name__ == "__main__":
    unittest.main()
