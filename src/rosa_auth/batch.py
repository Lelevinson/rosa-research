"""Checkpoint boundaries for future batches; no experiment or retry policy."""
from contextlib import contextmanager


@contextmanager
def checkpointed_trial(backend, checkpoint):
    """Save progress even when ROSA catches an error, then stop unavailable runs.

    The caller owns the checkpoint schema, atomic write, counters and limits.
    A checkpoint must record interrupted/unknown outcomes as such, never success.
    No credentials, model responses or tool state are written by this helper.
    """
    try:
        backend.raise_if_unavailable()
        yield
    finally:
        checkpoint()
    # ROSA.invoke() may catch SafeError and return an ordinary string instead.
    backend.raise_if_unavailable()
