"""website_journey.py - Lab 02: The Journey of a Website.

What happens between typing an address and seeing the page, in eight simple stages.
This is a simulation only: nothing is looked up and no website is contacted.
The address the user types is just used as example text.
"""

import re
from urllib.parse import urlsplit

from simulations import encryption
from simulations.steps import make_node, make_packet

# A website name: letters, digits and hyphens, separated by dots, ending in a word like "com".
DOMAIN_PATTERN = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")

# Made-up addresses. 198.51.100.0/24 and 203.0.113.0/24 are reserved for examples.
DEVICE_IP = "192.168.1.20"
ROUTER_IP = "192.168.1.1"
ROUTER_MAC = "00:11:22:33:44:01"
RESOLVER_IP = "198.51.100.53"


def demo_ip(domain):
    """A made-up IP address for the domain. The same name always gives the same number."""
    return "203.0.113." + str(sum(ord(letter) for letter in domain) % 254 + 1)


def read_address(text, protocol):
    """Split what the user typed into protocol, domain and path.

    Returns (address, None) when it looks like a website address,
    or (None, message) explaining what is wrong.
    """
    text = (text or "").strip()
    if not text:
        return None, "Please type a website address, for example google.com."
    if " " in text:
        return None, "A website address cannot contain spaces. Try something like google.com."

    # No protocol typed: use the one chosen with the HTTPS / HTTP switch.
    if "://" not in text:
        text = protocol.lower() + "://" + text

    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        # For example a port that is not a number: "google.com:abc".
        return None, "That does not look like a website address. Try something like google.com or example.org/news."

    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        return None, "Only addresses starting with http:// or https:// are supported here."

    domain = (parts.hostname or "").lower().rstrip(".")
    if not DOMAIN_PATTERN.match(domain):
        return None, "That does not look like a website name. Try something like google.com or example.org."

    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    default_port = 443 if scheme == "https" else 80

    address = {
        "scheme": scheme,
        "domain": domain,
        "path": path,
        "port": port or default_port,
        "full": scheme + "://" + domain + (":" + str(port) if port else "") + path,
        "ip": demo_ip(domain),
    }
    return address, None


def make_stage(title, concept, explanation, points, details, parts, visual="network", nodes=None):
    """One stage of the journey. Each part is shown when the user presses Next Step."""
    return {
        "title": title,
        "concept": concept,
        "explanation": explanation,
        "points": points,
        "details": details,
        "visual": visual,
        "nodes": nodes or [],
        "parts": parts,
    }


def make_part(caption, packet=None, highlight=None, show=None, status=None, panel=None):
    """One moment inside a stage: a caption, and optionally a packet to animate."""
    return {"caption": caption, "packet": packet, "highlight": highlight or {},
            "show": show, "status": status, "panel": panel}


# --- The eight stages ---

def stage_read_address(address):
    secure = address["scheme"] == "https"
    return make_stage(
        "Your browser reads the address",
        "URL parsing",
        "Your browser works out which website you want, and how to talk to it.",
        ["A protocol is a set of rules for how two computers talk to each other."],
        ["A full website address is called a URL (Uniform Resource Locator).",
         "Many browsers now try HTTPS first when you leave out the protocol. This demo uses "
         + address["scheme"].upper() + "."],
        [
            make_part("Protocol: " + address["scheme"] + " - the rules for talking to the website. "
                      + ("The s stands for secure." if secure else "There is no s, so the connection will not be encrypted."),
                      show="scheme"),
            make_part("Domain: " + address["domain"] + " - the name of the website.", show="domain"),
            make_part(("Path: " + address["path"] + " - which page on the website. "
                       + ("A single / means the home page." if address["path"] == "/" else "")).strip(), show="path"),
        ],
        visual="address",
    )


def stage_check_cache(address):
    return make_stage(
        "Checking what's already saved",
        "Browser and DNS caching",
        "Your browser checks whether it already saved what it needs.",
        ["Caching means temporarily saving information so it can be reused.",
         "Cache hit: the information is already saved, so time is saved.",
         "Cache miss: it is not saved (or too old), so it has to be fetched again."],
        ["The browser cache keeps copies of website files, such as pages, pictures and styles.",
         "The DNS cache keeps website names and their IP addresses. The two caches are separate.",
         "Real visits vary. On a repeat visit the page, the address, or both may already be saved, "
         "and some of the next stages would be skipped. This demo shows a first visit."],
        [
            make_part("Browser cache: is a saved copy of " + address["domain"] + " available? "
                      "Not this time - a cache miss, because this is your first visit.",
                      show="browser-cache", status="miss"),
            make_part("DNS cache: does your device already know the IP address for " + address["domain"]
                      + "? No - another cache miss, so the address has to be looked up next.",
                      show="dns-cache", status="miss"),
        ],
        visual="cache",
    )


