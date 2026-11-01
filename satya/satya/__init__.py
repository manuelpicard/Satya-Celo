"""Satya - Layer 2 of the Satya stack: verifiable content provenance.

Satya never guesses whether content is AI-generated. It returns a definitive verdict
only when an accountable party has made a cryptographically verifiable statement.
"""

from .engine import Config, Satya, __version__
from .model import Direction, Evidence, Result, Tier, Verdict

__all__ = ["Config", "Satya", "Evidence", "Result", "Tier", "Direction", "Verdict", "__version__"]
