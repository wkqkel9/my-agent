import json
import unittest
from unittest.mock import MagicMock, patch

import server
from training_commands import resolve_tool_call


class TrainingCommandsTest(unittest.TestCase):
    def tool_call(self, name, arguments):
        return {"tool_calls": [{"type": "function", "function": {
            "name": name, "arguments": json.dumps(arguments),
        }}]}

    def test_route_sends_tools_and_uses_model_arguments(self):
        handler = self.handler({"text": "이번엔 공항 상황으로 조금 쉽게 해 줘"})
        handler.path = "/api/training_command"
        message = self.tool_call("change_practice_settings", {"topic": "해외여행 ✈️", "level": "easier"})
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": message}]}
        ).encode()
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=True):
            with patch("server.urllib.request.urlopen", return_value=response) as request:
                handler.do_POST()
        sent = json.loads(request.call_args.args[0].data)
        self.assertEqual("auto", sent["tool_choice"])
        self.assertEqual("이번엔 공항 상황으로 조금 쉽게 해 줘", sent["messages"][-1]["content"])
        self.assertIn("change_practice_settings", [tool["function"]["name"] for tool in sent["tools"]])
        self.assertNotIn("response_format", sent)
        self.assertEqual({"topic": "해외여행 ✈️", "level": "easier"}, self.result["body"]["action"])

    def test_only_registered_actions_with_valid_arguments_execute(self):
        for name, arguments in [
            ("unknown_function", {}),
            ("next_question", {"level": "B2"}),
            ("change_practice_settings", {"level": "C2"}),
            ("change_practice_settings", {"topic": ["해외여행 ✈️"]}),
            ("change_practice_settings", {"unexpected": True}),
        ]:
            with self.subTest(name=name, arguments=arguments):
                self.assertIsNone(resolve_tool_call(self.tool_call(name, arguments), "실행해 줘")["action"])
        for name in ("next_question", "finish_session"):
            self.assertEqual({name: True}, resolve_tool_call(self.tool_call(name, {}), "실행해 줘")["action"])

    def test_inquiry_cannot_execute_even_if_model_returns_mutating_tool(self):
        message = self.tool_call("next_question", {})
        self.assertIsNone(resolve_tool_call(message, "다른 문제로 바꿀 수 있어?")["action"])
        self.assertIsNone(resolve_tool_call(self.tool_call("explain_practice", {}), "훈련 종료 방법")["action"])
        self.assertFalse(resolve_tool_call({"content": "unrelated"}, "문법 질문")["handled"])

    def test_provider_unavailable_does_not_execute(self):
        handler = self.handler({"text": "훈련 종료"})
        handler.path = "/api/training_command"
        with patch("server._call_training_command", return_value=None):
            handler.do_POST()
        self.assertEqual(503, self.result["status"])
        self.assertNotIn("action", self.result["body"])

    def test_replacement_rejects_same_question(self):
        handler = self.handler({'previous_question': '어제 공항에 갔다.'})
        with patch('server._auth_user', return_value=None), patch('server._call_llm_json', return_value={
            'korean': '어제 공항에 갔다.', 'reference_answer': 'I went to the airport yesterday.',
        }) as model:
            handler._handle_generate_question()
        self.assertIn('어제 공항에 갔다.', model.call_args.args[1])
        self.assertEqual(503, self.result['status'])

    def handler(self, payload):
        handler = object.__new__(server.AgentHandler)
        handler.headers = {}
        handler._read_json = lambda: payload
        self.result = {}
        handler._send_json = lambda status, body: self.result.update(status=status, body=body)
        return handler

    def test_requested_settings_reach_generation_prompt(self):
        handler = self.handler({'cefr_level': 'A2', 'topic': '해외여행 ✈️'})
        with patch('server._auth_user', return_value=None), patch('server._call_llm_json', return_value={
            'korean': '어제 공항에 갔다.', 'reference_answer': 'I went to the airport yesterday.',
        }) as model:
            handler._handle_generate_question()
        self.assertEqual(200, self.result['status'])
        self.assertEqual('A2', self.result['body']['cefr_level'])
        self.assertEqual('해외여행 ✈️', self.result['body']['category'])
        self.assertIn('CEFR target: A2', model.call_args.args[1])
        self.assertIn('해외여행', model.call_args.args[0])

    def test_invalid_settings_never_call_model(self):
        handler = self.handler({'cefr_level': 'C2'})
        with patch('server._call_llm_json') as model:
            handler._handle_generate_question()
        self.assertEqual(400, self.result['status'])
        model.assert_not_called()


if __name__ == '__main__':
    unittest.main()
