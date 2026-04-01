"""
disk_utils.py – Disk detection and raw access utilities for Windows.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

Uses WMI (via win32com) and pywin32 to enumerate physical disks,
logical drives, and open raw read handles for bit-to-bit dumping.
"""

import ctypes
import struct
import string

import win32file
import win32api
import win32com.client
import winioctlcon
import pythoncom


# ─── Disk / Partition Enumeration ─────────────────────────────────────────────

def list_physical_disks():
    """
    Enumerate physical disk drives via WMI.

    Returns a list of dicts:
        [
            {
                "index": 0,
                "path": "\\\\.\\PhysicalDrive0",
                "model": "Samsung SSD 970 EVO 1TB",
                "size": 1000204886016,
                "size_hr": "931.5 GB",
                "media_type": "Fixed hard disk media",
            },
            ...
        ]
    """
    # COM must be initialized per-thread (needed when called from GUI threads)
    pythoncom.CoInitialize()
    try:
        wmi = win32com.client.GetObject("winmgmts:")
        disks = []
        for disk in wmi.InstancesOf("Win32_DiskDrive"):
            size = int(disk.Size) if disk.Size else 0
            disks.append({
                "index": int(disk.Index),
                "path": f"\\\\.\\PhysicalDrive{int(disk.Index)}",
                "model": (disk.Model or "Unknown").strip(),
                "size": size,
                "size_hr": _human_readable_size(size),
                "media_type": (disk.MediaType or "Unknown").strip(),
            })
        disks.sort(key=lambda d: d["index"])
        return disks
    finally:
        # Release COM objects before uninitializing COM to avoid warnings
        try:
            del wmi
        except NameError:
            pass
        pythoncom.CoUninitialize()


def list_logical_drives():
    """
    Enumerate logical drives (C:, D:, E:, …) with volume info.

    Returns a list of dicts:
        [
            {
                "letter": "C",
                "path": "\\\\.\\C:",
                "label": "Windows",
                "file_system": "NTFS",
                "size": 499971518464,
                "size_hr": "465.7 GB",
                "drive_type": "Fixed",
            },
            ...
        ]
    """
    drive_type_map = {
        0: "Unknown",
        1: "No Root Dir",
        2: "Removable",
        3: "Fixed",
        4: "Network",
        5: "CD-ROM",
        6: "RAM Disk",
    }

    raw = win32api.GetLogicalDriveStrings()
    drive_roots = [d for d in raw.split("\x00") if d]  # e.g. ["C:\\", "D:\\"]

    drives = []
    for root in drive_roots:
        letter = root[0].upper()
        dtype_int = ctypes.windll.kernel32.GetDriveTypeW(root)
        dtype = drive_type_map.get(dtype_int, "Unknown")

        label = ""
        file_system = ""
        size = 0
        try:
            info = win32api.GetVolumeInformation(root)
            label = info[0] or ""
            file_system = info[4] or ""
        except Exception:
            pass

        try:
            sec_per_clus, bytes_per_sec, free_clus, total_clus = (
                win32api.GetDiskFreeSpace(root)
            )
            size = sec_per_clus * bytes_per_sec * total_clus
        except Exception:
            pass

        drives.append({
            "letter": letter,
            "path": f"\\\\.\\{letter}:",
            "label": label,
            "file_system": file_system,
            "size": size,
            "size_hr": _human_readable_size(size),
            "drive_type": dtype,
        })

    drives.sort(key=lambda d: d["letter"])
    return drives


# ─── Raw Disk Handle ──────────────────────────────────────────────────────────

def open_disk_handle(device_path: str):
    """
    Open a raw read-only handle to a physical disk or logical drive.

    Args:
        device_path: e.g. "\\\\.\\PhysicalDrive0" or "\\\\.\\C:"

    Returns:
        A PyHANDLE that can be used with win32file.ReadFile.

    Raises:
        PermissionError: if not running as Administrator.
        OSError: if the device cannot be opened.
    """
    try:
        handle = win32file.CreateFile(
            device_path,
            win32file.GENERIC_READ,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_FLAG_NO_BUFFERING | win32file.FILE_FLAG_SEQUENTIAL_SCAN,
            None,
        )
        return handle
    except win32file.error as e:
        if e.winerror == 5:  # ACCESS_DENIED
            raise PermissionError(
                "Access denied. Please run this tool as Administrator."
            ) from e
        raise OSError(f"Cannot open device '{device_path}': {e}") from e


def get_disk_size(handle) -> int:
    """
    Get total byte size of an opened disk/volume handle.

    Uses IOCTL_DISK_GET_LENGTH_INFO.

    Args:
        handle: a PyHANDLE returned by open_disk_handle().

    Returns:
        Total size in bytes.
    """
    IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
    result = win32file.DeviceIoControl(
        handle,
        IOCTL_DISK_GET_LENGTH_INFO,
        None,
        512,  # output buffer size
    )
    # Result is a bytes object containing a LARGE_INTEGER (8 bytes, little-endian)
    size = struct.unpack("<q", result[:8])[0]
    return size


def close_handle(handle):
    """Safely close a disk handle."""
    try:
        win32file.CloseHandle(handle)
    except Exception:
        pass


# ─── Admin Check ──────────────────────────────────────────────────────────────

def is_admin() -> bool:
    """Check if the current process has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _human_readable_size(size_bytes: int) -> str:
    """Convert byte count to human-readable string (e.g. '931.5 GB')."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"
