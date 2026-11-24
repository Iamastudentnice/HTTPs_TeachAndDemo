"""mitm.py - Module Five: Man-in-the-Middle (MITM) Attack Laboratory."""

from simulations import certificates, encryption
from simulations.steps import make_node, make_packet, make_step

VICTIM = "victim"
ATTACKER = "attacker"
SERVER = "server"

VICTIM_IP = "192.168.1.20"
ATTACKER_IP = "192.168.1.66"
SERVER_IP = "203.0.113.10"
SITE = certificates.SITE_NAME

# The scenarios users can choose, in the order they appear on the page.
SCENARIOS = {
    "normal_http": "Normal HTTP",
    "normal_https": "Normal HTTPS",
    "http_mitm": "A · HTTP + MITM",
    "https_mitm": "B · HTTPS + MITM",
    "cert_spoof": "C · Fake certificate",
    "ssl_strip": "D · TLS stripping",
    "arp": "E · ARP spoofing",
}

# One-line summaries shown under the scenario buttons (kept short on purpose).
SCENARIO_NOTES = {
    "normal_http": {"goal": "Baseline: HTTP through an honest router. It works - but only because nobody is listening.",
                    "defence": "Nothing protects HTTP traffic. Any device on the path could read or change it."},
    "normal_https": {"goal": "Baseline: HTTPS through an honest router. The router forwards ciphertext.",
                     "defence": "TLS gives confidentiality, integrity and server authentication end to end."},
    "http_mitm": {"goal": "The attacker reads the plaintext login and can rewrite it before the server sees it.",
                  "defence": "Use HTTPS. HTTP has no encryption and no integrity check."},
    "https_mitm": {"goal": "Same attacker position, but TLS is in use. Passive interception yields only ciphertext; tampering is detected.",
                   "defence": "TLS stops passive reading and modification. Active interception still works if a user "
                              "clicks through a certificate warning or a malicious root CA is installed (see C)."},
    "cert_spoof": {"goal": "The attacker impersonates the server with its own certificate. Will the browser accept it?",
                   "defence": "Certificate validation (name, dates, signature, trusted root). Never click through warnings; "
                              "protect the device's trust store."},
    "ssl_strip": {"goal": "The attacker keeps the victim on HTTP while it talks HTTPS to the real server.",
                  "defence": "HSTS (preloaded), HTTPS-Only Mode, and always using https:// links and bookmarks."},
    "arp": {"goal": "On a local network the attacker lies in ARP replies so traffic is delivered to its MAC address.",
            "defence": "Dynamic ARP Inspection, static ARP entries, port security, and end-to-end encryption (TLS/VPN)."},
}

CERT_PROBLEMS = {
    "mismatch": "Certificate for the wrong domain",
    "expired": "Expired certificate",
    "untrusted": "Self-made CA (not trusted)",
    "bad_signature": "Forged signature",
    "attacker_trusted": "Attacker's CA installed on victim device",
}


# --- Small helpers ---

def diagram_nodes(attacker_active):
    """Return the three devices."""
    if attacker_active:
        middle = make_node(ATTACKER, "MITM Attacker", ATTACKER_IP, "attacker", "attacker")
    else:
        middle = make_node(ATTACKER, "Router", "honest network device", "router", "router")
    return [
        make_node(VICTIM, "Victim Browser", VICTIM_IP, "laptop", "client"),
        middle,
        make_node(SERVER, "Web Server", SITE, "server", "server"),
    ]


def build_request(message):
    """Wrap the user's message in a simple HTTP POST request."""
    body = message.replace("\n", "&")
    return ("POST /login HTTP/1.1\nHost: " + SITE + "\n"
            "Content-Type: application/x-www-form-urlencoded\n\n" + body)


def modify_message(original, find_text, replace_text):
    """The attacker's edit: replace one piece of text with another."""
    if find_text and find_text in original:
        return original.replace(find_text, replace_text), True
    return original, False


def details(protocol, source, destination, encrypted, extra=None):
    """Build the details dictionary shown when a packet is clicked."""
    info = {"Protocol": protocol, "Source": source, "Destination": destination,
            "Encrypted": encrypted}
    if extra:
        info.update(extra)
    return info


# --- Normal (no attacker) scenarios ---

