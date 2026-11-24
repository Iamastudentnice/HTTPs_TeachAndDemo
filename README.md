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
