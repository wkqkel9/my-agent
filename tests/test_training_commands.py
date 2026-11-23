import json
import unittest
from unittest.mock import MagicMock, patch

import server
from training_commands import CATEGORIES, EXPLAIN_TOOL, FOLLOWUP_TOOL, LEVELS, resolve_tool_call


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

    def test_polite_request_can_execute_but_availability_question_cannot(self):
        message = self.tool_call("next_question", {})
        self.assertEqual({"next_question": True}, resolve_tool_call(message, "다른 거 내줄래?")["action"])
        self.assertIsNone(resolve_tool_call(message, "지금 문제를 바꿀 수 있어?")["action"])

    def test_catalog_questions_use_actual_settings_without_changing_them(self):
        cases = [
            ("주제를 뭐로 바꿀수있어?", "topic", CATEGORIES),
            ("난이도는 뭐가 있어?", "level", LEVELS),
        ]
        for text, subject, values in cases:
            with self.subTest(text=text):
                message = self.tool_call(EXPLAIN_TOOL, {"subject": subject, "answer": "임의의 설정 목록"})
                result = resolve_tool_call(message, text)
                self.assertIsNone(result["action"])
                self.assertIn(", ".join(values), result["message"])
                self.assertNotIn("임의의", result["message"])

    def test_service_answer_does_not_consume_pending_settings(self):
        pending = {"missing": ["topic"], "settings": {"level": "B2"}}
        answer = "60초가 지나도 입력한 답안을 Enter로 제출할 수 있어요."
        message = self.tool_call(EXPLAIN_TOOL, {"subject": "general", "answer": answer})
        with patch("server._call_chat_completion") as model:
            model.side_effect = lambda payload, decode: decode(message)
            result = server._call_training_command("제한 시간 지나면 어떻게 해?", pending)
        sent = model.call_args.args[0]
        self.assertIn("60-second timer", sent["messages"][0]["content"])
        self.assertIn("subject", next(tool for tool in sent["tools"] if tool["function"]["name"] == EXPLAIN_TOOL)
                      ["function"]["parameters"]["properties"])
        self.assertEqual({"handled": True, "action": None, "message": answer}, result)
        self.assertEqual({"level": "B2", "topic": "일·커리어"},
                         server._call_training_command("일·커리어", pending)["action"])

    def test_asks_only_for_missing_setting_and_keeps_explicit_topic(self):
        message = self.tool_call("change_practice_settings", {"topic": "해외여행 ✈️", "ask_for": ["level"]})
        result = resolve_tool_call(message, "여행 문제로 하고 난이도도 바꿔 줘")
        self.assertIsNone(result["action"])
        self.assertIn("어느 난이도", result["message"])
        self.assertEqual({"missing": ["level"], "settings": {"topic": "해외여행 ✈️"}}, result["pending"])

        with patch("server._call_chat_completion") as model:
            invalid = server._call_training_command("C2", result["pending"])
            final = server._call_training_command("b2+", invalid["pending"])
        model.assert_not_called()
        self.assertIsNone(invalid["action"])
        self.assertEqual({"topic": "해외여행 ✈️", "level": "B2+"}, final["action"])

    def test_can_fill_two_settings_in_either_order_or_cancel(self):
        pending = {"missing": ["topic", "level"], "settings": {}}
        with patch("server._call_chat_completion") as model:
            first = server._call_training_command("조금 쉽게", pending)
            final = server._call_training_command("일·커리어", first["pending"])
            canceled = server._call_training_command("취소", first["pending"])
        model.assert_not_called()
        self.assertEqual(["topic"], first["pending"]["missing"])
        self.assertEqual({"level": "easier", "topic": "일·커리어"}, final["action"])
        self.assertIsNone(canceled["pending"])
        self.assertIsNone(canceled["action"])

    def test_followup_can_use_model_and_only_fill_missing_values(self):
        pending = {"missing": ["topic"], "settings": {"level": "B2"}}
        reply = "회사 동료하고 일하다 갈등 생기는 상황으로"
        topic = "회사 동료하고 일하다 갈등 생기는 상황"
        with patch("server._call_chat_completion") as model:
            model.side_effect = lambda payload, decode: decode(self.tool_call(FOLLOWUP_TOOL, {"topic": topic}))
            result = server._call_training_command(reply, pending)
        sent = model.call_args.args[0]
        self.assertIn("pending clarification asks for: topic", sent["messages"][0]["content"])
        self.assertEqual(reply, sent["messages"][-1]["content"])
        self.assertEqual({"topic": topic, "level": "B2"}, result["action"])
        wrong_field = self.tool_call(FOLLOWUP_TOOL, {"level": "A2"})
        self.assertIsNone(resolve_tool_call(wrong_field, "A2", pending)["action"])
        self.assertIsNone(resolve_tool_call(wrong_field, "A2")["action"])
        superseding = self.tool_call("next_question", {})
        self.assertEqual({"next_question": True}, resolve_tool_call(superseding, "그냥 다음 문제 줘", pending)["action"])

    def test_route_rejects_invalid_pending_state_before_model_call(self):
        for pending in (False, {"missing": ["mode"], "settings": {}},
                        {"missing": ["level"], "settings": {"topic": "한 줄\n다음 줄"}},
                        {"missing": ["level", "level"], "settings": {}}):
            with self.subTest(pending=pending):
                handler = self.handler({"text": "B2", "pending": pending})
                handler.path = "/api/training_command"
                with patch("server._call_training_command") as command:
                    handler.do_POST()
                self.assertEqual(400, self.result["status"])
                command.assert_not_called()

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
        self.assertIn('해외여행', model.call_args.args[1])

    def test_custom_topic_flows_from_command_to_question(self):
        topic = "해외 학회에서 발표 후 질문받는 상황"
        message = self.tool_call("change_practice_settings", {"topic": topic, "level": "B2"})
        result = resolve_tool_call(message, topic + "으로 내 줘")
        self.assertEqual({"topic": topic, "level": "B2"}, result["action"])
        handler = self.handler({"topic": result["action"]["topic"], "cefr_level": result["action"]["level"]})
        with patch("server._auth_user", return_value=None), patch("server._call_llm_json", return_value={
            "korean": "발표가 끝난 뒤 한 연구자가 질문을 했다.",
            "reference_answer": "A researcher asked a question after the presentation.",
        }) as model:
            handler._handle_generate_question()
        self.assertEqual(200, self.result["status"])
        self.assertEqual(topic, self.result["body"]["category"])
        self.assertIn(json.dumps(topic, ensure_ascii=False), model.call_args.args[1])
        self.assertNotIn(topic, model.call_args.args[0])

    def test_invalid_topic_never_calls_model(self):
        for topic in ("", "  ", "주제\n추가 지시", "긴" * 101, ["여행"]):
            with self.subTest(topic=topic), patch("server._call_llm_json") as model:
                self.handler({"topic": topic})._handle_generate_question()
                self.assertEqual(400, self.result["status"])
                model.assert_not_called()

    def test_invalid_settings_never_call_model(self):
        handler = self.handler({'cefr_level': 'C2'})
        with patch('server._call_llm_json') as model:
            handler._handle_generate_question()
        self.assertEqual(400, self.result['status'])
        model.assert_not_called()


if __name__ == '__main__':
    unittest.main()
