"""steps.py - Shared helpers for building simulation steps."""


def make_node(node_id, label, sublabel, icon, role):
    """Describe one device in the left-to-right network diagram."""
    return {"id": node_id, "label": label, "sublabel": sublabel, "icon": icon, "role": role}


def make_packet(from_device, to_device, style, label, details=None, payload=""):
    """Describe one packet travelling along a connection line."""
    return {
        "from": from_device,
        "to": to_device,
        "style": style,
        "label": label,
        "details": details or {},
        "payload": payload,
    }


def make_step(title, explanation, packet=None, highlight=None, panels=None):
    """Describe one step of a simulation."""
    return {
        "title": title,
        "explanation": explanation,
        "packet": packet,
        "highlight": highlight or {},
        "panels": panels or {},
    }
