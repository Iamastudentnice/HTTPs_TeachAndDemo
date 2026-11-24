# HTTPS & TLS Learning Lab

A Flask app that demonstrates HTTPS, TLS and Man-in-the-Middle attacks.
All networks and attacks are simulated; the cryptography is real (Python `cryptography` library).

## Run it

Requires Python 3.10 or newer (check with `python3 --version`; download from python.org if needed).

### macOS / Linux (Terminal)

First time:

```bash
cd ~/Downloads/https_learning_lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Every time after that:

```bash
cd ~/Downloads/https_learning_lab
source .venv/bin/activate
python app.py
```

### Windows (PowerShell)

First time:

```powershell
cd $HOME\Downloads\https_learning_lab
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Every time after that: run the `cd`, `Activate.ps1` and `python app.py` lines.

### Open the app

Go to http://127.0.0.1:5000 in your browser. Keep the terminal window open while using it;
press `Ctrl + C` in the terminal to stop the app.

### Troubleshooting

- **macOS: "Address already in use" or a "403 Forbidden" page** – AirPlay Receiver also uses
  port 5000. Turn it off in System Settings → General → AirDrop & Handoff → AirPlay Receiver,
  or change `port=5000` to `port=5050` on the last line of `app.py` and open
  http://127.0.0.1:5050 instead.
- **`python3: command not found`** – install Python from python.org, then reopen the terminal.
- **Windows: "running scripts is disabled"** – run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

## Using the app

- **Landing page** (`/`) – a one-line explanation, a live MITM preview (HTTP vs HTTPS) and the list of labs.
- **Quick Guide** – an optional three-step guide (button in the header). It never advances by itself;
  use Next / Back, or Skip / Esc to close it.
- **Six labs**, all reachable from the laboratory index on the left: HTTP vs HTTPS, TLS 1.3 handshake,
  Encryption, Certificates, MITM attacks (incl. fake certificates, TLS stripping and ARP spoofing),
  Packet inspection. MITM scenarios can be linked directly, e.g. `/mitm?scenario=arp`.
- Simulations only run when you press Start. Controls: Start, Pause, Resume, Previous Step, Next Step,
  Replay, Reset. Select any packet to inspect it.

## Structure

```
app.py                 Flask routes (pages + JSON API)
progress.py            Exploration progress
simulations/           One Python module per lab
templates/             HTML pages
static/css, static/js  Styling and animations (interactions.js is shared)
```

Python builds each simulation as a list of steps and returns it as JSON;
JavaScript only animates those steps.
