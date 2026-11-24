"""packet_inspection.py - Module Six: a Wireshark-style packet inspection simulator."""

from simulations import encryption

CLIENT_IP = "192.168.1.20"
DNS_SERVER_IP = "192.168.1.1"
SERVER_IP = "203.0.113.10"
SITE = "shop.example.com"
CLIENT_PORT = 51544

# Header sizes in bytes, used to calculate realistic packet lengths.
ETHERNET_HEADER = 14
IP_HEADER = 20
TCP_HEADER = 20
UDP_HEADER = 8
TLS_RECORD_HEADER = 5

# Captures are generated once and then reused, so the ciphertext does not
# change every time the user applies a filter.
_capture_cache = {}


# --- Helpers ---

def hex_dump(data):
    """Format bytes like Wireshark's bottom panel: offset, hex bytes, ASCII."""
    lines = []
    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]
        hex_part = " ".join(format(byte, "02x") for byte in chunk)
        ascii_part = ""
        for byte in chunk:
            if 32 <= byte < 127:
                ascii_part += chr(byte)
            else:
                ascii_part += "."
        lines.append(format(offset, "04x") + "  " + hex_part.ljust(48) + "  " + ascii_part)
    return "\n".join(lines)


def make_packet(number, time, direction, source_ip, destination_ip, protocol,
                source_port, destination_port, transport, payload_bytes, info,
                application_layer, readable):
    """Build one packet dictionary, calculating its total length."""
    if transport == "UDP":
        transport_header = UDP_HEADER
    else:
        transport_header = TCP_HEADER
    length = ETHERNET_HEADER + IP_HEADER + transport_header + len(payload_bytes)

    layers = [
        {"name": "Ethernet II", "visible": True,
         "fields": [["Source MAC", "aa:bb:cc:00:00:20" if direction == "out" else "00:11:22:33:44:01"],
                    ["Destination MAC", "00:11:22:33:44:01" if direction == "out" else "aa:bb:cc:00:00:20"]]},
        {"name": "Internet Protocol v4", "visible": True,
         "fields": [["Source IP", source_ip], ["Destination IP", destination_ip],
                    ["Time to live", "64"], ["Protocol", transport]]},
        {"name": "Transmission Control Protocol" if transport == "TCP" else "User Datagram Protocol",
         "visible": True,
         "fields": [["Source port", str(source_port)], ["Destination port", str(destination_port)]]},
    ]
    if application_layer:
        layers.append(application_layer)

    return {
        "number": number,
        "time": format(time, ".3f"),
        "direction": direction,
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "protocol": protocol,
        "transport": transport,
        "source_port": source_port,
        "destination_port": destination_port,
        "length": length,
        "info": info,
        "layers": layers,
        "payload_readable": readable,
        "payload_text": payload_bytes.decode("utf-8", errors="replace") if readable else "",
        "hex_dump": hex_dump(payload_bytes) if payload_bytes else "(no payload)",
    }


def tcp_handshake(start_number, start_time, server_port):
    """The three TCP packets that open every connection (SYN, SYN-ACK, ACK)."""
    out_ports = (CLIENT_PORT, server_port)
    in_ports = (server_port, CLIENT_PORT)
    return [
        make_packet(start_number, start_time, "out", CLIENT_IP, SERVER_IP, "TCP", out_ports[0], out_ports[1],
                    "TCP", b"", str(CLIENT_PORT) + " → " + str(server_port) + " [SYN]", None, True),
        make_packet(start_number + 1, start_time + 0.021, "in", SERVER_IP, CLIENT_IP, "TCP", in_ports[0], in_ports[1],
                    "TCP", b"", str(server_port) + " → " + str(CLIENT_PORT) + " [SYN, ACK]", None, True),
        make_packet(start_number + 2, start_time + 0.022, "out", CLIENT_IP, SERVER_IP, "TCP", out_ports[0], out_ports[1],
                    "TCP", b"", str(CLIENT_PORT) + " → " + str(server_port) + " [ACK]", None, True),
    ]


def dns_packets():
    """A DNS lookup."""
    query = ("Standard query A " + SITE).encode("ascii")
    answer = ("Standard query response A " + SITE + " A " + SERVER_IP).encode("ascii")
    return [
        make_packet(1, 0.000, "out", CLIENT_IP, DNS_SERVER_IP, "DNS", 53001, 53, "UDP", query,
                    "Standard query A " + SITE,
                    {"name": "Domain Name System", "visible": True,
                     "fields": [["Query", SITE + " (type A)"],
                                ["Encrypted", "No - visible to anyone on the path"]]}, True),
        make_packet(2, 0.014, "in", DNS_SERVER_IP, CLIENT_IP, "DNS", 53, 53001, "UDP", answer,
                    "Standard query response A " + SERVER_IP,
                    {"name": "Domain Name System", "visible": True,
                     "fields": [["Answer", SITE + " → " + SERVER_IP]]}, True),
    ]


