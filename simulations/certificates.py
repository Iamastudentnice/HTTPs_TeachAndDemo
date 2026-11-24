"""certificates.py - Module Four: Digital Certificate Explorer."""

import datetime

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

SITE_NAME = "shop.example.com"

# Chrome-style error codes a browser would show for each failure.
BROWSER_ERRORS = {
    "hostname": "NET::ERR_CERT_COMMON_NAME_INVALID",
    "validity": "NET::ERR_CERT_DATE_INVALID",
    "signature": "NET::ERR_CERT_INVALID",
    "trust": "NET::ERR_CERT_AUTHORITY_INVALID",
}

# Short explanations shown when a user clicks a certificate field.
FIELD_EXPLANATIONS = {
    "subject": "Who the certificate was issued TO. For websites the Common Name (CN) is "
               "the domain, but browsers actually check the Subject Alternative Names.",
    "issuer": "Who issued and signed the certificate - normally an intermediate "
              "Certificate Authority (CA). The browser uses the issuer's public key to "
              "check the signature.",
    "san": "Subject Alternative Names: the exact list of domain names this certificate is "
           "valid for. If the site you visit is not listed, the browser shows a "
           "name-mismatch error.",
    "validity": "The certificate is only valid between 'Not Before' and 'Not After'. Public "
                "website certificates are short-lived (months, not years) to limit damage "
                "if a key leaks.",
    "public_key": "The server's public key. During the TLS handshake the server proves it "
                  "holds the matching private key by signing the handshake "
                  "(CertificateVerify). It is NOT used to encrypt your page data.",
    "signature_algorithm": "The algorithm the issuer used to sign this certificate, e.g. "
                           "ECDSA with SHA-256. If the signature does not verify, the "
                           "certificate was altered or forged.",
    "serial": "A unique number the CA gives each certificate. It is used when a certificate "
              "has to be revoked.",
    "ca": "The Certificate Authority is a trusted organisation that checks domain ownership "
          "before issuing certificates. Browsers trust a small set of root CAs stored in a "
          "'trust store'.",
    "chain": "The chain of trust: the site certificate is signed by an intermediate CA, "
             "which is signed by a root CA. The browser follows the signatures up to a root "
             "it already trusts.",
    "fingerprint": "A SHA-256 hash of the whole certificate. It uniquely identifies the "
                   "certificate - change one byte and the fingerprint changes completely.",
    "basic_constraints": "Says whether this certificate may act as a CA and sign other "
                         "certificates. A website certificate must have CA:FALSE.",
}

# Description of every scenario offered in the explorer.
SCENARIOS = {
    "valid": {"title": "Valid certificate",
              "summary": "Correct domain, in date, signed by a trusted CA."},
    "expired": {"title": "Expired certificate",
                "summary": "The validity period ended 35 days ago."},
    "mismatch": {"title": "Domain name mismatch",
                 "summary": "The certificate is for a different domain."},
    "untrusted": {"title": "Untrusted certificate authority",
                  "summary": "Issued by a CA that is not in the trust store."},
    "bad_signature": {"title": "Invalid certificate signature",
                      "summary": "Claims to be issued by the Demo CA but the signature is forged."},
}

# All generated certificates are stored here after the first call.
_generated = {}


# --- Building certificates ---

def make_name(common_name, organisation):
    """Build an X.509 name such as 'CN=shop.example.com, O=Example Shop Ltd, C=GB'."""
    return x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organisation),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "GB"),
    ])


def build_certificate(subject_name, subject_key, issuer_name, signing_key,
                      days_before, days_after, is_ca, dns_names=None):
    """Create and sign one certificate."""
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(subject_name)
    builder = builder.issuer_name(issuer_name)
    builder = builder.public_key(subject_key.public_key())
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.not_valid_before(now + datetime.timedelta(days=days_before))
    builder = builder.not_valid_after(now + datetime.timedelta(days=days_after))
    builder = builder.add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
    if dns_names:
        san = x509.SubjectAlternativeName([x509.DNSName(name) for name in dns_names])
        builder = builder.add_extension(san, critical=False)
    return builder.sign(signing_key, hashes.SHA256())


