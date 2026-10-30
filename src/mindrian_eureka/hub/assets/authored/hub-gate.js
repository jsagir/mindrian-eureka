(function () {
  "use strict";

  const envelope = window.HUB_ENVELOPE;
  const app = window.HubApp;
  if (!envelope || !app || !app.copy) return;
  const block = document.getElementById("hub-locked");
  const form = document.getElementById("hub-locked-form");
  const field = document.getElementById("hub-passphrase");
  const toggle = document.getElementById("hub-passphrase-toggle");
  const unlock = document.getElementById("hub-unlock");
  const status = document.getElementById("hub-locked-status");
  let busy = false;

  function message(id, error) {
    status.textContent = app.fmt(id);
    status.classList.toggle("hub-gate-error", Boolean(error));
    document.getElementById("hub-face").setAttribute("src",
      "assets/faces/theo-" + (id === "L08" ? "limit" : "boundary") + ".svg");
  }
  function bytes(value) {
    const decoded = atob(value);
    const result = new Uint8Array(decoded.length);
    for (let index = 0; index < decoded.length; index += 1) result[index] = decoded.charCodeAt(index);
    return result;
  }
  field.classList.add("hub-field");
  unlock.classList.add("hub-button");
  toggle.classList.add("hub-button", "hub-button--quiet");
  if (!window.crypto || !window.crypto.subtle) {
    message("L06", true);
    unlock.disabled = true;
    field.disabled = true;
    toggle.disabled = true;
    return;
  }
  field.focus();
  toggle.addEventListener("click", function () {
    const show = field.type === "password";
    field.type = show ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(show));
    toggle.textContent = app.fmt(show ? "L03.hide" : "L03.show");
  });
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (busy) return;
    busy = true;
    unlock.disabled = true;
    message("L04", false);
    let passphrase = field.value;
    try {
      let cleartext;
      try {
        if (!passphrase || envelope.schema !== "eureka.hub-envelope.v1" ||
            envelope.kdf.name !== "PBKDF2-SHA256" || envelope.kdf.iterations !== 600000 ||
            envelope.cipher.name !== "AES-256-GCM") throw new Error();
        const salt = bytes(envelope.kdf.salt);
        const nonce = bytes(envelope.cipher.nonce);
        const ciphertext = bytes(envelope.ciphertext);
        if (salt.length !== 16 || nonce.length !== 12 || ciphertext.length < 16) throw new Error();
        const material = await window.crypto.subtle.importKey(
          "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"]
        );
        const key = await window.crypto.subtle.deriveKey({
          name: "PBKDF2", salt: salt, iterations: envelope.kdf.iterations, hash: "SHA-256"
        }, material, {name: "AES-GCM", length: 256}, false, ["decrypt"]);
        const aad = new TextEncoder().encode(envelope.schema + "|" + envelope.kdf.iterations);
        cleartext = await window.crypto.subtle.decrypt({
          name: "AES-GCM", iv: nonce, additionalData: aad, tagLength: 128
        }, key, ciphertext);
      } catch (_) {
        message("L05", true);
        field.focus();
        return;
      }
      let payload;
      try {
        payload = JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(cleartext));
        if (!payload || payload.schema !== "eureka.hub-data.v1" ||
            !Array.isArray(payload.records) || !Array.isArray(payload.pairs) ||
            !Array.isArray(payload.hoods) || !Array.isArray(payload.bridges) ||
            !payload.counts || !payload.config || !payload.engines || !payload.data_check) {
          throw new Error();
        }
      } catch (_) {
        message("L08", true);
        field.focus();
        return;
      }
      field.value = "";
      passphrase = null;
      block.remove();
      app.start(payload);
      document.getElementById("hub-title").focus();
    } finally {
      passphrase = null;
      busy = false;
      unlock.disabled = false;
    }
  });
})();
