"""
Security & Authentication module for SwiftLedger.

Handles password hashing and credential verification.
"""

import hashlib
import hmac
import secrets


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

