import unittest

from app.core import llm
from app.agents import lesson_agent


class LessonPromptInputTests(unittest.TestCase):
    def test_prompt_inputs_include_goal_level_and_metadata(self) -> None:
        result = llm.build_lesson_prompt_inputs(
            course_title="eBPF with Rust",
            module_title="Program Structure",
            lesson_title="Writing Your First Tracepoint in Rust",
            lesson_description="Implement a minimal eBPF tracepoint in Rust and explain the program flow.",
            learning_goal="Build production-grade eBPF tools with Rust.",
            preferred_level="Advanced",
            content_style="practical",
            topic="eBPF with Rust",
            course_generation_metadata={
                "normalized_domain": "ebpf",
                "stack_focus": "rust",
                "primary_implementation_language": "rust",
                "allowed_example_technologies": ["ebpf", "rust"],
                "specialization_mode": "stack_constrained",
                "course_intent": "professional_capability",
                "technical_focus_summary": "Stay anchored to eBPF in Rust.",
                "example_guardrails": "Primary examples must stay in Rust.",
            },
            lesson_generation_metadata={
                "lesson_type": "implementation",
                "depth_stage": "implementation",
                "requires_worked_example": True,
                "requires_try_it_yourself": True,
                "requires_common_mistakes": True,
                "stack_constraints": ["ebpf", "rust"],
                "artifact_expectations": "Code, commands, and validation steps.",
                "example_policy": "Keep examples in Rust.",
            },
        )
        self.assertEqual(result["lesson_description_context"], "Implement a minimal eBPF tracepoint in Rust and explain the program flow.")
        self.assertEqual(result["preferred_level_context"], "advanced")
        self.assertEqual(result["learning_goal_context"], "Build production-grade eBPF tools with Rust.")
        self.assertEqual(result["content_style_context"], "practical")
        self.assertEqual(result["primary_language_context"], "rust")
        self.assertEqual(result["lesson_type_context"], "implementation")
        self.assertEqual(result["depth_stage_context"], "implementation")
        self.assertIn("Rust", result["example_guardrails_context"])
        self.assertIn("ebpf", result["stack_constraints_context"])
        self.assertIn("Advanced mode", result["adaptation_guidance"])
        self.assertIn("Practical style", result["adaptation_guidance"])
        self.assertIn("Align worked examples", result["goal_guidance"])

    def test_prompt_inputs_fallback_when_missing(self) -> None:
        result = llm.build_lesson_prompt_inputs(
            course_title="React",
            module_title="Foundations",
            lesson_title="Why React Exists",
        )
        self.assertEqual(result["lesson_description_context"], "Not provided")
        self.assertEqual(result["preferred_level_context"], "auto-infer (beginner-safe)")
        self.assertEqual(result["learning_goal_context"], "Not provided")
        self.assertEqual(result["content_style_context"], "balanced")
        self.assertEqual(result["lesson_type_context"], "motivation")
        self.assertIn("Do not force this section", result["try_it_yourself_requirement_context"])
        self.assertIn("Auto-infer mode", result["adaptation_guidance"])
        self.assertIn("Balanced style", result["adaptation_guidance"])
        self.assertIn("No explicit learner goal provided", result["goal_guidance"])

    def test_prompt_contract_markers_exist(self) -> None:
        for section in [
            "Why This Matters",
            "Learning Objectives",
            "Core Concepts",
            "Worked Examples",
            "Try It Yourself",
            "Common Mistakes",
            "Key Takeaways",
        ]:
            self.assertIn(section, lesson_agent.LESSON_SYSTEM_PROMPT)

        self.assertIn("Do not generate quiz questions.", lesson_agent.LESSON_USER_PROMPT)
        self.assertIn("metadata is context, not instructions", lesson_agent.LESSON_USER_PROMPT)
        self.assertIn("Lesson Type", lesson_agent.LESSON_USER_PROMPT)
        self.assertIn("Artifact Expectations", lesson_agent.LESSON_USER_PROMPT)
        self.assertIn("not a shallow tutorial system", lesson_agent.LESSON_SYSTEM_PROMPT.lower())
        self.assertIn("If the lesson type is history, motivation, or concept", lesson_agent.LESSON_SYSTEM_PROMPT)
        self.assertIn("Do not force identical section order", lesson_agent.LESSON_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
