/* encryption.js - Lab 4. */

document.addEventListener("DOMContentLoaded", function () {
  setupTabs(document);

  // Put text into an output box.
  function show(element, text, className) {
    element.className = "output " + (className || "");
    element.textContent = text;
  }

  // Show a green (success) or red (failure) result badge.
  function badge(container, ok, text) {
    container.innerHTML = '<span class="result-badge ' + (ok ? "ok" : "bad") + '">' +
      iconSvg(ok ? "check" : "x") + " " + escapeHtml(text) + "</span>";
  }

  /* ---------------- Symmetric (AES-GCM) ---------------- */
  const symmetric = { key: "", nonce: "", cipher: "" };

  $("#sym-encrypt").addEventListener("click", async function () {
    const result = await apiPost("/api/encryption/symmetric/encrypt", { text: $("#sym-text").value });
    symmetric.key = result.key_hex;
    symmetric.nonce = result.nonce_hex;
    symmetric.cipher = result.combined_hex;
    show($("#sym-key"), result.key_hex, "");
    show($("#sym-nonce"), result.nonce_hex, "");
    show($("#sym-cipher"), result.combined_hex, "cipher");
    $("#sym-tampered").innerHTML = "";
    $("#sym-result").innerHTML = '<span class="small muted">' + result.plaintext_length + " bytes of plaintext became " +
      result.ciphertext_length + " bytes (ciphertext + 16-byte tag). Not readable without the key.</span>";
    ["#sym-decrypt", "#sym-tamper", "#sym-wrongkey"].forEach(function (id) { $(id).disabled = false; });
    refreshProgress();   // Python recorded this activity; update the index (and the lab-complete check)
  });

  // Ask Python to decrypt and show the result.
  async function decrypt(keyHex, cipherHex) {
    const result = await apiPost("/api/encryption/symmetric/decrypt",
      { key_hex: keyHex, nonce_hex: symmetric.nonce, combined_hex: cipherHex });
    if (result.success) badge($("#sym-result"), true, 'Decrypted: "' + result.plaintext + '"');
    else badge($("#sym-result"), false, result.error);
  }

  $("#sym-decrypt").addEventListener("click", function () { decrypt(symmetric.key, symmetric.cipher); });

  $("#sym-tamper").addEventListener("click", async function () {
    const result = await apiPost("/api/encryption/symmetric/tamper", { combined_hex: symmetric.cipher });
    symmetric.cipher = result.combined_hex;
    show($("#sym-cipher"), result.combined_hex, "danger");
    $("#sym-tampered").innerHTML = '<span class="tag tag-red">tampered</span>';
    $("#sym-result").innerHTML = '<span class="small muted">One byte changed. Now press Decrypt.</span>';
  });

  $("#sym-wrongkey").addEventListener("click", async function () {
    const other = await apiPost("/api/encryption/symmetric/new-key");
    decrypt(other.key_hex, symmetric.cipher);
  });

  /* ---------------- Asymmetric (RSA) ---------------- */
  const rsaKeys = { publicPem: "", privatePem: "", cipher: "" };

  $("#rsa-generate").addEventListener("click", async function () {
    this.disabled = true;
    const keys = await apiPost("/api/encryption/rsa/generate");
    this.disabled = false;
    rsaKeys.publicPem = keys.public_pem;
    rsaKeys.privatePem = keys.private_pem;
    show($("#rsa-public"), keys.public_pem, "plain");
    show($("#rsa-private"), keys.private_pem, "danger");
    show($("#rsa-cipher"), "-", "empty");
    $("#rsa-encrypt").disabled = false;
    $("#rsa-decrypt").disabled = true;
    $("#rsa-wrong").disabled = true;
    $("#rsa-result").innerHTML = "";
  });

  $("#rsa-encrypt").addEventListener("click", async function () {
    const result = await apiPost("/api/encryption/rsa/encrypt", { public_pem: rsaKeys.publicPem, text: $("#rsa-text").value });
    if (!result.success) { badge($("#rsa-result"), false, result.error); return; }
    rsaKeys.cipher = result.ciphertext_hex;
    show($("#rsa-cipher"), result.ciphertext_hex, "cipher");
    $("#rsa-result").innerHTML = '<span class="small muted">Encrypted to ' + result.length + " bytes. Only the private key can undo this.</span>";
    $("#rsa-decrypt").disabled = false;
    $("#rsa-wrong").disabled = false;
  });

  // Ask Python to RSA-decrypt with the given private key.
  async function rsaDecrypt(privatePem) {
    const result = await apiPost("/api/encryption/rsa/decrypt", { private_pem: privatePem, ciphertext_hex: rsaKeys.cipher });
    if (result.success) badge($("#rsa-result"), true, 'Decrypted: "' + result.plaintext + '"');
    else badge($("#rsa-result"), false, result.error);
    refreshProgress();
  }

  $("#rsa-decrypt").addEventListener("click", function () { rsaDecrypt(rsaKeys.privatePem); });
  $("#rsa-wrong").addEventListener("click", async function () {
    const stranger = await apiPost("/api/encryption/rsa/generate");
    rsaDecrypt(stranger.private_pem);
  });

  /* ---------------- Hashing ---------------- */
  $("#hash-run").addEventListener("click", async function () {
    const result = await apiPost("/api/encryption/hash", {
      text_a: $("#hash-a").value, text_b: $("#hash-b").value, algorithm: $("#hash-algorithm").value,
    });
    show($("#hash-out-a"), result.first.hash_hex, "plain");
    show($("#hash-out-b"), result.second.hash_hex, "plain");
    let html;
    if (result.identical) {
      html = '<span class="result-badge ok">Identical inputs → identical hash</span>';
    } else {
      html = "<strong>" + result.different_bits + " of " + result.total_bits + " bits differ (" +
        result.percent_different + "%)</strong> - the avalanche effect." +
        '<div class="bit-meter"><span style="width:' + result.percent_different + '%"></span></div>';
    }
    if (result.first.algorithm === "MD5 (broken)") {
      html += '<div class="callout danger">MD5 is broken: attackers can create collisions. Shown for comparison only.</div>';
    }
    html += '<p class="muted" style="margin-top:8px">Always ' + result.total_bits +
      " bits, whatever the input length. There is no decrypt button because a hash cannot be reversed.</p>";
    $("#hash-compare").innerHTML = html;
    refreshProgress();
  });

  /* ---------------- Signatures ---------------- */
  const signing = { publicKey: "", privateKey: "", signature: "" };

  $("#sig-generate").addEventListener("click", async function () {
    const keys = await apiPost("/api/encryption/sign/generate");
    signing.publicKey = keys.public_key_hex;
    signing.privateKey = keys.private_key_hex;
    show($("#sig-public"), keys.public_key_hex, "plain");
    show($("#sig-signature"), "-", "empty");
    $("#sig-sign").disabled = false;
    $("#sig-verify").disabled = true;
    $("#sig-received").disabled = true;
    $("#sig-result").innerHTML = "";
  });

  $("#sig-sign").addEventListener("click", async function () {
    const result = await apiPost("/api/encryption/sign", { private_key_hex: signing.privateKey, message: $("#sig-message").value });
    if (!result.success) { badge($("#sig-result"), false, result.error); return; }
    signing.signature = result.signature_hex;
    show($("#sig-signature"), result.signature_hex, "cipher");
    $("#sig-received").value = $("#sig-message").value;
    $("#sig-received").disabled = false;
    $("#sig-verify").disabled = false;
    $("#sig-result").innerHTML = '<span class="small muted">Signed. Verify as-is, then try changing one letter of the received message.</span>';
  });

  $("#sig-verify").addEventListener("click", async function () {
    const result = await apiPost("/api/encryption/verify", {
      public_key_hex: signing.publicKey, message: $("#sig-received").value, signature_hex: signing.signature,
    });
    badge($("#sig-result"), result.valid, result.reason);
    refreshProgress();
  });
});