def stage_dns(address):
    nodes = [
        make_node("client", "Your Browser", DEVICE_IP, "laptop", "client"),
        make_node("resolver", "DNS Resolver", RESOLVER_IP, "globe", "router"),
    ]
    question = make_packet("client", "resolver", "plain", "DNS query: " + address["domain"] + "?",
                           {"Question": "What is the IP address of " + address["domain"] + "?",
                            "Protocol": "DNS, usually over UDP port 53",
                            "Encrypted": "No (classic DNS)"},
                           "Where is " + address["domain"] + "?")
    answer = make_packet("resolver", "client", "plain", "Answer: " + address["ip"],
                         {"Answer": address["domain"] + " is at " + address["ip"],
                          "Note": "Made-up example address, not the real one"},
                         address["domain"] + " -> " + address["ip"] + " (example address)")
    return make_stage(
        "Finding the website",
        "DNS lookup",
        "Computers find each other by number, so the name must be looked up.",
        ["An IP address is a number that identifies a computer on the internet, like " + address["ip"] + ".",
         "DNS (Domain Name System) works like a phonebook: look up a name, get a number."],
        ["A DNS resolver is usually run by your internet provider or a public service. If it does not "
         "have the answer saved, it asks other DNS servers in turn until it finds it.",
         "Classic DNS is not encrypted, so the network can see which names you look up. Newer options, "
         "such as DNS over HTTPS, encrypt these lookups.",
         address["ip"] + " comes from 203.0.113.0/24, a range reserved for examples. It is not the real "
         "address of " + address["domain"] + "."],
        [
            make_part("Your browser asks a DNS resolver: what is the IP address of " + address["domain"] + "?",
                      packet=question, highlight={"client": "active"}),
            make_part("The resolver answers with the IP address: " + address["ip"] + " (an example address for this demo).",
                      packet=answer, highlight={"client": "active"}),
        ],
        nodes=nodes,
    )


def stage_routing(address):
    nodes = [
        make_node("device", "Your Device", DEVICE_IP, "laptop", "client"),
        make_node("router", "Home Router", ROUTER_IP + " (gateway)", "router", "router"),
        make_node("internet", "The Internet", "towards " + address["ip"], "globe", "server"),
    ]
    arp_question = make_packet("device", "router", "plain", "ARP: who has " + ROUTER_IP + "?",
                               {"Type": "ARP request, sent to every device on the home network",
                                "Question": "Who has " + ROUTER_IP + "? Tell " + DEVICE_IP},
                               "Who has " + ROUTER_IP + "?")
    arp_answer = make_packet("router", "device", "plain", "ARP: I am " + ROUTER_MAC,
                             {"Type": "ARP reply", "Answer": ROUTER_IP + " is at " + ROUTER_MAC},
                             ROUTER_IP + " is at " + ROUTER_MAC)
    outgoing = make_packet("device", "internet", "plain", "Packet for " + address["ip"],
                           {"From": DEVICE_IP, "To": address["ip"],
                            "First stop": "Home router (" + ROUTER_IP + "), which forwards it onwards"},
                           "Data addressed to " + address["ip"])
    return make_stage(
        "Finding the way out",
        "Local network and routing",
        "Your device works out where to send the data first.",
        ["A router connects your home network to the internet and passes traffic between them.",
         "The default gateway is the router your device uses for anything outside your home network.",
         "A MAC address is a hardware address used to deliver data on the local network."],
        ["ARP (Address Resolution Protocol) is how IPv4 devices find the MAC address that belongs "
         "to a local IP address. The answer is usually saved for a while, so this is often skipped.",
         "IPv6 networks do not use ARP. They use a different mechanism called Neighbor Discovery.",
         "Out on the internet, many routers pass the packet along, each choosing the next hop."],
        [
            make_part("If it does not know the router's MAC address yet, your device asks the network: "
                      "who has " + ROUTER_IP + " (the router)?",
                      packet=arp_question, highlight={"device": "active"}),
            make_part("The router answers with its MAC address, so your device knows where to hand over data.",
                      packet=arp_answer, highlight={"router": "active"}),
            make_part("Your device sends the data to the router, which forwards it out of your home network "
                      "towards the website.", packet=outgoing, highlight={"router": "active"}),
        ],
        nodes=nodes,
    )


