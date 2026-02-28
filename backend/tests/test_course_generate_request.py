import unittest

from pydantic import ValidationError

from app.schemas.course import CourseGenerateRequest


class CourseGenerateRequestTests(unittest.TestCase):
    def test_accepts_valid_payload(self) -> None:
        payload = CourseGenerateRequest(
            topic="FastAPI",
            learning_goal="Build and deploy a production-ready FastAPI service.",
            preferred_level="beginner",
        )
        self.assertEqual(payload.preferred_level, "beginner")
        self.assertEqual(payload.learning_goal, "Build and deploy a production-ready FastAPI service.")

    def test_legacy_payload_topic_only_is_valid(self) -> None:
        payload = CourseGenerateRequest(topic="Machine Learning")
        self.assertIsNone(payload.learning_goal)
        self.assertIsNone(payload.preferred_level)

    def test_rejects_invalid_preferred_level(self) -> None:
        with self.assertRaises(ValidationError):
            CourseGenerateRequest(
                topic="Databases",
                learning_goal="Understand relational modeling in depth.",
                preferred_level="expert",
            )

    def test_rejects_too_long_learning_goal(self) -> None:
        with self.assertRaises(ValidationError):
            CourseGenerateRequest(
                topic="Data Engineering",
                learning_goal="a" * 301,
                preferred_level="intermediate",
            )

    def test_rejects_short_learning_goal(self) -> None:
        with self.assertRaises(ValidationError):
            CourseGenerateRequest(
                topic="Python",
                learning_goal="too short",
                preferred_level="beginner",
            )

    def test_trims_blank_learning_goal_to_none(self) -> None:
        payload = CourseGenerateRequest(
            topic="Networking",
            learning_goal="   ",
            preferred_level="advanced",
        )
        self.assertIsNone(payload.learning_goal)


if __name__ == "__main__":
    unittest.main()
