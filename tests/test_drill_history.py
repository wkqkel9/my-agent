import unittest
from unittest.mock import patch

import server


class DrillHistoryTest(unittest.TestCase):
    def make_handler(self):
        handler = object.__new__(server.AgentHandler)
        handler.headers = {}
        handler.path = "/api/assess"
        handler._bearer_token = lambda: "test-token"
        return handler

    def test_assess_allows_guest_trial_without_saving(self):
        handler = self.make_handler()
        handler._read_json = lambda: {
            "korean": "나는 어제 책을 읽었다.",
            "reference_answer": "I read a book yesterday.",
            "user_text": "I read a book yesterday.",
            "time_spent": 12,
        }
        response = {}
        handler._send_json = lambda status, payload: response.update(status=status, payload=payload)
        with patch("server._auth_user", return_value=None):
            with patch("server._call_llm_json", return_value={
                "is_correct": True,
                "corrected_sentence": "I read a book yesterday.",
                "feedback_points": ["자연스러운 문장입니다."],
                "missed_nuance": None,
                "result": "correct",
            }):
                handler._handle_assess()
        self.assertEqual(200, response["status"])
        self.assertTrue(response["payload"]["is_correct"])

    def test_generate_question_allows_guest_trial(self):
        handler = self.make_handler()
        handler.path = "/api/generate_question"
        handler._read_json = lambda: {}
        response = {}
        handler._send_json = lambda status, payload: response.update(status=status, payload=payload)
        with patch("server._auth_user", return_value=None):
            with patch("server._call_llm_json", return_value={
                "category": "일상",
                "korean": "나는 어제 책을 읽었다.",
                "target_expression": "read a book",
                "reference_answer": "I read a book yesterday.",
                "hint": "read a book",
                "question_type": "사건 설명",
            }):
                handler._handle_generate_question()
        self.assertEqual(200, response["status"])
        self.assertEqual("나는 어제 책을 읽었다.", response["payload"]["korean"])

    def test_history_requires_login(self):
        handler = self.make_handler()
        handler.path = "/api/drill_history"
        response = {}
        handler._send_json = lambda status, payload: response.update(status=status, payload=payload)
        with patch("server._auth_user", return_value=None):
            handler._handle_drill_history_get()
        self.assertEqual(401, response["status"])
        self.assertEqual("로그인이 필요합니다.", response["payload"]["error"])

    def test_history_reset_requires_login(self):
        handler = self.make_handler()
        response = {}
        handler._send_json = lambda status, payload: response.update(status=status, payload=payload)
        with patch("server._auth_user", return_value=None):
            handler._handle_drill_history_delete()
        self.assertEqual(401, response["status"])

    def test_history_reset_deletes_only_authenticated_users_learning_data(self):
        handler = self.make_handler()
        response = {}
        calls = []
        handler._send_json = lambda status, payload: response.update(status=status, payload=payload)
        with patch("server._auth_user", return_value="user-123"):
            with patch("server._supabase", side_effect=lambda path, **kwargs: calls.append((path, kwargs))):
                handler._handle_drill_history_delete()
        self.assertEqual(200, response["status"])
        self.assertEqual(3, len(calls))
        self.assertTrue(all("user_id=eq.user-123" in path for path, _ in calls))
        self.assertTrue(all(kwargs["method"] == "DELETE" for _, kwargs in calls))


if __name__ == "__main__":
    unittest.main()
