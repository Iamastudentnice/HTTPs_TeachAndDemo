"""glossary.py - Short, plain-English meanings of the words used in the labs.

Each entry has the word, a one-sentence meaning, and the lab where it is shown
(a slug from progress.py), so the glossary page can link to it.
"""

TERMS = [
    {"term": "ARP", "lab": "mitm",
     "meaning": "How devices on a home network find each other's MAC address from an IP address."},
    {"term": "ARP spoofing", "lab": "mitm",
     "meaning": "An attacker sends fake ARP replies so traffic flows through their device."},
    {"term": "Browser", "lab": "http_https",
     "meaning": "The app you use to visit websites, such as Chrome, Safari or Firefox."},
    {"term": "Cache", "lab": "journey",
     "meaning": "A saved copy of something, kept so it does not have to be fetched again."},
    {"term": "Certificate", "lab": "certificates",
     "meaning": "A website's ID card. It proves the website really owns its name."},
    {"term": "Certificate authority (CA)", "lab": "certificates",
     "meaning": "A trusted organisation that checks and signs certificates."},
    {"term": "Certificate chain", "lab": "certificates",
     "meaning": "The line of signatures from a website's certificate up to a trusted root CA."},
    {"term": "Ciphertext", "lab": "encryption",
     "meaning": "Scrambled text produced by encryption. It looks like random characters."},
    {"term": "Decryption", "lab": "encryption",
     "meaning": "Turning ciphertext back into readable text, using the right key."},
    {"term": "Digital signature", "lab": "encryption",
     "meaning": "Proof, made with a private key, that a message is genuine and unchanged."},
    {"term": "DNS", "lab": "journey",
     "meaning": "The internet's phone book: it turns a name like example.com into an IP address."},
    {"term": "Eavesdropper", "lab": "http_https",
     "meaning": "Someone who quietly watches network traffic without changing it."},
    {"term": "Encryption", "lab": "encryption",
     "meaning": "Scrambling information so only someone with the right key can read it."},
    {"term": "Handshake", "lab": "tls_handshake",
     "meaning": "The first few messages that set up a connection before any data is sent."},
    {"term": "Hash", "lab": "encryption",
     "meaning": "A short fingerprint of some data. Any change gives a completely different hash."},
    {"term": "HSTS", "lab": "mitm",
     "meaning": "A website's instruction to browsers: always use HTTPS with me, never HTTP."},
    {"term": "HTTP", "lab": "http_https",
     "meaning": "The language browsers and websites use to talk. It is not encrypted."},
    {"term": "HTTPS", "lab": "http_https",
     "meaning": "HTTP sent through TLS, so it is encrypted while it travels."},
    {"term": "IP address", "lab": "journey",
     "meaning": "A number that identifies a device on a network, like a postal address."},
    {"term": "Key", "lab": "encryption",
     "meaning": "The secret value used to encrypt or decrypt information."},
    {"term": "MAC address", "lab": "mitm",
     "meaning": "The fixed hardware address of a network device on the local network."},
    {"term": "Man-in-the-middle (MITM)", "lab": "mitm",
     "meaning": "An attacker who secretly sits between you and a website and relays the traffic."},
    {"term": "Metadata", "lab": "packet_inspection",
     "meaning": "Information about a message, such as who, where, when and how big - not its content."},
    {"term": "Packet", "lab": "http_https",
     "meaning": "A small piece of data travelling across a network. Messages are sent in packets."},
    {"term": "Packet capture", "lab": "packet_inspection",
     "meaning": "A recording of the packets that passed through a network."},
    {"term": "Padlock", "lab": "http_https",
     "meaning": "The browser's sign that the connection is protected. It does not mean the site is honest."},
    {"term": "Plaintext", "lab": "encryption",
     "meaning": "Normal, readable text before it is encrypted."},
    {"term": "Port", "lab": "packet_inspection",
     "meaning": "A number that says which service a packet is for, e.g. 443 for HTTPS."},
    {"term": "Private key", "lab": "encryption",
     "meaning": "The half of a key pair that is kept secret. It decrypts and signs."},
    {"term": "Public key", "lab": "encryption",
     "meaning": "The half of a key pair that anyone may have. It encrypts and checks signatures."},
    {"term": "Root CA", "lab": "certificates",
     "meaning": "A certificate authority your device trusts already. Every chain must end at one."},
    {"term": "Router", "lab": "journey",
     "meaning": "The box that connects your home network to the internet and passes data along."},
    {"term": "Server", "lab": "http_https",
     "meaning": "The computer that runs a website and answers your browser."},
    {"term": "Session key", "lab": "tls_handshake",
     "meaning": "A fresh secret key, agreed during the handshake, used for one connection only."},
    {"term": "TCP", "lab": "journey",
     "meaning": "Makes sure every packet arrives, in order, so nothing is lost on the way."},
    {"term": "TLS", "lab": "tls_handshake",
     "meaning": "The protection behind HTTPS: it encrypts data and checks the website's certificate."},
    {"term": "TLS stripping", "lab": "mitm",
     "meaning": "An attack that quietly downgrades a visit from HTTPS to plain HTTP."},
    {"term": "Trust store", "lab": "certificates",
     "meaning": "The list of root CAs your device or browser trusts."},
]


def terms_by_letter():
    """Group the terms by first letter, in alphabetical order: [("A", [...]), ("B", [...])]."""
    groups = {}
    for entry in sorted(TERMS, key=lambda item: item["term"].lower()):
        letter = entry["term"][0].upper()
        if letter not in groups:
            groups[letter] = []
        groups[letter].append(entry)
    return list(groups.items())