def new_key():
    """Generate an elliptic-curve (P-256) key pair - fast and widely used on the web."""
    return ec.generate_private_key(ec.SECP256R1())


def generate_all_certificates():
    """Create every CA and website certificate used by the lab (runs once)."""
    if _generated:
        return _generated

    # Root CAs - self-signed, meaning issuer == subject.
    demo_root_key = new_key()
    demo_root_name = make_name("Demo Root CA", "Demo Trust Services")
    demo_root = build_certificate(demo_root_name, demo_root_key, demo_root_name,
                                  demo_root_key, -3650, 3650, True)

    unknown_root_key = new_key()
    unknown_root_name = make_name("Unknown Root CA", "Unverified Certificates Co")
    unknown_root = build_certificate(unknown_root_name, unknown_root_key, unknown_root_name,
                                     unknown_root_key, -365, 3650, True)

    # The attacker's own CA, used in the MITM lab to show what happens when a
    # malicious root is installed on the victim's device.
    attacker_root_key = new_key()
    attacker_root_name = make_name("Interception Proxy CA", "Attacker Lab")
    attacker_root = build_certificate(attacker_root_name, attacker_root_key, attacker_root_name,
                                      attacker_root_key, -30, 3650, True)

    # Intermediate CA signed by the Demo Root.
    intermediate_key = new_key()
    intermediate_name = make_name("Demo Intermediate CA", "Demo Trust Services")
    intermediate = build_certificate(intermediate_name, intermediate_key, demo_root_name,
                                     demo_root_key, -1000, 1500, True)

    site_names = [SITE_NAME, "www." + SITE_NAME]
    site_subject = make_name(SITE_NAME, "Example Shop Ltd")

    valid_leaf = build_certificate(site_subject, new_key(), intermediate_name,
                                   intermediate_key, -30, 60, False, site_names)
    expired_leaf = build_certificate(site_subject, new_key(), intermediate_name,
                                     intermediate_key, -400, -35, False, site_names)
    mismatch_leaf = build_certificate(make_name("other-site.example.net", "Other Site Ltd"),
                                      new_key(), intermediate_name, intermediate_key,
                                      -30, 60, False, ["other-site.example.net"])
    untrusted_leaf = build_certificate(site_subject, new_key(), unknown_root_name,
                                       unknown_root_key, -10, 80, False, site_names)
    # Forged: the issuer NAME says "Demo Intermediate CA", but it is signed with
    # a completely different key, so the signature check will fail.
    forged_leaf = build_certificate(site_subject, new_key(), intermediate_name,
                                    new_key(), -30, 60, False, site_names)
    attacker_leaf = build_certificate(site_subject, new_key(), attacker_root_name,
                                      attacker_root_key, -1, 30, False, site_names)

    _generated["roots"] = {
        "Demo Root CA": demo_root,
        "Unknown Root CA": unknown_root,
        "Interception Proxy CA": attacker_root,
    }
    # The chain each "server" presents. Roots normally come from the trust store,
    # so the Demo chain does not include the root itself.
    _generated["chains"] = {
        "valid": [valid_leaf, intermediate],
        "expired": [expired_leaf, intermediate],
        "mismatch": [mismatch_leaf, intermediate],
        "untrusted": [untrusted_leaf, unknown_root],
        "bad_signature": [forged_leaf, intermediate],
        "attacker_trusted": [attacker_leaf, attacker_root],
    }
    return _generated


# --- Reading certificate fields for display ---

def get_common_name(name):
    """Pull the CN value out of an X.509 name."""
    values = name.get_attributes_for_oid(NameOID.COMMON_NAME)
    if values:
        return values[0].value
    return "(none)"


def get_dns_names(certificate):
    """Return the list of DNS names in the Subject Alternative Name extension."""
    try:
        extension = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    except x509.ExtensionNotFound:
        return []
    return extension.value.get_values_for_type(x509.DNSName)


