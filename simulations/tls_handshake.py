"""tls_handshake.py - Module Two: a step-by-step TLS 1.3 handshake."""

import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from simulations import encryption
from simulations.steps import make_node, make_packet

CLIENT = "client"
SERVER = "server"
SERVER_NAME = "shop.example.com"


def diagram_nodes():
    """Client on the left, server on the right."""
    return [
        make_node(CLIENT, "Browser", "TLS client", "laptop", "client"),
        make_node(SERVER, "Web Server", SERVER_NAME, "server", "server"),
    ]


def public_key_hex(private_key):
    """Return the raw 32-byte public key of an X25519 key pair, as hex."""
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return public_bytes.hex()


def derive_key(shared_secret, label, length=32):
    """Derive a key from the shared secret using HKDF-SHA256."""
    hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=None, info=label.encode("ascii"))
    return hkdf.derive(shared_secret)


def perform_key_exchange():
    """Run a real X25519 key exchange and return every value involved."""
    client_private = x25519.X25519PrivateKey.generate()
    server_private = x25519.X25519PrivateKey.generate()

    client_public_hex = public_key_hex(client_private)
    server_public_hex = public_key_hex(server_private)

    # Each side uses ITS OWN private key and the OTHER side's public key.
    client_shared = client_private.exchange(server_private.public_key())
    server_shared = server_private.exchange(client_private.public_key())

    client_write_key = derive_key(client_shared, "tls13 demo client application key")
    server_write_key = derive_key(client_shared, "tls13 demo server application key")

    return {
        "client_public": client_public_hex,
        "server_public": server_public_hex,
        "client_shared": client_shared.hex(),
        "server_shared": server_shared.hex(),
        "secrets_match": client_shared == server_shared,
        "client_write_key": client_write_key,
        "server_write_key": server_write_key,
    }


def make_stage(number, title, who, what, exchanged, why, purpose, packet=None, highlight=None, extra=None):
    """Bundle the five pieces of information shown for every handshake stage."""
    return {
        "title": str(number) + ". " + title,
        "explanation": what,
        "packet": packet,
        "highlight": highlight or {},
        "panels": {
            "who": who,
            "what": what,
            "exchanged": exchanged,
            "why": why,
            "purpose": purpose,
            "extra": extra or [],
        },
    }


