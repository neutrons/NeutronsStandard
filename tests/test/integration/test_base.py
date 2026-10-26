from neutrons_standard.test.integration.test_base import IntegrationTest
from neutrons_standard.test.integration.test_summary import TestSummary


class TestIntegrationTest(IntegrationTest):
    def test_init(self):
        assert self.test_summary is None
        self.test_summary = TestSummary.builder().step("Initialize Step!").build()
        self.test_summary.success()
