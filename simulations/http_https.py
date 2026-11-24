"""http_https.py - Module One: HTTP vs HTTPS browser simulation."""

from simulations import encryption
from simulations.steps import make_node, make_packet, make_step


# The three devices drawn on the screen, from left to right.
CLIENT = "client"
NETWORK = "network"
SERVER = "server"

# Example (made-up) addresses used in every demonstration.
CLIENT_IP = "192.168.1.20"
SERVER_IP = "203.0.113.10"   # 203.0.113.0/24 is reserved for documentation
SERVER_NAME = "shop.example.com"


def build_http_request(message):
    """Build the raw text of an HTTP POST request containing the message."""
    body = message.replace("\n", "&")
    request_lines = [
        "POST /login HTTP/1.1",
        "Host: " + SERVER_NAME,
        "Content-Type: application/x-www-form-urlencoded",
        "Content-Length: " + str(len(body)),
        "",
        body,
    ]
    return "\n".join(request_lines)


def build_http_response():
    """A short HTTP response the server sends back."""
    return "HTTP/1.1 200 OK\nContent-Type: text/html\n\n<h1>Welcome back!</h1>"


def short_hex(hex_text, length=64):
    """Shorten a long hex string so it fits in a packet label."""
    if len(hex_text) <= length:
        return hex_text
    return hex_text[:length] + "..."


def simulate_transmission(protocol, message, eavesdropper_enabled):
    """Return the full list of steps for sending a message over HTTP or HTTPS."""
    if protocol == "HTTPS":
        return simulate_https(message, eavesdropper_enabled)
    return simulate_http(message, eavesdropper_enabled)


def diagram_nodes(eavesdropper_enabled):
    """The three devices shown left-to-right."""
    if eavesdropper_enabled:
        middle = make_node(NETWORK, "Wi-Fi Eavesdropper", "sniffing public Wi-Fi", "attacker", "attacker")
    else:
        middle = make_node(NETWORK, "Wi-Fi Router", "forwards packets", "router", "router")
    return [
        make_node(CLIENT, "Your Browser", CLIENT_IP, "laptop", "client"),
        middle,
        make_node(SERVER, "Web Server", SERVER_NAME, "server", "server"),
    ]


def simulate_http(message, eavesdropper_enabled):
    """Steps for an unencrypted HTTP transmission."""
    request_text = build_http_request(message)
    steps = []

    steps.append(make_step(
        "1. User submits the form",
        "You typed your details and clicked Log in. The browser will use plain HTTP "
        "because the address starts with http://.",
        highlight={CLIENT: "warning"},
        panels={"address": "http://" + SERVER_NAME + "/login", "secure": False,
                "client_view": message},
    ))

    steps.append(make_step(
        "2. Browser builds an HTTP request",
        "HTTP is plain text. The browser writes your data directly into the request "
        "with no encryption at all.",
        highlight={CLIENT: "warning"},
        panels={"wire_data": request_text},
    ))

    first_hop_details = {
        "Protocol": "HTTP/1.1 over TCP",
        "Source": CLIENT_IP + ":51544",
        "Destination": SERVER_IP + ":80",
        "Encrypted": "No",
    }
    steps.append(make_step(
        "3. Packet travels across the Wi-Fi network",
        "The request leaves your device. Every device it passes through (Wi-Fi router, "
        "ISP equipment) handles readable text.",
        packet=make_packet(CLIENT, NETWORK, "plain", "POST /login (plaintext)",
                           first_hop_details, request_text),
        highlight={CLIENT: "active"},
    ))

    if eavesdropper_enabled:
        steps.append(make_step(
            "4. The eavesdropper reads everything",
            "Someone sniffing the same Wi-Fi captures the packet. Because HTTP has no "
            "encryption, your username and password are fully readable.",
            highlight={NETWORK: "danger"},
            panels={"attacker_view": request_text, "attacker_can_read": True},
        ))
    else:
        steps.append(make_step(
            "4. The router forwards the packet",
            "No attacker is present this time, but the data is still readable by any "
            "device on the path. HTTP offers no protection if someone is listening.",
            highlight={NETWORK: "warning"},
        ))

    steps.append(make_step(
        "5. Packet reaches the web server",
        "The server receives the request exactly as sent. HTTP has no integrity "
        "check, so the server cannot tell if anything was altered on the way.",
        packet=make_packet(NETWORK, SERVER, "plain", "POST /login (plaintext)",
                           first_hop_details, request_text),
        highlight={SERVER: "active"},
        panels={"server_view": message},
    ))

    response_text = build_http_response()
    response_details = {
        "Protocol": "HTTP/1.1 over TCP",
        "Source": SERVER_IP + ":80",
        "Destination": CLIENT_IP + ":51544",
        "Encrypted": "No",
    }
    steps.append(make_step(
        "6. Server replies over HTTP",
        "The response travels back the same way, also as readable text.",
        packet=make_packet(SERVER, NETWORK, "plain", "200 OK (plaintext)",
                           response_details, response_text),
    ))
    steps.append(make_step(
        "7. Browser shows 'Not secure'",
        "The page loads, but the browser warns that the connection is not secure. "
        "Anything sent over HTTP could have been read or changed.",
        packet=make_packet(NETWORK, CLIENT, "plain", "200 OK (plaintext)",
                           response_details, response_text),
        highlight={CLIENT: "warning"},
    ))
    return steps