# --- Building the two example captures ---

def build_http_capture():
    """An example HTTP login - every byte of the request is readable."""
    form_body = "username=John+Doe&password=example123"
    request = ("POST /login HTTP/1.1\r\nHost: " + SITE + "\r\n"
               "Content-Type: application/x-www-form-urlencoded\r\n"
               "Content-Length: " + str(len(form_body)) + "\r\n\r\n" + form_body).encode("ascii")
    response = ("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nSet-Cookie: session=7f3a91c2\r\n\r\n"
                "<h1>Welcome back, John Doe</h1>").encode("ascii")

    packets = dns_packets() + tcp_handshake(3, 0.030, 80)
    packets.append(make_packet(6, 0.055, "out", CLIENT_IP, SERVER_IP, "HTTP", CLIENT_PORT, 80, "TCP",
                               request, "POST /login HTTP/1.1  (application/x-www-form-urlencoded)",
                               {"name": "Hypertext Transfer Protocol", "visible": True,
                                "fields": [["Request", "POST /login HTTP/1.1"], ["Host", SITE],
                                           ["Form data", form_body]]}, True))
    packets.append(make_packet(7, 0.077, "in", SERVER_IP, CLIENT_IP, "TCP", 80, CLIENT_PORT, "TCP", b"",
                               "80 → " + str(CLIENT_PORT) + " [ACK]", None, True))
    packets.append(make_packet(8, 0.102, "in", SERVER_IP, CLIENT_IP, "HTTP", 80, CLIENT_PORT, "TCP",
                               response, "HTTP/1.1 200 OK  (text/html)",
                               {"name": "Hypertext Transfer Protocol", "visible": True,
                                "fields": [["Status", "200 OK"], ["Set-Cookie", "session=7f3a91c2"]]}, True))
    return packets


def tls_record(content):
    """Encrypt content with real AES-GCM and add a 5-byte TLS record header."""
    encrypted = encryption.symmetric_encrypt(content)
    ciphertext = bytes.fromhex(encrypted["combined_hex"])
    header = bytes([23, 3, 3]) + len(ciphertext).to_bytes(2, "big")
    return header + ciphertext


def encrypted_layer(hidden_description):
    """The application layer as an observer sees it in TLS 1.3."""
    return {"name": "Transport Layer Security", "visible": True,
            "fields": [["Record type", "Application Data (23)"], ["Version on wire", "TLS 1.2 (0x0303) - legacy value; real version is 1.3"],
                       ["Encrypted payload", "Unreadable without the session key"],
                       ["Hidden inside", hidden_description]]}


def build_https_capture():
    """An example HTTPS login - the HTTP request is encrypted inside TLS."""
    packets = dns_packets() + tcp_handshake(3, 0.030, 443)

    client_hello = ("\x16\x03\x01ClientHello SNI=" + SITE + " ALPN=h2,http/1.1 key_share=x25519").encode("latin-1")
    packets.append(make_packet(6, 0.052, "out", CLIENT_IP, SERVER_IP, "TLSv1.3", CLIENT_PORT, 443, "TCP",
                               client_hello, "Client Hello (SNI=" + SITE + ")",
                               {"name": "Transport Layer Security", "visible": True,
                                "fields": [["Handshake type", "Client Hello (not encrypted)"],
                                           ["Server Name (SNI)", SITE + "  ← visible to observers"],
                                           ["Supported versions", "TLS 1.3, TLS 1.2"],
                                           ["Key share", "x25519 public key (safe to reveal)"]]}, False))

    server_hello = b"\x16\x03\x03ServerHello cipher=TLS_AES_256_GCM_SHA384 key_share=x25519"
    packets.append(make_packet(7, 0.075, "in", SERVER_IP, CLIENT_IP, "TLSv1.3", 443, CLIENT_PORT, "TCP",
                               server_hello, "Server Hello, Change Cipher Spec",
                               {"name": "Transport Layer Security", "visible": True,
                                "fields": [["Handshake type", "Server Hello (not encrypted)"],
                                           ["Cipher suite", "TLS_AES_256_GCM_SHA384"],
                                           ["Change Cipher Spec", "Dummy record kept only for middlebox compatibility"]]}, False))

    certificate_record = tls_record("EncryptedExtensions Certificate CN=" + SITE + " CertificateVerify Finished")
    packets.append(make_packet(8, 0.076, "in", SERVER_IP, CLIENT_IP, "TLSv1.3", 443, CLIENT_PORT, "TCP",
                               certificate_record, "Application Data (encrypted handshake)",
                               encrypted_layer("Certificate, CertificateVerify, Finished - TLS 1.3 encrypts the certificate"),
                               False))

    finished_record = tls_record("Client Finished")
    packets.append(make_packet(9, 0.098, "out", CLIENT_IP, SERVER_IP, "TLSv1.3", CLIENT_PORT, 443, "TCP",
                               finished_record, "Change Cipher Spec, Application Data",
                               encrypted_layer("Client Finished message"), False))

    request_record = tls_record("POST /login HTTP/1.1\r\nHost: " + SITE + "\r\n\r\nusername=John+Doe&password=example123")
    packets.append(make_packet(10, 0.099, "out", CLIENT_IP, SERVER_IP, "TLSv1.3", CLIENT_PORT, 443, "TCP",
                               request_record, "Application Data",
                               encrypted_layer("The HTTP POST /login request with the username and password"),
                               False))

    response_record = tls_record("HTTP/1.1 200 OK\r\nSet-Cookie: session=7f3a91c2\r\n\r\n<h1>Welcome back, John Doe</h1>")
    packets.append(make_packet(11, 0.131, "in", SERVER_IP, CLIENT_IP, "TLSv1.3", 443, CLIENT_PORT, "TCP",
                               response_record, "Application Data",
                               encrypted_layer("The HTTP 200 OK response, including the session cookie"),
                               False))
    return packets