def is_ca_certificate(certificate):
    """True if Basic Constraints says this certificate is a CA."""
    try:
        extension = certificate.extensions.get_extension_for_class(x509.BasicConstraints)
    except x509.ExtensionNotFound:
        return False
    return extension.value.ca


def describe_certificate(certificate):
    """Turn a certificate object into a simple dictionary for the web page."""
    public_bytes = certificate.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return {
        "subject": certificate.subject.rfc4514_string(),
        "subject_cn": get_common_name(certificate.subject),
        "issuer": certificate.issuer.rfc4514_string(),
        "issuer_cn": get_common_name(certificate.issuer),
        "san": get_dns_names(certificate),
        "not_before": certificate.not_valid_before_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "not_after": certificate.not_valid_after_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "serial": format(certificate.serial_number, "x"),
        "public_key": "EC P-256 (secp256r1), 256 bits: " + public_bytes.hex()[:40] + "...",
        "signature_algorithm": "ECDSA with SHA-256 (" + certificate.signature_algorithm_oid.dotted_string + ")",
        "signature": certificate.signature.hex()[:48] + "...",
        "fingerprint": certificate.fingerprint(hashes.SHA256()).hex(":")[:59] + "...",
        "is_ca": is_ca_certificate(certificate),
        "self_signed": certificate.issuer == certificate.subject,
        "pem": certificate.public_bytes(serialization.Encoding.PEM).decode("ascii"),
    }


# --- Verifying certificates - the browser's job ---

def hostname_matches(hostname, dns_name):
    """Check one hostname against one certificate name, including wildcards."""
    hostname = hostname.lower().strip(".")
    dns_name = dns_name.lower()
    if dns_name.startswith("*."):
        suffix = dns_name[2:]
        first_label, _, rest = hostname.partition(".")
        return rest == suffix and first_label != ""
    return hostname == dns_name


def check_hostname(certificate, hostname):
    """Is the visited hostname listed in the certificate's SAN?"""
    names = get_dns_names(certificate)
    for name in names:
        if hostname_matches(hostname, name):
            return {"name": "Domain name", "key": "hostname", "passed": True,
                    "detail": "'" + hostname + "' matches the certificate name '" + name + "'."}
    return {"name": "Domain name", "key": "hostname", "passed": False,
            "detail": "'" + hostname + "' is not in the certificate's names: " + ", ".join(names) + "."}


def check_validity(chain):
    """Are all certificates in the chain inside their validity period?"""
    now = datetime.datetime.now(datetime.timezone.utc)
    for certificate in chain:
        name = get_common_name(certificate.subject)
        if now < certificate.not_valid_before_utc:
            return {"name": "Validity period", "key": "validity", "passed": False,
                    "detail": "'" + name + "' is not valid yet."}
        if now > certificate.not_valid_after_utc:
            days_ago = (now - certificate.not_valid_after_utc).days
            return {"name": "Validity period", "key": "validity", "passed": False,
                    "detail": "'" + name + "' expired " + str(days_ago) + " days ago ("
                              + certificate.not_valid_after_utc.strftime("%Y-%m-%d") + ")."}
    return {"name": "Validity period", "key": "validity", "passed": True,
            "detail": "Every certificate in the chain is currently within its validity dates."}


def signature_is_valid(certificate, issuer_certificate):
    """Use the issuer's PUBLIC key to check the certificate's signature."""
    issuer_public_key = issuer_certificate.public_key()
    try:
        issuer_public_key.verify(
            certificate.signature,
            certificate.tbs_certificate_bytes,   # the signed part of the certificate
            ec.ECDSA(certificate.signature_hash_algorithm),
        )
    except InvalidSignature:
        return False
    return True


def find_issuer(certificate, chain, position, trusted_roots):
    """Find the certificate that issued this one: the next one in the chain, or a trusted root whose name matches the issuer field."""
    if position + 1 < len(chain):
        return chain[position + 1]
    for root in trusted_roots:
        if root.subject == certificate.issuer:
            return root
    if certificate.issuer == certificate.subject:
        return certificate   # self-signed: it vouches for itself
    return None