def normal_http(message):
    """HTTP through an honest router: works, but is readable by anyone on the path."""
    request = build_request(message)
    info = details("HTTP", VICTIM_IP + ":51544", SERVER_IP + ":80", "No")
    return [
        make_step("1. Victim sends the form over HTTP",
                  "The browser sends readable text. Nobody is attacking, but nothing protects it.",
                  highlight={VICTIM: "warning"},
                  panels={"address": "http://" + SITE + "/login", "secure": False, "victim_sent": message}),
        make_step("2. Packet reaches the router",
                  "The honest router just forwards it. It COULD read it - HTTP relies on every "
                  "device on the path being trustworthy.",
                  packet=make_packet(VICTIM, ATTACKER, "plain", "POST /login", info, request)),
        make_step("3. Server receives the request",
                  "The message arrives unchanged, by luck rather than by protection.",
                  packet=make_packet(ATTACKER, SERVER, "plain", "POST /login", info, request),
                  highlight={SERVER: "active"},
                  panels={"server_received": message}),
    ]


def normal_https(message):
    """HTTPS through an honest router: encrypted end to end."""
    request = build_request(message)
    record = encryption.symmetric_encrypt(request)
    info = details("TLS 1.3 Application Data", VICTIM_IP + ":51544", SERVER_IP + ":443",
                   "Yes (AES-256-GCM)")
    return [
        make_step("1. TLS handshake",
                  "Browser and server agree on session keys and the certificate is verified.",
                  packet=make_packet(VICTIM, SERVER, "encrypted", "TLS handshake",
                                     details("TLS 1.3", VICTIM_IP, SERVER_IP, "Key exchange")),
                  highlight={VICTIM: "secure", SERVER: "secure"},
                  panels={"address": "https://" + SITE + "/login", "secure": True, "victim_sent": message}),
        make_step("2. Encrypted data passes the router",
                  "The router forwards ciphertext. It can see addresses and ports, not the content.",
                  packet=make_packet(VICTIM, ATTACKER, "encrypted", "Application Data", info,
                                     record["combined_hex"]),
                  panels={"wire": record["combined_hex"]}),
        make_step("3. Server decrypts the request",
                  "Only the server holds the session key, so only it can read the message.",
                  packet=make_packet(ATTACKER, SERVER, "encrypted", "Application Data", info,
                                     record["combined_hex"]),
                  highlight={SERVER: "secure"},
                  panels={"server_received": message}),
    ]


# --- Scenario A - HTTP interception ---

def http_mitm(message, attacker_modifies, find_text, replace_text):
    """The attacker reads (and optionally rewrites) unencrypted HTTP."""
    request = build_request(message)
    modified_message, was_changed = modify_message(message, find_text, replace_text)
    if not attacker_modifies:
        modified_message, was_changed = message, False
    modified_request = build_request(modified_message)

    steps = [
        make_step("1. Victim submits the form",
                  "The site uses http://, so the form is sent as plain text.",
                  highlight={VICTIM: "warning"},
                  panels={"address": "http://" + SITE + "/login", "secure": False, "victim_sent": message}),
        make_step("2. Traffic flows into the attacker",
                  "The attacker sits on the path (e.g. via ARP spoofing or a rogue Wi-Fi hotspot). "
                  "Every packet now passes through them.",
                  packet=make_packet(VICTIM, ATTACKER, "malicious", "POST /login (plaintext)",
                                     details("HTTP", VICTIM_IP + ":51544", SERVER_IP + ":80", "No",
                                             {"Intercepted": "Yes - by " + ATTACKER_IP}), request),
                  highlight={ATTACKER: "danger"}),
        make_step("3. Attacker reads the message",
                  "No decryption is needed. The username and password are readable immediately.",
                  highlight={ATTACKER: "danger"},
                  panels={"attacker_saw": request, "attacker_can_read": True}),
    ]

    if attacker_modifies and was_changed:
        steps.append(make_step(
            "4. Attacker modifies the message",
            "The attacker replaces '" + find_text + "' with '" + replace_text + "'. HTTP has no "
            "integrity protection, so nothing will detect this.",
            highlight={ATTACKER: "danger"},
            panels={"original": message, "modified": modified_message, "was_modified": True}))
    elif attacker_modifies:
        steps.append(make_step(
            "4. Attacker tries to modify the message",
            "The text '" + find_text + "' was not found, so the message is forwarded unchanged. "
            "The attacker could still have rewritten anything.",
            highlight={ATTACKER: "warning"},
            panels={"original": message, "modified": message, "was_modified": False}))
    else:
        steps.append(make_step(
            "4. Attacker silently copies the data",
            "A passive attacker just records the credentials and forwards the packet so the "
            "victim notices nothing.",
            highlight={ATTACKER: "danger"}))

    steps.append(make_step(
        "5. Attacker forwards to the server",
        "The server receives whatever the attacker sends and has no way to know it was changed.",
        packet=make_packet(ATTACKER, SERVER, "malicious",
                           "POST /login (modified)" if was_changed else "POST /login (copied)",
                           details("HTTP", VICTIM_IP + ":51544 (spoofed)", SERVER_IP + ":80", "No",
                                   {"Modified": "Yes" if was_changed else "No"}), modified_request),
        highlight={SERVER: "warning"},
        panels={"server_received": modified_message}))

    steps.append(make_step(
        "6. Response returns through the attacker",
        "The reply also passes the attacker, who could inject malicious scripts into the page.",
        packet=make_packet(SERVER, VICTIM, "malicious", "200 OK (via attacker)",
                           details("HTTP", SERVER_IP + ":80", VICTIM_IP + ":51544", "No"),
                           "HTTP/1.1 200 OK\n\n<h1>Welcome!</h1>"),
        highlight={VICTIM: "warning"}))
    return steps


