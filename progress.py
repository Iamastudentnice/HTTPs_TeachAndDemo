"""progress.py - Tracks which activities a learner has completed."""

MODULES = [
    {"slug": "http_https", "number": 1, "title": "HTTP vs HTTPS", "endpoint": "http_https_page",
     "icon": "globe", "summary": "See why plain HTTP is readable by anyone on the path, and how TLS changes that.",
     "activities": {"http": "Run the HTTP simulation", "https": "Run the HTTPS simulation"}},
    {"slug": "tls_handshake", "number": 2, "title": "TLS Handshake", "endpoint": "tls_handshake_page",
     "icon": "handshake", "summary": "Step through a TLS 1.3 handshake with a real X25519 key exchange.",
     "activities": {"handshake": "Complete all seven handshake stages"}},
    {"slug": "encryption", "number": 3, "title": "Encryption Lab", "endpoint": "encryption_page",
     "icon": "key", "summary": "Experiment with AES, RSA, SHA-256 and Ed25519 signatures on your own text.",
     "activities": {"symmetric": "Encrypt with AES-GCM", "asymmetric": "Use an RSA key pair",
                    "hashing": "Hash some text", "signature": "Verify a digital signature"}},
    {"slug": "certificates", "number": 4, "title": "Certificate Explorer", "endpoint": "certificates_page",
     "icon": "certificate", "summary": "Inspect real X.509 certificates and break each browser check.",
     "activities": {"valid": "Valid certificate", "expired": "Expired certificate",
                    "mismatch": "Domain mismatch", "untrusted": "Untrusted CA",
                    "bad_signature": "Invalid signature"}},
    {"slug": "mitm", "number": 5, "title": "MITM Attack Lab", "endpoint": "mitm_page",
     "icon": "attacker", "summary": "Become the attacker: intercept, modify, spoof certificates, strip TLS and poison ARP.",
     "activities": {"http_mitm": "A · HTTP interception", "https_mitm": "B · HTTPS protection",
                    "cert_spoof": "C · Certificate spoofing", "ssl_strip": "D · TLS stripping",
                    "arp": "E · ARP spoofing"}},
    {"slug": "packet_inspection", "number": 6, "title": "Packet Inspector", "endpoint": "packet_inspection_page",
     "icon": "packets", "summary": "Inspect example packets and discover what HTTPS hides - and what it doesn't.",
     "activities": {"HTTP": "Inspect an HTTP packet", "HTTPS": "Inspect an HTTPS packet"}},
]


def find_module(slug):
    """Return the module dictionary with this slug, or None."""
    for module in MODULES:
        if module["slug"] == slug:
            return module
    return None


def record_activity(session, module_slug, activity):
    """Mark one activity as done."""
    module = find_module(module_slug)
    if module is None or activity not in module["activities"]:
        return False

    progress = session.get("progress", {})
    done = progress.get(module_slug, [])
    if activity not in done:
        done.append(activity)
    progress[module_slug] = done
    # Re-assigning tells Flask the session changed and must be saved.
    session["progress"] = progress
    return True


def summarise_progress(session):
    """Build the progress information shown in the sidebar and on the home page."""
    progress = session.get("progress", {})
    modules = []
    total_activities = 0
    total_done = 0

    for module in MODULES:
        done = progress.get(module["slug"], [])
        activity_list = []
        for key, label in module["activities"].items():
            activity_list.append({"key": key, "label": label, "done": key in done})
        done_count = len([item for item in activity_list if item["done"]])

        total_activities += len(activity_list)
        total_done += done_count
        modules.append({
            "slug": module["slug"],
            "number": module["number"],
            "title": module["title"],
            "endpoint": module["endpoint"],
            "icon": module["icon"],
            "summary": module["summary"],
            "activities": activity_list,
            "done": done_count,
            "total": len(activity_list),
            "complete": done_count == len(activity_list),
        })

    percent = round(100 * total_done / total_activities) if total_activities else 0
    completed_modules = len([module for module in modules if module["complete"]])
    return {"modules": modules, "percent": percent, "completed_modules": completed_modules,
            "total_modules": len(modules)}
