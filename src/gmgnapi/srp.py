"""
SRP-6a client used by GMGN's email/password login.

GMGN's web app authenticates with SRP-6a (RFC 5054) via the JavaScript
``secure-remote-password`` package. The password itself never leaves the
machine; only the SRP proof does.

This module is a byte-exact port of that package, which matters because the
proof is a hash over fixed-width hex encodings: every integer carries the hex
width it was created with and is re-encoded at that width when hashed, so a
value that merely compares equal is not enough (``SRPInteger``).

The JavaScript package does its arithmetic with ``jsbn``, whose ``mod`` and
``modPow`` normalise into ``[0, m)``, matching Python's ``%`` and ``pow``. That
normalisation is load-bearing: SRP's ``B - k*g^x`` is routinely negative, and
only the sign of the reduced result makes the proof agree with the server.

Test vectors generated from the JavaScript package live in ``tests/test_srp.py``.
"""

import hashlib
import secrets
from typing import Optional, Union

__all__ = [
    "SRPInteger",
    "Ephemeral",
    "Session",
    "generate_salt",
    "generate_ephemeral",
    "derive_private_key",
    "derive_verifier",
    "derive_session",
    "verify_session",
]


def _js_hex(value: int) -> str:
    """Render an integer the way ``jsbn``'s ``toString(16)`` does."""
    return f"-{abs(value):x}" if value < 0 else f"{value:x}"


class SRPInteger:
    """An integer that remembers the hex width it should be encoded at."""

    __slots__ = ("value", "hex_length")

    ZERO: "SRPInteger"

    def __init__(self, value: int, hex_length: Optional[int]) -> None:
        self.value = value
        self.hex_length = hex_length

    @classmethod
    def from_hex(cls, value: str) -> "SRPInteger":
        return cls(int(value, 16), len(value))

    @classmethod
    def random_integer(cls, num_bytes: int) -> "SRPInteger":
        return cls.from_hex(secrets.token_bytes(num_bytes).hex())

    def to_hex(self) -> str:
        if self.hex_length is None:
            raise ValueError("This SRPInteger has no specified length")
        return _js_hex(self.value).rjust(self.hex_length, "0")

    def add(self, other: "SRPInteger") -> "SRPInteger":
        return SRPInteger(self.value + other.value, None)

    def subtract(self, other: "SRPInteger") -> "SRPInteger":
        return SRPInteger(self.value - other.value, self.hex_length)

    def multiply(self, other: "SRPInteger") -> "SRPInteger":
        return SRPInteger(self.value * other.value, None)

    def xor(self, other: "SRPInteger") -> "SRPInteger":
        return SRPInteger(self.value ^ other.value, self.hex_length)

    def mod(self, modulus: "SRPInteger") -> "SRPInteger":
        return SRPInteger(self.value % modulus.value, modulus.hex_length)

    def mod_pow(self, exponent: "SRPInteger", modulus: "SRPInteger") -> "SRPInteger":
        return SRPInteger(
            pow(self.value, exponent.value, modulus.value), modulus.hex_length
        )

    def equals(self, other: "SRPInteger") -> bool:
        return self.value == other.value

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        text = _js_hex(self.value)
        suffix = "..." if len(text) > 16 else ""
        return f"<SRPInteger {text[:16]}{suffix}>"


SRPInteger.ZERO = SRPInteger(0, None)


# RFC 5054 2048-bit group, SHA-256 — the parameters GMGN's web client uses.
_LARGE_SAFE_PRIME = (
    "AC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC3192943DB56050"
    "A37329CBB4A099ED8193E0757767A13DD52312AB4B03310DCD7F48A9DA04FD50"
    "E8083969EDB767B0CF6095179A163AB3661A05FBD5FAAAE82918A9962F0B93B8"
    "55F97993EC975EEAA80D740ADBF4FF747359D041D5C33EA71D281E446B14773B"
    "CA97B43A23FB801676BD207A436C6481F1D2B9078717461A5B9D32E688F87748"
    "544523B524B0D57D5EA77A2775D2ECFA032CFBDBF52FB3786160279004E57AE6"
    "AF874E7303CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DBFBB6"
    "94B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F9E4AFF73"
)
_GENERATOR_MODULO = "02"
HASH_OUTPUT_BYTES = 32