# --- Scenario B - HTTPS under interception ---

def https_mitm(message, attacker_modifies):
    """The attacker is on the path but the traffic is protected by TLS."""
    request = build_request(message)
    key = encryption.generate_symmetric_key()
    record = encryption.symmetric_encrypt(request, key)
    info = details("TLS 1.3 Application Data", VICTIM_IP + ":51544", SERVER_IP + ":443",
                   "Yes (AES-256-GCM)", {"Intercepted": "Yes - captured by " + ATTACKER_IP})

    steps = [
        make_step("1. TLS handshake passes through the attacker",
                  "The attacker relays the handshake but cannot change it: the server's certificate "
                  "and signature prove its identity, and Diffie-Hellman means the session key is "
                  "never sent.",
                  packet=make_packet(VICTIM, SERVER, "encrypted", "TLS handshake (relayed)",
                                     details("TLS 1.3", VICTIM_IP, SERVER_IP, "Key exchange")),
                  highlight={VICTIM: "secure", SERVER: "secure"},
                  panels={"address": "https://" + SITE + "/login", "secure": True, "victim_sent": message}),
        make_step("2. Browser encrypts the request",
                  "The login request is encrypted with the session key (real AES-256-GCM output below).",
                  highlight={VICTIM: "secure"},
                  panels={"wire": record["combined_hex"]}),
        make_step("3. Attacker captures the packet",
                  "The packet still flows through the attacker - interception is possible - but "
                  "the payload is ciphertext.",
                  packet=make_packet(VICTIM, ATTACKER, "encrypted", "Application Data (captured)",
                                     info, record["combined_hex"]),
                  highlight={ATTACKER: "warning"}),
        make_step("4. Attacker cannot read the content",
                  "Without the session key the attacker sees only metadata: IP addresses, port "
                  "443, the server name (SNI), packet sizes and timing.",
                  highlight={ATTACKER: "warning"},
                  panels={"attacker_saw": "Source: " + VICTIM_IP + ":51544\nDestination: " + SERVER_IP
                          + ":443\nSNI: " + SITE + "\nLength: " + str(record["ciphertext_length"])
                          + " bytes\n\nPayload:\n" + record["combined_hex"],
                          "attacker_can_read": False}),
    ]

    if attacker_modifies:
        tampered = encryption.tamper_with_hex(record["combined_hex"], 5)
        # The server really tries to decrypt the tampered record.
        result = encryption.symmetric_decrypt(record["key_hex"], record["nonce_hex"], tampered)
        steps.append(make_step(
            "5. Attacker flips bits in the ciphertext",
            "The attacker blindly changes one byte, hoping to alter the request.",
            packet=make_packet(ATTACKER, SERVER, "malicious", "Tampered Application Data",
                               details("TLS 1.3", VICTIM_IP, SERVER_IP + ":443", "Yes", {"Tampered": "Yes"}),
                               tampered),
            highlight={ATTACKER: "danger"},
            panels={"original": record["combined_hex"], "modified": tampered, "was_modified": True}))
        steps.append(make_step(
            "6. Server detects the tampering",
            "AES-GCM authentication fails, so the server rejects the record, sends a "
            "'bad_record_mac' alert and closes the connection. Real result: "
            + ("decryption FAILED" if not result["success"] else "decrypted"),
            highlight={SERVER: "danger"},
            panels={"server_received": "REJECTED - " + result.get("error", ""),
                    "tamper_detected": not result["success"]}))
    else:
        result = encryption.symmetric_decrypt(record["key_hex"], record["nonce_hex"], record["combined_hex"])
        steps.append(make_step(
            "5. Attacker forwards the ciphertext",
            "A passive interceptor can only pass the data along unchanged.",
            packet=make_packet(ATTACKER, SERVER, "encrypted", "Application Data", info,
                               record["combined_hex"]),
            highlight={SERVER: "secure"}))
        steps.append(make_step(
            "6. Server decrypts successfully",
            "The authentication tag checks out, so the server knows the data is exactly what "
            "the victim sent.",
            highlight={SERVER: "secure"},
            panels={"server_received": result.get("plaintext", "")}))

    steps.append(make_step(
        "7. Important limitation",
        "TLS defeats ordinary interception, but an ACTIVE attacker can still succeed if the user "
        "clicks through a certificate warning, or if a malicious root CA is installed on the "
        "victim's device. Try Scenario C to see both.",
        highlight={ATTACKER: "warning"}))
    return steps


