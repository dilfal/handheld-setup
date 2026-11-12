(() => {
  "use strict";

  const DEVICES = {
    oxp: {
      name: "OneXPlayer 1S",
      shortPath: "070293.xyz/oxp",
      script: "install-onexplayer.sh",
      profile: "onexplayer1s",
      image: "bazzite-deck",
      installGuide: "guide/installazione_onexplayer_1s.html",
      optGuide: "guide/ottimizzazione_onexplayer_1s.html",
      notes: [
        "Immagine Bazzite consigliata: <strong>bazzite-deck</strong> (KDE Plasma 6).",
        "Include la correzione <code>INTEL_DEBUG=norbc</code> contro lo schermo nero in Gaming Mode.",
        "TDP regolabile via Intel RAPL (15W / 20W / 28W), modalità silenziosa con tasto fisico MUTE sul retro e Cura Batteria all'80%."
      ]
    },
    ally: {
      name: "ASUS ROG Ally (Z1 Extreme)",
      shortPath: "070293.xyz/ally",
      script: "install-rog-ally.sh",
      profile: "rogallyz1x",
      image: "bazzite-deck",
      installGuide: "guide/installazione_rog_ally.html",
      optGuide: "guide/ottimizzazione_rog_ally.html",
      notes: [
        "Immagine Bazzite consigliata: <strong>bazzite-deck</strong> (KDE Plasma 6; <code>bazzite-ally</code> non esiste più).",
        "Il limite di carica all'80% usa un servizio systemd + regola udev per restare attivo dopo riavvio, standby e collegamento USB-C.",
        "TDP (7W–30W) e FreeSync VRR 120Hz si gestiscono dal Menu Rapido di Steam (tasto Armoury Crate)."
      ]
    },
    generico: {
      name: "Altro handheld (profilo generico)",
      shortPath: "070293.xyz/bhs",
      script: "install.sh",
      profile: "generico",
      image: "bazzite-deck",
      installGuide: "guide/index.html",
      optGuide: "guide/index.html",
      notes: [
        "Rileva automaticamente l'hardware quando avvii la finestra grafica e applica solo impostazioni sicure.",
        "Include tema scuro KDE, scala display 125%, tastiera a schermo e Cura Batteria all'80%.",
        "Se il dispositivo reale non corrisponde allo script lanciato, la finestra ti avvisa senza bloccarsi."
      ]
    }
  };

  const SITUATIONS = {
    windows: {
      badge: "Passo 1 · Preparazione",
      title: (d) => `Prepara Windows e la chiavetta USB per ${d.name}`,
      desc: (d) =>
        `Prima di lanciare lo script, disattiva BitLocker e Avvio Rapido su Windows e scrivi la ISO di <strong>${d.image}</strong> su chiavetta con Rufus. Qui sotto trovi già il comando che userai subito dopo l'installazione.`,
      cmdLabel: "Comando da tenere pronto dopo il setup di Bazzite",
      useNoPipePrimary: false
    },
    live: {
      badge: "Modalità Live USB (/mnt/sysimage)",
      title: (d) => `Pre-configura l'SSD prima di riavviare (${d.name})`,
      desc: () =>
        "A installazione finita dalla Live USB di Bazzite (prima di estrarre la chiavetta e riavviare), apri il terminale e lancia il comando: l'installatore riconosce <code>/mnt/sysimage</code>, applica subito i fix iniziali sul disco appena installato e prepara l'apertura automatica della finestra KDE al primo avvio.",
      cmdLabel: "Comando da eseguire nel terminale della Live USB",
      useNoPipePrimary: false
    },
    console: {
      badge: "Recupero automatico Console (Ctrl+Alt+F3)",
      title: (d) => `Sblocca lo schermo nero dalla console (${d.name})`,
      desc: (d) =>
        d.profile === "onexplayer1s"
          ? "Premi <code>Ctrl+Alt+F3</code> e accedi col tuo utente. Lo script rileva la console senza sessione grafica: applica subito <code>INTEL_DEBUG=norbc</code>, scarica l'app e il <code>.venv</code> PySide6, imposta l'Autostart sul Desktop KDE e riavvia da solo dopo 5 secondi."
          : "Premi <code>Ctrl+Alt+F3</code> e accedi col tuo utente. Lo script rileva la console senza sessione grafica, prepara l'app e il <code>.venv</code> PySide6 in <code>~/.local/share/bazzite-handheld-setup</code>, imposta l'Autostart sul Desktop KDE e riavvia automaticamente dopo 5 secondi.",
      cmdLabel: "Variante comoda da digitare a mano (senza barra verticale |)",
      useNoPipePrimary: true
    },
    desktop: {
      badge: "Avvio guidato Qt6",
      title: (d) => `Apri la finestra grafica su KDE Plasma (${d.name})`,
      desc: () =>
        "Apri Konsole sul Desktop KDE e incolla il comando: scarica l'app, crea l'ambiente virtuale isolato <code>.venv</code> con PySide6 (preservandolo negli aggiornamenti successivi), aggiunge le icone nel menu e sul Desktop e apre la finestra guidata. Nulla viene modificato finché non premi «Installa».",
      cmdLabel: "Comando rapido per Konsole (Desktop KDE)",
      useNoPipePrimary: false
    }
  };

  const SHOTS = [
    {
      key: "0_benvenuto",
      title: "0 · Benvenuto e controllo sistema",
      desc: "Mostra la panoramica iniziale e lo scopo dell'assistente senza modificare alcun file sul dispositivo."
    },
    {
      key: "1_dispositivo",
      title: "1 · Rilevamento dispositivo e profilo",
      desc: "Legge modello hardware, immagine Bazzite e note specifiche del profilo (con avviso non bloccante se il dispositivo differisce)."
    },
    {
      key: "2_app",
      title: "2 · Scelta delle app (Flatpak, Brew, ujust)",
      desc: "21+ applicazioni suddivise per Launcher, Emulazione, Handheld e Utilità; le app già presenti risultano spuntate e bloccate."
    },
    {
      key: "3_tweak",
      title: "3 · Tweak consigliati e Avanzate",
      desc: "Impostazioni KDE Plasma 6, fix hardware (es. INTEL_DEBUG=norbc), Cura Batteria 80% e opzioni avanzate facoltative."
    },
    {
      key: "4_riepilogo",
      title: "4 · Riepilogo trasparente prima di applicare",
      desc: "Elenca ogni comando e azione prevista (incluse eventuali richieste pkexec) prima di toccare il sistema."
    },
    {
      key: "5_esecuzione",
      title: "5 · Esecuzione e log in tempo reale",
      desc: "Esegue i comandi in sequenza mostrando l'avanzamento passo per passo e l'esito finale."
    }
  ];

  let selectedDevice = "oxp";
  let selectedSituation = "desktop";
  let shotDevice = "oxp";
  let shotIndex = 0;

  function buildCommands(device) {
    const shortPipe = `curl -L ${device.shortPath} | sh`;
    const shortNoPipe = `curl -Lo f ${device.shortPath} && sh f`;
    const githubRaw = `curl -fsSL https://raw.githubusercontent.com/dilfal/bazzite-handheld-setup/main/${device.script} | bash`;
    return { shortPipe, shortNoPipe, githubRaw };
  }

  function copyText(button, text) {
    const markCopied = () => {
      const original = button.dataset.origLabel || button.textContent;
      button.dataset.origLabel = original;
      button.textContent = "Copiato!";
      button.classList.add("copied");
      setTimeout(() => {
        button.textContent = original;
        button.classList.remove("copied");
      }, 1800);
    };

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(markCopied).catch(() => fallbackCopy(text, markCopied));
    } else {
      fallbackCopy(text, markCopied);
    }
  }

  function fallbackCopy(text, onDone) {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand("copy");
      onDone();
    } finally {
      document.body.removeChild(area);
    }
  }

  function renderWizard() {
    const device = DEVICES[selectedDevice];
    const situation = SITUATIONS[selectedSituation];
    const cmds = buildCommands(device);

    document.querySelectorAll("[data-device]").forEach((btn) => {
      const active = btn.dataset.device === selectedDevice;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", String(active));
    });

    document.querySelectorAll("[data-situation]").forEach((btn) => {
      const active = btn.dataset.situation === selectedSituation;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", String(active));
    });

    const panel = document.getElementById("wizard-result");
    panel.dataset.accent = selectedDevice;

    const primaryCmd = situation.useNoPipePrimary ? cmds.shortNoPipe : cmds.shortPipe;
    const secondaryCmd = situation.useNoPipePrimary ? cmds.shortPipe : cmds.shortNoPipe;
    const secondaryLabel = situation.useNoPipePrimary
      ? "Versione breve con pipe (|):"
      : "Variante senza barra verticale | (comoda in console Ctrl+Alt+F3):";

    const guideLinks =
      selectedDevice === "generico"
        ? `<a class="btn-link primary" href="guide/index.html">Apri l'Hub Guide</a>`
        : `<a class="btn-link primary" href="${device.installGuide}">Apri Guida Installazione (${device.name})</a>
           <a class="btn-link" href="${device.optGuide}">Guida Ottimizzazione Giochi .exe</a>`;

    panel.innerHTML = `
      <div class="result-top">
        <span class="result-badge">${situation.badge}</span>
        <span style="font-size:12.5px; color: var(--text-muted);">Profilo: <code>${device.profile}</code> · Script: <code>${device.script}</code></span>
      </div>
      <h3>${situation.title(device)}</h3>
      <p class="result-desc">${situation.desc(device)}</p>

      <div style="font-size:12px; color: var(--text-muted); margin-bottom:6px; font-weight:600;">${situation.cmdLabel}</div>
      <div class="cmd-box">
        <code>${primaryCmd}</code>
        <button type="button" class="btn-copy" data-copy="${encodeURIComponent(primaryCmd)}">Copia comando</button>
      </div>

      <div class="alt-cmds">
        <div class="alt-cmd-item">
          <div>
            <span class="alt-cmd-label">${secondaryLabel}</span>
            <code>${secondaryCmd}</code>
          </div>
          <button type="button" class="btn-copy" data-copy="${encodeURIComponent(secondaryCmd)}">Copia</button>
        </div>
        <div class="alt-cmd-item">
          <div>
            <span class="alt-cmd-label">Indirizzo diretto da GitHub (fallback se la scorciatoia non risponde):</span>
            <code>${cmds.githubRaw}</code>
          </div>
          <button type="button" class="btn-copy" data-copy="${encodeURIComponent(cmds.githubRaw)}">Copia</button>
        </div>
      </div>

      <div class="result-notes">
        <strong>Note specifiche per ${device.name}:</strong>
        <ul>
          ${device.notes.map((n) => `<li>${n}</li>`).join("")}
        </ul>
      </div>

      <div class="result-actions">
        ${guideLinks}
      </div>
    `;

    panel.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", () => {
        copyText(btn, decodeURIComponent(btn.dataset.copy));
      });
    });
  }

  function renderShots() {
    const step = SHOTS[shotIndex];
    const prefix = shotDevice === "oxp" ? "oxp/oxp_fisso-onexplayer1s" : "ally/ally_fisso-rogallyz1x";
    const src = `shots/${prefix}_${step.key}.png`;
    const labelDevice = shotDevice === "oxp" ? "OneXPlayer 1S" : "ASUS ROG Ally";

    const img = document.getElementById("shot-img");
    img.src = src;
    img.alt = `${step.title} — ${labelDevice}`;

    document.getElementById("shot-title").textContent = `${step.title} (${labelDevice})`;
    document.getElementById("shot-desc").textContent = step.desc;

    document.querySelectorAll("[data-shot-device]").forEach((btn) => {
      const active = btn.dataset.shotDevice === shotDevice;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", String(active));
    });

    document.querySelectorAll("[data-shot-step]").forEach((btn) => {
      const active = Number(btn.dataset.shotStep) === shotIndex;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-current", active ? "step" : "false");
    });
  }

  function init() {
    document.querySelectorAll("[data-device]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedDevice = btn.dataset.device;
        if (selectedDevice === "oxp" || selectedDevice === "ally") {
          shotDevice = selectedDevice;
          renderShots();
        }
        renderWizard();
      });
    });

    document.querySelectorAll("[data-situation]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedSituation = btn.dataset.situation;
        renderWizard();
      });
    });

    document.querySelectorAll("[data-shot-device]").forEach((btn) => {
      btn.addEventListener("click", () => {
        shotDevice = btn.dataset.shotDevice;
        renderShots();
      });
    });

    const stepList = document.getElementById("shot-step-list");
    stepList.innerHTML = SHOTS.map(
      (s, idx) =>
        `<button type="button" class="shot-step-btn" data-shot-step="${idx}">${s.title}</button>`
    ).join("");
    stepList.querySelectorAll("[data-shot-step]").forEach((btn) => {
      btn.addEventListener("click", () => {
        shotIndex = Number(btn.dataset.shotStep);
        renderShots();
      });
    });

    // Lightbox per ingrandire lo screenshot
    const lightbox = document.getElementById("lightbox");
    const lightboxImg = document.getElementById("lightbox-img");
    const shotImg = document.getElementById("shot-img");

    shotImg.addEventListener("click", () => {
      lightboxImg.src = shotImg.src;
      lightboxImg.alt = shotImg.alt;
      lightbox.classList.add("is-open");
    });

    const closeLightbox = () => lightbox.classList.remove("is-open");
    document.getElementById("lightbox-close").addEventListener("click", closeLightbox);
    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) closeLightbox();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeLightbox();
    });

    renderWizard();
    renderShots();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
