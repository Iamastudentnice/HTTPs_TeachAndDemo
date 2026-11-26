"""browser_api.py - Used only on the GitHub Pages copy of the lab.

GitHub Pages cannot run a Python server, so static_site.js runs Python inside the
visitor's browser (Pyodide) and loads this file. It passes each request from the
page to the real Flask app with Flask's test client, so app.py runs unchanged.
"""

import json

import app as lab

client = lab.app.test_client()


def call(method, url, body_json, saved_session):
    """Send one request to the Flask app and return the reply as JSON text.

    saved_session is the visitor's progress cookie from the last request (kept by
    static_site.js in the browser), so progress survives moving between pages.
    """
    if saved_session:
        client.set_cookie("session", saved_session)
    if method == "GET":
        response = client.get(url)
    else:
        response = client.post(url, data=body_json, content_type="application/json")
    cookie = client.get_cookie("session")
    return json.dumps({
        "status": response.status_code,
        "body": response.get_data(as_text=True),
        "session": cookie.value if cookie else "",
    })