# --- Scenario C - Certificate spoofing ---

def cert_spoof(message, cert_problem):
    """The attacker answers the TLS handshake with its own certificate."""
    if cert_problem not in CERT_PROBLEMS:
        cert_problem = "untrusted"

    trust_store = ["Demo Root CA"]
    if cert_problem == "attacker_trusted":
        # The victim's device has been compromised (or configured by a proxy)
        # so the attacker's CA is in its trust store.
        trust_store.append("Interception Proxy CA")

    chain = certificates.generate_all_certificates()["chains"][cert_problem]
    result = certificates.verify_chain(chain, SITE, trust_store)
    fake_cert = certificates.describe_certificate(chain[0])
    request = build_request(message)

    steps = [
        make_step("1. Victim connects to https://" + SITE,
                  "The browser sends a ClientHello. The attacker intercepts it instead of "
                  "letting it reach the server.",
                  packet=make_packet(VICTIM, ATTACKER, "malicious", "ClientHello (intercepted)",
                                     details("TLS 1.3", VICTIM_IP, SERVER_IP + ":443", "Not yet",
                                             {"SNI": SITE})),
                  highlight={ATTACKER: "danger"},
                  panels={"address": "https://" + SITE, "secure": None, "victim_sent": message}),
        make_step("2. Attacker connects to the real server",
                  "The attacker opens its OWN genuine TLS connection to the server, pretending to "
                  "be the browser.",
                  packet=make_packet(ATTACKER, SERVER, "encrypted", "Attacker's TLS session",
                                     details("TLS 1.3", ATTACKER_IP, SERVER_IP + ":443", "Yes")),
                  highlight={ATTACKER: "danger"}),
        make_step("3. Attacker presents a fake certificate",
                  "The attacker cannot use the real certificate because it does not have the "
                  "server's private key, so it sends one it made itself: "
                  + CERT_PROBLEMS[cert_problem] + ".",
                  packet=make_packet(ATTACKER, VICTIM, "warning", "Fake certificate",
                                     {"Subject": fake_cert["subject_cn"], "Issuer": fake_cert["issuer_cn"],
                                      "Valid until": fake_cert["not_after"],
                                      "Names": ", ".join(fake_cert["san"])},
                                     fake_cert["pem"]),
                  highlight={VICTIM: "warning"},
                  panels={"certificate": fake_cert}),
        make_step("4. Browser verifies the certificate",
                  "The browser runs its checks (these results come from real X.509 verification "
                  "in Python).",
                  highlight={VICTIM: "secure" if result["verdict"]["trusted"] else "warning"},
                  panels={"checks": result["checks"], "verdict": result["verdict"]}),
    ]

    if result["verdict"]["trusted"]:
        # Malicious root installed: no warning at all.
        steps.extend(intercepted_tls_steps(request, message, padlock_shown=True))
        return steps

    warning_step = make_step(
        "5. Browser shows a security warning",
        "The browser refuses to continue automatically. What does the user do?",
        highlight={VICTIM: "warning"},
        panels={"warning": result["verdict"]})
    warning_step["choices"] = [
        {"id": "back", "label": "Go back to safety", "style": "secure"},
        {"id": "proceed", "label": "Proceed anyway (unsafe)", "style": "danger"},
    ]
    warning_step["branches"] = {
        "back": [make_step(
            "6. Connection rejected",
            "The browser closes the connection. No login data was ever sent, so the attacker "
            "gets nothing. This is certificate validation doing its job.",
            highlight={VICTIM: "secure", ATTACKER: "inactive"},
            panels={"outcome": "safe"})],
        "proceed": intercepted_tls_steps(request, message, padlock_shown=False),
    }
    steps.append(warning_step)
    return steps


