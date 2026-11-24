"""app.py - The Flask web application for the HTTPS & TLS Learning Laboratory."""

import os

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

import progress
from simulations import (arp_spoofing, certificates, encryption, http_https, mitm,
                         packet_inspection, tls_handshake)

app = Flask(__name__)
# The secret key signs the session cookie that stores exploration progress.
# Set LAB_SECRET_KEY to keep sessions valid across restarts.
app.secret_key = os.environ.get("LAB_SECRET_KEY", os.urandom(32))

MAX_MESSAGE_LENGTH = 300
DEFAULT_MESSAGE = "Username: John Doe\nPassword: example123"


# --- Helpers ---

def get_json_data():
    """Return the JSON sent by the page as a dictionary (empty if none)."""
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return {}


def clean_text(value, default=""):
    """Make sure user input is a string of a sensible length."""
    if not isinstance(value, str) or value.strip() == "":
        return default
    return value[:MAX_MESSAGE_LENGTH]


@app.context_processor
def add_progress_to_templates():
    """Make progress information available in every template (for the sidebar)."""
    return {"progress": progress.summarise_progress(session)}


# --- Page routes ---

@app.route("/labs")
def index():
    """Overview of every lab, with a short MITM preview."""
    return render_template("index.html", active="home", default_message=DEFAULT_MESSAGE)


@app.route("/present")
def presentation_page():
    """The old timed presentation was removed. Old links go to the start page instead."""
    return redirect(url_for("http_https_page"))


@app.route("/")
@app.route("/http-https")
def http_https_page():
    """Lab 1, HTTP vs HTTPS. This is also the start page for new visitors."""
    return render_template("http_https.html", active="http_https",
                           comparison=http_https.COMPARISON_TABLE, default_message=DEFAULT_MESSAGE)


@app.route("/tls-handshake")
def tls_handshake_page():
    """Lab 2 page: TLS handshake."""
    return render_template("tls_handshake.html", active="tls_handshake")


@app.route("/encryption")
def encryption_page():
    """Lab 3 page: encryption laboratory."""
    return render_template("encryption.html", active="encryption",
                           hash_algorithms=list(encryption.HASH_ALGORITHMS.keys()) + ["MD5 (broken)"])


@app.route("/certificates")
def certificates_page():
    """Lab 4 page: certificate explorer."""
    return render_template("certificates.html", active="certificates",
                           scenarios=certificates.SCENARIOS,
                           field_explanations=certificates.FIELD_EXPLANATIONS)


@app.route("/mitm")
def mitm_page():
    """Lab 5 page: MITM attack lab. ?scenario=arp (etc.) opens a scenario directly."""
    start_scenario = request.args.get("scenario", "http_mitm")
    if start_scenario not in mitm.SCENARIOS:
        start_scenario = "http_mitm"
    return render_template("mitm.html", active="mitm", scenarios=mitm.SCENARIOS,
                           start_scenario=start_scenario,
                           scenario_notes=mitm.SCENARIO_NOTES,
                           cert_problems=mitm.CERT_PROBLEMS, arp_defences=arp_spoofing.DEFENCES,
                           default_message=DEFAULT_MESSAGE)


@app.route("/packet-inspection")
def packet_inspection_page():
    """Lab 6 page: packet inspector."""
    return render_template("packet_inspection.html", active="packet_inspection",
                           example_filters=packet_inspection.SUPPORTED_FILTERS)


# --- Module 1 - HTTP vs HTTPS ---

@app.route("/api/http-https/simulate", methods=["POST"])
def api_http_https():
    """Build the HTTP or HTTPS transmission steps."""
    data = get_json_data()
    protocol = "HTTPS" if data.get("protocol") == "HTTPS" else "HTTP"
    message = clean_text(data.get("message"), DEFAULT_MESSAGE)
    eavesdropper = bool(data.get("eavesdropper"))
    return jsonify({
        "nodes": http_https.diagram_nodes(eavesdropper),
        "steps": http_https.simulate_transmission(protocol, message, eavesdropper),
    })


# --- Module 2 - TLS handshake ---

@app.route("/api/tls/handshake", methods=["POST"])
def api_tls_handshake():
    """Build a fresh TLS handshake with new keys."""
    data = get_json_data()
    message = clean_text(data.get("message"), "GET /account HTTP/1.1")
    return jsonify({"nodes": tls_handshake.diagram_nodes(),
                    "steps": tls_handshake.build_handshake_steps(message)})


# --- Module 3 - Encryption laboratory ---

@app.route("/api/encryption/symmetric/encrypt", methods=["POST"])
def api_symmetric_encrypt():
    """Encrypt the user's text with AES-GCM."""
    data = get_json_data()
    text = clean_text(data.get("text"), "Hello")
    key = encryption.from_hex(data.get("key_hex", "")) if data.get("key_hex") else None
    if key is not None and len(key) != 32:
        key = None
    progress.record_activity(session, "encryption", "symmetric")
    return jsonify(encryption.symmetric_encrypt(text, key))


@app.route("/api/encryption/symmetric/decrypt", methods=["POST"])
def api_symmetric_decrypt():
    """Try to decrypt AES-GCM data."""
    data = get_json_data()
    return jsonify(encryption.symmetric_decrypt(str(data.get("key_hex", "")),
                                                str(data.get("nonce_hex", "")),
                                                str(data.get("combined_hex", ""))))


@app.route("/api/encryption/symmetric/tamper", methods=["POST"])
def api_symmetric_tamper():
    """Flip one byte of the ciphertext (simulated attacker)."""
    data = get_json_data()
    return jsonify({"combined_hex": encryption.tamper_with_hex(str(data.get("combined_hex", "")), 3)})


