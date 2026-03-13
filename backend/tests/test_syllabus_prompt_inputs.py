import unittest

from app.core import llm
from app.agents import course_agent


class SyllabusPromptInputTests(unittest.TestCase):
    def test_syllabus_prompt_inputs_include_context(self) -> None:
        result = llm.build_course_syllabus_prompt_inputs(
            topic="Rust",
            learning_goal="Build secure systems tools with Rust.",
            preferred_level="Intermediate",
            content_style="conceptual",
            topic_fit_context="Strong technical match.",
        )
        self.assertEqual(result["topic"], "Rust")
        self.assertEqual(result["preferred_level_context"], "intermediate")
        self.assertEqual(result["learning_goal_context"], "Build secure systems tools with Rust.")
        self.assertEqual(result["content_style_context"], "conceptual")
        self.assertEqual(result["topic_fit_context"], "Strong technical match.")

    def test_syllabus_prompt_inputs_fallbacks(self) -> None:
        result = llm.build_course_syllabus_prompt_inputs(topic="Distributed Systems")
        self.assertEqual(result["preferred_level_context"], "auto-infer (beginner-safe)")
        self.assertEqual(result["learning_goal_context"], "Not provided")
        self.assertEqual(result["content_style_context"], "balanced")

    def test_syllabus_prompt_mentions_context(self) -> None:
        self.assertIn("Preferred Level", course_agent.COURSE_USER_PROMPT)
        self.assertIn("Learning Goal", course_agent.COURSE_USER_PROMPT)
        self.assertIn("Content Style", course_agent.COURSE_USER_PROMPT)
        self.assertIn(
            "Total course size should land between 30 and 56 lessons",
            course_agent.COURSE_SYSTEM_PROMPT,
        )
        self.assertNotIn("all subjects", course_agent.COURSE_SYSTEM_PROMPT.lower())
        self.assertNotIn("non-technical", course_agent.COURSE_SYSTEM_PROMPT.lower())

    def test_assess_topic_fit_warns_for_non_technical_topics(self) -> None:
        result = course_agent.assess_topic_fit("History of Rome")
        self.assertEqual(result["fit"], "weak")
        self.assertEqual(result["warnings"], [course_agent.TOPIC_WARNING_MESSAGE])

    def test_assess_topic_fit_accepts_technical_topics(self) -> None:
        result = course_agent.assess_topic_fit(
            "Kubernetes Networking",
            "Troubleshoot service-to-service traffic and ingress behavior.",
        )
        self.assertEqual(result["fit"], "technical")
        self.assertEqual(result["warnings"], [])


if __name__ == "__main__":
    unittest.main()