def intercepted_tls_steps(request, message, padlock_shown):
    """Steps for when the victim ends up with a TLS session to the ATTACKER."""
    attacker_key_record = encryption.symmetric_encrypt(request)
    server_record = encryption.symmetric_encrypt(request)
    if padlock_shown:
        intro = ("No warning appears and the padlock is shown, because the victim's device "
                 "trusts the attacker's CA. HTTPS cannot protect a compromised endpoint.")
    else:
        intro = ("The user clicked through the warning. Sites using HSTS do not even offer "
                 "this option, precisely to prevent this mistake.")
    return [
        make_step("5. Victim sends the login - to the attacker",
                  intro + " The data is encrypted, but with a key shared with the attacker.",
                  packet=make_packet(VICTIM, ATTACKER, "malicious", "Application Data (attacker's key)",
                                     details("TLS 1.3", VICTIM_IP, SERVER_IP + ":443",
                                             "Yes - but to the attacker"), attacker_key_record["combined_hex"]),
                  highlight={VICTIM: "danger", ATTACKER: "danger"}),
        make_step("6. Attacker decrypts and reads everything",
                  "The attacker holds the session key for the victim's connection, so it can read "
                  "the plaintext.",
                  highlight={ATTACKER: "danger"},
                  panels={"attacker_saw": request, "attacker_can_read": True}),
        make_step("7. Attacker re-encrypts and forwards",
                  "Using its own genuine session with the server, the attacker forwards the data. "
                  "The server sees a normal login.",
                  packet=make_packet(ATTACKER, SERVER, "encrypted", "Application Data (re-encrypted)",
                                     details("TLS 1.3", ATTACKER_IP, SERVER_IP + ":443", "Yes"),
                                     server_record["combined_hex"]),
                  highlight={SERVER: "warning"},
                  panels={"server_received": message, "outcome": "compromised"}),
    ]


# --- Scenario D - TLS (SSL) stripping ---

def ssl_strip(message, protection):
    """Attacker tries to keep the victim on HTTP while it talks HTTPS to the server."""
    if protection == "hsts":
        return strip_blocked(message, "HSTS")
    if protection == "https_only":
        return strip_blocked(message, "HTTPS-Only Mode")

    request = build_request(message)
    original_html = ('<form action="https://' + SITE + '/login" method="post">\n'
                     'Strict-Transport-Security: max-age=31536000')
    stripped_html = ('<form action="http://' + SITE + '/login" method="post">\n'
                     '(Strict-Transport-Security header removed)')
    return [
        make_step("1. Victim types '" + SITE + "' without https://",
                  "With no HSTS record, the browser's first request may go out over plain HTTP. "
                  "The attacker intercepts it.",
                  packet=make_packet(VICTIM, ATTACKER, "malicious", "GET http://" + SITE,
                                     details("HTTP", VICTIM_IP, SERVER_IP + ":80", "No")),
                  highlight={ATTACKER: "danger"},
                  panels={"address": "http://" + SITE, "secure": False, "victim_sent": message}),
        make_step("2. Attacker talks HTTPS to the real server",
                  "Instead of letting the server redirect the victim to HTTPS, the attacker "
                  "makes its own secure connection.",
                  packet=make_packet(ATTACKER, SERVER, "encrypted", "GET https://" + SITE,
                                     details("HTTPS", ATTACKER_IP, SERVER_IP + ":443", "Yes")),
                  highlight={ATTACKER: "danger"}),
        make_step("3. Server returns the secure page",
                  "The server sees a normal HTTPS visitor and returns the login page.",
                  packet=make_packet(SERVER, ATTACKER, "encrypted", "200 OK (HTTPS)",
                                     details("HTTPS", SERVER_IP + ":443", ATTACKER_IP, "Yes")),
                  panels={"original": original_html}),
        make_step("4. Attacker strips HTTPS from the page",
                  "Every https:// link becomes http:// and the HSTS header is deleted, then the "
                  "page is sent to the victim over plain HTTP.",
                  packet=make_packet(ATTACKER, VICTIM, "malicious", "200 OK (stripped, HTTP)",
                                     details("HTTP", SERVER_IP + ":80 (spoofed)", VICTIM_IP, "No"),
                                     stripped_html),
                  highlight={ATTACKER: "danger", VICTIM: "warning"},
                  panels={"original": original_html, "modified": stripped_html, "was_modified": True}),
        make_step("5. Victim logs in over HTTP",
                  "The page looks normal; only the missing padlock and 'Not secure' label give it "
                  "away. The login goes out as plain text.",
                  packet=make_packet(VICTIM, ATTACKER, "malicious", "POST /login (plaintext)",
                                     details("HTTP", VICTIM_IP, SERVER_IP + ":80", "No"), request),
                  highlight={VICTIM: "danger"}),
        make_step("6. Attacker reads and forwards over HTTPS",
                  "The attacker captures the password and forwards it over HTTPS. The server "
                  "believes everything is secure.",
                  packet=make_packet(ATTACKER, SERVER, "encrypted", "POST /login (HTTPS)",
                                     details("HTTPS", ATTACKER_IP, SERVER_IP + ":443", "Yes")),
                  highlight={ATTACKER: "danger"},
                  panels={"attacker_saw": request, "attacker_can_read": True,
                          "server_received": message, "outcome": "compromised"}),
    ]


