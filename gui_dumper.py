"""
gui_dumper.py – Threaded dump engine adapter for the GUI.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

Wraps the core DiskDumper logic to run in a background thread and
communicate progress/state changes back to the GUI via callbacks.
"""

import json
import os
import time
import threading

import win32file

from disk_utils import open_disk_handle, get_disk_size, close_handle


class GUIDumper:
    """
    Threaded disk dumper for GUI integration.

    Callbacks:
        on_progress(offset, total, speed, eta_seconds, errors)
        on_error(offset, error_msg)
        on_complete(success, message)
        on_state_change(state)  – 'idle', 'running', 'paused', 'hashing', 'done'
    """

    def __init__(self):
        self.source_path: str = ""
        self.output_path: str = ""
        self.sector_size: int = 4096
        self.total_size: int = 0
        self.offset: int = 0
        self.errors_count: int = 0
        self.error_log: list[dict] = []

        # Callbacks
        self.on_progress = None
        self.on_error = None
        self.on_complete = None
        self.on_state_change = None

        # Thread control
        self._thread: threading.Thread | None = None
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_flag = False
        self._state = "idle"

    @property
    def state(self):
        return self._state

    def _set_state(self, state: str):
        self._state = state
        if self.on_state_change:
            self.on_state_change(state)

    # ── State Persistence ─────────────────────────────────────────────────

    def _state_path(self) -> str:
        return self.output_path + ".state"

    def _save_state(self):
        state = {
            "source": self.source_path,
            "output": self.output_path,
            "offset": self.offset,
            "total_size": self.total_size,
            "sector_size": self.sector_size,
            "errors": self.error_log[-500:],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            with open(self._state_path(), "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _load_state(self) -> dict | None:
        sp = self._state_path()
        if not os.path.isfile(sp):
            return None
        try:
            with open(sp, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def _clear_state(self):
        sp = self._state_path()
        if os.path.isfile(sp):
            try:
                os.remove(sp)
            except Exception:
                pass

    @staticmethod
    def check_resume(output_path: str) -> dict | None:
        """Check if a resume state exists for the given output path."""
        sp = output_path + ".state"
        if not os.path.isfile(sp):
            return None
        try:
            with open(sp, "r") as f:
                return json.load(f)
        except Exception:
            return None

    # ── Control ───────────────────────────────────────────────────────────

    def start(self, source_path: str, output_path: str,
              sector_size: int = 4096, resume: bool = False):
        """Start the dump in a background thread."""
        if self._thread and self._thread.is_alive():
            return

        self.source_path = source_path
        self.output_path = output_path
        self.sector_size = sector_size
        self.offset = 0
        self.errors_count = 0
        self.error_log = []
        self._stop_flag = False
        self._pause_event.set()

        self._thread = threading.Thread(
            target=self._run, args=(resume,), daemon=True
        )
        self._thread.start()

    def pause(self):
        """Pause the dump."""
        self._pause_event.clear()
        self._set_state("paused")

    def resume(self):
        """Resume the dump."""
        self._pause_event.set()
        self._set_state("running")

    def stop(self):
        """Stop the dump and save state."""
        self._stop_flag = True
        self._pause_event.set()  # unblock if paused

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Core Thread ───────────────────────────────────────────────────────

    def _run(self, resume: bool):
        """Main dump thread."""
        handle = None
        out_file = None
        try:
            self._set_state("running")

            # Open device
            handle = open_disk_handle(self.source_path)
            self.total_size = get_disk_size(handle)

            # Resume handling
            if resume:
                state = self._load_state()
                if state and state.get("source") == self.source_path:
                    self.offset = state["offset"]
                    self.sector_size = state.get("sector_size", self.sector_size)
                    self.error_log = state.get("errors", [])
                    self.errors_count = len(self.error_log)

            # Seek if resuming
            if self.offset > 0:
                win32file.SetFilePointer(handle, self.offset, win32file.FILE_BEGIN)

            # Open output file
            mode = "r+b" if (resume and os.path.isfile(self.output_path)) else "wb"
            out_file = open(self.output_path, mode)
            if self.offset > 0 and mode == "r+b":
                out_file.seek(self.offset)

            # Copy loop
            zero_block = b"\x00" * self.sector_size
            last_time = time.time()
            last_offset = self.offset
            speed = 0.0

            while self.offset < self.total_size:
                # Check stop
                if self._stop_flag:
                    self._save_state()
                    self._set_state("idle")
                    if self.on_complete:
                        self.on_complete(False, "Stopped. State saved for resume.")
                    return

                # Check pause
                self._pause_event.wait()

                # Read size
                read_size = min(self.sector_size, self.total_size - self.offset)

                # Read sector
                try:
                    hr, data = win32file.ReadFile(handle, read_size)
                    if len(data) == 0:
                        break
                    if len(data) < read_size:
                        data = data + b"\x00" * (read_size - len(data))
                except Exception as e:
                    self.errors_count += 1
                    err_entry = {
                        "offset": self.offset,
                        "size": read_size,
                        "error": str(e),
                        "time": time.strftime("%H:%M:%S"),
                    }
                    self.error_log.append(err_entry)
                    data = zero_block[:read_size]

                    if self.on_error:
                        self.on_error(self.offset, str(e))

                    try:
                        win32file.SetFilePointer(
                            handle, self.offset + read_size, win32file.FILE_BEGIN
                        )
                    except Exception:
                        pass

                # Write
                out_file.write(data)
                self.offset += len(data)

                # Speed calculation (every 0.5s)
                now = time.time()
                elapsed = now - last_time
                if elapsed >= 0.5:
                    bytes_done = self.offset - last_offset
                    speed = bytes_done / elapsed
                    last_time = now
                    last_offset = self.offset

                    # ETA
                    remaining = self.total_size - self.offset
                    eta = remaining / speed if speed > 0 else 0

                    if self.on_progress:
                        self.on_progress(
                            self.offset, self.total_size,
                            speed, eta, self.errors_count
                        )

            # Done
            self._clear_state()
            self._set_state("done")
            if self.on_complete:
                self.on_complete(True, f"Dump complete! ({self.errors_count} errors)")

        except PermissionError as e:
            self._set_state("idle")
            if self.on_complete:
                self.on_complete(False, f"Access denied: {e}")
        except Exception as e:
            self._save_state()
            self._set_state("idle")
            if self.on_complete:
                self.on_complete(False, f"Error: {e}")
        finally:
            if out_file:
                out_file.close()
            if handle:
                close_handle(handle)
