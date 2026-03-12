import unittest

import app.agents.dsa_coach_agent as dsa_coach_agent
import app.agents.dsa_learn_agent as dsa_learn_agent
import app.agents.dsa_solve_agent as dsa_solve_agent
from app.core import llm


class DSACoachPromptInputTests(unittest.TestCase):
    def test_prompt_inputs_normalize_missing_values(self) -> None:
        result = llm.build_dsa_coaching_prompt_inputs(
            coaching_mode="solve_problem",
            topic="  Arrays  ",
            problem_statement="  Find max subarray sum.  ",
            prior_knowledge="  I know loops and arrays  ",
            learner_attempt="   ",
            history_excerpt="",
            last_user_message="  help me start  ",
        )
        self.assertEqual(result["topic"], "arrays")
        self.assertEqual(result["problem_statement"], "Find max subarray sum.")
        self.assertEqual(result["prior_knowledge"], "I know loops and arrays")
        self.assertEqual(result["learner_attempt"], "Not provided")
        self.assertEqual(result["history_excerpt"], "No prior turns yet.")
        self.assertEqual(result["last_user_message"], "help me start")

    def test_detect_mode_switches_to_reflection(self) -> None:
        solve_state = {"last_user_message": "I solved it. Can you review my mistakes?"}
        learn_state = {"last_user_message": "Done with this topic, reflect please."}
        self.assertEqual(dsa_solve_agent._detect_mode_node(solve_state)["detected_mode"], "reflection")
        self.assertEqual(dsa_learn_agent._detect_mode_node(learn_state)["detected_mode"], "reflection")

    def test_learn_mode_ignores_attempt_in_prompt_inputs(self) -> None:
        result = llm.build_dsa_coaching_prompt_inputs(
            coaching_mode="learn_topic",
            topic="graphs",
            problem_statement="Topic-first mode",
            prior_knowledge=None,
            learner_attempt="Here is code attempt",
            history_excerpt=None,
            last_user_message="start",
        )
        self.assertNotIn("learner_attempt", result)

    def test_prompt_contract_markers_exist(self) -> None:
        self.assertIn("pattern recognition", dsa_solve_agent.SOLVE_RESPONSE_SYSTEM_PROMPT)
        self.assertIn("### Pattern Lens", dsa_solve_agent.SOLVE_RESPONSE_USER_PROMPT)
        self.assertIn("teaches by doing", dsa_learn_agent.LEARN_RESPONSE_SYSTEM_PROMPT)
        self.assertIn("### Learning By Doing", dsa_learn_agent.LEARN_RESPONSE_USER_PROMPT)
        self.assertIn("ask_initial_thought", dsa_solve_agent.SOLVE_ANALYSIS_OPENAI_JSON_RULES)
        self.assertIn("assess_baseline", dsa_learn_agent.LEARN_ANALYSIS_OPENAI_JSON_RULES)

    def test_learn_analysis_schema_has_comprehension_fields(self) -> None:
        schema = dsa_learn_agent.LearnTurnAnalysisSchema(
            learner_stage="understanding",
            diagnosis="Student has not yet seen a trace-through",
            concept_focus="two pointers",
        )
        self.assertFalse(schema.comprehension_verified)
        self.assertTrue(schema.example_needed)
        self.assertFalse(schema.stuck_signal)

    def test_learn_analysis_schema_new_actions_accepted(self) -> None:
        for action in ("worked_example", "correct_misconception", "verify_understanding"):
            schema = dsa_learn_agent.LearnTurnAnalysisSchema(
                next_action=action,
                learner_stage="understanding",
                diagnosis="Student needs this action",
                concept_focus="arrays",
            )
            self.assertEqual(schema.next_action, action)

    def test_learn_analysis_json_rules_has_new_actions(self) -> None:
        for marker in ("worked_example", "correct_misconception", "verify_understanding",
                       "comprehension_verified", "example_needed", "stuck_signal"):
            self.assertIn(marker, dsa_learn_agent.LEARN_ANALYSIS_OPENAI_JSON_RULES)

    def test_learn_response_prompt_has_new_sections(self) -> None:
        for section in ("### Acknowledgement", "### Core Concept", "### Worked Example", "### Checkpoint"):
            self.assertIn(section, dsa_learn_agent.LEARN_RESPONSE_USER_PROMPT)

    def test_learn_response_system_prompt_teaching_rules(self) -> None:
        for marker in ("intuition", "trace", "misconception", "stuck"):
            self.assertIn(marker, dsa_learn_agent.LEARN_RESPONSE_SYSTEM_PROMPT.lower())

    def test_dispatcher_selects_different_input_shapes(self) -> None:
        learn = dsa_coach_agent.build_dsa_coaching_prompt_inputs(
            coaching_mode="learn_topic",
            topic="graphs",
            problem_statement="topic-first",
            prior_knowledge=None,
            learner_attempt="ignored",
            history_excerpt=None,
            last_user_message="start",
        )
        solve = dsa_coach_agent.build_dsa_coaching_prompt_inputs(
            coaching_mode="solve_problem",
            topic="graphs",
            problem_statement="problem",
            prior_knowledge=None,
            learner_attempt="my code",
            history_excerpt=None,
            last_user_message="help",
        )
        self.assertNotIn("learner_attempt", learn)
        self.assertIn("learner_attempt", solve)


if __name__ == "__main__":
    unittest.main()