def strip_blocked(message, defence):
    """Steps showing HSTS or HTTPS-Only Mode defeating a stripping attempt."""
    if defence == "HSTS":
        upgrade_reason = ("The browser remembers (or has preloaded) the site's HSTS policy "
                          "'Strict-Transport-Security: max-age=31536000; includeSubDomains', so it "
                          "upgrades to https:// internally BEFORE sending anything.")
    else:
        upgrade_reason = ("HTTPS-Only Mode makes the browser try https:// for every site. It "
                          "only falls back to HTTP after showing the user a clear warning.")

    return [
        make_step("1. Victim types '" + SITE + "' without https://",
                  upgrade_reason,
                  highlight={VICTIM: "secure"},
                  panels={"address": "https://" + SITE, "secure": True, "victim_sent": message}),
        make_step("2. Browser connects with TLS straight away",
                  "No plain HTTP request ever leaves the device, so there is nothing to strip.",
                  packet=make_packet(VICTIM, ATTACKER, "encrypted", "ClientHello (HTTPS)",
                                     details("TLS 1.3", VICTIM_IP, SERVER_IP + ":443", "Handshake")),
                  highlight={ATTACKER: "warning"}),
        make_step("3. Attacker's options all fail",
                  "Answering with HTTP is refused, and presenting a fake certificate fails "
                  "validation. With " + defence + ", the browser does not let the user click "
                  "through the error.",
                  packet=make_packet(ATTACKER, VICTIM, "warning", "Downgrade attempt",
                                     details("HTTP / fake cert", ATTACKER_IP, VICTIM_IP, "No")),
                  highlight={ATTACKER: "warning", VICTIM: "secure"}),
        make_step("4. Attack blocked",
                  "The browser shows a hard error instead of a downgraded page. No credentials "
                  "are sent. Defences: HSTS (with preload for the very first visit), HTTPS-Only "
                  "Mode, and typing or bookmarking https:// addresses.",
                  highlight={VICTIM: "secure", ATTACKER: "inactive"},
                  panels={"outcome": "safe"}),
    ]


# --- Entry point used by the Flask route ---

def run_scenario(scenario, message, options):
    """Pick the right scenario function and return the nodes and steps."""
    if scenario == "normal_http":
        steps = normal_http(message)
    elif scenario == "normal_https":
        steps = normal_https(message)
    elif scenario == "http_mitm":
        steps = http_mitm(message, options.get("attacker_modifies", True),
                          options.get("find_text", ""), options.get("replace_text", ""))
    elif scenario == "https_mitm":
        steps = https_mitm(message, options.get("attacker_modifies", False))
    elif scenario == "cert_spoof":
        steps = cert_spoof(message, options.get("cert_problem", "untrusted"))
    elif scenario == "ssl_strip":
        steps = ssl_strip(message, options.get("protection", "none"))
    else:
        scenario = "normal_http"
        steps = normal_http(message)

    attacker_active = not scenario.startswith("normal")
    return {"scenario": scenario, "nodes": diagram_nodes(attacker_active), "steps": steps}
