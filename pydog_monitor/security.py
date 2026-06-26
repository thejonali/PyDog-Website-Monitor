import os

from cryptography.fernet import Fernet, InvalidToken

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


FERNET_KEY_ENV_VAR = "PYDOG_FERNET_KEY"
ENCRYPTED_PREFIX = "fernet:"
LEGACY_FERNET_PREFIX = "gAAAAA"

if load_dotenv:
    load_dotenv()


class SecretConfigurationError(RuntimeError):
    """Raised when an encrypted secret cannot be read with the current config."""


def _get_cipher():
    key = os.getenv(FERNET_KEY_ENV_VAR)
    if not key:
        return None

    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise SecretConfigurationError(
            f"{FERNET_KEY_ENV_VAR} is set but is not a valid Fernet key. "
            "Run `python generate_fernet_key.py` to generate a valid key."
        ) from exc


def encryption_enabled():
    return _get_cipher() is not None


def encrypt_secret(value):
    if value is None:
        return value

    cipher = _get_cipher()
    if cipher is None:
        print(
            f"Warning: {FERNET_KEY_ENV_VAR} is not set; this secret is not "
            "currently encrypting and will be stored as plaintext. Run "
            "`python generate_fernet_key.py` and add the key to `.env` to "
            "enable encryption."
        )
        return value

    encrypted_value = cipher.encrypt(value.encode()).decode()
    return f"{ENCRYPTED_PREFIX}{encrypted_value}"


def decrypt_secret(value):
    if value is None:
        return value

    if not value.startswith(ENCRYPTED_PREFIX):
        if value.startswith(LEGACY_FERNET_PREFIX):
            raise SecretConfigurationError(
                "This looks like a secret saved by the old temporary-key "
                "encryption. It cannot be decrypted reliably. Re-enter the "
                "integration secret so it can be saved with the current "
                "configuration."
            )
        return value

    cipher = _get_cipher()
    if cipher is None:
        raise SecretConfigurationError(
            f"{FERNET_KEY_ENV_VAR} is not set, but this secret is encrypted. "
            "Add the original key to `.env` or your shell environment."
        )

    encrypted_value = value[len(ENCRYPTED_PREFIX):]
    try:
        return cipher.decrypt(encrypted_value.encode()).decode()
    except InvalidToken as exc:
        raise SecretConfigurationError(
            f"This secret could not be decrypted with the current "
            f"{FERNET_KEY_ENV_VAR}. Restore the original key or re-enter the "
            "integration secret."
        ) from exc