def stage_tcp(address):
    nodes = [
        make_node("client", "Your Browser", DEVICE_IP, "laptop", "client"),
        make_node("server", "Web Server", address["domain"] + " (" + address["ip"] + ")", "server", "server"),
    ]
    port = str(address["port"])

    def tcp(sender, receiver, flags, label, meaning):
        return make_packet(sender, receiver, "plain", label,
                           {"Flags": flags, "Server port": port, "Meaning": meaning,
                            "Sequence numbers": "example values"}, flags)

    return make_stage(
        "Establishing a connection",
        "TCP three-way handshake",
        "Before sending data, your browser and the server may open a connection.",
        ["TCP (Transmission Control Protocol) makes sure data arrives complete and in the right order.",
         "This connection is used by HTTP/1.1 and HTTP/2."],
        ["Not every HTTPS connection uses TCP: HTTP/3 uses QUIC instead, which sets up the connection "
         "and its security together.",
         "If the browser already has an open connection to this server, it can reuse it and skip this stage.",
         "Port " + port + " is the usual door for " + address["scheme"].upper() + "."],
        [
            make_part("1. SYN - your device asks to establish a connection.",
                      packet=tcp("client", "server", "SYN", "SYN", "Can we connect?"), highlight={"client": "active"}),
            make_part("2. SYN-ACK - the server responds: yes, and it is ready too.",
                      packet=tcp("server", "client", "SYN-ACK", "SYN-ACK", "Yes, I am ready"), highlight={"server": "active"}),
            make_part("3. ACK - your device confirms. The connection is open.",
                      packet=tcp("client", "server", "ACK", "ACK", "Great, connected"),
                      highlight={"client": "active", "server": "active"}),
        ],
        nodes=nodes,
    )


def stage_tls(address):
    nodes = [
        make_node("client", "Your Browser", DEVICE_IP, "laptop", "client"),
        make_node("server", "Web Server", address["domain"], "server", "server"),
    ]
    explanation = "HTTPS uses TLS to protect the data on its way."

    if address["scheme"] == "http":
        return make_stage(
            "Securing the connection",
            "TLS handshake (HTTPS only)",
            explanation + " Ordinary HTTP does not set up TLS, so this stage does not happen.",
            ["TLS (Transport Layer Security) is the technology that protects HTTPS connections."],
            ["Try the journey again with HTTPS to see this stage."],
            [make_part("Skipped: with http:// there is no TLS handshake. Nothing will be encrypted, and the browser "
                       "has no certificate to check who it is talking to.", highlight={"client": "warning"})],
            nodes=nodes,
        )

    hello = make_packet("client", "server", "plain", "Client Hello",
                        {"Contains": "Supported security methods and the browser's half of a key exchange",
                         "Encrypted": "No - nothing secret is in it"}, "Client Hello")
    server_hello = make_packet("server", "client", "plain", "Server Hello",
                               {"Contains": "The chosen security methods and the server's half of the key exchange",
                                "Encrypted": "No - nothing secret is in it"}, "Server Hello")
    certificate = make_packet("server", "client", "encrypted", "Certificate",
                              {"Contains": "The certificate for " + address["domain"] + " and proof the server owns it",
                               "Encrypted": "Yes - in TLS 1.3 this part is already encrypted"},
                              "Certificate for " + address["domain"])
    finished = make_packet("client", "server", "encrypted", "Finished",
                           {"Meaning": "Both sides confirm the handshake was not tampered with"}, "Finished")
    return make_stage(
        "Securing the connection",
        "TLS handshake",
        explanation,
        ["TLS stands for Transport Layer Security.",
         "The certificate proves the server's identity. The shared keys do the encrypting."],
        ["This is a simplified TLS 1.3 handshake. The key exchange travels inside the two Hello messages, "
         "and the certificate is already encrypted when it is sent.",
         "The certificate itself does not encrypt your data. It lets your browser check it is talking to the "
         "real " + address["domain"] + ". The shared encryption keys protect the data that follows.",
         "Lab 03 shows the full handshake with real keys. Lab 05 lets you break each certificate check."],
        [
            make_part("Client Hello: your browser lists the security methods it supports and sends "
                      "its half of a key exchange.", packet=hello, highlight={"client": "active"}),
            make_part("Server Hello: the server picks the methods and sends its half of the key exchange.",
                      packet=server_hello, highlight={"server": "active"}),
            make_part("Key agreement: both sides work out the same secret keys. The keys are never sent.",
                      highlight={"client": "active", "server": "active"}),
            make_part("Certificate check: your browser checks the website's ID card is trusted, in date "
                      "and really for " + address["domain"] + ".",
                      packet=certificate, highlight={"client": "secure"}),
            make_part("Secure connection: from now on, the website's data is encrypted with the shared keys.",
                      packet=finished,
                      highlight={"client": "secure", "server": "secure"}),
        ],
        nodes=nodes,
    )


