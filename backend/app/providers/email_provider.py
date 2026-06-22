from __future__ import annotations

import random


class EmailProvider:
    def __init__(
        self,
        *,
        simulation_enabled: bool,
        failure_rate: float,
    ) -> None:
        self.simulation_enabled = simulation_enabled
        self.failure_rate = failure_rate

    def send_email(self, *, recipient: str, subject: str, body: str) -> None:
        if not self.simulation_enabled:
            # Phase 1: do nothing (but don't fail).
            return

        if random.random() < self.failure_rate:
            raise Exception("Provider failure")

        # Simulated success: no-op.
        return