def get_capture(mode):
    """Return the cached capture for "HTTP" or "HTTPS"."""
    if mode not in ("HTTP", "HTTPS"):
        mode = "HTTP"
    if mode not in _capture_cache:
        if mode == "HTTP":
            _capture_cache[mode] = build_http_capture()
        else:
            _capture_cache[mode] = build_https_capture()
    return _capture_cache[mode]


# --- Display filters (a small subset of Wireshark's syntax) ---

SUPPORTED_FILTERS = [
    "http", "tls", "dns", "tcp", "udp",
    "ip.addr == 203.0.113.10", "ip.src == 192.168.1.20", "ip.dst == 192.168.1.20",
    "tcp.port == 443", "tcp.port == 80", "udp.port == 53",
    "tcp and ip.dst == 203.0.113.10",
]


def packet_matches_condition(packet, condition):
    """Check ONE filter condition such as 'tls' or 'tcp.port == 443'."""
    condition = condition.strip().lower()

    # Protocol names on their own
    if condition == "http":
        return packet["protocol"] == "HTTP"
    if condition in ("tls", "ssl"):
        return packet["protocol"].startswith("TLS")
    if condition == "dns":
        return packet["protocol"] == "DNS"
    if condition == "tcp":
        return packet["transport"] == "TCP"
    if condition == "udp":
        return packet["transport"] == "UDP"

    # Field comparisons: field == value
    if "==" not in condition:
        return None
    field, value = [part.strip() for part in condition.split("==", 1)]

    if field == "ip.addr":
        return value in (packet["source_ip"], packet["destination_ip"])
    if field == "ip.src":
        return packet["source_ip"] == value
    if field == "ip.dst":
        return packet["destination_ip"] == value
    if field in ("tcp.port", "udp.port"):
        wanted_transport = field.split(".")[0].upper()
        ports = (str(packet["source_port"]), str(packet["destination_port"]))
        return packet["transport"] == wanted_transport and value in ports
    return None


def filter_packets(packets, filter_text):
    """Apply a display filter."""
    filter_text = (filter_text or "").strip()
    if filter_text == "":
        return packets, ""

    conditions = filter_text.lower().replace("&&", " and ").split(" and ")
    matching = []
    for packet in packets:
        keep = True
        for condition in conditions:
            result = packet_matches_condition(packet, condition)
            if result is None:
                return [], "Unsupported filter: '" + condition.strip() + "'. Try one of the examples."
            if not result:
                keep = False
        if keep:
            matching.append(packet)
    return matching, ""


def visibility_summary(mode):
    """What a network observer can and cannot see in each mode."""
    if mode == "HTTPS":
        return {
            "visible": ["Source and destination IP addresses", "Ports (443 reveals HTTPS)",
                        "DNS query for " + SITE + " (unless DNS-over-HTTPS is used)",
                        "Server name in the ClientHello SNI (unless Encrypted Client Hello is used)",
                        "Packet sizes, counts and timing", "TCP handshake and TLS version negotiation"],
            "hidden": ["The URL path (/login)", "HTTP headers and cookies", "Usernames and passwords",
                       "Page content", "The certificate itself (encrypted in TLS 1.3)"],
        }
    return {
        "visible": ["Everything: IP addresses, ports, DNS", "Full URL and HTTP headers",
                    "Usernames, passwords and cookies", "Complete page content"],
        "hidden": ["Nothing - HTTP provides no confidentiality"],
    }