N = SRPInteger.from_hex(_LARGE_SAFE_PRIME)
g = SRPInteger.from_hex(_GENERATOR_MODULO)


def H(*args: Union[SRPInteger, str]) -> SRPInteger:
    """SHA-256 over the concatenation of the arguments.

    ``SRPInteger`` arguments contribute their fixed-width hex encoding decoded
    to bytes; ``str`` arguments contribute their UTF-8 bytes.
    """
    buffer = bytearray()
    for arg in args:
        if isinstance(arg, SRPInteger):
            buffer.extend(bytes.fromhex(arg.to_hex()))
        elif isinstance(arg, str):
            buffer.extend(arg.encode("utf-8"))
        else:
            raise TypeError("Expected string or SRPInteger")
    return SRPInteger.from_hex(hashlib.sha256(bytes(buffer)).hexdigest())


k = H(N, g)


class Ephemeral:
    """A client's ephemeral key pair, as hex strings."""

    __slots__ = ("secret", "public")

    def __init__(self, secret: str, public: str) -> None:
        self.secret = secret
        self.public = public

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Ephemeral public={self.public[:16]}...>"


class Session:
    """A derived SRP session: the shared ``key`` and the client ``proof``."""

    __slots__ = ("key", "proof")

    def __init__(self, key: str, proof: str) -> None:
        self.key = key
        self.proof = proof

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Session proof={self.proof[:16]}...>"


def generate_salt() -> str:
    """Generate a random salt as a hex string."""
    return SRPInteger.random_integer(HASH_OUTPUT_BYTES).to_hex()


def generate_ephemeral() -> Ephemeral:
    """Generate the client's ephemeral key pair (``a`` and ``A = g^a mod N``)."""
    secret = SRPInteger.random_integer(HASH_OUTPUT_BYTES)
    public = g.mod_pow(secret, N)
    return Ephemeral(secret=secret.to_hex(), public=public.to_hex())


def derive_private_key(salt: str, username: str, password: str) -> str:
    """Derive the SRP private key ``x = H(salt, H(username:password))``."""
    return H(SRPInteger.from_hex(salt), H(f"{username}:{password}")).to_hex()


def derive_verifier(private_key: str) -> str:
    """Derive the SRP verifier ``v = g^x mod N``."""
    return g.mod_pow(SRPInteger.from_hex(private_key), N).to_hex()


def derive_session(
    client_secret: str,
    server_public: str,
    salt: str,
    username: str,
    private_key: str,
) -> Session:
    """Derive the shared session key and the client proof ``M1``.

    Raises:
        ValueError: If the server's ephemeral public value is invalid.
    """
    a = SRPInteger.from_hex(client_secret)
    B = SRPInteger.from_hex(server_public)
    s = SRPInteger.from_hex(salt)
    I = str(username)
    x = SRPInteger.from_hex(private_key)

    A = g.mod_pow(a, N)

    if B.mod(N).equals(SRPInteger.ZERO):
        raise ValueError("The server sent an invalid public ephemeral")

    u = H(A, B)
    S = B.subtract(k.multiply(g.mod_pow(x, N))).mod_pow(a.add(u.multiply(x)), N)
    K = H(S)
    M = H(H(N).xor(H(g)), H(I), s, A, B, K)

    return Session(key=K.to_hex(), proof=M.to_hex())


def verify_session(client_public: str, session: Session, server_proof: str) -> None:
    """Verify the server's proof ``M2``.

    Raises:
        ValueError: If the server's proof does not match.
    """
    expected = H(
        SRPInteger.from_hex(client_public),
        SRPInteger.from_hex(session.proof),
        SRPInteger.from_hex(session.key),
    )
    if not SRPInteger.from_hex(server_proof).equals(expected):
        raise ValueError("Server provided session proof is invalid")
