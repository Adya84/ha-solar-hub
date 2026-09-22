"""Contract tests for Solar Hub scan payloads."""

import importlib.util
from pathlib import Path
import sys
import unittest


MODELS_PATH = Path(__file__).parents[1] / "custom_components" / "solar_hub" / "models.py"
MODELS_SPEC = importlib.util.spec_from_file_location("solar_hub_models", MODELS_PATH)
assert MODELS_SPEC and MODELS_SPEC.loader
MODELS = importlib.util.module_from_spec(MODELS_SPEC)
sys.modules[MODELS_SPEC.name] = MODELS
MODELS_SPEC.loader.exec_module(MODELS)
HardwareProfile = MODELS.HardwareProfile


class HardwareProfileTests(unittest.TestCase):
    def test_basic_profile_has_not_scanned_deep_state(self):
        profile = HardwareProfile(provider="test", manufacturer="Test")
        payload = profile.as_dict()
        self.assertEqual(payload["deep_scan"]["state"], "not_run")
        self.assertEqual(payload["deep_data"], {})
