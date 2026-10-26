import pytest

from neutrons_standard.test.integration.test_summary import TestSummary


@pytest.mark.integration
class IntegrationTest:
    @pytest.fixture(scope="function", autouse=True)  # noqa: PT003
    def _setup(self):
        self.test_summary = None

        import faulthandler

        faulthandler.enable()

        yield

        faulthandler.disable()

        if self.test_summary is None:
            raise RuntimeError(
                "Integration test failed to initialize self.test_summary.  "
                "Every integration test must build its own TestSummary object."
            )

        if isinstance(self.test_summary, TestSummary):
            if not self.test_summary.is_complete():
                self.test_summary.failure()
            if self.test_summary.is_failure():
                pytest.fail(f"Test Summary (-vv for full table): {self.test_summary}")