def simulate_https(message, eavesdropper_enabled):
    """Steps for an HTTPS transmission, using REAL AES-256-GCM encryption."""
    request_text = build_http_request(message)
    # Encrypt the real request text. In real TLS 1.3 the session key comes from
    # the handshake (see Module 2); here we generate a random one.
    encrypted = encryption.symmetric_encrypt(request_text)
    ciphertext = encrypted["combined_hex"]
    steps = []

    steps.append(make_step(
        "1. User submits the form",
        "The address starts with https://, so the browser will protect this data with "
        "TLS before sending anything.",
        highlight={CLIENT: "secure"},
        panels={"address": "https://" + SERVER_NAME + "/login", "secure": True,
                "client_view": message},
    ))

    handshake_details = {
        "Protocol": "TLS 1.3 handshake",
        "Source": CLIENT_IP + ":51544",
        "Destination": SERVER_IP + ":443",
        "Purpose": "Agree on keys and verify the server's certificate",
    }
    steps.append(make_step(
        "2. TLS handshake",
        "Browser and server agree on a fresh session key and the browser checks the "
        "server's certificate. Module 2 shows this handshake in detail.",
        packet=make_packet(CLIENT, SERVER, "encrypted", "TLS handshake",
                           handshake_details, "ClientHello / ServerHello / Certificate ..."),
        highlight={CLIENT: "secure", SERVER: "secure"},
    ))

    steps.append(make_step(
        "3. Browser encrypts the request",
        "The same HTTP request is now encrypted with AES-256-GCM using the session key. "
        "The output below is real ciphertext produced by Python.",
        highlight={CLIENT: "secure"},
        panels={"wire_data": "Plaintext (inside your browser only):\n" + request_text +
                "\n\nEncrypted TLS record (what actually leaves your device):\n" + ciphertext},
    ))

    encrypted_details = {
        "Protocol": "TLS 1.3 Application Data",
        "Source": CLIENT_IP + ":51544  (visible)",
        "Destination": SERVER_IP + ":443  (visible)",
        "Cipher": "AES-256-GCM (authenticated encryption)",
        "Encrypted": "Yes - only the payload; addresses and ports remain visible",
        "Ciphertext length": str(encrypted["ciphertext_length"]) + " bytes",
    }
    steps.append(make_step(
        "4. Encrypted packet crosses the network",
        "Routers can still see where the packet is going (IP address and port 443), "
        "but the content is unreadable ciphertext.",
        packet=make_packet(CLIENT, NETWORK, "encrypted", "TLS Application Data",
                           encrypted_details, ciphertext),
        highlight={CLIENT: "secure"},
    ))

    if eavesdropper_enabled:
        attacker_view = ("Visible metadata:\n  Source: " + CLIENT_IP + ":51544\n"
                         "  Destination: " + SERVER_IP + ":443\n"
                         "  Server name (SNI, sent during handshake): " + SERVER_NAME + "\n"
                         "  Size: " + str(encrypted["ciphertext_length"]) + " bytes\n\n"
                         "Payload:\n" + ciphertext)
        steps.append(make_step(
            "5. The eavesdropper captures only ciphertext",
            "The sniffer records the packet but cannot read it without the session key. "
            "It can still see metadata such as IP addresses, ports, timing and size.",
            highlight={NETWORK: "danger"},
            panels={"attacker_view": attacker_view, "attacker_can_read": False},
        ))
    else:
        steps.append(make_step(
            "5. The router forwards the encrypted packet",
            "The router only needs the address to forward the packet. It never sees "
            "the plaintext.",
            highlight={NETWORK: "active"},
        ))

    steps.append(make_step(
        "6. Server decrypts and verifies",
        "The server uses the same session key to decrypt. The GCM authentication tag "
        "proves the data was not modified on the way.",
        packet=make_packet(NETWORK, SERVER, "encrypted", "TLS Application Data",
                           encrypted_details, ciphertext),
        highlight={SERVER: "secure"},
        panels={"server_view": message},
    ))

    response_cipher = encryption.symmetric_encrypt(build_http_response())["combined_hex"]
    response_details = {
        "Protocol": "TLS 1.3 Application Data",
        "Source": SERVER_IP + ":443",
        "Destination": CLIENT_IP + ":51544",
        "Encrypted": "Yes",
    }
    steps.append(make_step(
        "7. Encrypted response returns",
        "The reply is encrypted too. Your browser shows the padlock: the connection is "
        "encrypted and the server proved it owns " + SERVER_NAME + ". The padlock does "
        "NOT prove the website itself is honest.",
        packet=make_packet(SERVER, CLIENT, "encrypted", "TLS Application Data",
                           response_details, response_cipher),
        highlight={CLIENT: "secure", SERVER: "secure"},
    ))
    return steps


# Static comparison table shown on the page (kept in Python so all
# educational facts live in one place).
COMPARISON_TABLE = [
    {"feature": "Full name", "http": "HyperText Transfer Protocol",
     "https": "HyperText Transfer Protocol Secure (HTTP over TLS)"},
    {"feature": "Default port", "http": "80", "https": "443"},
    {"feature": "Confidentiality", "http": "None - data travels as readable text",
     "https": "Data is encrypted with a session key"},
    {"feature": "Integrity", "http": "None - changes go unnoticed",
     "https": "Authenticated encryption detects any modification"},
    {"feature": "Server authentication", "http": "None - you cannot tell who answered",
     "https": "Certificate proves the server controls the domain"},
    {"feature": "Browser indicator", "http": "'Not secure' warning",
     "https": "Padlock / connection details (not a guarantee of honesty)"},
]
