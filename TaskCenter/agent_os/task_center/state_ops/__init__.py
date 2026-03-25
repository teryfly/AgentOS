"""
State operations subpackage.

Provides metadata and runtime state update operations with CAS retry.
"""
from .state_ops import StateOps
from .retry_cas import retry_optimistic

__all__ = [
    "StateOps",
    "retry_optimistic"
]