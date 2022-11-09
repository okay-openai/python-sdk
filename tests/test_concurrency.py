import threading
import time
import os
import unittest
import json

from unittest.mock import patch
from tests.network_stub import NetworkStub
from statsig import statsig, StatsigUser, StatsigOptions, StatsigEvent, StatsigEnvironmentTier

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../testdata/download_config_specs.json')) as r:
    CONFIG_SPECS_RESPONSE = r.read()


class TestStatsigConcurrency(unittest.TestCase):
    _api_override = "http://test-statsig-concurrency"
    _network_stub = NetworkStub(_api_override)
    _idlist_sync_count = 0
    _download_id_list_count = 0
    _event_count = 0

    @classmethod
    @patch('requests.post', side_effect=_network_stub.mock)
    @patch('requests.get', side_effect=_network_stub.mock)
    def setUpClass(cls, mock_post, mock_get):
        cls._idlist_sync_count = 0
        cls._download_id_list_count = 0
        cls._event_count = 0

        cls._network_stub.stub_request_with_value(
            "download_config_specs", 200, json.loads(CONFIG_SPECS_RESPONSE))

        def id_lists_callback(url: str, data: dict):
            size = 10 + 3 * cls._idlist_sync_count
            cls._idlist_sync_count += 1
            return {
                "list_1": {
                    "name": "list_1",
                    "size": size,
                    "url": cls._api_override + "/list_1",
                    "creationTime": 1,
                    "fileID": "file_id_1",
                },
            }

        cls._network_stub.stub_request_with_function(
            "get_id_lists", 200, id_lists_callback)

        def id_list_download_callback(url: str, data: dict):
            cls._download_id_list_count += 1
            if cls._download_id_list_count == 1:
                return "+7/rrkvF6\n"
            return f'+{cls._download_id_list_count}\n-{cls._download_id_list_count}\n'

        cls._network_stub.stub_request_with_function(
            "list_1", 202, id_list_download_callback)

        def log_event_callback(url: str, data: dict):
            cls._event_count += len(data["json"]["events"])

        cls._network_stub.stub_request_with_function(
            "log_event", 202, log_event_callback)

        cls.statsig_user = StatsigUser(
            "123", email="testuser@statsig.com", private_attributes={"test": 123})
        cls.random_user = StatsigUser("random")
        cls.logs = {}
        options = StatsigOptions(
            api=cls._api_override,
            tier=StatsigEnvironmentTier.development,
            idlists_sync_interval=0.01,
            rulesets_sync_interval=0.01,
            event_queue_size=400)

        statsig.initialize("secret-key", options)
        cls.initTime = round(time.time() * 1000)

    @patch('requests.post', side_effect=_network_stub.mock)
    @patch('requests.get', side_effect=_network_stub.mock)
    def test_checking_and_updating_concurrently(self, mock_post, mock_get):
        self.threads = []
        for x in range(10):
            thread = threading.Thread(
                target=self.run_checks, args=(0.01, 20))
            thread.start()
            self.threads.append(thread)

        for t in self.threads:
            t.join()

        self.assertEqual(200, len(statsig.get_instance()._logger._events))
        self.assertEqual(1600, self._event_count)
        statsig.shutdown()

        self.assertEqual(0, len(statsig.get_instance()._logger._events))
        self.assertEqual(1800, self._event_count)

    def run_checks(self, interval, times):
        for x in range(times):
            user = StatsigUser(
                f'user_id_{x}', email="testuser@statsig.com", private_attributes={"test": 123})
            statsig.log_event(StatsigEvent(
                user, "test_event", 1, {"key": "value"}))
            self.assertEqual(True, statsig.check_gate(
                user, "on_for_statsig_email"))
            self.assertEqual(True, statsig.check_gate(user, "always_on_gate"))
            self.assertTrue(statsig.check_gate(
                StatsigUser("regular_user_id"), "on_for_id_list"))

            statsig.log_event(StatsigEvent(
                user, "test_event_2", 1, {"key": "value"}))
            exp_param = statsig.get_experiment(
                user, "sample_experiment").get("experiment_param", "default")
            self.assertTrue(exp_param == "test" or exp_param == "control")

            statsig.log_event(StatsigEvent(
                user, "test_event_3", 1, {"key": "value"}))
            self.assertEqual(7, statsig.get_config(
                user, "test_config").get("number", 0))
            self.assertTrue(statsig.get_layer(
                user, "a_layer").get("layer_param", False))

            time.sleep(interval)


if __name__ == '__main__':
    unittest.main()
