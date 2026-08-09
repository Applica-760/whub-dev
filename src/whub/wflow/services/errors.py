"""Compatibility exports for Flow errors."""

from whub.services.flow.errors import Diagnostic, FlowError

WflowError = FlowError

__all__ = ["Diagnostic", "WflowError"]
