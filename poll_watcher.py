import threading
import time

from scanner import scan_folder

def watch_folder(folder, interval=5, verbose=False):
    # Signal used to stop the watcher
    stop_event = threading.Event()
    def _loop():
        while not stop_event.is_set():
            scan_folder(folder, verbose=verbose)
            stop_event.wait(interval)

    # Run scanning in the background
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return stop_event 


if __name__ == "__main__":
    import sys
    # Get folder and scan interval from arguments
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