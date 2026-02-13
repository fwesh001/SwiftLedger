"""
Security & Authentication module for SwiftLedger.

Handles password hashing, credential verification, and system-level authentication
including Windows Hello integration.
"""

import ctypes
from ctypes import wintypes
import hashlib
import hmac
import os
import platform
import secrets
from typing import Tuple


# ──────────────────────────────────────────────────────────────────────────────
# Credential Hashing & Verification
# ──────────────────────────────────────────────────────────────────────────────


def hash_credential(plain_text: str) -> str:
    """
    Hash a credential (password or PIN) with a salt using SHA-256.

    Uses the `secrets` module to generate a cryptographically secure random
    salt, then combines salt + hash for storage.

    Args:
        plain_text: The plain-text credential to hash.

    Returns:
        A string in the format: "salt$hash" suitable for database storage.
    """
    # Generate a cryptographically secure random salt (16 bytes)
    salt = secrets.token_hex(16)

    # Create SHA-256 hash of salt + plain_text
    hash_obj = hashlib.sha256((salt + plain_text).encode("utf-8"))
    hash_hex = hash_obj.hexdigest()

    # Return salt and hash separated by a delimiter
    return f"{salt}${hash_hex}"


def verify_credential(input_text: str, stored_hash: str) -> bool:
    """
    Verify a user's input against a stored salted hash.

    Extracts the salt from the stored hash, re-hashes the input with that salt,
    and compares using constant-time comparison to prevent timing attacks.

    Args:
        input_text:  The plain-text input from the user.
        stored_hash: The stored hash in format "salt$hash".

    Returns:
        True if the input matches the stored hash; False otherwise.
    """
    try:
        # Extract salt and stored hash
        parts = stored_hash.split("$")
        if len(parts) != 2:
            return False

        salt, expected_hash = parts
        # Re-hash the input with the same salt
        hash_obj = hashlib.sha256((salt + input_text).encode("utf-8"))
        computed_hash = hash_obj.hexdigest()

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_hash, expected_hash)

    except (ValueError, AttributeError):
        return False


# ──────────────────────────────────────────────────────────────────────────────
# System-Level Authentication (Windows Hello / System Login)
# ──────────────────────────────────────────────────────────────────────────────


def check_system_auth() -> bool:
    """
    Attempt to trigger Windows Hello or system login authentication.

    On Windows systems, this uses Windows credential provider APIs via ctypes
    to initiate a secure logon dialog. This serves as an additional security
    layer beyond application-level authentication.

    On non-Windows systems, returns False (placeholder).

    Returns:
        True if authentication was successful; False otherwise.
    """
    if platform.system() != "Windows":
        print("⚠ System authentication not available on non-Windows platforms.")
        return False

    try:
        credential_provider = ctypes.CDLL("credui.dll")

        class CREDUI_INFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hwndParent", wintypes.HWND),
                ("pszMessageText", wintypes.LPCWSTR),
                ("pszCaptionText", wintypes.LPCWSTR),
                ("hbmBanner", wintypes.HANDLE),
            ]

        CredUIPromptForCredentials = credential_provider.CredUIPromptForCredentialsW
        CredUIPromptForCredentials.argtypes = [
            ctypes.POINTER(CREDUI_INFO),
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.ULONG,
            wintypes.LPWSTR,
            wintypes.ULONG,
            ctypes.POINTER(wintypes.BOOL),
            wintypes.DWORD,
        ]

        max_user_len = 512
        max_pass_len = 512
        username_buffer = ctypes.create_unicode_buffer(max_user_len)
        password_buffer = ctypes.create_unicode_buffer(max_pass_len)
        save_cred = wintypes.BOOL(False)

        ui_info = CREDUI_INFO()
        ui_info.cbSize = ctypes.sizeof(CREDUI_INFO)
        ui_info.hwndParent = None
        ui_info.pszMessageText = "Please authenticate to continue"
        ui_info.pszCaptionText = "SwiftLedger"
        ui_info.hbmBanner = None

        result = CredUIPromptForCredentials(
            ctypes.byref(ui_info),
            "SwiftLedger",
            None,
            0,
            username_buffer,
            max_user_len,
            password_buffer,
            max_pass_len,
            ctypes.byref(save_cred),
            0,
        )

        # CREDUI_E_SUCCESS = 0 (authentication succeeded)
        # The function returns 0 on success, non-zero error codes on failure
        if result == 0:
            return True
        else:
            print(f"⚠ Authentication dialog cancelled or failed (code: {result}).")
            return False

    except (OSError, ctypes.ArgumentError) as e:
        print(f"⚠ Error accessing credential provider: {e}")
        print("  Ensure this is running on Windows with credential provider support.")
        return False

    except Exception as e:
        print(f"⚠ Unexpected error during system authentication: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────────────────────


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: The number of bytes to generate (will be hex-encoded).

    Returns:
        A hex-encoded string of random bytes.
    """
    return secrets.token_hex(length)


if __name__ == "__main__":
    # ─ Test hash_credential and verify_credential ──────────────────────────
    print("=" * 70)
    print("CREDENTIAL HASHING TEST")
    print("=" * 70)

    # Create a test password
    password = "MySecurePassword123!"
    print(f"\nOriginal password: {password}")

    # Hash the password
    hashed = hash_credential(password)
    print(f"Hashed credential: {hashed}")

    # Verify with correct password
    is_valid = verify_credential(password, hashed)
    print(f"✓ Verification (correct): {is_valid}")

    # Verify with incorrect password
    is_valid = verify_credential("WrongPassword", hashed)
    print(f"✓ Verification (incorrect): {is_valid}")

    # ─ Test check_system_auth (placeholder) ────────────────────────────────
    print("\n" + "=" * 70)
    print("SYSTEM AUTHENTICATION TEST")
    print("=" * 70)
    print("\n[Placeholder] System authentication would open Windows credential dialog.")
    print("In production, this function enables Windows Hello / system login.")

    # Uncomment the line below to test the system authentication dialog:
    # result = check_system_auth()
    # print(f"\nSystem authentication result: {result}")
