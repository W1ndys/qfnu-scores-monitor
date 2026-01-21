import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key():
    """生成随机加密密钥"""
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode()


def encrypt_session(session_data, key_b64):
    """加密session数据"""
    key = base64.b64decode(key_b64)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, session_data.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_session(encrypted_data, key_b64):
    """解密session数据"""
    key = base64.b64decode(key_b64)
    aesgcm = AESGCM(key)
    data = base64.b64decode(encrypted_data)
    nonce = data[:12]
    ciphertext = data[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()
