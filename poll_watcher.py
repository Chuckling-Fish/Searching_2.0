import threading
import time

from scanner import scan_folder


def watch_folder(folder, interval=5, verbose=False):
    """
    Dependency-free replacement for the `watchdog` library.

    `watchdog` wraps OS-level file-event APIs (inotify on Linux,
    ReadDirectoryChangesW on Windows, FSEvents on macOS) to react to
    changes instantly. This does the much simpler thing instead:
    re-run the existing scan_folder() on a timer, in a background
    thread.

    Why this is good enough: scan_folder()'s change detection already
    makes an unchanged file cost almost nothing (one stat() + a dict
    lookup, no read/hash/extract), so polling an unchanged folder
    every `interval` seconds is cheap.

    The real trade-off: a change is detected up to `interval` seconds
    late instead of instantly, and every poll still walks the entire
    folder tree (one stat() per file) even when nothing changed - for
    a folder with tens of thousands of files, that walk itself has a
    real cost, so `interval` should grow with folder size.
    """

    stop_event = threading.Event()

    def _loop():
        while not stop_event.is_set():
            scan_folder(folder, verbose=verbose)
            stop_event.wait(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()

    return stop_event  # call .set() to stop watching


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else input("Folder to watch: ")
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 5

    stop = watch_folder(target, interval=interval, verbose=True)

    print(f"Watching '{target}' every {interval}s (Ctrl+C to stop)...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()
        print("Stopped.")
