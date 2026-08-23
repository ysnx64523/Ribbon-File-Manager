"""Small helpers to run blocking I/O off the GTK main loop.

All file system work (directory enumeration, copy, delete, trash...) can block
for a long time on large directories or slow network mounts. We run it on a
bounded worker pool and marshal the result back onto the GTK main loop with
:func:`GLib.idle_add`, so the UI never freezes.
"""

from __future__ import annotations

import concurrent.futures
import functools
from typing import Any, Callable, Optional

from gi.repository import GLib

_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="ribbonfm")


def call_async(
    fn: Callable[..., Any],
    args: tuple = (),
    kwargs: Optional[dict] = None,
    on_done: Optional[Callable[..., Any]] = None,
    on_error: Optional[Callable[[BaseException], Any]] = None,
) -> concurrent.futures.Future:
    """Run ``fn`` on a worker thread and call ``on_done(result)`` on the main
    thread when it completes.

    ``on_error`` is invoked with the exception (still on the main thread). An
    unhandled error is logged rather than crashing the UI.
    """
    kwargs = kwargs or {}

    def _run() -> Any:
        # The default GLib.MainContext is only the main thread's; we always
        # marshal back there.
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - surfaced to on_error
            if on_error is not None:
                GLib.idle_add(on_error, exc)
            else:
                _log_error(exc)
            # Re-raise in the worker so the future reports it; idempotent.
            raise
        else:
            if on_done is not None:
                GLib.idle_add(on_done, result)
            return result

    return _POOL.submit(_run)


def _log_error(exc: BaseException) -> None:
    try:
        from gi.repository import GObject

        GObject.log(
            __name__,
            GObject.LogLevelFlags.WARNING,
            "async operation failed: %s" % exc,
        )
    except Exception:  # pragma: no cover - logging must never throw
        import logging

        logging.getLogger(__name__).warning("async operation failed: %s", exc)


def call_async_chain(
    step: Callable[..., Any],
    then: Callable[[Any], None],
    *,
    error: Optional[Callable[[BaseException], None]] = None,
) -> Callable[[], None]:
    """Chain a blocking ``step`` into a synchronous ``then`` callback.

    Useful for file operations that need a slow prepare phase or progress
    handling followed by UI refresh.
    """
    return lambda: call_async(step, on_done=then, on_error=error)


# Re-exported for convenience.
idle_add = GLib.idle_add

