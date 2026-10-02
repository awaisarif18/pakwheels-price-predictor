"""Replace completed local files despite brief Windows sharing conflicts."""

import time
from pathlib import Path


def replace_file(temporary: Path, destination: Path) -> None:
    """Retry access/sharing denials six times, waiting at most 3.1 seconds.

    Never truncate the previous destination or retry unrelated filesystem errors.
    If the lock persists, raise the original error and leave the temporary file
    available for recovery. This retries local writes, never HTTP requests.
    """
    for attempt in range(6):
        try:
            temporary.replace(destination)
            return
        except OSError as exc:
            access_denied = isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {5, 32, 33}
            if not access_denied or attempt == 5:
                raise
            time.sleep(0.1 * 2 ** attempt)
