import unittest
from unittest.mock import patch

import server
from training_commands import parse_command


class TrainingCommandsTest(unittest.TestCase):
    def test_commands_and_equivalent_requests(self):
        for text in ['오답노트로 연습해 줘', '틀린 문제 다시 풀래']:
            self.assertEqual({'mode': 'wrong'}, parse_command(text)['action'])
        self.assertEqual('B2+', parse_command('난이도 B2+로 바꿔 줘')['action']['level'])
        self.assertEqual('easier', parse_command('좀 쉽게 해 줘')['action']['level'])
        self.assertEqual('해외여행 ✈️', parse_command('여행 주제로 바꿔 줘')['action']['topic'])
        self.assertEqual('auto', parse_command('난이도 자동으로 설정해 줘')['action']['level'])

    def test_questions_do_not_execute(self):
        for text in ['오답으로 연습할 수 있어?', '난이도 바꿔도 되나요', '여행 주제로 바꿔 줘?', '주제 바꾸는 방법 알려 줘']:
            self.assertIsNone(parse_command(text)['action'])
        self.assertFalse(parse_command('did 다음에 went를 써도 돼?')['handled'])
        self.assertIsNone(parse_command('난이도 C2로 바꿔 줘')['action'])

    def test_next_question_keeps_practice_mode(self):
        for text in ['다른 문제로 바꿔 줘', '다음 문제', '새 문제 줘', '문제 넘겨 줘']:
            self.assertEqual({'next_question': True}, parse_command(text)['action'])
        self.assertIsNone(parse_command('다른 문제로 바꿔도 돼?')['action'])

    def test_finish_training_requires_command(self):
        for text in ['훈련 종료', '훈련 종료해줘', '연습을 끝내 줘', '훈련 마치기']:
            self.assertEqual({'finish_session': True}, parse_command(text)['action'])
        self.assertIsNone(parse_command('훈련 종료해도 돼?').get('action'))

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
