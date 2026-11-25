"""progress.py - Tracks which activities a learner has completed."""

MODULES = [
    {"slug": "http_https", "number": 1, "title": "HTTP vs HTTPS", "endpoint": "http_https_page",
     "icon": "globe", "summary": "Send a login over HTTP and HTTPS, and see what changes.",
     "activities": {"http": "Run the HTTP simulation", "https": "Run the HTTPS simulation"},
     "done_title": "HTTP vs HTTPS Lab Completed", "done_text": "You've seen how HTTP and HTTPS handle information differently."},
    {"slug": "journey", "number": 2, "title": "The Journey of a Website", "endpoint": "journey_page",
     "icon": "globe", "summary": "Follow a website visit, one stage at a time.",
     "activities": {"journey": "Finish the journey"},
     "done_title": "Journey of a Website Completed", "done_text": "You've followed a website request from pressing Enter to the page appearing."},
    {"slug": "tls_handshake", "number": 3, "title": "TLS 1.3 Handshake", "endpoint": "tls_handshake_page",
     "icon": "handshake", "summary": "Watch a browser and website agree a secret key.",
     "activities": {"handshake": "Complete all seven handshake stages"},
     "done_title": "TLS 1.3 Lab Completed", "done_text": "You've learned how a secure connection is established."},
    {"slug": "encryption", "number": 4, "title": "Encryption Lab", "endpoint": "encryption_page",
     "icon": "key", "summary": "Encrypt, hash and sign your own text.",
     "activities": {"symmetric": "Encrypt with AES-GCM", "asymmetric": "Use an RSA key pair",
                    "hashing": "Hash some text", "signature": "Verify a digital signature"},
     "done_title": "Encryption Lab Completed", "done_text": "You've used symmetric and public-key encryption, hashing and digital signatures."},
    {"slug": "certificates", "number": 5, "title": "Certificate Explorer", "endpoint": "certificates_page",
     "icon": "certificate", "summary": "Check a website's ID card - then break it.",
     "activities": {"valid": "Valid certificate", "expired": "Expired certificate",
                    "mismatch": "Domain mismatch", "untrusted": "Untrusted CA",
                    "bad_signature": "Invalid signature"},
     "done_title": "Certificate Explorer Completed", "done_text": "You've seen every check a browser makes on a certificate, and what happens when one fails."},
    {"slug": "mitm", "number": 6, "title": "MITM Attack Lab", "endpoint": "mitm_page",
     "icon": "attacker", "summary": "See what an attacker in the middle can do, and what stops them.",
     "activities": {"http_mitm": "A · HTTP interception", "https_mitm": "B · HTTPS protection",
                    "cert_spoof": "C · Certificate spoofing", "ssl_strip": "D · TLS stripping",
                    "arp": "E · ARP spoofing"},
     "done_title": "MITM Lab Completed", "done_text": "You've seen what an attacker in the middle can and cannot do, and which defences stop them."},
    {"slug": "packet_inspection", "number": 7, "title": "Packet Inspector", "endpoint": "packet_inspection_page",
     "icon": "packets", "summary": "See what HTTPS hides in captured traffic, and what it does not.",
     "activities": {"HTTP": "Inspect an HTTP packet", "HTTPS": "Inspect an HTTPS packet"},
     "done_title": "Packet Inspector Completed", "done_text": "You've seen what HTTPS hides in captured traffic, and what it still reveals."},
]


def next_module(slug):
    """The lab that comes after this one, or None for the last lab."""
    for position, module in enumerate(MODULES):
        if module["slug"] == slug and position + 1 < len(MODULES):
            return MODULES[position + 1]
    return None


def completion_info(url_for):
    """What the browser needs for the "lab completed" box: name, link and message for each lab."""
    labs = []
    for module in MODULES:
        labs.append({"slug": module["slug"], "title": module["title"], "url": url_for(module["endpoint"]),
                     "summary": module["summary"], "done_title": module["done_title"],
                     "done_text": module["done_text"]})
    return labs


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
