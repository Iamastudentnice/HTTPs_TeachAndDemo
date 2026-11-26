"""build_site.py - Build the GitHub Pages copy of the lab into the folder "site".

GitHub Pages only serves files, so this script:
1. asks Flask to render every page once and saves each one as an .html file;
2. copies the static folder (CSS, JavaScript, images);
3. packs the Python code (app.py, simulations...) and Flask itself into
   static/python-lab.zip, which static_site.js runs in the visitor's browser.

Run:  python build_site.py   (it needs the internet once, to download Flask's files)
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from importlib.metadata import version

from app import app

SITE = "site"
# GitHub Pages serves this repository at https://<user>.github.io/HTTPs_TeachAndDemo/
BASE_PATH = "/HTTPs_TeachAndDemo"

# Address on the site -> file to save. GitHub Pages opens /journey from journey.html.
PAGES = {
    "/": "index.html",
    "/http-https": "http-https.html",   # Lab 01 again: the sidebar links to this address
    "/journey": "journey.html",
    "/tls-handshake": "tls-handshake.html",
    "/encryption": "encryption.html",
    "/certificates": "certificates.html",
    "/mitm": "mitm.html",
    "/packet-inspection": "packet-inspection.html",
    "/labs": "labs.html",
    "/glossary": "glossary.html",
}

# Our own Python files that run in the browser.
PYTHON_FILES = ["app.py", "progress.py", "glossary.py", "browser_api.py"]

# Flask and the packages it needs (pure Python). Same versions as installed here.
FLASK_PACKAGES = ["flask", "werkzeug", "jinja2", "itsdangerous", "click", "blinker"]


def render_pages():
    """Save every page as HTML, with links that start with BASE_PATH."""
    app.config["STATIC_SITE"] = True   # base.html then adds static_site.js
    client = app.test_client()
    for path, filename in PAGES.items():
        response = client.get(path, base_url="http://localhost" + BASE_PATH)
        if response.status_code != 200:
            sys.exit("Could not render " + path + ": " + str(response.status_code))
        with open(os.path.join(SITE, filename), "w", encoding="utf-8") as page:
            page.write(response.get_data(as_text=True))
        print("page   ", filename)


def download_flask(folder):
    """Download the Flask wheels (zip files) into folder."""
    packages = [name + "==" + version(name) for name in FLASK_PACKAGES]
    subprocess.run([sys.executable, "-m", "pip", "download", "--quiet", "--no-deps",
                    "--only-binary", ":all:", "--dest", folder] + packages, check=True)


def build_python_zip():
    """Pack our Python files and Flask into static/python-lab.zip."""
    zip_path = os.path.join(SITE, "static", "python-lab.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in PYTHON_FILES:
            bundle.write(name)
        for name in sorted(os.listdir("simulations")):
            if name.endswith(".py"):
                bundle.write(os.path.join("simulations", name))

        # A wheel is a zip file: copy its contents (e.g. the flask/ folder) into ours.
        with tempfile.TemporaryDirectory() as folder:
            download_flask(folder)
            for wheel_name in sorted(os.listdir(folder)):
                with zipfile.ZipFile(os.path.join(folder, wheel_name)) as wheel:
                    for item in wheel.namelist():
                        bundle.writestr(item, wheel.read(item))
                print("package", wheel_name)
    print("zip    ", zip_path, os.path.getsize(zip_path) // 1024, "KB")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))   # work next to this file
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    shutil.copytree("static", os.path.join(SITE, "static"))
    render_pages()
    build_python_zip()
    # Tell GitHub Pages to serve the files as they are (no Jekyll processing).
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    print("Done. Publish the contents of", SITE, "to the gh-pages branch.")


if __name__ == "__main__":
    main()
