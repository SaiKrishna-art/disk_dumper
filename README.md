# Disk Dumper — Bit-to-Bit Storage Extractor

> A forensic-grade, bit-to-bit disk imaging tool for Windows with both a CLI and a modern dark-themed GUI.

**Author:** Murthy Sai Krishna  
**Version:** 1.0  
**License:** Proprietary (see [LICENSE](LICENSE))

---

## Features

### Core Imaging Engine
- **Bit-to-bit raw sector copying** from physical disks and logical drives
- **Configurable sector/block size** (512 B – 64 KB)
- **Bad-sector error handling** — zero-fills unreadable sectors and logs every error
- **Pause & Resume** — interrupt a dump with `Ctrl+C` (CLI) or buttons (GUI), then resume later
- **Session persistence** — saves state to a `.state` JSON file so dumps survive crashes and reboots

### Device Detection
- **WMI-powered** enumeration of physical disks (model, size, media type)
- **Logical drive listing** with volume label, file system, and drive type
- Works with HDDs, SSDs, USB drives, SD cards, and more

### Hash Verification
- **MD5** and **SHA-256** support for image files
- **Drive hashing** — compute hashes directly from raw physical/logical drives
- **Progress bar** during hash computation
- **Hash comparison** — paste an expected hash to verify integrity

### Dual Interface
| | CLI (`main.py`) | GUI (`gui.py`) |
|---|---|---|
| Interface | Interactive ANSI-colored terminal menus | Premium dark-themed CustomTkinter window |
| Progress | `tqdm` progress bar with speed & ETA | Circular + linear progress indicators with live stats |
| Pause/Resume | `Ctrl+C` interactive menu | Dedicated Pause / Resume / Stop buttons |
| Best for | Scripting, remote sessions | everyday use, visual monitoring |

### Security
- **HMAC-based copyright integrity check** — the application verifies its own copyright information at startup and refuses to run if tampered with

---

## 📋 Requirements

- **OS:** Windows 10 / 11 (uses Win32 APIs and WMI)
- **Python:** 3.10+
- **Privileges:** Must run **as Administrator** (raw disk access requires elevated rights)

### Python Dependencies

```
pywin32
tqdm
customtkinter
Pillow
```

Install with:

```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

> **Important:** Always run as Administrator. Right-click your terminal → *Run as Administrator*.

### CLI Mode

```bash
python main.py
```

You'll see an interactive menu:

```
  1. Start New Dump
  2. Resume Previous Dump
  3. Verify Image Hash
  4. List Devices
  0. Exit
```

#### Quick Example

1. Select **Start New Dump**
2. Choose a source device from the detected list
3. Enter an output path (e.g., `usb_backup.img`)
4. Choose sector size (default: 4096)
5. Confirm to begin — press `Ctrl+C` at any time to pause

### GUI Mode

```bash
python gui.py
```

Navigate using the sidebar:

| Page | Description |
|---|---|
| **Dashboard** | Select device, configure output, start/pause/stop dumps, view live progress |
| **Devices** | Browse and select from detected physical disks and logical drives |
| **Hash Verify** | Compute MD5/SHA-256 for image files or raw drives, with copy-to-clipboard |
| **Error Log** | Review any bad-sector read errors encountered during a dump |

---

## Project Structure

```
disk dumper/
├── main.py             # CLI entry point — interactive menus & dump flow
├── gui.py              # GUI entry point — CustomTkinter dark-themed app
├── dumper.py            # Core dump engine — sector-by-sector copy with tqdm
├── gui_dumper.py        # Threaded dump adapter for the GUI (callbacks)
├── disk_utils.py        # Disk detection (WMI), raw handle I/O, admin check
├── hasher.py            # Hash computation (MD5/SHA-256) for files & drives
├── copyright_guard.py   # HMAC-based copyright integrity verification
├── requirements.txt     # Python dependencies
└── LICENSE              # Proprietary license
```

---

## How It Works

1. **Device Enumeration** — `disk_utils.py` queries WMI (`Win32_DiskDrive`) for physical disks and `GetLogicalDriveStrings` for volumes.
2. **Raw Access** — Opens a read-only handle via `win32file.CreateFile` with `FILE_FLAG_NO_BUFFERING`.
3. **Sector Copy** — Reads sectors sequentially with `win32file.ReadFile`, writes to the output `.img` file.
4. **Error Handling** — Failed reads are logged and replaced with zero-filled blocks; the handle seeks past bad sectors.
5. **State Persistence** — Progress is saved to `<output>.state` as JSON, enabling cross-session resume.
6. **Integrity Check** — At startup, `copyright_guard.py` recomputes an HMAC over author metadata and compares it against the expected signature.

---

## License

This software is **proprietary**. See [LICENSE](LICENSE) for full terms.

© 2026 Murthy Sai Krishna. All rights reserved.
