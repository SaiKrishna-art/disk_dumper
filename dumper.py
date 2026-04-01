"""
dumper.py – Core disk dumping engine.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

Reads raw sectors from a disk/partition and writes them to an image file
with progress tracking, error handling, and pause/resume support.
"""

import json
import os
import sys
import time
import threading

import win32file
from tqdm import tqdm

from disk_utils import open_disk_handle, get_disk_size, close_handle


# ─── State file helpers ───────────────────────────────────────────────────────

def _state_path(output_path: str) -> str:
    """Return path to the .state JSON file for a given output image."""
    return output_path + ".state"


def _save_state(output_path: str, offset: int, total_size: int, source_path: str,
                sector_size: int, error_log: list):
    """Persist current dump state so it can be resumed later."""
    state = {
        "source": source_path,
        "output": output_path,
        "offset": offset,
        "total_size": total_size,
        "sector_size": sector_size,
        "errors": error_log[-500:],  # keep last 500 errors max
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(_state_path(output_path), "w") as f:
        json.dump(state, f, indent=2)


def _load_state(output_path: str) -> dict | None:
    """Load saved dump state, or return None if none exists."""
    sp = _state_path(output_path)
    if not os.path.isfile(sp):
        return None
    try:
        with open(sp, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _clear_state(output_path: str):
    """Remove the state file after a completed dump."""
    sp = _state_path(output_path)
    if os.path.isfile(sp):
        os.remove(sp)


# ─── DiskDumper class ─────────────────────────────────────────────────────────

class DiskDumper:
    """
    Bit-to-bit disk dumper.

    Reads raw sectors from a source device and writes them sequentially
    to an output image file.

    Features:
        • Progress bar with speed and ETA
        • Bad-sector error handling (zero-fill + log)
        • Pause / resume via Ctrl+C interactive menu
        • Save state & resume across sessions
    """

    DEFAULT_SECTOR_SIZE = 4096  # 4 KB – also works for 512-byte sector disks

    def __init__(
        self,
        source_path: str,
        output_path: str,
        sector_size: int = DEFAULT_SECTOR_SIZE,
    ):
        self.source_path = source_path
        self.output_path = output_path
        self.sector_size = sector_size

        # runtime state
        self.total_size: int = 0
        self.offset: int = 0
        self.error_log: list[dict] = []
        self.errors_count: int = 0

        # control
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused
        self._stop = False

    # ── Public API ────────────────────────────────────────────────────────

    def start(self, resume: bool = False) -> bool:
        """
        Run the dump.

        Args:
            resume: If True, attempt to resume from a saved state.

        Returns:
            True if dump completed, False if aborted.
        """
        handle = None
        out_file = None
        try:
            # Open source device
            print(f"\n  Opening source: {self.source_path}")
            handle = open_disk_handle(self.source_path)
            self.total_size = get_disk_size(handle)
            print(f"  Total size: {self._hr(self.total_size)}")

            # Handle resume
            if resume:
                state = _load_state(self.output_path)
                if state and state.get("source") == self.source_path:
                    self.offset = state["offset"]
                    self.sector_size = state.get("sector_size", self.sector_size)
                    self.error_log = state.get("errors", [])
                    self.errors_count = len(self.error_log)
                    print(f"  Resuming from offset {self._hr(self.offset)} "
                          f"({self._pct(self.offset)}%)")
                else:
                    print("  No compatible state file found. Starting fresh.")
                    self.offset = 0

            # Seek source handle
            if self.offset > 0:
                win32file.SetFilePointer(handle, self.offset, win32file.FILE_BEGIN)

            # Open output file
            mode = "r+b" if (resume and os.path.isfile(self.output_path)) else "wb"
            out_file = open(self.output_path, mode)
            if self.offset > 0 and mode == "r+b":
                out_file.seek(self.offset)

            # Run the copy loop
            completed = self._copy_loop(handle, out_file)

            if completed:
                _clear_state(self.output_path)
                print(f"\n  ✅ Dump complete: {self.output_path}")
                print(f"     Total written: {self._hr(self.offset)}")
                if self.errors_count > 0:
                    print(f"     ⚠  Sectors with read errors: {self.errors_count}")
                return True
            else:
                # User chose to save & quit
                _save_state(
                    self.output_path, self.offset, self.total_size,
                    self.source_path, self.sector_size, self.error_log,
                )
                print(f"\n  💾 State saved. You can resume this dump later.")
                print(f"     Progress: {self._hr(self.offset)} / "
                      f"{self._hr(self.total_size)} ({self._pct(self.offset)}%)")
                return False

        except PermissionError as e:
            print(f"\n  ❌ {e}")
            return False
        except Exception as e:
            print(f"\n  ❌ Unexpected error: {e}")
            # Try to save state
            try:
                _save_state(
                    self.output_path, self.offset, self.total_size,
                    self.source_path, self.sector_size, self.error_log,
                )
                print(f"  💾 State saved at offset {self._hr(self.offset)}.")
            except Exception:
                pass
            return False
        finally:
            if out_file:
                out_file.close()
            if handle:
                close_handle(handle)

    # ── Core Copy Loop ────────────────────────────────────────────────────

    def _copy_loop(self, handle, out_file) -> bool:
        """
        Sequential sector read/write with progress bar.

        Returns True if completed, False if user aborted (save & quit).
        """
        remaining = self.total_size - self.offset
        zero_block = b"\x00" * self.sector_size

        with tqdm(
            initial=self.offset,
            total=self.total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc="  Dumping",
            bar_format="  {l_bar}{bar:35}{r_bar}",
            colour="green",
            miniters=1,
        ) as pbar:
            while self.offset < self.total_size:
                # Pause check
                if not self._pause_event.is_set():
                    action = self._pause_menu()
                    if action == "abort":
                        self._stop = True
                        return False
                    elif action == "save_quit":
                        return False
                    # else "resume" → continue

                if self._stop:
                    return False

                # Calculate read size (last chunk may be smaller)
                read_size = min(self.sector_size, self.total_size - self.offset)

                # Read sector
                try:
                    hr, data = win32file.ReadFile(handle, read_size)
                    if len(data) == 0:
                        # End of device
                        break
                    # Pad last block if needed (for sector alignment)
                    if len(data) < read_size:
                        data = data + b"\x00" * (read_size - len(data))
                except Exception as e:
                    # Bad sector – log error, write zeros
                    self.errors_count += 1
                    err_entry = {
                        "offset": self.offset,
                        "size": read_size,
                        "error": str(e),
                        "time": time.strftime("%H:%M:%S"),
                    }
                    self.error_log.append(err_entry)
                    data = zero_block[:read_size]

                    # Show error inline (without breaking progress bar)
                    pbar.write(
                        f"  ⚠  Read error at offset {self.offset:#x}: {e}"
                    )

                    # Try to seek past the bad sector
                    try:
                        win32file.SetFilePointer(
                            handle,
                            self.offset + read_size,
                            win32file.FILE_BEGIN,
                        )
                    except Exception:
                        pass

                # Write to output
                out_file.write(data)

                self.offset += len(data)
                pbar.update(len(data))

        return True

    # ── Pause Menu ────────────────────────────────────────────────────────

    def trigger_pause(self):
        """Called externally (e.g. from a signal handler) to pause the dump."""
        self._pause_event.clear()

    def _pause_menu(self) -> str:
        """Show interactive pause menu. Returns 'resume', 'save_quit', or 'abort'."""
        print("\n")
        print("  ╔══════════════════════════════════════╗")
        print("  ║        ⏸  DUMP PAUSED                ║")
        print("  ╠══════════════════════════════════════╣")
        print(f"  ║  Progress: {self._pct(self.offset):>5}%                    ║")
        print(f"  ║  Copied:   {self._hr(self.offset):>12}             ║")
        print(f"  ║  Errors:   {self.errors_count:>5}                    ║")
        print("  ╠══════════════════════════════════════╣")
        print("  ║  [1] Resume                          ║")
        print("  ║  [2] Save & Quit (resume later)      ║")
        print("  ║  [3] Abort (discard progress)        ║")
        print("  ╚══════════════════════════════════════╝")

        while True:
            try:
                choice = input("\n  Enter choice (1/2/3): ").strip()
            except (EOFError, KeyboardInterrupt):
                choice = "2"

            if choice == "1":
                self._pause_event.set()
                print("  ▶  Resuming…\n")
                return "resume"
            elif choice == "2":
                return "save_quit"
            elif choice == "3":
                confirm = input("  Are you sure? This discards progress. (y/N): ").strip().lower()
                if confirm == "y":
                    return "abort"
            else:
                print("  Invalid choice. Try again.")

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _hr(size_bytes: int) -> str:
        """Human-readable size."""
        if size_bytes <= 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}"

    def _pct(self, offset: int) -> str:
        """Percentage of offset relative to total_size."""
        if self.total_size <= 0:
            return "0.0"
        return f"{(offset / self.total_size) * 100:.1f}"


# ─── Convenience Function ─────────────────────────────────────────────────────

def check_resume_available(output_path: str) -> dict | None:
    """
    Check if a resumable state exists for the given output path.

    Returns the state dict or None.
    """
    return _load_state(output_path)
