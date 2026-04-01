"""
hasher.py – Hash verification for disk image files.

© 2026 Murthy Sai Krishna. All rights reserved.
Unauthorized modification or removal of this notice is prohibited.

Supports MD5 and SHA-256 with streaming + progress bar.
"""

import hashlib
import os

from tqdm import tqdm


SUPPORTED_ALGORITHMS = ("md5", "sha256")
DEFAULT_ALGORITHM = "sha256"
READ_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB


def compute_hash(file_path: str, algorithm: str = DEFAULT_ALGORITHM) -> str:
    """
    Compute the hash of a file with a progress bar.

    Args:
        file_path:  Path to the file to hash.
        algorithm:  'md5' or 'sha256'.

    Returns:
        Hex-digest string.

    Raises:
        ValueError:  If algorithm is not supported.
        FileNotFoundError: If file does not exist.
    """
    algorithm = algorithm.lower()
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}'. "
            f"Choose from: {', '.join(SUPPORTED_ALGORITHMS)}"
        )

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    h = hashlib.new(algorithm)

    print(f"\n  Computing {algorithm.upper()} hash …")
    with open(file_path, "rb") as f:
        with tqdm(
            total=file_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=f"  {algorithm.upper()}",
            bar_format="  {l_bar}{bar:30}{r_bar}",
            colour="cyan",
        ) as pbar:
            while True:
                chunk = f.read(READ_CHUNK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
                pbar.update(len(chunk))

    return h.hexdigest()


def compute_hash_silent(file_path: str, algorithm: str = DEFAULT_ALGORITHM) -> str:
    """
    Compute the hash of a file without any console output.

    Same as compute_hash but without tqdm progress bars or print statements.
    Suitable for GUI use.
    """
    algorithm = algorithm.lower()
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}'. "
            f"Choose from: {', '.join(SUPPORTED_ALGORITHMS)}"
        )

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


def compute_drive_hash_silent(
    device_path: str, algorithm: str = DEFAULT_ALGORITHM
) -> str:
    """
    Compute the hash of a raw physical or logical drive without console output.

    Uses disk_utils to open a raw handle and read the entire drive.
    Suitable for GUI use.

    Args:
        device_path: e.g. "\\\\.\\PhysicalDrive0" or "\\\\.\\C:"
        algorithm:   'md5' or 'sha256'.

    Returns:
        Hex-digest string.
    """
    import win32file
    from disk_utils import open_disk_handle, get_disk_size, close_handle

    algorithm = algorithm.lower()
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported algorithm '{algorithm}'. "
            f"Choose from: {', '.join(SUPPORTED_ALGORITHMS)}"
        )

    handle = open_disk_handle(device_path)
    try:
        total_size = get_disk_size(handle)
        h = hashlib.new(algorithm)
        bytes_read = 0

        while bytes_read < total_size:
            chunk_size = min(READ_CHUNK_SIZE, total_size - bytes_read)
            # Align chunk_size to 512-byte sector boundary
            chunk_size = (chunk_size // 512) * 512
            if chunk_size == 0:
                break
            try:
                hr, data = win32file.ReadFile(handle, chunk_size)
                if not data:
                    break
                h.update(data)
                bytes_read += len(data)
            except Exception:
                break

        return h.hexdigest()
    finally:
        close_handle(handle)


def verify_hash(
    file_path: str, expected_hash: str, algorithm: str = DEFAULT_ALGORITHM
) -> bool:
    """
    Compute file hash and compare against an expected value.

    Returns True if they match.
    """
    computed = compute_hash(file_path, algorithm)
    match = computed.lower() == expected_hash.lower().strip()
    if match:
        print(f"  ✅ Hash MATCH: {computed}")
    else:
        print(f"  ❌ Hash MISMATCH!")
        print(f"     Expected: {expected_hash.lower().strip()}")
        print(f"     Got:      {computed}")
    return match
