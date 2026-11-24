"""presentation.py - The script for Presentation Mode (the two-minute demo)."""

from simulations import certificates, encryption, tls_handshake
from simulations.steps import make_node, make_packet

TOTAL_SECONDS = 120
SITE = certificates.SITE_NAME

# Shared demo data
LOGIN = "username=Brian&password=example123"
TRANSFER = "Pay £10 to Alice"
TAMPERED_TRANSFER = "Pay £9,000 to Mallory"


def card(label, value, tone="neutral"):
    """A small information box shown beside the diagram."""
    return {"label": label, "value": value, "tone": tone}


def step(at, caption, packet=None, highlight=None, cards=None):
    """One timed moment of the presentation."""
    return {"at": at, "caption": caption, "packet": packet,
            "highlight": highlight or {}, "cards": cards or []}


def short(hex_text, length=40):
    """Shorten long hex so it fits on screen."""
    return hex_text[:length] + "…"


# --- Scene builders - one function per scene ---

def scene_introduction():
    """0:00 - 0:20  What HTTP and HTTPS are and why it matters."""
    nodes = [make_node("client", "Your Browser", "you", "laptop", "client"),
             make_node("server", "Website", SITE, "server", "server")]
    return {
        "title": "Introduction",
        "start": 0, "end": 20,
        "headline": "Every web page travels across networks you don't control.",
        "nodes": nodes,
        "steps": [
            step(0, "HTTP (HyperText Transfer Protocol) is how browsers ask websites for pages. It sends everything as readable text.",
                 make_packet("client", "server", "plain", "HTTP request",
                             {"Protocol": "HTTP", "Encrypted": "No"}, "GET /login HTTP/1.1"),
                 {"client": "active"},
                 [card("HTTP", "HyperText Transfer Protocol · port 80 · plain text", "plain")]),
            step(8, "HTTPS is the same HTTP, sent inside a TLS connection: encrypted, tamper-proof, and the server proves who it is.",
                 make_packet("client", "server", "encrypted", "HTTPS request",
                             {"Protocol": "HTTP inside TLS 1.3", "Encrypted": "Yes"}, "(encrypted)"),
                 {"client": "secure", "server": "secure"},
                 [card("HTTP", "HyperText Transfer Protocol · port 80 · plain text", "plain"),
                  card("HTTPS", "HTTP over TLS · port 443 · encrypted", "secure")]),
            step(15, "Why it matters: passwords, payments and private messages cross Wi-Fi, routers and ISPs on the way.",
                 None, {"client": "secure", "server": "secure"},
                 [card("HTTP", "HyperText Transfer Protocol · port 80 · plain text", "plain"),
                  card("HTTPS", "HTTP over TLS · port 443 · encrypted", "secure"),
                  card("At risk without it", "Passwords · card numbers · cookies · messages", "warning")]),
        ],
    }


def scene_http_vs_https():
    """0:20 - 0:45  The same login sent over HTTP and then HTTPS."""
    record = encryption.symmetric_encrypt(LOGIN)
    ciphertext = record["combined_hex"]
    nodes = [make_node("client", "Your Browser", "192.168.1.20", "laptop", "client"),
             make_node("sniffer", "Wi-Fi Eavesdropper", "on the same network", "attacker", "attacker"),
             make_node("server", "Website", SITE, "server", "server")]
    return {
        "title": "HTTP vs HTTPS",
        "start": 20, "end": 45,
        "headline": "Same login, two protocols. What can the eavesdropper read?",
        "nodes": nodes,
        "steps": [
            step(20, "Over HTTP the login is sent as plain text across the Wi-Fi…",
                 make_packet("client", "server", "plain", LOGIN,
                             {"Protocol": "HTTP", "Destination": "203.0.113.10:80", "Encrypted": "No"}, LOGIN),
                 {"client": "warning", "sniffer": "danger"},
                 [card("Browser address bar", "http://" + SITE + "  ·  Not secure", "danger")]),
            step(26, "…so the eavesdropper reads the password instantly. No hacking skill needed.",
                 None, {"sniffer": "danger"},
                 [card("Browser address bar", "http://" + SITE + "  ·  Not secure", "danger"),
                  card("Eavesdropper sees", LOGIN, "danger")]),
            step(33, "Over HTTPS the browser encrypts the same login with AES-256-GCM before it leaves the device.",
                 make_packet("client", "server", "encrypted", short(ciphertext, 18),
                             {"Protocol": "TLS 1.3 Application Data", "Destination": "203.0.113.10:443",
                              "Cipher": "AES-256-GCM", "Encrypted": "Yes"}, ciphertext),
                 {"client": "secure", "server": "secure", "sniffer": "warning"},
                 [card("Browser address bar", "https://" + SITE + "  ·  🔒", "secure")]),
            step(39, "The eavesdropper only captures ciphertext. It can see the server's address, but not the content.",
                 None, {"client": "secure", "server": "secure", "sniffer": "inactive"},
                 [card("Browser address bar", "https://" + SITE + "  ·  🔒", "secure"),
                  card("Eavesdropper sees", short(ciphertext, 64), "secure"),
                  card("Still visible", "IP addresses · port 443 · site name · size & timing", "warning")]),
        ],
    }


