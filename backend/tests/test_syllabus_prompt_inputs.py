import unittest

from app.core import llm
from app.agents import course_agent


class SyllabusPromptInputTests(unittest.TestCase):
    def test_syllabus_prompt_inputs_include_context(self) -> None:
        topic_interpretation = course_agent.interpret_topic_focus(
            topic="eBPF with Rust",
            learning_goal="Build secure and observable kernel tooling with Rust.",
        )
        result = llm.build_course_syllabus_prompt_inputs(
            topic="eBPF with Rust",
            learning_goal="Build secure and observable kernel tooling with Rust.",
            preferred_level="Intermediate",
            content_style="conceptual",
            topic_fit_context="Strong technical match.",
            topic_interpretation=topic_interpretation,
        )
        self.assertEqual(result["topic"], "eBPF with Rust")
        self.assertEqual(result["preferred_level_context"], "intermediate")
        self.assertEqual(result["learning_goal_context"], "Build secure and observable kernel tooling with Rust.")
        self.assertEqual(result["content_style_context"], "conceptual")
        self.assertEqual(result["topic_fit_context"], "Strong technical match.")
        self.assertEqual(result["specialization_mode_context"], "stack_constrained")
        self.assertEqual(result["primary_language_context"], "rust")
        self.assertIn("ebpf", result["allowed_example_technologies_context"])
        self.assertIn("Primary examples must stay anchored", result["example_guardrails_context"])

    def test_syllabus_prompt_inputs_fallbacks(self) -> None:
        result = llm.build_course_syllabus_prompt_inputs(topic="Distributed Systems")
        self.assertEqual(result["preferred_level_context"], "auto-infer (beginner-safe)")
        self.assertEqual(result["learning_goal_context"], "Not provided")
        self.assertEqual(result["content_style_context"], "balanced")
        self.assertEqual(result["specialization_mode_context"], "domain_first")

    def test_syllabus_prompt_mentions_context(self) -> None:
        self.assertIn("Preferred Level", course_agent.COURSE_USER_PROMPT)
        self.assertIn("Learning Goal", course_agent.COURSE_USER_PROMPT)
        self.assertIn("Content Style", course_agent.COURSE_USER_PROMPT)
        self.assertIn("Specialization Mode", course_agent.COURSE_USER_PROMPT)
        self.assertIn("Avoid tutorial-series sprawl", course_agent.COURSE_SYSTEM_PROMPT)
        self.assertIn("professional capability", course_agent.COURSE_SYSTEM_PROMPT.lower())
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

    def test_interpret_topic_focus_uses_domain_first_for_broad_topics(self) -> None:
        result = course_agent.interpret_topic_focus("ebpf")
        self.assertEqual(result.normalized_domain, "ebpf")
        self.assertEqual(result.specialization_mode, "domain_first")
        self.assertIsNone(result.primary_implementation_language)
        self.assertIn("broad technical domain", result.technical_focus_summary)

    def test_interpret_topic_focus_preserves_explicit_stack_constraints(self) -> None:
        result = course_agent.interpret_topic_focus("eBPF with Rust")
        self.assertEqual(result.normalized_domain, "ebpf")
        self.assertEqual(result.specialization_mode, "stack_constrained")
        self.assertEqual(result.primary_implementation_language, "rust")
        self.assertEqual(result.stack_focus, "rust")
        self.assertIn("rust", result.allowed_example_technologies)


if __name__ == "__main__":
    unittest.main()
