from enum import StrEnum


class TestSummary:
    def __init__(self):
        self._index = 0
        self._steps = []

    def success(self):
        step = self._steps[self._index]
        step.status = self.TestStep.StepStatus.SUCCESS
        self._index += 1

    def failure(self):
        step = self._steps[self._index]
        step.status = self.TestStep.StepStatus.FAILURE
        self._index += 1

    def skipped(self):
        step = self._steps[self._index]
        step.status = self.TestStep.StepStatus.SKIPPED
        self._index += 1

    def is_complete(self):
        return self._index == len(self._steps)

    def is_failure(self):
        return any(step.status == self.TestStep.StepStatus.FAILURE for step in self._steps)

    def builder():
        return TestSummary.TestSummaryBuilder()

    def __str__(self):
        longest_status = max(len(step.status) for step in self._steps)
        longest_name = max(len(step.name) for step in self._steps)
        table_cap_str = "#" * (longest_name + longest_status + 6)
        table_str = (
            f"\n{table_cap_str}\n"
            + "\n".join(f"# {step.name:{longest_name}}: {step.status:{longest_status}} #" for step in self._steps)
            + f"\n{table_cap_str}\n"
        )
        return table_str

    class TestStep:
        class StepStatus(StrEnum):
            SUCCESS = "SUCCESS"
            FAILURE = "FAILURE"
            INCOMPLETE = "INCOMPLETE"
            SKIPPED = "SKIPPED"

        def __init__(self, name: str):
            self.name = name
            self.status = self.StepStatus.INCOMPLETE

    class TestSummaryBuilder:
        def __init__(self):
            self.summary = TestSummary()

        def step(self, name: str):
            self.summary._steps.append(TestSummary.TestStep(name))
            return self

        def build(self):
            return self.summary