def scene_tls_handshake():
    """0:45 - 1:10  A simplified TLS 1.3 handshake with a real key exchange."""
    keys = tls_handshake.perform_key_exchange()
    nodes = [make_node("client", "Browser", "TLS client", "laptop", "client"),
             make_node("server", "Website", SITE, "server", "server")]
    secret_card = card("Shared secret (computed separately on BOTH sides)",
                       short(keys["client_shared"], 32) + ("  ✔ identical" if keys["secrets_match"] else ""),
                       "secure")
    return {
        "title": "TLS Handshake",
        "start": 45, "end": 70,
        "headline": "Before any data is sent, TLS 1.3 sets up keys and checks identity - in one round trip.",
        "nodes": nodes,
        "steps": [
            step(45, "1 · Client Hello: “I speak TLS 1.3, here are my ciphers and my public key share.”",
                 make_packet("client", "server", "plain", "Client Hello + key share",
                             {"Message": "ClientHello", "Key share (public)": short(keys["client_public"], 24)}),
                 {"client": "active"},
                 [card("Sent openly", "Client public key: " + short(keys["client_public"], 24), "plain")]),
            step(50, "2 · Server Hello: the server picks a cipher and sends its own public key share.",
                 make_packet("server", "client", "plain", "Server Hello + key share",
                             {"Message": "ServerHello", "Key share (public)": short(keys["server_public"], 24)}),
                 {"server": "active"},
                 [card("Sent openly", "Server public key: " + short(keys["server_public"], 24), "plain")]),
            step(55, "3 · Both sides combine their PRIVATE key with the other's PUBLIC key and get the same secret. It never crosses the network (ephemeral Diffie-Hellman).",
                 None, {"client": "secure", "server": "secure"},
                 [secret_card]),
            step(60, "4 · Certificate: the server sends its certificate and signs the handshake, proving it really is " + SITE + ". The browser checks it against trusted CAs.",
                 make_packet("server", "client", "encrypted", "Certificate + signature",
                             {"Message": "Certificate, CertificateVerify, Finished",
                              "Purpose": "Authentication - not encryption of your data"}),
                 {"client": "secure", "server": "secure"},
                 [secret_card, card("Certificate check", "Name ✔  Dates ✔  Signed by trusted CA ✔", "secure")]),
            step(65, "5 · Secure channel ready: every request now travels encrypted with keys derived from that shared secret.",
                 make_packet("client", "server", "encrypted", "Encrypted application data",
                             {"Cipher": "AES-256-GCM", "Key": "Derived from the shared secret (HKDF)"}),
                 {"client": "secure", "server": "secure"},
                 [secret_card, card("Certificate check", "Name ✔  Dates ✔  Signed by trusted CA ✔", "secure"),
                  card("Result", "Encrypted ✔  Tamper-evident ✔  Server verified ✔", "secure")]),
        ],
    }


