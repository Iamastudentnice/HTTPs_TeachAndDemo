"""http_https.py - Module One: HTTP vs HTTPS browser simulation."""

from simulations import encryption
from simulations.steps import make_node, make_packet, make_step


# Device ids used in the diagram (left to right).
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
        steps = simulate_https(message, eavesdropper_enabled)
    else:
        steps = simulate_http(message, eavesdropper_enabled)

    # Number the steps here, so adding or removing a step never breaks the numbering.
    for number, step in enumerate(steps, start=1):
        step["title"] = str(number) + ". " + step["title"]
    return steps


def diagram_nodes(eavesdropper_enabled):
    """The devices shown left-to-right.

    Without the observer it is just your browser and the website.
    With the observer turned on, the eavesdropper sits in the middle.
    """
    browser = make_node(CLIENT, "Your Browser", CLIENT_IP, "laptop", "client")
    website = make_node(SERVER, "Website", SERVER_NAME, "server", "server")
    if not eavesdropper_enabled:
        return [browser, website]
    observer = make_node(NETWORK, "Wi-Fi Eavesdropper", "watching public Wi-Fi", "attacker", "attacker")
    return [browser, observer, website]


def simulate_http(message, eavesdropper_enabled):
    """Steps for sending a message over plain HTTP (no encryption)."""
    request_text = build_http_request(message)
    steps = []

    steps.append(make_step(
        "You press Log in",
        "The address starts with http://, so your browser will send your details "
        "using HTTP, without encryption.",
        highlight={CLIENT: "warning"},
        panels={"address": "http://" + SERVER_NAME + "/login", "secure": False,
                "client_view": message},
    ))

    steps.append(make_step(
        "Your browser writes the message",
        "Your details go straight into the message as normal, readable text.",
        highlight={CLIENT: "warning"},
        panels={"wire_data": request_text, "network_view": request_text, "network_can_read": True},
    ))

    request_details = {
        "Protocol": "HTTP/1.1 over TCP",
        "Source": CLIENT_IP + ":51544",
        "Destination": SERVER_IP + ":80",
        "Encrypted": "No",
    }
    request_packet = "POST /login (readable)"

    if eavesdropper_enabled:
        steps.append(make_step(
            "The message travels over the Wi-Fi",
            "On its way to the website, the message passes the eavesdropper on the same Wi-Fi.",
            packet=make_packet(CLIENT, NETWORK, "plain", request_packet, request_details, request_text),
            highlight={CLIENT: "active"},
        ))
        steps.append(make_step(
            "The eavesdropper reads it",
            "Because nothing is encrypted, the eavesdropper can read your username and "
            "password. This is a passive attack: they only watch, they change nothing.",
            highlight={NETWORK: "danger"},
            panels={"attacker_view": request_text, "attacker_can_read": True},
        ))
        steps.append(make_step(
            "The website receives your details",
            "The website gets the message as normal. Neither you nor the website can "
            "tell that someone else read it.",
            packet=make_packet(NETWORK, SERVER, "plain", request_packet, request_details, request_text),
            highlight={SERVER: "active"},
            panels={"server_view": message},
        ))
    else:
        steps.append(make_step(
            "The message travels to the website",
            "It crosses several networks on the way, such as your Wi-Fi and your internet "
            "provider. Anyone watching any of them could read it.",
            packet=make_packet(CLIENT, SERVER, "plain", request_packet, request_details, request_text),
            highlight={CLIENT: "active"},
        ))
        steps.append(make_step(
            "The website receives your details",
            "The website's server reads your message. HTTP has no way to show whether "
            "it was read or changed on the way.",
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
        "The website replies",
        "The reply comes back the same way, also as readable text.",
        packet=make_packet(SERVER, CLIENT, "plain", "200 OK (readable)", response_details, response_text),
    ))
    steps.append(make_step(
        "Your browser shows \"Not secure\"",
        "The page loads, but the browser warns you: anything sent over this connection "
        "could have been read along the way.",
        highlight={CLIENT: "warning"},
    ))
    return steps


