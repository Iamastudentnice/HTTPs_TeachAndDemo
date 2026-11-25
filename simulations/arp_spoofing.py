"""arp_spoofing.py - Scenario E of the MITM lab: ARP spoofing on a local network."""

from simulations.steps import make_node, make_packet, make_step

VICTIM = "victim"
ATTACKER = "attacker"
GATEWAY = "gateway"

DEVICES = {
    VICTIM: {"ip": "192.168.1.20", "mac": "aa:bb:cc:00:00:20"},
    ATTACKER: {"ip": "192.168.1.66", "mac": "de:ad:be:ef:00:66"},
    GATEWAY: {"ip": "192.168.1.1", "mac": "00:11:22:33:44:01"},
}

DEFENCES = {
    "none": "No protection",
    "dai": "Dynamic ARP Inspection (switch)",
    "static": "Static ARP entry on victim",
}


def diagram_nodes():
    """Victim, attacker and gateway from left to right."""
    return [
        make_node(VICTIM, "Victim PC", DEVICES[VICTIM]["ip"], "laptop", "client"),
        make_node(ATTACKER, "Attacker", DEVICES[ATTACKER]["ip"], "attacker", "attacker"),
        make_node(GATEWAY, "Gateway / Router", DEVICES[GATEWAY]["ip"], "router", "gateway"),
    ]


def table_entry(device, status="ok", mac_override=None):
    """One row of an ARP table: IP address -> MAC address."""
    mac = mac_override or DEVICES[device]["mac"]
    return {"ip": DEVICES[device]["ip"], "mac": mac, "status": status}


def detect_arp_spoofing(arp_table):
    """Look for the classic sign of ARP spoofing: one MAC address claiming to be several different IP addresses."""
    ips_for_mac = {}
    for entry in arp_table:
        mac = entry["mac"]
        if mac not in ips_for_mac:
            ips_for_mac[mac] = []
        ips_for_mac[mac].append(entry["ip"])

    warnings = []
    for mac, ip_list in ips_for_mac.items():
        if len(ip_list) > 1:
            warnings.append("MAC " + mac + " is claiming several IPs: " + ", ".join(ip_list)
                            + ". This is a strong sign of ARP spoofing.")
    return warnings


def frame_details(kind, source_device, destination_mac, sender_ip, sender_mac, target_ip):
    """Details shown when an ARP packet is clicked."""
    return {
        "Protocol": "ARP (" + kind + ")",
        "Ethernet source MAC": DEVICES[source_device]["mac"],
        "Ethernet destination MAC": destination_mac,
        "Sender IP / MAC": sender_ip + " / " + sender_mac,
        "Target IP": target_ip,
        "Authenticated": "No - ARP has no authentication",
    }


def direct_packet(from_device, to_device, style, label, details, payload=""):
    """A packet that travels the direct switch path (not through the attacker)."""
    packet = make_packet(from_device, to_device, style, label, details, payload)
    packet["route"] = "direct"
    return packet


