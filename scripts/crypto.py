"""AES-GCM encryption with key derived from Gmail App Password.

Compatible con WebCrypto del browser (`docs/app.js`):
- PBKDF2-HMAC-SHA256, 100_000 iter, salt fijo "daily-sync-salesperson-v1"
- AES-256-GCM, 12-byte IV aleatorio
- Output JSON: {iv: base64, ct: base64, salt: base64, v: 1}

Uso CLI:
    python crypto.py encrypt input.json output.json.enc
    python crypto.py decrypt input.json.enc output.json
"""
import base64
import json
import os
import sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SALT = b"daily-sync-salesperson-v1"
ITERATIONS = 100_000
KEY_LEN = 32  # AES-256


def derive_key(passphrase: str, salt: bytes = SALT) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt(data: bytes, passphrase: str) -> dict:
    key = derive_key(passphrase)
    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(iv, data, associated_data=None)
    return {
        "v": 1,
        "iv": base64.b64encode(iv).decode("ascii"),
        "salt": base64.b64encode(SALT).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
    }


def decrypt(blob: dict, passphrase: str) -> bytes:
    if blob.get("v") != 1:
        raise ValueError(f"Unsupported version: {blob.get('v')}")
    salt = base64.b64decode(blob["salt"])
    iv = base64.b64decode(blob["iv"])
    ct = base64.b64decode(blob["ct"])
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ct, associated_data=None)


def encrypt_json(obj, passphrase: str) -> dict:
    return encrypt(json.dumps(obj, ensure_ascii=False).encode("utf-8"), passphrase)


def decrypt_json(blob: dict, passphrase: str):
    return json.loads(decrypt(blob, passphrase).decode("utf-8"))


def _cli():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    op, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    pw = os.environ.get("APP_PASS") or input("App Password: ").strip()
    if op == "encrypt":
        with open(src, "rb") as f:
            data = f.read()
        blob = encrypt(data, pw)
        with open(dst, "w") as f:
            json.dump(blob, f, indent=2)
    elif op == "decrypt":
        with open(src) as f:
            blob = json.load(f)
        data = decrypt(blob, pw)
        with open(dst, "wb") as f:
            f.write(data)
    else:
        print(f"Unknown op: {op}")
        sys.exit(2)
    print(f"OK: {dst}")


if __name__ == "__main__":
    _cli()
