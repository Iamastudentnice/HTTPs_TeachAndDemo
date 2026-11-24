"""encryption.py - Real cryptography demonstrations for the Encryption Laboratory."""

import hashlib
import os

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# --- Small helpers ---

def to_hex(data):
    """Turn raw bytes into a readable hexadecimal string."""
    return data.hex()


def from_hex(hex_text):
    """Turn a hexadecimal string back into raw bytes."""
    try:
        return bytes.fromhex(hex_text.strip())
    except (ValueError, AttributeError):
        return None


def generate_symmetric_key():
    """Create a brand new random 256-bit AES key (32 bytes)."""
    return AESGCM.generate_key(bit_length=256)


def symmetric_encrypt(plaintext, key=None):
    """Encrypt text with AES-256-GCM and return every piece as hex."""
    if key is None:
        key = generate_symmetric_key()

    nonce = os.urandom(12)
    cipher = AESGCM(key)
    # The output is the ciphertext with a 16-byte authentication tag on the end.
    ciphertext_with_tag = cipher.encrypt(nonce, plaintext.encode("utf-8"), None)

    return {
        "algorithm": "AES-256-GCM",
        "plaintext": plaintext,
        "plaintext_hex": to_hex(plaintext.encode("utf-8")),
        "key_hex": to_hex(key),
        "nonce_hex": to_hex(nonce),
        "ciphertext_hex": to_hex(ciphertext_with_tag[:-16]),
        "tag_hex": to_hex(ciphertext_with_tag[-16:]),
        "combined_hex": to_hex(ciphertext_with_tag),
        "plaintext_length": len(plaintext.encode("utf-8")),
        "ciphertext_length": len(ciphertext_with_tag),
    }


def symmetric_decrypt(key_hex, nonce_hex, combined_hex):
    """Try to decrypt AES-GCM data."""
    key = from_hex(key_hex)
    nonce = from_hex(nonce_hex)
    combined = from_hex(combined_hex)

    if key is None or nonce is None or combined is None:
        return {"success": False, "error": "One of the values is not valid hexadecimal."}
    if len(key) not in (16, 24, 32):
        return {"success": False, "error": "An AES key must be 16, 24 or 32 bytes long."}
    if len(nonce) != 12:
        return {"success": False, "error": "The nonce must be exactly 12 bytes (24 hex characters)."}

    try:
        plaintext = AESGCM(key).decrypt(nonce, combined, None)
    except InvalidTag:
        return {
            "success": False,
            "error": "Authentication failed (InvalidTag). Either the key is wrong or the "
                     "ciphertext was modified. AES-GCM refuses to return any plaintext.",
        }

    return {"success": True, "plaintext": plaintext.decode("utf-8", errors="replace")}


def tamper_with_hex(hex_text, position=0):
    """Flip the bits of one byte in a hex string - simulating an attacker changing data while it travels across the network."""
    data = bytearray(from_hex(hex_text) or b"")
    if len(data) == 0:
        return hex_text
    position = position % len(data)
    data[position] = data[position] ^ 0xFF
    return to_hex(bytes(data))


def generate_rsa_key_pair():
    """Create an RSA key pair and return both keys as PEM text."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    return {"private_pem": private_pem, "public_pem": public_pem, "key_size": 2048}


def rsa_encrypt(public_pem, plaintext):
    """Encrypt a short message with someone's PUBLIC key."""
    try:
        public_key = serialization.load_pem_public_key(public_pem.encode("ascii"))
    except (ValueError, TypeError):
        return {"success": False, "error": "That public key could not be read."}

    message_bytes = plaintext.encode("utf-8")
    # RSA-2048 with OAEP/SHA-256 can only encrypt up to 190 bytes. This is one
    # reason real systems use RSA/DH only to agree on a symmetric key.
    if len(message_bytes) > 190:
        return {"success": False,
                "error": "RSA-2048 can only encrypt about 190 bytes. Real protocols use "
                         "asymmetric keys to agree on a symmetric key instead."}

    ciphertext = public_key.encrypt(message_bytes, _oaep_padding())
    return {"success": True, "ciphertext_hex": to_hex(ciphertext), "length": len(ciphertext)}


