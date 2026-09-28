"""一次性 RSA-OAEP 钥匙。私钥只留在辅助库，日志不得写入。"""

import base64
import secrets

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

_KEY_SIZE = 2048
_PUBLIC_EXPONENT = 65537


def generate_login_keypair() -> tuple[str, str, str]:
    """返回 (key_id, 私钥 PEM, SPKI 公钥 Base64)。"""
    private_key = rsa.generate_private_key(
        public_exponent=_PUBLIC_EXPONENT,
        key_size=_KEY_SIZE,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_id = secrets.token_hex(16)
    return key_id, private_pem, base64.b64encode(public_der).decode("ascii")


def decrypt_password(private_key_pem: str, password_cipher: str) -> str:
    """解密失败抛 ValueError，异常链里不带密文或明文。"""
    try:
        ciphertext = base64.b64decode(password_cipher, validate=True)
        loaded = serialization.load_pem_private_key(
            private_key_pem.encode("ascii"),
            password=None,
        )
        if not isinstance(loaded, RSAPrivateKey):
            raise ValueError("登录密文无法解密")
        plain = loaded.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plain.decode("utf-8")
    except Exception:
        raise ValueError("登录密文无法解密") from None
