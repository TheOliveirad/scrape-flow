"""
Retry policy with exponential backoff.

Provides a reusable RetryPolicy class that calculates delay times
using exponential backoff with optional jitter. Used by the scraping
engine to handle transient failures gracefully.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """
    Configurable retry strategy with exponential backoff.

    Parameters
    ----------
    max_attempts : int
        Total number of attempts (including the first try).
    backoff_factor : float
        Multiplier for exponential delay: delay = factor ^ attempt.
    max_delay : float
        Cap on the delay between retries (seconds).
    jitter : bool
        Add random jitter (0–25% of delay) to prevent thundering herd.
    """

    max_attempts: int = 3
    backoff_factor: float = 1.5
    max_delay: float = 60.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """
        Calculate the delay before the next retry.

        Parameters
        ----------
        attempt : int
            The current attempt number (1-indexed).

        Returns
        -------
        float
            Seconds to wait before retrying.
        """
        delay = min(self.backoff_factor ** attempt, self.max_delay)
        if self.jitter:
            delay += random.uniform(0, delay * 0.25)
        return round(delay, 3)

    def should_retry(self, attempt: int) -> bool:
        """Return True if we haven't exhausted all attempts."""
        return attempt < self.max_attempts
