"""AES-256-GCM encryption for OAuth tokens."""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class TokenEncryptor:
    def __init__(self, key_hex: str):
        self.aesgcm = AESGCM(bytes.fromhex(key_hex))

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()

    def decrypt(self, token: str) -> str:
        data = base64.b64decode(token)
        nonce, ciphertext = data[:12], data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None).decode()
