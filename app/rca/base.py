"""Explainable deterministic RCA port interface definition."""

from typing import Protocol

from app.models.incident import Incident
from app.models.rca import RCAResult


class RCAEnginePort(Protocol):
    """Hexagonal Port: Deterministic root cause analysis rule evaluator."""

    def evaluate_incident(self, incident: Incident) -> RCAResult:
        """Evaluate deterministic rules against parsed diagnostic report."""
        ...
