# HTTPS & TLS Learning Lab

A Flask app that demonstrates HTTPS, TLS and Man-in-the-Middle attacks.
All networks and attacks are simulated; the cryptography is real (Python `cryptography` library).

## Run it

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Modes

- **Presentation Mode** (`/present`) – a self-running 2-minute demo with a timer.
  Controls: Pause/Resume (Space), Previous/Next scene (← →), Restart.
- **Exploration Mode** – six labs: HTTP vs HTTPS, TLS handshake, Encryption, Certificates,
  MITM attacks (incl. ARP spoofing and TLS stripping), Packet inspection.

## Structure

```
app.py                 Flask routes (pages + JSON API)
progress.py            Exploration progress
simulations/           One Python module per lab + presentation.py
templates/             HTML pages
static/css, static/js  Styling and animations (interactions.js is shared)
```

Python builds each simulation as a list of steps and returns it as JSON;
JavaScript only animates those steps.
