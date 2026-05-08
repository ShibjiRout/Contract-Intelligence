from cryptography.fernet import Fernet, InvalidToken

from contracts_platform.core.config import settings
from contracts_platform.core.exceptions import ContractPlatformError


def _get_fernet() -> Fernet:
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as e:
        raise ContractPlatformError("Decryption failed — invalid token") from e
