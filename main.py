"""
main.py – CLI entry point for Disk Dumper.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

Interactive menus for selecting a source device, starting a dump,
pausing/resuming, and running hash verification.
"""

import os
import sys
import signal

from disk_utils import is_admin, list_physical_disks, list_logical_drives
from dumper import DiskDumper, check_resume_available
from hasher import compute_hash, SUPPORTED_ALGORITHMS
from copyright_guard import enforce_copyright, AUTHOR, COPYRIGHT_NOTICE


# ─── ANSI Colors ──────────────────────────────────────────────────────────────

class C:
    """ANSI color codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"


# ─── Banner ───────────────────────────────────────────────────────────────────

BANNER = f"""
{C.CYAN}{C.BOLD}
  ╔════════════════════════════════════════════════════════╗
  ║                                                        ║
  ║     ██████╗ ██╗███████╗██╗  ██╗                        ║
  ║     ██╔══██╗██║██╔════╝██║ ██╔╝                        ║
  ║     ██║  ██║██║███████╗█████╔╝                         ║
  ║     ██║  ██║██║╚════██║██╔═██╗                         ║
  ║     ██████╔╝██║███████║██║  ██╗                        ║
  ║     ╚═════╝ ╚═╝╚══════╝╚═╝  ╚═╝                       ║
  ║     ██████╗ ██╗   ██╗███╗   ███╗██████╗ ███████╗██████╗ ║
  ║     ██╔══██╗██║   ██║████╗ ████║██╔══██╗██╔════╝██╔══██╗║
  ║     ██║  ██║██║   ██║██╔████╔██║██████╔╝█████╗  ██████╔╝║
  ║     ██║  ██║██║   ██║██║╚██╔╝██║██╔═══╝ ██╔══╝  ██╔══██╗║
  ║     ██████╔╝╚██████╔╝██║ ╚═╝ ██║██║     ███████╗██║  ██║║
  ║     ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝║
  ║                                                        ║
  ║     Bit-to-Bit Storage Extractor          v1.0         ║
  ║                                                        ║
  ║     © Murthy Sai Krishna. All rights reserved.         ║
  ║                                                        ║
  ╚════════════════════════════════════════════════════════╝
{C.RESET}"""


# ─── Utility ──────────────────────────────────────────────────────────────────

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def prompt(text: str, default: str = "") -> str:
    """Prompt user for input with an optional default."""
    if default:
        val = input(f"  {text} [{default}]: ").strip()
        return val if val else default
    return input(f"  {text}: ").strip()


def press_enter():
    input(f"\n  {C.DIM}Press Enter to continue…{C.RESET}")


# ─── Device Selection ────────────────────────────────────────────────────────

def select_source() -> tuple[str, str]:
    """
    Interactive device selection menu.

    Returns:
        (device_path, description)  e.g. ("\\\\.\\PhysicalDrive1", "Disk 1 – SanDisk Ultra")
    """
    print(f"\n  {C.BOLD}{C.CYAN}═══ Select Source Device ═══{C.RESET}\n")

    # Gather devices
    print(f"  {C.DIM}Scanning devices…{C.RESET}")
    physical = list_physical_disks()
    logical = list_logical_drives()

    options: list[tuple[str, str]] = []  # (path, description)

    # Physical disks
    if physical:
        print(f"\n  {C.BOLD}{C.YELLOW}Physical Disks:{C.RESET}")
        for d in physical:
            idx = len(options) + 1
            desc = f"Disk {d['index']} – {d['model']} ({d['size_hr']}, {d['media_type']})"
            print(f"    {C.GREEN}{idx:>3}.{C.RESET} {desc}")
            options.append((d["path"], desc))

    # Logical drives
    if logical:
        print(f"\n  {C.BOLD}{C.YELLOW}Logical Drives:{C.RESET}")
        for d in logical:
            idx = len(options) + 1
            label = f" [{d['label']}]" if d['label'] else ""
            desc = (
                f"{d['letter']}: drive{label} "
                f"({d['size_hr']}, {d['file_system']}, {d['drive_type']})"
            )
            print(f"    {C.GREEN}{idx:>3}.{C.RESET} {desc}")
            options.append((d["path"], desc))

    if not options:
        print(f"\n  {C.RED}No devices found.{C.RESET}")
        sys.exit(1)

    # User selection
    while True:
        try:
            choice = int(prompt(f"\n  Enter choice (1–{len(options)})"))
            if 1 <= choice <= len(options):
                path, desc = options[choice - 1]
                print(f"\n  {C.GREEN}✓ Selected:{C.RESET} {desc}")
                return path, desc
            print(f"  {C.RED}Invalid choice.{C.RESET}")
        except ValueError:
            print(f"  {C.RED}Please enter a number.{C.RESET}")
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {C.YELLOW}Cancelled.{C.RESET}")
            sys.exit(0)


def get_output_path() -> str:
    """Prompt for output file path with extension validation."""
    valid_extensions = (".img", ".raw", ".dd")
    while True:
        path = prompt(
            f"Output file path (e.g. usb_dump.img)",
            default="disk_dump.img",
        )
        # Add default extension if missing
        _, ext = os.path.splitext(path)
        if not ext:
            path += ".img"
            ext = ".img"

        if ext.lower() not in valid_extensions:
            print(f"  {C.YELLOW}Tip: Common extensions are "
                  f"{', '.join(valid_extensions)}. Using '{ext}' anyway.{C.RESET}")

        # Check if file exists
        if os.path.isfile(path):
            overwrite = prompt(
                f"{C.YELLOW}File exists. Overwrite? (y/N){C.RESET}"
            ).lower()
            if overwrite != "y":
                continue

        # Ensure parent directory exists
        parent = os.path.dirname(path)
        if parent and not os.path.isdir(parent):
            try:
                os.makedirs(parent, exist_ok=True)
            except OSError as e:
                print(f"  {C.RED}Cannot create directory: {e}{C.RESET}")
                continue

        return path


def get_sector_size() -> int:
    """Prompt for sector/block size."""
    val = prompt("Sector size in bytes", default="4096")
    try:
        size = int(val)
        if size < 512 or size % 512 != 0:
            print(f"  {C.YELLOW}Using 4096 (must be multiple of 512).{C.RESET}")
            return 4096
        return size
    except ValueError:
        print(f"  {C.YELLOW}Invalid. Using default 4096.{C.RESET}")
        return 4096


# ─── Main Menu ────────────────────────────────────────────────────────────────

def main_menu():
    """Show the main menu and handle user choices."""
    while True:
        clear_screen()
        print(BANNER)
        print(f"  {C.BOLD}{C.WHITE}Main Menu{C.RESET}")
        print(f"  {'─' * 40}")
        print(f"    {C.GREEN}1.{C.RESET} Start New Dump")
        print(f"    {C.GREEN}2.{C.RESET} Resume Previous Dump")
        print(f"    {C.GREEN}3.{C.RESET} Verify Image Hash")
        print(f"    {C.GREEN}4.{C.RESET} List Devices")
        print(f"    {C.GREEN}0.{C.RESET} Exit")
        print()

        try:
            choice = prompt("Enter choice")
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        if choice == "1":
            start_new_dump()
        elif choice == "2":
            resume_dump()
        elif choice == "3":
            verify_hash_menu()
        elif choice == "4":
            show_devices()
        elif choice == "0":
            print(f"\n  {C.CYAN}Goodbye!{C.RESET}\n")
            sys.exit(0)
        else:
            print(f"  {C.RED}Invalid choice.{C.RESET}")
            press_enter()


# ─── Actions ──────────────────────────────────────────────────────────────────

def start_new_dump():
    """Interactive flow for a new dump."""
    clear_screen()
    print(BANNER)

    # 1. Select source
    source_path, source_desc = select_source()

    # 2. Output path
    print()
    output_path = get_output_path()

    # 3. Sector size
    sector_size = get_sector_size()

    # 4. Confirm
    print(f"\n  {C.BOLD}═══ Dump Configuration ═══{C.RESET}")
    print(f"    Source:      {source_desc}")
    print(f"    Output:      {output_path}")
    print(f"    Sector size: {sector_size} bytes")
    print()

    confirm = prompt(f"  {C.YELLOW}Start dump? (Y/n){C.RESET}").lower()
    if confirm == "n":
        print(f"  {C.YELLOW}Cancelled.{C.RESET}")
        press_enter()
        return

    # 5. Run dump
    dumper = DiskDumper(source_path, output_path, sector_size)

    # Set up Ctrl+C handler
    original_handler = signal.getsignal(signal.SIGINT)

    def on_interrupt(sig, frame):
        print(f"\n  {C.YELLOW}⏸  Pausing…{C.RESET}")
        dumper.trigger_pause()

    signal.signal(signal.SIGINT, on_interrupt)

    completed = dumper.start(resume=False)

    # Restore
    signal.signal(signal.SIGINT, original_handler)

    # 6. Post-dump
    if completed:
        print()
        do_hash = prompt(
            f"{C.CYAN}Compute hash of the image? (Y/n){C.RESET}"
        ).lower()
        if do_hash != "n":
            algo = prompt(
                f"Algorithm (md5/sha256)", default="sha256"
            ).lower()
            if algo not in SUPPORTED_ALGORITHMS:
                algo = "sha256"
            digest = compute_hash(output_path, algo)
            print(f"\n  {C.GREEN}{algo.upper()}: {digest}{C.RESET}")

    press_enter()


def resume_dump():
    """Resume a previously interrupted dump."""
    clear_screen()
    print(BANNER)
    print(f"\n  {C.BOLD}{C.CYAN}═══ Resume Dump ═══{C.RESET}\n")

    output_path = prompt("Path to the .img file to resume")
    if not output_path:
        return

    state = check_resume_available(output_path)
    if not state:
        print(f"\n  {C.RED}No resume state found for: {output_path}{C.RESET}")
        print(f"  {C.DIM}(Looking for: {output_path}.state){C.RESET}")
        press_enter()
        return

    from disk_utils import _human_readable_size

    print(f"  {C.GREEN}Found saved state:{C.RESET}")
    print(f"    Source:   {state['source']}")
    print(f"    Progress: {_human_readable_size(state['offset'])} / "
          f"{_human_readable_size(state['total_size'])}")
    print(f"    Saved at: {state.get('timestamp', 'unknown')}")
    print()

    confirm = prompt(f"{C.YELLOW}Resume this dump? (Y/n){C.RESET}").lower()
    if confirm == "n":
        return

    dumper = DiskDumper(
        state["source"],
        output_path,
        state.get("sector_size", 4096),
    )

    original_handler = signal.getsignal(signal.SIGINT)

    def on_interrupt(sig, frame):
        print(f"\n  {C.YELLOW}⏸  Pausing…{C.RESET}")
        dumper.trigger_pause()

    signal.signal(signal.SIGINT, on_interrupt)
    completed = dumper.start(resume=True)
    signal.signal(signal.SIGINT, original_handler)

    if completed:
        print()
        do_hash = prompt(
            f"{C.CYAN}Compute hash of the image? (Y/n){C.RESET}"
        ).lower()
        if do_hash != "n":
            algo = prompt("Algorithm (md5/sha256)", default="sha256").lower()
            if algo not in SUPPORTED_ALGORITHMS:
                algo = "sha256"
            digest = compute_hash(output_path, algo)
            print(f"\n  {C.GREEN}{algo.upper()}: {digest}{C.RESET}")

    press_enter()


def verify_hash_menu():
    """Standalone hash verification."""
    clear_screen()
    print(BANNER)
    print(f"\n  {C.BOLD}{C.CYAN}═══ Hash Verification ═══{C.RESET}\n")

    file_path = prompt("Path to image file")
    if not file_path or not os.path.isfile(file_path):
        print(f"  {C.RED}File not found.{C.RESET}")
        press_enter()
        return

    algo = prompt("Algorithm (md5/sha256)", default="sha256").lower()
    if algo not in SUPPORTED_ALGORITHMS:
        algo = "sha256"

    digest = compute_hash(file_path, algo)
    print(f"\n  {C.GREEN}{C.BOLD}{algo.upper()}: {digest}{C.RESET}")

    # Optional: compare
    expected = prompt(f"\n  Paste expected hash to compare (or Enter to skip)")
    if expected:
        if expected.lower().strip() == digest.lower():
            print(f"  {C.GREEN}✅ Hashes MATCH!{C.RESET}")
        else:
            print(f"  {C.RED}❌ Hashes DO NOT match!{C.RESET}")

    press_enter()


def show_devices():
    """List all detected devices."""
    clear_screen()
    print(BANNER)
    print(f"\n  {C.BOLD}{C.CYAN}═══ Detected Devices ═══{C.RESET}\n")

    print(f"  {C.DIM}Scanning…{C.RESET}\n")
    physical = list_physical_disks()
    logical = list_logical_drives()

    if physical:
        print(f"  {C.BOLD}{C.YELLOW}Physical Disks:{C.RESET}")
        print(f"  {'─' * 60}")
        for d in physical:
            print(f"    Drive {d['index']:>2} │ {d['model']:<35} │ {d['size_hr']:>10}")
            print(f"    {'':>8} │ Path: {d['path']}")
            print(f"    {'':>8} │ Type: {d['media_type']}")
            print(f"    {'─' * 58}")

    if logical:
        print(f"\n  {C.BOLD}{C.YELLOW}Logical Drives:{C.RESET}")
        print(f"  {'─' * 60}")
        for d in logical:
            label = f" [{d['label']}]" if d["label"] else ""
            print(f"    {d['letter']}:{label:<20} │ {d['file_system']:<6} │ "
                  f"{d['size_hr']:>10} │ {d['drive_type']}")
        print(f"  {'─' * 60}")

    press_enter()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    """Application entry point."""
    # Enable ANSI colors on Windows
    if os.name == "nt":
        os.system("")  # trick to enable VT100 processing

    # Copyright integrity check – DO NOT REMOVE
    enforce_copyright(is_gui=False)

    # Admin check
    if not is_admin():
        print(f"\n  {C.RED}{C.BOLD}╔══════════════════════════════════════════════╗{C.RESET}")
        print(f"  {C.RED}{C.BOLD}║  ⚠  ADMINISTRATOR PRIVILEGES REQUIRED       ║{C.RESET}")
        print(f"  {C.RED}{C.BOLD}║                                              ║{C.RESET}")
        print(f"  {C.RED}{C.BOLD}║  Right-click Command Prompt or Terminal      ║{C.RESET}")
        print(f"  {C.RED}{C.BOLD}║  and select 'Run as Administrator'.          ║{C.RESET}")
        print(f"  {C.RED}{C.BOLD}╚══════════════════════════════════════════════╝{C.RESET}")
        print()
        sys.exit(1)

    main_menu()


if __name__ == "__main__":
    main()
