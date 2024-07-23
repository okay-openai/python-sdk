import json
import os
import unittest
from unittest.mock import patch

from statsig import StatsigOptions, StatsigServer, _Evaluator, StatsigUser, IDataStore
from statsig.evaluation_details import EvaluationReason
from gzip_helpers import GzipHelpers
from network_stub import NetworkStub

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../testdata/download_config_specs.json')) as r:
    CONFIG_SPECS_RESPONSE = r.read()

_api_override = "http://evaluation-details-test"
_network_stub = NetworkStub(_api_override)




class TestEvaluationDetails(unittest.TestCase):
    _server: StatsigServer
    _evaluator: _Evaluator
    _user = StatsigUser(user_id="a-user")

    @patch('requests.request', side_effect=_network_stub.mock)
    def setUp(self, mock_request) -> None:
        server = StatsigServer()
        options = StatsigOptions(
            api=_api_override,
            disable_diagnostics=True
        )

        _network_stub.reset()

        _network_stub.stub_request_with_value(
            "download_config_specs/.*", 200, json.loads(CONFIG_SPECS_RESPONSE))

        server.initialize("secret-key", options)
        self._server = server
        self._evaluator = server._evaluator

    def test_fast_match_string_in_array(self):
        condition = { "targetValue" : ["foo", "bar", "baz"] }

        # search for strings
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("foo", condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("bar", condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("baz", condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("gosh", condition), False)

        # search for strings insensitive
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("FOO", condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("Bar", condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("baZ", condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array("gosh", condition), False)

        # search for integer
        condition = { "targetValue" : [1, 2, 3, 4, 5, 6, 7] }
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array(1, condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array(4, condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array(7, condition), True)
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array(-1, condition), False)

        # search empty value
        condition = { "targetValue" : [1, 2, 3, 4, 5, 6, 7] }
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array(None, condition), False)

        # search in an empty array
        condition = { "targetValue" : [] }
        self.assertEqual(self._evaluator._Evaluator__fast_match_string_in_array(1, condition), False)

        # search for booleans

if __name__ == "__main__":
    unittest.main()
