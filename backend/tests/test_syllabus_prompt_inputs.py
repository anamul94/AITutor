import unittest

from app.core import llm
from app.agents import course_agent


class SyllabusPromptInputTests(unittest.TestCase):
    def test_syllabus_prompt_inputs_include_context(self) -> None:
        result = llm.build_course_syllabus_prompt_inputs(
            topic="Rust",
            learning_goal="Build secure systems tools with Rust.",
            preferred_level="Intermediate",
        )
        self.assertEqual(result["topic"], "Rust")
        self.assertEqual(result["preferred_level_context"], "intermediate")
        self.assertEqual(result["learning_goal_context"], "Build secure systems tools with Rust.")

    def test_syllabus_prompt_inputs_fallbacks(self) -> None:
        result = llm.build_course_syllabus_prompt_inputs(topic="Distributed Systems")
        self.assertEqual(result["preferred_level_context"], "auto-infer (beginner-safe)")
        self.assertEqual(result["learning_goal_context"], "Not provided")

    def test_syllabus_prompt_mentions_context(self) -> None:
        self.assertIn("Preferred Level", course_agent.COURSE_USER_PROMPT)
        self.assertIn("Learning Goal", course_agent.COURSE_USER_PROMPT)
        self.assertIn(
            "lesson MUST include a 1-3 sentence description",
            course_agent.COURSE_SYSTEM_PROMPT,
        )


if __name__ == "__main__":
    unittest.main()