def simulate_https(message, eavesdropper_enabled):
    """Steps for sending the same message over HTTPS, using real AES-256-GCM encryption."""
    request_text = build_http_request(message)
    # Real TLS gets this key from the handshake (Lab 02). Here we just make a random one.
    encrypted = encryption.symmetric_encrypt(request_text)
    ciphertext = encrypted["combined_hex"]
    steps = []

    steps.append(make_step(
        "You press Log in",
        "The address starts with https://, so your browser will encrypt your details "
        "before they leave your device.",
        highlight={CLIENT: "secure"},
        panels={"address": "https://" + SERVER_NAME + "/login", "secure": True,
                "client_view": message},
    ))

    handshake_details = {
        "Protocol": "TLS 1.3 handshake",
        "Source": CLIENT_IP + ":51544",
        "Destination": SERVER_IP + ":443",
        "Purpose": "Agree on keys and check the website's certificate",
    }
    steps.append(make_step(
        "Browser and website set up a protected connection",
        "They agree on a secret key, and the website shows a certificate (an ID that "
        "proves it really is " + SERVER_NAME + "). This uses TLS, the technology behind HTTPS.",
        packet=make_packet(CLIENT, SERVER, "encrypted", "TLS handshake",
                           handshake_details, "ClientHello / ServerHello / Certificate ..."),
        highlight={CLIENT: "secure", SERVER: "secure"},
    ))

    # What someone on the network path can still see: where it goes, not what it says.
    network_view = ("Still visible:\n  From: " + CLIENT_IP + "\n  To: " + SERVER_IP + " (port 443)\n"
                    "  Website name: " + SERVER_NAME + "\n"
                    "  Size: " + str(encrypted["ciphertext_length"]) + " bytes\n\n"
                    "Your details (encrypted):\n" + ciphertext)
    steps.append(make_step(
        "Your browser encrypts the message",
        "The same message is scrambled with the secret key. Only the website has the "
        "key to unscramble it. The scrambled text below is real encryption done by Python.",
        highlight={CLIENT: "secure"},
        panels={"wire_data": "Before encryption (only inside your browser):\n" + request_text +
                "\n\nAfter encryption (what actually leaves your device):\n" + ciphertext,
                "network_view": network_view, "network_can_read": False},
    ))

    encrypted_details = {
        "Protocol": "TLS 1.3 Application Data",
        "Source": CLIENT_IP + ":51544  (visible)",
        "Destination": SERVER_IP + ":443  (visible)",
        "Cipher": "AES-256-GCM (authenticated encryption)",
        "Encrypted": "Yes - only the contents; addresses and ports remain visible",
        "Ciphertext length": str(encrypted["ciphertext_length"]) + " bytes",
    }

    if eavesdropper_enabled:
        steps.append(make_step(
            "The encrypted message travels over the Wi-Fi",
            "It passes the eavesdropper, just like before.",
            packet=make_packet(CLIENT, NETWORK, "encrypted", "TLS Application Data",
                               encrypted_details, ciphertext),
            highlight={CLIENT: "secure"},
        ))
        steps.append(make_step(
            "The eavesdropper sees only scrambled text",
            "Without the key they cannot read your details. They can still see that you "
            "are talking to " + SERVER_NAME + ", and when and how much.",
            highlight={NETWORK: "danger"},
            panels={"attacker_view": network_view, "attacker_can_read": False},
        ))
        steps.append(make_step(
            "The website unscrambles your details",
            "The website uses the key to read the message. The encryption also lets it "
            "detect if anyone changed the message on the way.",
            packet=make_packet(NETWORK, SERVER, "encrypted", "TLS Application Data",
                               encrypted_details, ciphertext),
            highlight={SERVER: "secure"},
            panels={"server_view": message},
        ))
    else:
        steps.append(make_step(
            "The encrypted message travels to the website",
            "Networks on the way can see where it is going, but not what it says.",
            packet=make_packet(CLIENT, SERVER, "encrypted", "TLS Application Data",
                               encrypted_details, ciphertext),
            highlight={CLIENT: "secure"},
        ))
        steps.append(make_step(
            "The website unscrambles your details",
            "The website uses the key to read the message. The encryption also lets it "
            "detect if anyone changed the message on the way.",
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
        "The reply is encrypted too",
        "Your browser shows a padlock. It means the connection is protected and the "
        "certificate matched " + SERVER_NAME + ". It does not mean the website itself "
        "is trustworthy.",
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
     "https": "Padlock - the connection is protected, not a promise the site is honest"},
    {"feature": "Still visible to the network", "http": "Everything",
     "https": "Which website, IP addresses, timing and size - but not the contents"},
]