@app.route("/api/encryption/symmetric/new-key", methods=["POST"])
def api_symmetric_new_key():
    """Return a new random AES key (used for the wrong-key test)."""
    return jsonify({"key_hex": encryption.to_hex(encryption.generate_symmetric_key())})


@app.route("/api/encryption/rsa/generate", methods=["POST"])
def api_rsa_generate():
    """Generate an RSA key pair."""
    return jsonify(encryption.generate_rsa_key_pair())


@app.route("/api/encryption/rsa/encrypt", methods=["POST"])
def api_rsa_encrypt():
    """Encrypt text with an RSA public key."""
    data = get_json_data()
    return jsonify(encryption.rsa_encrypt(str(data.get("public_pem", "")),
                                          clean_text(data.get("text"), "Hello")))


@app.route("/api/encryption/rsa/decrypt", methods=["POST"])
def api_rsa_decrypt():
    """Decrypt with an RSA private key."""
    data = get_json_data()
    result = encryption.rsa_decrypt(str(data.get("private_pem", "")), str(data.get("ciphertext_hex", "")))
    if result["success"]:
        progress.record_activity(session, "encryption", "asymmetric")
    return jsonify(result)


@app.route("/api/encryption/hash", methods=["POST"])
def api_hash():
    """Hash two inputs and compare them."""
    data = get_json_data()
    algorithm = str(data.get("algorithm", "SHA-256"))
    progress.record_activity(session, "encryption", "hashing")
    return jsonify(encryption.compare_hashes(clean_text(data.get("text_a"), ""),
                                             clean_text(data.get("text_b"), ""), algorithm))


@app.route("/api/encryption/sign/generate", methods=["POST"])
def api_sign_generate():
    """Generate an Ed25519 signing key pair."""
    return jsonify(encryption.generate_signing_keys())


@app.route("/api/encryption/sign", methods=["POST"])
def api_sign():
    """Sign a message with the private key."""
    data = get_json_data()
    return jsonify(encryption.sign_message(str(data.get("private_key_hex", "")),
                                           clean_text(data.get("message"), "")))


@app.route("/api/encryption/verify", methods=["POST"])
def api_verify():
    """Verify a signature with the public key."""
    data = get_json_data()
    progress.record_activity(session, "encryption", "signature")
    return jsonify(encryption.verify_signature(str(data.get("public_key_hex", "")),
                                               clean_text(data.get("message"), ""),
                                               str(data.get("signature_hex", ""))))


# --- Module 4 - Certificates ---

@app.route("/api/certificates/scenario", methods=["POST"])
def api_certificate_scenario():
    """Load and verify the chosen certificate scenario."""
    data = get_json_data()
    scenario = data.get("scenario", "valid")
    if scenario not in certificates.SCENARIOS:
        scenario = "valid"
    hostname = clean_text(data.get("hostname"), certificates.SITE_NAME).strip().lower()
    trusted = data.get("trusted")
    if not isinstance(trusted, list):
        trusted = ["Demo Root CA"]
    progress.record_activity(session, "certificates", scenario)
    return jsonify(certificates.explore_scenario(scenario, hostname, trusted))


# --- Module 5 - MITM lab (including ARP spoofing) ---

@app.route("/api/mitm/simulate", methods=["POST"])
def api_mitm():
    """Build the steps for a MITM scenario (A-D or normal)."""
    data = get_json_data()
    options = data.get("options") if isinstance(data.get("options"), dict) else {}
    options["find_text"] = clean_text(options.get("find_text"), "")
    options["replace_text"] = clean_text(options.get("replace_text"), "")
    message = clean_text(data.get("message"), DEFAULT_MESSAGE)
    return jsonify(mitm.run_scenario(str(data.get("scenario", "")), message, options))


@app.route("/api/arp/simulate", methods=["POST"])
def api_arp():
    """Build the steps for the ARP spoofing scenario."""
    data = get_json_data()
    return jsonify(arp_spoofing.build_arp_steps(str(data.get("defence", "none"))))


# --- Module 6 - Packet inspection ---

@app.route("/api/packets", methods=["POST"])
def api_packets():
    """Return the example capture, filtered."""
    data = get_json_data()
    mode = "HTTPS" if data.get("mode") == "HTTPS" else "HTTP"
    all_packets = packet_inspection.get_capture(mode)
    shown, error = packet_inspection.filter_packets(all_packets, str(data.get("filter", "")))
    return jsonify({"mode": mode, "packets": shown, "total": len(all_packets), "error": error,
                    "visibility": packet_inspection.visibility_summary(mode)})


# --- Progress tracking ---

@app.route("/api/progress/record", methods=["POST"])
def api_progress_record():
    """Mark one exploration activity as done."""
    data = get_json_data()
    recorded = progress.record_activity(session, str(data.get("module", "")), str(data.get("activity", "")))
    return jsonify({"recorded": recorded, "progress": progress.summarise_progress(session)})


@app.route("/api/progress", methods=["GET"])
def api_progress():
    """Return the learner's progress."""
    return jsonify(progress.summarise_progress(session))


@app.route("/api/progress/reset", methods=["POST"])
def api_progress_reset():
    """Clear the learner's progress."""
    session.pop("progress", None)
    return jsonify(progress.summarise_progress(session))


if __name__ == "__main__":
    # Generate the demo certificates once at start-up so the first page load is fast.
    certificates.generate_all_certificates()
    # debug=False by default; set FLASK_DEBUG=1 for auto-reload while editing.
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