def build_arp_steps(defence="none"):
    """Return the nodes, extra links and steps for the ARP spoofing scenario."""
    if defence not in DEFENCES:
        defence = "none"
    victim_ip = DEVICES[VICTIM]["ip"]
    gateway_ip = DEVICES[GATEWAY]["ip"]
    attacker_mac = DEVICES[ATTACKER]["mac"]

    steps = []
    steps.append(make_step(
        "1. The local network",
        "Three devices share one switch. The victim needs the gateway's MAC address first.",
        highlight={VICTIM: "active"},
        panels={"tables": {VICTIM: [], GATEWAY: [], ATTACKER: []},
                "defence": DEFENCES[defence]}))

    steps.append(make_step(
        "2. ARP request (broadcast)",
        "The victim asks everyone: 'Who has " + gateway_ip + "?' The attacker hears it too.",
        packet=direct_packet(VICTIM, GATEWAY, "plain", "ARP: Who has " + gateway_ip + "?",
                             frame_details("request", VICTIM, "ff:ff:ff:ff:ff:ff (broadcast)",
                                           victim_ip, DEVICES[VICTIM]["mac"], gateway_ip)),
        highlight={VICTIM: "active", ATTACKER: "warning"}))

    steps.append(make_step(
        "3. ARP reply from the real gateway",
        "The gateway answers: '" + gateway_ip + " is at " + DEVICES[GATEWAY]["mac"] + "'. The "
        "victim stores this in its ARP table.",
        packet=direct_packet(GATEWAY, VICTIM, "plain", "ARP: " + gateway_ip + " is at 00:11:..",
                             frame_details("reply", GATEWAY, DEVICES[VICTIM]["mac"],
                                           gateway_ip, DEVICES[GATEWAY]["mac"], victim_ip)),
        highlight={GATEWAY: "active"},
        panels={"tables": {VICTIM: [table_entry(GATEWAY)],
                           GATEWAY: [table_entry(VICTIM)], ATTACKER: []}}))

    steps.append(make_step(
        "4. Normal traffic goes straight to the gateway",
        "Traffic goes straight to the gateway. The attacker is not on the path.",
        packet=direct_packet(VICTIM, GATEWAY, "plain", "Frame → 00:11:22:33:44:01",
                             {"Ethernet destination MAC": DEVICES[GATEWAY]["mac"],
                              "IP destination": "198.51.100.7 (a website)",
                              "Path": "Victim → switch → gateway"}),
        highlight={VICTIM: "active", GATEWAY: "active"}))

    poisoned_victim_table = [table_entry(GATEWAY, "poisoned", attacker_mac)]
    forged_to_victim = make_packet(
        ATTACKER, VICTIM, "malicious", "Forged ARP: " + gateway_ip + " is at de:ad:..",
        frame_details("unsolicited reply", ATTACKER, DEVICES[VICTIM]["mac"],
                      gateway_ip + " (LIE)", attacker_mac, victim_ip))

    if defence == "dai":
        steps.append(make_step(
            "5. Attacker sends a forged ARP reply",
            "The attacker claims to be the gateway, but the switch checks every ARP reply.",
            packet=forged_to_victim,
            highlight={ATTACKER: "danger"}))
        steps.append(make_step(
            "6. The switch drops the forged reply",
            "That MAC does not own " + gateway_ip + ", so the switch drops the reply. "
            "The victim's table stays correct.",
            highlight={ATTACKER: "inactive", VICTIM: "secure"},
            panels={"detection": ["Switch log: Invalid ARP from de:ad:be:ef:00:66 claiming "
                                  + gateway_ip + " - dropped (DAI)."], "outcome": "safe"}))
        steps.append(make_step(
            "7. Traffic still flows directly",
            "The attacker never gets into the path.",
            packet=direct_packet(VICTIM, GATEWAY, "plain", "Frame → 00:11:22:33:44:01",
                                 {"Ethernet destination MAC": DEVICES[GATEWAY]["mac"],
                                  "Path": "Victim → switch → gateway"}),
            highlight={VICTIM: "secure", GATEWAY: "active"}))
        return package(steps)

    if defence == "static":
        steps.append(make_step(
            "5. Attacker sends a forged ARP reply",
            "The attacker claims to be the gateway, but the victim's entry is fixed (static).",
            packet=forged_to_victim,
            highlight={ATTACKER: "danger"},
            panels={"tables": {VICTIM: [table_entry(GATEWAY, "static")],
                               GATEWAY: [table_entry(VICTIM)], ATTACKER: []}}))
        steps.append(make_step(
            "6. The forged reply is ignored",
            "Traffic still goes to the real gateway. (Static entries are hard to manage at scale.)",
            packet=direct_packet(VICTIM, GATEWAY, "plain", "Frame → 00:11:22:33:44:01",
                                 {"Ethernet destination MAC": DEVICES[GATEWAY]["mac"]}),
            highlight={VICTIM: "secure", ATTACKER: "inactive"},
            panels={"outcome": "safe"}))
        return package(steps)

    # No defence: the attack succeeds.
    steps.append(make_step(
        "5. Attacker poisons the victim's ARP table",
        "A fake reply says '" + gateway_ip + " is at " + attacker_mac
        + "'. ARP has no checks, so the victim believes it.",
        packet=forged_to_victim,
        highlight={ATTACKER: "danger", VICTIM: "danger"},
        panels={"tables": {VICTIM: poisoned_victim_table, GATEWAY: [table_entry(VICTIM)],
                           ATTACKER: []}}))

    poisoned_gateway_table = [table_entry(VICTIM, "poisoned", attacker_mac)]
    steps.append(make_step(
        "6. Attacker poisons the gateway too",
        "A second fake reply fools the gateway. Now traffic both ways goes to the attacker.",
        packet=make_packet(ATTACKER, GATEWAY, "malicious", "Forged ARP: " + victim_ip + " is at de:ad:..",
                           frame_details("unsolicited reply", ATTACKER, DEVICES[GATEWAY]["mac"],
                                         victim_ip + " (LIE)", attacker_mac, gateway_ip)),
        highlight={ATTACKER: "danger", GATEWAY: "danger"},
        panels={"tables": {VICTIM: poisoned_victim_table, GATEWAY: poisoned_gateway_table,
                           ATTACKER: [table_entry(VICTIM), table_entry(GATEWAY)]}}))

    steps.append(make_step(
        "7. Victim's traffic now goes to the attacker",
        "The IP address is right, but the MAC is the attacker's - so the attacker gets it.",
        packet=make_packet(VICTIM, ATTACKER, "malicious", "Frame → de:ad:be:ef:00:66",
                           {"Ethernet destination MAC": attacker_mac + " (attacker!)",
                            "IP destination": "198.51.100.7 (unchanged)",
                            "Path": "Victim → attacker"}),
        highlight={VICTIM: "danger", ATTACKER: "danger"}))

    steps.append(make_step(
        "8. Attacker forwards to the real gateway",
        "The attacker passes traffic on, so nothing seems wrong. It is now a man in the middle.",
        packet=make_packet(ATTACKER, GATEWAY, "malicious", "Forwarded frame",
                           {"Ethernet destination MAC": DEVICES[GATEWAY]["mac"],
                            "Note": "HTTP content is readable; HTTPS content stays encrypted"}),
        highlight={ATTACKER: "danger"}))

    # Run the real detection function on the victim's table plus the attacker's own entry.
    victim_view = poisoned_victim_table + [table_entry(ATTACKER)]
    warnings = detect_arp_spoofing(victim_view)
    steps.append(make_step(
        "9. Detecting the attack",
        "Python scanned the ARP table: two IP addresses now share one MAC. That is the clue.",
        highlight={VICTIM: "warning"},
        panels={"tables": {VICTIM: victim_view, GATEWAY: poisoned_gateway_table,
                           ATTACKER: [table_entry(VICTIM), table_entry(GATEWAY)]},
                "detection": warnings, "outcome": "compromised"}))
    return package(steps)


def package(steps):
    """Bundle the steps with the diagram layout, including the direct switch path."""
    return {
        "nodes": diagram_nodes(),
        "extra_links": [{"from": VICTIM, "to": GATEWAY, "label": "direct path via switch"}],
        "steps": steps,
    }
