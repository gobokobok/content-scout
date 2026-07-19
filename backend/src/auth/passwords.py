import bcrypt

# Pre-computed once at process start so dummy_verify() costs the same as a real verify.
# Rounds=12 matches hash_password so response-time parity holds.
_DUMMY_HASH: bytes = bcrypt.hashpw(b"timing-dummy-do-not-use", bcrypt.gensalt(rounds=12))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def dummy_verify() -> None:
    """Run a bcrypt check against a dummy hash to prevent user-enumeration via timing."""
    bcrypt.checkpw(b"", _DUMMY_HASH)