def stage_request(address):
    nodes = [
        make_node("client", "Your Browser", DEVICE_IP, "laptop", "client"),
        make_node("server", "Web Server", address["domain"], "server", "server"),
    ]
    request_text = "GET " + address["path"] + " HTTP/1.1\nHost: " + address["domain"]
    response_text = ("HTTP/1.1 200 OK\nContent-Type: text/html\n\n"
                     "<html><h1>Example page for " + address["domain"] + "</h1></html>")
    secure = address["scheme"] == "https"

    if secure:
        # Real AES-GCM encryption of the made-up messages, like the HTTP vs HTTPS lab.
        request_seen = encryption.symmetric_encrypt(request_text)["combined_hex"]
        response_seen = encryption.symmetric_encrypt(response_text)["combined_hex"]
        style = "encrypted"
        label_start = "Encrypted "
        visible = "Only scrambled data (plus the IP addresses, port " + str(address["port"]) + " and size)"
    else:
        request_seen = request_text
        response_seen = response_text
        style = "plain"
        label_start = ""
        visible = "Everything, as readable text"

    request = make_packet("client", "server", style, label_start + "HTTP request",
                          {"Asks for": "GET " + address["path"], "Encrypted": "Yes, with the TLS keys" if secure else "No",
                           "Visible to the network": visible}, request_seen)
    response = make_packet("server", "client", style, label_start + "HTTP response",
                           {"Status": "200 OK (success)", "Contains": "The page files",
                            "Encrypted": "Yes, with the TLS keys" if secure else "No"}, response_seen)
    panel_title = "What someone on the network could read"
    return make_stage(
        "Sending and receiving information",
        "HTTP request and response",
        "Your browser asks for the page, and the server sends it back.",
        ["A request asks the server for something - here, the page at " + address["path"] + ".",
         "A response contains the result: a status, such as 200 OK, and the page itself.",
         ("With HTTPS, only the two ends can read it." if secure
          else "With HTTP, anyone on the path could read or change it.")],
        ["Common status codes: 200 OK (success), 301 (moved somewhere else), 404 (not found).",
         "A real page usually needs many requests: one for the HTML, then more for styles, scripts and pictures.",
         "The page content here is made up for the demo."],
        [
            make_part("Request: your browser asks the server for " + address["path"] + "."
                      + (" It is encrypted, so the network only sees scrambled data." if secure
                         else " It travels as readable text."),
                      packet=request, highlight={"client": "secure" if secure else "warning"},
                      panel={"title": panel_title, "text": request_seen, "readable": not secure}),
            make_part("Response: the server sends back the page (200 OK means success)"
                      + (", also encrypted." if secure else ", also as readable text."),
                      packet=response, highlight={"server": "secure" if secure else "warning"},
                      panel={"title": panel_title, "text": response_seen, "readable": not secure}),
        ],
        nodes=nodes,
    )


def stage_render(address):
    return make_stage(
        "The website appears",
        "Browser rendering",
        "The browser processes the information it receives and turns it into the webpage you see.",
        ["HTML describes the page structure.",
         "CSS controls how the page looks.",
         "JavaScript adds interactive behaviour."],
        ["The browser builds a model of the page from the HTML, applies the CSS, runs the JavaScript, "
         "then draws the result on screen.",
         "Real pages often load many files, and the browser starts drawing before everything has arrived."],
        [
            make_part("HTML arrives first: it describes the structure - a heading, some text and a button.", show="html"),
            make_part("CSS controls how it looks: colours, fonts and layout.", show="css"),
            make_part("JavaScript adds behaviour: try the button in the example page.", show="js"),
        ],
        visual="render",
    )


def build_journey(text, protocol):
    """Read the address and build all eight stages, or explain what is wrong with the address."""
    protocol = "HTTP" if protocol == "HTTP" else "HTTPS"
    address, error = read_address(text, protocol)
    if error:
        return {"ok": False, "error": error}

    stages = [
        stage_read_address(address),
        stage_check_cache(address),
        stage_dns(address),
        stage_routing(address),
        stage_tcp(address),
        stage_tls(address),
        stage_request(address),
        stage_render(address),
    ]
    return {"ok": True, "address": address, "stages": stages}