def scene_mitm():
    """1:10 - 1:45  The attacker in the middle: HTTP vs HTTPS."""
    record = encryption.symmetric_encrypt(TRANSFER)
    tampered = encryption.tamper_with_hex(record["combined_hex"], 4)
    tamper_result = encryption.symmetric_decrypt(record["key_hex"], record["nonce_hex"], tampered)
    fake_chain = certificates.generate_all_certificates()["chains"]["untrusted"]
    cert_result = certificates.verify_chain(fake_chain, SITE, ["Demo Root CA"])
    error_code = cert_result["verdict"]["error_code"] or "certificate rejected"

    nodes = [make_node("victim", "Victim", "192.168.1.20", "laptop", "client"),
             make_node("attacker", "MITM Attacker", "192.168.1.66", "attacker", "attacker"),
             make_node("server", "Website", SITE, "server", "server")]
    return {
        "title": "MITM Attack",
        "start": 70, "end": 105,
        "headline": "The attacker sits between victim and website. Every packet passes through them.",
        "nodes": nodes,
        "steps": [
            step(70, "HTTP · The victim sends a payment. The attacker receives it first and reads it.",
                 make_packet("victim", "attacker", "malicious", TRANSFER,
                             {"Protocol": "HTTP", "Intercepted": "Yes"}, "POST /transfer\n\n" + TRANSFER),
                 {"attacker": "danger"},
                 [card("Victim sent", TRANSFER, "plain"),
                  card("Attacker reads", TRANSFER, "danger")]),
            step(76, "HTTP · The attacker rewrites the message. HTTP has no integrity check, so nothing notices.",
                 None, {"attacker": "danger"},
                 [card("Victim sent", TRANSFER, "plain"),
                  card("Attacker changes it to", TAMPERED_TRANSFER, "danger")]),
            step(81, "HTTP · The website receives the forged payment and processes it.",
                 make_packet("attacker", "server", "malicious", TAMPERED_TRANSFER,
                             {"Protocol": "HTTP", "Modified": "Yes"}, "POST /transfer\n\n" + TAMPERED_TRANSFER),
                 {"attacker": "danger", "server": "warning"},
                 [card("Victim sent", TRANSFER, "plain"),
                  card("Website received", TAMPERED_TRANSFER, "danger")]),
            step(87, "HTTPS · Same attack. Now the attacker only captures ciphertext - it can't read the payment.",
                 make_packet("victim", "attacker", "encrypted", short(record["combined_hex"], 16),
                             {"Protocol": "TLS 1.3", "Encrypted": "Yes (AES-256-GCM)"}, record["combined_hex"]),
                 {"victim": "secure", "attacker": "warning"},
                 [card("Victim sent", TRANSFER + "  (encrypted)", "secure"),
                  card("Attacker sees", short(record["combined_hex"], 48), "secure")]),
            step(93, "HTTPS · If the attacker flips bits, the server's decryption fails the integrity check and the data is rejected.",
                 make_packet("attacker", "server", "malicious", "tampered ciphertext",
                             {"Tampered": "Yes", "Server result": "Authentication tag failed"}, tampered),
                 {"attacker": "danger", "server": "secure"},
                 [card("Server decrypts", "REJECTED - integrity check failed" if not tamper_result["success"] else "accepted",
                       "secure")]),
            step(99, "HTTPS · Pretending to be the website needs a valid certificate. The attacker's fake one fails, so the browser blocks the connection.",
                 make_packet("attacker", "victim", "warning", "Fake certificate",
                             {"Issuer": "Unknown Root CA", "Browser check": "Not trusted"}),
                 {"victim": "secure", "attacker": "inactive"},
                 [card("Browser warning", "Your connection is not private · " + error_code, "warning"),
                  card("Result", "No data sent - impersonation stopped", "secure")]),
        ],
    }


def scene_conclusion():
    """1:45 - 2:00  Summary."""
    nodes = [make_node("client", "Your Browser", "you", "laptop", "client"),
             make_node("server", "Website", SITE, "server", "server")]
    pillars = [card("Confidentiality", "Encryption stops eavesdroppers reading data.", "secure"),
               card("Integrity", "Any modification is detected and rejected.", "secure"),
               card("Authentication", "Certificates prove the server's identity.", "secure")]
    return {
        "title": "Conclusion",
        "start": 105, "end": 120,
        "headline": "HTTPS = HTTP + TLS: three protections in one.",
        "nodes": nodes,
        "steps": [
            step(105, "HTTPS protects data in transit with confidentiality, integrity and authentication.",
                 make_packet("client", "server", "encrypted", "HTTPS",
                             {"Confidentiality": "Yes", "Integrity": "Yes", "Authentication": "Yes"}),
                 {"client": "secure", "server": "secure"}, pillars),
            step(112, "Limits: the padlock doesn't mean a site is honest, and HTTPS can't protect a device that already has malware.",
                 None, {"client": "secure", "server": "secure"},
                 pillars + [card("Remember", "Padlock ≠ trustworthy website · never click through certificate warnings", "warning")]),
        ],
    }


def build_presentation():
    """Return the full two-minute script as one dictionary."""
    scenes = [scene_introduction(), scene_http_vs_https(), scene_tls_handshake(),
              scene_mitm(), scene_conclusion()]
    return {"total_seconds": TOTAL_SECONDS, "scenes": scenes}