def build_handshake_steps(message="GET /account HTTP/1.1"):
    """Create the seven stages of a TLS 1.3 handshake with real key material."""
    client_random = os.urandom(32).hex()
    server_random = os.urandom(32).hex()
    keys = perform_key_exchange()
    record = encryption.symmetric_encrypt(message, keys["client_write_key"])

    stages = []

    stages.append(make_stage(
        1, "Browser says hello (Client Hello)", "Browser (client) → Server",
        "Your browser suggests how to protect the chat, and sends half of a key.",
        [
            "Supported TLS versions: TLS 1.3, TLS 1.2",
            "Cipher suites: TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256",
            "Client random: " + client_random[:32] + "...",
            "Server Name Indication (SNI): " + SERVER_NAME,
            "key_share (X25519 ephemeral PUBLIC key): " + keys["client_public"],
        ],
        "The server needs to know which versions and algorithms the browser supports.",
        "Speed: sending its public key now lets TLS 1.3 finish in one round trip.",
        packet=make_packet(CLIENT, SERVER, "plain", "ClientHello",
                           {"Message": "ClientHello", "Encrypted": "No (handshake has not started)",
                            "key_share": keys["client_public"][:24] + "...", "SNI": SERVER_NAME}),
        highlight={CLIENT: "active"},
        extra=["The client's private key never leaves the browser."],
    ))

    stages.append(make_stage(
        2, "Website replies (Server Hello)", "Server → Browser",
        "The website picks the settings and sends its half of the key.",
        [
            "Selected version: TLS 1.3",
            "Selected cipher suite: TLS_AES_256_GCM_SHA384",
            "Server random: " + server_random[:32] + "...",
            "key_share (X25519 ephemeral PUBLIC key): " + keys["server_public"],
        ],
        "Both sides must agree on the same algorithms before they can talk securely.",
        "From here on, everything (even the certificate) is encrypted.",
        packet=make_packet(SERVER, CLIENT, "plain", "ServerHello",
                           {"Message": "ServerHello", "Encrypted": "No",
                            "Cipher suite": "TLS_AES_256_GCM_SHA384",
                            "key_share": keys["server_public"][:24] + "..."}),
        highlight={SERVER: "active"},
    ))

    stages.append(make_stage(
        3, "Website proves who it is (Certificate)", "Server → Browser (encrypted with handshake keys)",
        "The website sends its ID card (certificate) and signs the handshake.",
        [
            "Certificate: CN=" + SERVER_NAME + ", issued by 'Demo Intermediate CA'",
            "Intermediate certificate: issued by 'Demo Root CA'",
            "CertificateVerify: a signature over the whole handshake so far, made with the "
            "server's PRIVATE key",
            "Finished: a MAC proving the server saw the same handshake messages",
        ],
        "Without proof of identity, the browser could be talking to an impostor.",
        "Authentication: the certificate links the name to a public key, and the signature "
        "proves the server holds the matching private key. It does NOT encrypt your data.",
        packet=make_packet(SERVER, CLIENT, "encrypted", "Certificate + Verify",
                           {"Messages": "EncryptedExtensions, Certificate, CertificateVerify, Finished",
                            "Encrypted": "Yes - with handshake keys (TLS 1.3 hides the certificate)"}),
        highlight={SERVER: "secure"},
    ))

    stages.append(make_stage(
        4, "Browser checks the ID (Verification)", "Browser (local check - nothing is sent)",
        "Your browser checks the certificate. Nothing is sent in this step.",
        [
            "Does the certificate cover " + SERVER_NAME + "? ✔",
            "Is today within the validity period? ✔",
            "Does each signature in the chain verify up to a trusted root CA? ✔",
            "Is the root CA in the browser/OS trust store? ✔",
            "Does CertificateVerify validate with the certificate's public key? ✔",
        ],
        "A certificate is only useful if the browser actually validates it.",
        "Stops impersonation: if any check fails, the browser warns you and stops (try it in Lab 05).",
        highlight={CLIENT: "secure"},
    ))

    stages.append(make_stage(
        5, "Both make the same secret (Key exchange)", "Both sides compute locally - nothing is sent",
        "Each side mixes its private key with the other's public key. Compare the two results.",
        [
            "Client computes: X25519(client_private, server_public)",
            "Server computes: X25519(server_private, client_public)",
            "Client result: " + keys["client_shared"],
            "Server result: " + keys["server_shared"],
            "Secrets match: " + ("YES ✔" if keys["secrets_match"] else "NO"),
        ],
        "Both sides need the same secret, but sending it would let eavesdroppers copy it.",
        "Confidentiality and forward secrecy: these keys are thrown away after the session, "
        "so recorded traffic stays safe even if a server key leaks later.",
        highlight={CLIENT: "secure", SERVER: "secure"},
        extra=["These values were calculated just now by Python using real X25519.",
               "An eavesdropper saw only the two PUBLIC keys and cannot compute this secret."],
    ))

    stages.append(make_stage(
        6, "Turn the secret into keys (Session keys)", "Browser → Server (Finished)",
        "Both sides turn the shared secret into session keys, then confirm.",
        [
            "Client write key (HKDF): " + keys["client_write_key"].hex(),
            "Server write key (HKDF): " + keys["server_write_key"].hex(),
            "Client Finished: MAC over the entire handshake transcript",
        ],
        "Separate keys for each direction, and a final check that nobody tampered with "
        "the handshake messages (e.g. forcing weaker algorithms).",
        "Handshake integrity: if anyone changed a hello message, the Finished check fails "
        "and the connection stops.",
        packet=make_packet(CLIENT, SERVER, "encrypted", "Finished",
                           {"Message": "Finished", "Encrypted": "Yes"}),
        highlight={CLIENT: "secure", SERVER: "secure"},
        extra=["Real TLS 1.3 uses a longer HKDF key schedule; one HKDF step is shown for clarity."],
    ))

    stages.append(make_stage(
        7, "Send data safely (Application data)", "Browser ⇄ Server",
        "Your request now travels encrypted with the new session key.",
        [
            "Plaintext (inside the browser): " + message,
            "AES-256-GCM nonce: " + record["nonce_hex"],
            "Encrypted record: " + record["combined_hex"],
        ],
        "This is the whole point of the handshake: protecting the real data.",
        "Authenticated encryption: any change to the ciphertext makes decryption fail.",
        packet=make_packet(CLIENT, SERVER, "encrypted", "Application Data",
                           {"Message": "TLS Application Data", "Cipher": "AES-256-GCM",
                            "Ciphertext": record["combined_hex"][:48] + "..."}),
        highlight={CLIENT: "secure", SERVER: "secure"},
        extra=["This ciphertext was produced with the client write key derived above."],
    ))
    return stages
