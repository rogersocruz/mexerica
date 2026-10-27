"""Motor de conversão, independente de GTK (testável e reutilizável)."""
from .formats import kind_of
from .ops import ACTIONS, BY_ID, CONVERT, TOOLS, Op, options_for
from .runner import Result, run

__all__ = ["kind_of", "options_for", "run", "Result", "Op", "BY_ID",
           "CONVERT", "TOOLS", "ACTIONS"]