def rsa_decrypt(private_pem, ciphertext_hex):
    """Decrypt with the matching PRIVATE key."""
    ciphertext = from_hex(ciphertext_hex)
    if ciphertext is None:
        return {"success": False, "error": "The ciphertext is not valid hexadecimal."}
    try:
        private_key = serialization.load_pem_private_key(private_pem.encode("ascii"), password=None)
        plaintext = private_key.decrypt(ciphertext, _oaep_padding())
    except ValueError:
        return {"success": False,
                "error": "Decryption failed. This private key does not match the public "
                         "key used, or the ciphertext was changed."}
    return {"success": True, "plaintext": plaintext.decode("utf-8", errors="replace")}


def _oaep_padding():
    """The modern, safe padding scheme for RSA encryption."""
    return padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )


HASH_ALGORITHMS = {
    "SHA-256": hashes.SHA256,
    "SHA-384": hashes.SHA384,
    "SHA-512": hashes.SHA512,
    "SHA3-256": hashes.SHA3_256,
}


def hash_text(text, algorithm_name="SHA-256"):
    """Return the hash of some text using the chosen algorithm."""
    if algorithm_name == "MD5 (broken)":
        # MD5 is included only to show an old, broken algorithm.
        digest = hashlib.md5(text.encode("utf-8")).digest()
    else:
        algorithm_class = HASH_ALGORITHMS.get(algorithm_name, hashes.SHA256)
        hasher = hashes.Hash(algorithm_class())
        hasher.update(text.encode("utf-8"))
        digest = hasher.finalize()

    return {
        "algorithm": algorithm_name,
        "input": text,
        "input_length": len(text.encode("utf-8")),
        "hash_hex": to_hex(digest),
        "hash_bits": len(digest) * 8,
    }


def count_different_bits(hex_a, hex_b):
    """Count how many bits differ between two equal-length hashes."""
    bytes_a = from_hex(hex_a)
    bytes_b = from_hex(hex_b)
    different_bits = 0
    for byte_a, byte_b in zip(bytes_a, bytes_b):
        different_bits += bin(byte_a ^ byte_b).count("1")
    return different_bits


def compare_hashes(text_a, text_b, algorithm_name="SHA-256"):
    """Hash two inputs and measure how different the results are."""
    result_a = hash_text(text_a, algorithm_name)
    result_b = hash_text(text_b, algorithm_name)
    total_bits = result_a["hash_bits"]
    different_bits = count_different_bits(result_a["hash_hex"], result_b["hash_hex"])

    return {
        "first": result_a,
        "second": result_b,
        "identical": result_a["hash_hex"] == result_b["hash_hex"],
        "different_bits": different_bits,
        "total_bits": total_bits,
        "percent_different": round(100 * different_bits / total_bits, 1),
    }


def generate_signing_keys():
    """Create an Ed25519 signing key pair, returned as hex."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {"private_key_hex": to_hex(private_raw), "public_key_hex": to_hex(public_raw)}


def sign_message(private_key_hex, message):
    """Sign a message with the private key."""
    private_raw = from_hex(private_key_hex)
    if private_raw is None or len(private_raw) != 32:
        return {"success": False, "error": "The private key must be 32 bytes of hex."}
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_raw)
    signature = private_key.sign(message.encode("utf-8"))
    return {"success": True, "signature_hex": to_hex(signature), "message": message}


def verify_signature(public_key_hex, message, signature_hex):
    """Check a signature with the public key."""
    public_raw = from_hex(public_key_hex)
    signature = from_hex(signature_hex)
    if public_raw is None or len(public_raw) != 32:
        return {"valid": False, "reason": "The public key must be 32 bytes of hex."}
    if signature is None or len(signature) != 64:
        return {"valid": False, "reason": "An Ed25519 signature must be 64 bytes of hex."}

    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_raw)
    try:
        public_key.verify(signature, message.encode("utf-8"))
    except InvalidSignature:
        return {"valid": False,
                "reason": "The signature does not match. Either the message was changed "
                          "after signing, or it was signed with a different private key."}
    return {"valid": True,
            "reason": "The signature is valid: the message is unchanged and was signed by "
                      "the holder of the matching private key."}