def check_signatures(chain, trusted_roots):
    """Walk up the chain checking every signature."""
    for position, certificate in enumerate(chain):
        issuer = find_issuer(certificate, chain, position, trusted_roots)
        name = get_common_name(certificate.subject)
        if issuer is None:
            # We cannot find the issuer at all - that is a trust problem, not a
            # broken signature, so the trust check reports it.
            continue
        if not signature_is_valid(certificate, issuer):
            return {"name": "Signature", "key": "signature", "passed": False,
                    "detail": "The signature on '" + name + "' does NOT verify with the public key of '"
                              + get_common_name(issuer.subject) + "'. It was forged or altered."}
    return {"name": "Signature", "key": "signature", "passed": True,
            "detail": "Every signature in the chain verifies with its issuer's public key."}


def check_trust(chain, trusted_roots):
    """Does the chain end at a root certificate that is in the trust store?"""
    last = chain[-1]
    trusted_fingerprints = [root.fingerprint(hashes.SHA256()) for root in trusted_roots]
    if last.fingerprint(hashes.SHA256()) in trusted_fingerprints:
        return {"name": "Trusted root CA", "key": "trust", "passed": True,
                "detail": "The chain ends at '" + get_common_name(last.subject) + "', which is in the trust store."}
    for root in trusted_roots:
        if root.subject == last.issuer:
            return {"name": "Trusted root CA", "key": "trust", "passed": True,
                    "detail": "The chain leads to '" + get_common_name(root.subject) + "', which is in the trust store."}
    return {"name": "Trusted root CA", "key": "trust", "passed": False,
            "detail": "The chain ends at '" + get_common_name(last.issuer) + "', which is NOT in the trust store."}


def verify_chain(chain, hostname, trusted_root_names):
    """Run all four browser checks and decide what the browser should do."""
    roots = generate_all_certificates()["roots"]
    trusted_roots = [roots[name] for name in trusted_root_names if name in roots]

    checks = [
        check_hostname(chain[0], hostname),
        check_validity(chain),
        check_signatures(chain, trusted_roots),
        check_trust(chain, trusted_roots),
    ]

    failed = [check for check in checks if not check["passed"]]
    if failed:
        first_failure = failed[0]
        verdict = {
            "trusted": False,
            "error_code": BROWSER_ERRORS[first_failure["key"]],
            "headline": "Your connection is not private",
            "message": "Attackers might be trying to steal your information from " + hostname
                       + ". " + first_failure["detail"],
        }
    else:
        verdict = {
            "trusted": True,
            "error_code": "",
            "headline": "Connection is secure",
            "message": "The certificate is valid for " + hostname + ". This proves you are "
                       "talking to the holder of this domain's key. It does NOT prove the "
                       "website is honest or safe.",
        }
    return {"checks": checks, "verdict": verdict}


def explore_scenario(scenario, hostname=SITE_NAME, trusted_root_names=None):
    """Return everything the Certificate Explorer page needs for one scenario."""
    if trusted_root_names is None:
        trusted_root_names = ["Demo Root CA"]
    data = generate_all_certificates()
    chain = data["chains"].get(scenario, data["chains"]["valid"])

    described_chain = [describe_certificate(certificate) for certificate in chain]
    # If the root comes from the trust store (not sent by the server), show it
    # at the top of the chain view so the full path is visible.
    last = chain[-1]
    root_from_store = None
    if last.issuer != last.subject:
        for root in data["roots"].values():
            if root.subject == last.issuer:
                root_from_store = describe_certificate(root)

    result = verify_chain(chain, hostname, trusted_root_names)
    return {
        "scenario": scenario,
        "hostname": hostname,
        "chain": described_chain,
        "root_from_store": root_from_store,
        "checks": result["checks"],
        "verdict": result["verdict"],
        "trust_store": list(data["roots"].keys()),
        "trusted": trusted_root_names,
    }
