from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# 2026 sensible defaults: time_cost=3, memory_cost=64 MiB, parallelism=1
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=1)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
