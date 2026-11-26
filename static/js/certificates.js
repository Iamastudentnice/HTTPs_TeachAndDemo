/* certificates.js - Lab 5. */

document.addEventListener("DOMContentLoaded", function () {
  let scenario = "valid";
  let trusted = ["Demo Root CA"];
  let trustStoreNames = [];
  let latest = null;
  let selectedCertificate = 0;

  // Which certificate field to flag for each failed check.
  const PROBLEM_FIELD = { hostname: "san", validity: "validity", signature: "signature_algorithm", trust: "issuer" };

  // Ask Python for the data and redraw the page.
  async function load() {
    latest = await apiPost("/api/certificates/scenario", {
      scenario: scenario, hostname: $("#hostname").value, trusted: trusted,
    });
    trustStoreNames = latest.trust_store;
    selectedCertificate = 0;
    renderTrustStore();
    renderBrowser();
    renderChecks();
    renderChain();
    renderCertificate();
    refreshProgress();
  }

  // Show the trust store checkboxes.
  function renderTrustStore() {
    const container = $("#trust-store");
    container.innerHTML = "";
    trustStoreNames.forEach(function (name) {
      const label = document.createElement("label");
      label.className = "checkbox";
      label.style.display = "flex";
      label.style.marginBottom = "6px";
      label.innerHTML = '<input type="checkbox" ' + (trusted.indexOf(name) >= 0 ? "checked" : "") + "> " + escapeHtml(name);
      $("input", label).addEventListener("change", function (event) {
        if (event.target.checked) trusted.push(name);
        else trusted = trusted.filter(function (item) { return item !== name; });
        load();
      });
      container.appendChild(label);
    });
  }

  // Show the padlock page or the browser warning.
  function renderBrowser() {
    const verdict = latest.verdict;
    const address = $("#address");
    address.className = "address " + (verdict.trusted ? "secure" : "insecure");
    $("svg use", address).setAttribute("href", verdict.trusted ? "#i-lock" : "#i-warning");
    if (verdict.trusted) {
      $("#browser-body").innerHTML = '<div class="secure-page"><h3>' + iconSvg("lock") + " " + escapeHtml(verdict.headline) +
        '</h3><p class="small">' + escapeHtml(verdict.message) + "</p></div>";
    } else {
      $("#browser-body").innerHTML = '<div class="warning-page"><h3>' + iconSvg("warning") + " " + escapeHtml(verdict.headline) +
        '</h3><p class="small">' + escapeHtml(verdict.message) + '</p><div class="code">' + escapeHtml(verdict.error_code) +
        '</div><div class="choice-row"><button class="btn btn-green btn-sm" id="go-back">Back to safety</button></div></div>';
      $("#go-back").addEventListener("click", function () {
        $("#browser-body").innerHTML = '<div class="callout good"><strong>Connection closed.</strong> No data was sent to the untrusted server.</div>';
      });
    }
  }

  // Show the four browser checks as pass/fail.
  function renderChecks() {
    $("#checks").innerHTML = latest.checks.map(function (check) {
      return '<li class="' + (check.passed ? "pass" : "fail") + '"><span class="mark">' + (check.passed ? "✓" : "✕") +
        "</span><div><strong>" + escapeHtml(check.name) + "</strong>" + escapeHtml(check.detail) + "</div></li>";
    }).join("");
  }

  // Chain is displayed root first: root → intermediate → site.
  function chainForDisplay() {
    const list = latest.chain.slice().reverse();
    if (latest.root_from_store) list.unshift(latest.root_from_store);
    return list;
  }

  // Draw the clickable certificate chain.
  function renderChain() {
    const chain = $("#chain");
    chain.innerHTML = "";
    const display = chainForDisplay();
    const signatureFailed = latest.checks.some(function (check) { return check.key === "signature" && !check.passed; });
    const trustFailed = latest.checks.some(function (check) { return check.key === "trust" && !check.passed; });
    display.forEach(function (certificate, position) {
      if (position > 0) chain.insertAdjacentHTML("beforeend", '<span class="chain-arrow">→</span>');
      const isLeaf = position === display.length - 1;
      const role = certificate.self_signed ? "Root CA" : certificate.is_ca ? "Intermediate CA" : "Website";
      const item = document.createElement("button");
      const bad = (isLeaf && signatureFailed) || (position === 0 && trustFailed);
      item.className = "chain-item" + (bad ? " bad" : "");
      item.innerHTML = '<span class="role">' + role + "</span><strong>" + escapeHtml(certificate.subject_cn) + "</strong>";
      item.addEventListener("click", function () {
        selectedCertificate = display.length - 1 - position;
        renderCertificate(certificate);
        $all(".chain-item", chain).forEach(function (other) { other.classList.toggle("selected", other === item); });
      });
      if (isLeaf) item.classList.add("selected");
      chain.appendChild(item);
    });
  }

  // Show the selected certificate's fields.
  function renderCertificate(certificate) {
    certificate = certificate || latest.chain[0];
    const problems = latest.checks.filter(function (check) { return !check.passed; })
      .map(function (check) { return PROBLEM_FIELD[check.key]; });
    const isLeaf = certificate === latest.chain[0];
    const fields = [
      ["subject", "Subject", certificate.subject],
      ["issuer", "Issuer (signed by)", certificate.issuer],
      ["san", "Domain names (SAN)", certificate.san.length ? certificate.san.join(", ") : "(none - CA certificate)"],
      ["validity", "Validity period", certificate.not_before + "  →  " + certificate.not_after],
      ["public_key", "Public key", certificate.public_key],
      ["signature_algorithm", "Signature algorithm", certificate.signature_algorithm],
      ["ca", "Certificate Authority", certificate.self_signed ? "Self-signed root CA (" + certificate.subject_cn + ")" : certificate.issuer_cn],
      ["basic_constraints", "Basic constraints", certificate.is_ca ? "CA: TRUE (may sign certificates)" : "CA: FALSE (website certificate)"],
      ["serial", "Serial number", certificate.serial],
      ["fingerprint", "SHA-256 fingerprint", certificate.fingerprint],
    ];
    let html = '<div class="cert-head">' + iconSvg("certificate") + '<div><strong>' + escapeHtml(certificate.subject_cn) +
      '</strong><div class="small muted">X.509 v3 certificate · generated by Python</div></div></div>';
    fields.forEach(function (field) {
      const problem = isLeaf && problems.indexOf(field[0]) >= 0;
      html += '<button class="cert-field' + (problem ? " problem" : "") + '" data-field="' + field[0] + '">' +
        '<span class="fname"><span class="info-dot">i</span>' + escapeHtml(field[1]) + (problem ? ' <span class="tag tag-red">problem</span>' : "") +
        '</span><span class="fvalue">' + escapeHtml(field[2]) + "</span></button>";
    });
    $("#certificate").innerHTML = html;
    $all(".cert-field", $("#certificate")).forEach(function (button) {
      button.addEventListener("click", function () {
        $all(".cert-field").forEach(function (other) { other.classList.toggle("selected", other === button); });
        const key = button.dataset.field;
        const label = $(".fname", button).textContent.replace(/^i/, "").replace("problem", "").trim();
        // Show the explanation directly under the field that was selected.
        const old = $(".field-help", $("#certificate"));
        if (old) old.remove();
        const help = document.createElement("div");
        help.className = "callout field-help";
        help.innerHTML = "<strong>" + escapeHtml(label) + ":</strong> " + escapeHtml(FIELD_EXPLANATIONS[key] || "");
        button.insertAdjacentElement("afterend", help);
      });
    });
  }

  $all(".scenario-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      $all(".scenario-btn").forEach(function (other) { other.classList.toggle("active", other === button); });
      scenario = button.dataset.scenario;
      load();
    });
  });
  $("#visit").addEventListener("click", load);
  $("#hostname").addEventListener("keydown", function (event) { if (event.key === "Enter") load(); });

  load();
});
