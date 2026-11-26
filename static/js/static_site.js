/* static_site.js - only on the GitHub Pages copy of the lab (see build_site.py).

   GitHub Pages can only serve files; it cannot run Python. So this file starts
   Pyodide (Python made to run in the browser), loads the same app.py and
   simulations from python-lab.zip, and sends every apiPost / apiGet to Flask
   inside the browser. The real encryption still happens in Python - just on the
   visitor's own computer. */

const PYODIDE_VERSION = "0.28.3";
const pythonReady = startPython();

// Start Python once per page. Pages wait for this before their first request.
async function startPython() {
  showPythonStatus("Starting Python in your browser... (the first visit can take a few seconds)");
  try {
    await loadScript("https://cdn.jsdelivr.net/pyodide/v" + PYODIDE_VERSION + "/full/pyodide.js");
    const pyodide = await loadPyodide();
    await pyodide.loadPackage(["cryptography", "markupsafe"]);
    const zip = await fetch(PYTHON_ZIP_URL);
    pyodide.unpackArchive(await zip.arrayBuffer(), "zip");
    // Signs this visitor's progress cookie. Made at random and kept in this browser only.
    pyodide.globals.set("visitor_key", visitorKey());
    pyodide.runPython("import os\nos.environ['LAB_SECRET_KEY'] = visitor_key");
    const api = pyodide.pyimport("browser_api");
    hidePythonStatus();
    return api;
  } catch (error) {
    showPythonStatus("Python could not start in this browser: " + error.message);
    throw error;
  }
}

// Same names as in interactions.js, so every page works without changes.
apiPost = function (url, data) { return callPython("POST", url, data); };
apiGet = function (url) { return callPython("GET", url, null); };

async function callPython(method, url, data) {
  const api = await pythonReady;
  const reply = JSON.parse(api.call(method, url, JSON.stringify(data || {}), readStored("labSession")));
  writeStored("labSession", reply.session);
  if (reply.status >= 400) throw new Error("Python returned " + reply.status);
  return JSON.parse(reply.body);
}

// The sidebar was drawn without the visitor's progress: fill it in once Python is ready.
// labWasComplete is set first, so an already finished lab does not offer "Continue" again.
pythonReady.then(async function () {
  const progress = await apiGet("/api/progress");
  progress.modules.forEach(function (module) { labWasComplete[module.slug] = module.complete; });
  updateSidebarProgress(progress);
});

function loadScript(src) {
  return new Promise(function (resolve, reject) {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = function () { reject(new Error("could not load " + src)); };
    document.head.appendChild(script);
  });
}

// localStorage can be blocked (private windows): then progress just lasts for this page.
function readStored(key) {
  try {
    return window.localStorage.getItem(key) || "";
  } catch (error) {
    return "";
  }
}

function writeStored(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (error) {
    // Nothing to do: storage is blocked.
  }
}

function visitorKey() {
  let key = readStored("labKey");
  if (!key) {
    const bytes = new Uint8Array(32);
    window.crypto.getRandomValues(bytes);
    key = Array.from(bytes, function (byte) { return byte.toString(16).padStart(2, "0"); }).join("");
    writeStored("labKey", key);
  }
  return key;
}

// A small note in the corner while Python starts (or if it cannot start).
function showPythonStatus(text) {
  let note = document.getElementById("python-status");
  if (!note) {
    note = document.createElement("div");
    note.id = "python-status";
    note.className = "python-status";
    note.setAttribute("role", "status");
    document.body.appendChild(note);
  }
  note.textContent = text;
}

function hidePythonStatus() {
  const note = document.getElementById("python-status");
  if (note) note.remove();
}
