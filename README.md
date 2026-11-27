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

- **Start page** (`/`) – the HTTP vs HTTPS lesson. It opens with one action (Send message) and
  reveals the rest as you go: the outputs after Send, then the comparison and the optional Wi-Fi
  eavesdropper after the first full run.
- **Start Here – Learn HTTPS** (green button) – an optional six-step tutorial. Each step has a task
  (for example, finish an HTTP run or open a packet) and Next only works once it has really been done.
  The tutorial box can be dragged by its header, and Hide (or Esc) tucks it away without ending it.
  While the tutorial is running, links to other labs are blocked (the page shakes and a short
  warning appears). Skip tutorial (click twice: it is padlocked) is the one way out early: it removes
  every restriction, and all labs open freely.
  Progress is kept for the browser tab: a refresh returns to the same step, and opening another lab
  by the back button or a typed address leads straight back to the tutorial.
  The box shows only what is happening (one sentence), what to do, and an arrow to where to look.
  Each step is split into small tasks shown one at a time. Reading tasks have a
  Got it button; action tasks (Send, Switch to HTTPS, tick the eavesdropper box) finish by
  themselves the moment the action really happens. A small green arrow points at the current task
  only, and it disappears as soon as the task is done (where there is no room for an arrow, the
  element gets a dashed green outline). The box moves beside each new target and never covers it.
  Step 6 is finished as soon as the eavesdropper box is ticked.
- **Lab completed prompt** – when a lab's activities are all done, a box offers
  "Continue to <next lab>" and "Explore Freely" (Packet Inspector, the last lab, only offers
  Explore Freely). Nothing opens by itself. Completing Lab 01 also ends the tutorial lock.
- **One part at a time** – Labs 05, 06 and 07 are shown in short numbered parts, like the stages of
  Lab 02. "Next" under the last part reveals the next one; "Show all" reveals everything at once.
- **Glossary** (`/glossary`, at the end of the index) – every key word from the labs in one line,
  A–Z, with a search box and a link to the lab that uses it.
- **The Journey of a Website** (`/journey`, Lab 02) – type an address (google.com is filled in) and
  follow it through eight stages: reading the address, saved copies (caching), DNS, leaving the home
  network, the TCP connection, TLS, the HTTP request and response, and the page appearing. Each stage
  waits for Next Step. It is a simulation only: nothing is looked up and no website is contacted.
- **Explore deeper** – the other labs in the left-hand index: TLS 1.3 handshake, Encryption,
  Certificates, MITM attacks (fake certificates, TLS stripping, ARP spoofing) and Packet inspection.
  `/labs` lists them all. MITM scenarios can be linked directly, e.g. `/mitm?scenario=arp`.
- Simulations only move when you press a button: Send message / Start shows the first step, and
  Next Step moves one step at a time. Select any packet to inspect it.
- The demo login (John Doe / example123) is fictional. Never type a real password into the app.

## Public copy on GitHub Pages

GitHub Pages can only serve files, it cannot run a Python server. `python build_site.py` builds a
copy of the lab in the `site` folder: every page saved as HTML, plus `static/python-lab.zip` with
this Python code. In that copy, `static/js/static_site.js` starts Pyodide (Python that runs inside
the browser) and sends each request to the same Flask app, so the encryption is still done by
Python - on the visitor's own computer. Publish the contents of `site` to the `gh-pages` branch.
Running the lab locally (above) does not use any of this.

## Structure

```
app.py                 Flask routes (pages + JSON API)
progress.py            Exploration progress
glossary.py            The glossary words and their one-line meanings
build_site.py          Builds the GitHub Pages copy (folder "site")
browser_api.py         GitHub Pages copy only: passes requests to Flask inside the browser
simulations/           One Python module per lab
templates/             HTML pages
static/css, static/js  Styling and animations (interactions.js is shared)
```

Python builds each simulation as a list of steps and returns it as JSON;
JavaScript only animates those steps.
