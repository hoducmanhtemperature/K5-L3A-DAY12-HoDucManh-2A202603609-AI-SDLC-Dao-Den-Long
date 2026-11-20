(() => {
  "use strict";

  const NIGHT_INTROS = {
    1: { title: "Đêm 1 — Đảo Bến", quote: "Ông Đăng: \"Thắp lại 5 ngọn đèn đầu tiên để xua sương đen khỏi bến cũ.\"" },
    2: { title: "Đêm 2 — Đảo Cau", quote: "Ông Đăng: \"Hai hòn đảo nối bằng cầu tre. Coi chừng Gió Lạc và tận dụng Bùa Gió!\"" },
    3: { title: "Đêm 3 — Đảo Chuông", quote: "Ông Đăng: \"Đảo Chuông ba tầng gió lớn. Lên tới tháp chuông và đón bình minh!\"" },
  };

  const wrap = document.getElementById("canvas-wrap");
  const overlay = document.getElementById("overlay");
  const modalKicker = document.getElementById("modal-kicker");
  const modalTitle = document.getElementById("modal-title");
  const modalDesc = document.getElementById("modal-desc");
  const controlsPanel = document.getElementById("controls-panel");
  const settingsPanel = document.getElementById("settings-panel");
  const optVolume = document.getElementById("opt-volume");
  const optSens = document.getElementById("opt-sens");
  const optColorblind = document.getElementById("opt-colorblind");
  const optReducedMotion = document.getElementById("opt-reduced-motion");
  const optLargeText = document.getElementById("opt-large-text");
  const btnResetKeys = document.getElementById("btn-reset-keys");
  const rebindList = document.getElementById("rebind-list");
  const rebindError = document.getElementById("rebind-error");
  const leaderboardPanel = document.getElementById("leaderboard-panel");
  const lbBody = document.getElementById("lb-body");
  const saveScorePanel = document.getElementById("save-score-panel");
  const lbName = document.getElementById("lb-name");
  const btnSaveScore = document.getElementById("btn-save-score");
  const lbSaveMsg = document.getElementById("lb-save-msg");

  const btnPrimary = document.getElementById("btn-primary");
  const btnSecondary = document.getElementById("btn-secondary");
  const btnLeaderboard = document.getElementById("btn-leaderboard");
  const btnSettings = document.getElementById("btn-settings");
  const btnMenu = document.getElementById("btn-menu");

  const elFlames = document.getElementById("flames");
  const elNightLabel = document.getElementById("night-label");
  const elTimer = document.getElementById("timer");
  const elWind = document.getElementById("wind-banner");
  const elLit = document.getElementById("lit-count");
  const elLitTarget = document.getElementById("lit-target");
  const elLowFuel = document.getElementById("low-fuel-banner");
  const elScore = document.getElementById("score");
  const elCarried = document.getElementById("carried-text");
  const elCharmTag = document.getElementById("charm-tag");
  const elPips = document.getElementById("pips");
  const elDashCd = document.getElementById("dash-cd");
  const elPulseCd = document.getElementById("pulse-cd");
  const elPrompt = document.getElementById("interact-prompt");
  const elArrow = document.getElementById("offscreen-arrow");
  const elShadeArrow = document.getElementById("shade-arrow");
  const elSubtitle = document.getElementById("subtitle-bar");

  // Persistent settings & Accessibility (Ticket-02, Ticket-03, Ticket-04)
  const DEFAULT_KEYS = {
    up: "KeyW", down: "KeyS", left: "KeyA", right: "KeyD",
    jump: "Space", dash: "ShiftLeft", interact: "KeyE", pulse: "KeyQ", pause: "Escape",
  };
  const ACTION_LABELS = {
    up: "Lên", down: "Xuống", left: "Trái", right: "Phải",
    jump: "Nhảy", dash: "Lướt", interact: "Tương tác", pulse: "Tỏa Sáng", pause: "Tạm dừng",
  };
  let keybinds = { ...DEFAULT_KEYS };
  try {
    const saved = JSON.parse(localStorage.getItem("ddl_keybinds") || "null");
    if (saved && typeof saved === "object") keybinds = { ...DEFAULT_KEYS, ...saved };
  } catch (_) {}
  let listeningAction = null;

  function renderRebindList() {
    rebindList.innerHTML = "";
    for (const [act, label] of Object.entries(ACTION_LABELS)) {
      const row = document.createElement("div");
      row.className = "rebind-row";
      const sp = document.createElement("span");
      sp.textContent = label;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "secondary small-btn";
      btn.textContent = listeningAction === act ? "Nhấn phím..." : keybinds[act];
      btn.addEventListener("click", () => {
        listeningAction = act;
        rebindError.classList.add("hidden");
        renderRebindList();
      });
      row.appendChild(sp);
      row.appendChild(btn);
      rebindList.appendChild(row);
    }
  }
  renderRebindList();
  btnResetKeys.addEventListener("click", () => {
    keybinds = { ...DEFAULT_KEYS };
    listeningAction = null;
    localStorage.setItem("ddl_keybinds", JSON.stringify(keybinds));
    rebindError.classList.add("hidden");
    renderRebindList();
  });

  const settings = {
    volume: parseFloat(localStorage.getItem("ddl_volume") || "0.6"),
    sensitivity: parseFloat(localStorage.getItem("ddl_sens") || "0.35"),
    colorblind: localStorage.getItem("ddl_colorblind") === "1",
    reducedMotion: localStorage.getItem("ddl_reduced_motion") === "1",
    largeText: localStorage.getItem("ddl_large_text") === "1",
  };
  optVolume.value = String(settings.volume);
  optSens.value = String(settings.sensitivity);
  optColorblind.checked = settings.colorblind;
  optReducedMotion.checked = settings.reducedMotion;
  optLargeText.checked = settings.largeText;
  document.body.classList.toggle("colorblind", settings.colorblind);
  document.body.classList.toggle("reduced-motion", settings.reducedMotion);
  document.body.classList.toggle("large-text", settings.largeText);
  optVolume.addEventListener("input", () => {
    settings.volume = parseFloat(optVolume.value);
    localStorage.setItem("ddl_volume", String(settings.volume));
  });
  optSens.addEventListener("input", () => {
    settings.sensitivity = parseFloat(optSens.value);
    localStorage.setItem("ddl_sens", String(settings.sensitivity));
  });
  optColorblind.addEventListener("change", () => {
    settings.colorblind = optColorblind.checked;
    localStorage.setItem("ddl_colorblind", settings.colorblind ? "1" : "0");
    document.body.classList.toggle("colorblind", settings.colorblind);
  });
  optReducedMotion.addEventListener("change", () => {
    settings.reducedMotion = optReducedMotion.checked;
    localStorage.setItem("ddl_reduced_motion", settings.reducedMotion ? "1" : "0");
    document.body.classList.toggle("reduced-motion", settings.reducedMotion);
  });
  optLargeText.addEventListener("change", () => {
    settings.largeText = optLargeText.checked;
    localStorage.setItem("ddl_large_text", settings.largeText ? "1" : "0");
    document.body.classList.toggle("large-text", settings.largeText);
  });

  let subtitleTimer = null;
  let lastSpawnedShadePos = null;
  let shadeArrowUntil = 0;
  function showSubtitle(text, ms = 2800) {
    elSubtitle.textContent = text;
    elSubtitle.classList.remove("hidden");
    if (subtitleTimer) clearTimeout(subtitleTimer);
    subtitleTimer = setTimeout(() => elSubtitle.classList.add("hidden"), ms);
  }

  async function refreshLeaderboard() {
    try {
      const res = await fetch("/api/leaderboard");
      const data = await res.json();
      lbBody.innerHTML = "";
      const entries = data.entries || [];
      if (!entries.length) {
        lbBody.innerHTML = '<tr><td colspan="4">Chưa có điểm nào được lưu.</td></tr>';
        return;
      }
      entries.forEach((e, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${idx + 1}</td><td>${e.name.replace(/[<>&]/g, "")}</td><td>${e.score}</td><td>${e.nights_won}/3</td>`;
        lbBody.appendChild(tr);
      });
    } catch (_) {}
  }

  // Procedural Web Audio (night ambience + SFX)
  let audioCtx = null;
  let lastCountdownSec = -1;
  function ensureAudio() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  function playTone(freq, dur, type = "sine", vol = 0.1) {
    if (!audioCtx || settings.volume <= 0.01) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(vol * settings.volume, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + dur);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
  }

  // Three.js scene with Ticket-02 Standard Palette
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0e1430);
  scene.fog = new THREE.FogExp2(0x1b2350, 0.02);

  const camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 0.1, 350);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  wrap.appendChild(renderer.domElement);

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.15);
  scene.add(ambientLight);
  const moonLight = new THREE.DirectionalLight(0xbcd0ff, 0.5);
  moonLight.position.set(25, 45, 20);
  scene.add(moonLight);

  const seaMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(500, 500),
    new THREE.MeshBasicMaterial({ color: 0x12384a, transparent: true, opacity: 0.9 })
  );
  seaMesh.rotation.x = -Math.PI / 2;
  seaMesh.position.y = -11;
  scene.add(seaMesh);

  let mapGroup = new THREE.Group();
  scene.add(mapGroup);
  let builtNight = 0;

  function buildNightGeometry(night) {
    if (builtNight === night) return;
    builtNight = night;
    scene.remove(mapGroup);
    mapGroup = new THREE.Group();
    const grass = new THREE.MeshStandardMaterial({ color: 0x2f5d50, roughness: 0.9 });
    const sand = new THREE.MeshStandardMaterial({ color: 0xc9b48a, roughness: 0.85 });
    const wood = new THREE.MeshStandardMaterial({ color: 0x6b4a2f, roughness: 0.8 });
    const padMat = new THREE.MeshBasicMaterial({ color: 0xf2c14e });

    const addIsland = (cx, cz, r, yTop, h = 2.4) => {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r - 1.2, h, 48), grass);
      m.position.set(cx, yTop - h / 2, cz);
      mapGroup.add(m);
      const rim = new THREE.Mesh(new THREE.TorusGeometry(r, 0.35, 8, 48), sand);
      rim.rotation.x = Math.PI / 2;
      rim.position.set(cx, yTop, cz);
      mapGroup.add(rim);
    };

    if (night === 1) {
      addIsland(0, 0, 40, 0);
    } else if (night === 2) {
      addIsland(0, 0, 28, 0);
      addIsland(70, 0, 28, 0);
      const bridge = new THREE.Mesh(new THREE.BoxGeometry(18, 0.5, 4), wood);
      bridge.position.set(35, -0.25, 0);
      mapGroup.add(bridge);
      for (const [px, py, pz] of [[20, 0, 18], [50, 0, -18]]) {
        const pad = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.1, 0.25, 20), padMat);
        pad.position.set(px, py + 0.12, pz);
        mapGroup.add(pad);
      }
    } else if (night === 3) {
      addIsland(0, 0, 45, 0);
      // Tier 1 half-annulus (Y=3, r in [12, 24], z > 0)
      const shape = new THREE.Shape();
      shape.absarc(0, 0, 24, 0, Math.PI, false);
      shape.absarc(0, 0, 12, Math.PI, 0, true);
      const extrude = new THREE.ExtrudeGeometry(shape, { depth: 3, bevelEnabled: false });
      const tier1 = new THREE.Mesh(extrude, grass);
      tier1.rotation.x = -Math.PI / 2;
      tier1.position.y = 0;
      mapGroup.add(tier1);
      // Tier 2 center disk (Y=6, r=8)
      addIsland(0, 0, 8, 6, 6);
      // Bell tower (R=2, H=8 on Tier 2)
      const tower = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.0, 8.0, 24), wood);
      tower.position.set(0, 10, 0);
      mapGroup.add(tower);
      // 2 Ramps at 30 deg & 150 deg
      for (const deg of [30, 150]) {
        const ang = (deg * Math.PI) / 180;
        const ramp = new THREE.Mesh(new THREE.BoxGeometry(6.7, 0.35, 3.0), sand);
        ramp.position.set(27 * Math.cos(ang), 1.5, 27 * Math.sin(ang));
        ramp.rotation.y = -ang;
        ramp.rotation.z = -Math.atan2(3, 6);
        mapGroup.add(ramp);
      }
      const pad = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.1, 0.25, 20), padMat);
      pad.position.set(0, 3.12, 13);
      mapGroup.add(pad);
    }
    scene.add(mapGroup);
  }

  // Player Mây (Standard Palette: cloak #E8E2D0, scarf #C8102E)
  const playerGroup = new THREE.Group();
  const cloak = new THREE.Mesh(new THREE.ConeGeometry(0.42, 1.15, 16), new THREE.MeshStandardMaterial({ color: 0xe8e2d0 }));
  cloak.position.y = 0.6;
  playerGroup.add(cloak);
  const scarf = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.07, 8, 16), new THREE.MeshStandardMaterial({ color: 0xc8102e }));
  scarf.rotation.x = Math.PI / 2;
  scarf.position.y = 1.05;
  playerGroup.add(scarf);
  const hat = new THREE.Mesh(new THREE.ConeGeometry(0.56, 0.34, 24), new THREE.MeshStandardMaterial({ color: 0xc9b48a }));
  hat.position.y = 1.48;
  playerGroup.add(hat);
  const smallLantern = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 10), new THREE.MeshBasicMaterial({ color: 0xffe9b0 }));
  smallLantern.position.set(0.45, 1.22, 0.25);
  playerGroup.add(smallLantern);
  const playerLight = new THREE.PointLight(0xffb347, 1.2, 11);
  playerLight.position.set(0, 1.3, 0.3);
  playerGroup.add(playerLight);
  scene.add(playerGroup);

  const pulseRing = new THREE.Mesh(
    new THREE.RingGeometry(0.4, 0.65, 36),
    new THREE.MeshBasicMaterial({ color: 0xffe58a, side: THREE.DoubleSide, transparent: true, opacity: 0 })
  );
  pulseRing.rotation.x = -Math.PI / 2;
  scene.add(pulseRing);
  let pulseAnim = 0;

  const lanternViews = new Map();
  const moteViews = new Map();
  const shadeViews = new Map();
  const drifterViews = new Map();
  const charmViews = new Map();

  function clearEntityPools() {
    for (const m of [lanternViews, moteViews, shadeViews, drifterViews, charmViews]) {
      for (const v of m.values()) scene.remove(v.grp || v);
      m.clear();
    }
  }

  function ensureLanternView(lan) {
    if (lanternViews.has(lan.id)) return lanternViews.get(lan.id);
    const grp = new THREE.Group();
    grp.position.set(lan.pos[0], lan.pos[1], lan.pos[2]);
    const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.58, 2.2, 12), new THREE.MeshStandardMaterial({ color: 0x6b4a2f }));
    pillar.position.y = 1.1;
    grp.add(pillar);
    const coreMat = new THREE.MeshStandardMaterial({ color: 0x5b5f6e, emissive: 0x000000, emissiveIntensity: 0 });
    const core = new THREE.Mesh(new THREE.OctahedronGeometry(0.48, 0), coreMat);
    core.position.y = 2.6;
    grp.add(core);
    // 3D Fuel bar above lantern (Ticket-03)
    const fuelBg = new THREE.Mesh(
      new THREE.PlaneGeometry(1.4, 0.18),
      new THREE.MeshBasicMaterial({ color: 0x151c3d, side: THREE.DoubleSide })
    );
    fuelBg.position.set(0, 3.45, 0);
    grp.add(fuelBg);
    const fuelBarMat = new THREE.MeshBasicMaterial({ color: 0xffb347, side: THREE.DoubleSide });
    const fuelBar = new THREE.Mesh(new THREE.PlaneGeometry(1.32, 0.12), fuelBarMat);
    fuelBar.position.set(0, 3.45, 0.01);
    grp.add(fuelBar);
    const safeRing = new THREE.Mesh(
      new THREE.RingGeometry(5.85, 6.0, 48),
      new THREE.MeshBasicMaterial({ color: 0xffb347, side: THREE.DoubleSide, transparent: true, opacity: 0 })
    );
    safeRing.rotation.x = -Math.PI / 2;
    safeRing.position.y = 0.05;
    grp.add(safeRing);
    const light = new THREE.PointLight(0xffb347, 0, 18);
    light.position.y = 2.7;
    grp.add(light);
    scene.add(grp);
    const entry = { grp, core, coreMat, fuelBg, fuelBar, fuelBarMat, safeRing, light };
    lanternViews.set(lan.id, entry);
    return entry;
  }

  // Session & UI state
  let ws = null;
  let currentNight = 1;
  let currentSeed = 1;
  let nightsWon = 0;
  let totalGameScore = 0;
  let screenMode = "menu"; // menu | intro | playing | paused | result | dawn
  let lastState = null;

  const keys = new Set();
  let camYawDeg = 0;
  let dragging = false;
  let lastMouseX = 0;
  let pendingPauseToggle = false;

  window.addEventListener("keydown", (e) => {
    if (listeningAction) {
      e.preventDefault();
      const dup = Object.entries(keybinds).find(([a, c]) => a !== listeningAction && c === e.code);
      if (dup) {
        rebindError.textContent = `Phím ${e.code} đang được dùng cho "${ACTION_LABELS[dup[0]]}". Hãy chọn phím khác.`;
        rebindError.classList.remove("hidden");
        return;
      }
      keybinds[listeningAction] = e.code;
      localStorage.setItem("ddl_keybinds", JSON.stringify(keybinds));
      listeningAction = null;
      rebindError.classList.add("hidden");
      renderRebindList();
      return;
    }
    if (document.activeElement === lbName) return;
    if ((e.code === keybinds.pause) && !e.repeat) {
      if (screenMode === "playing" || screenMode === "paused") {
        pendingPauseToggle = true;
      }
    }
    keys.add(e.code);
  });
  window.addEventListener("keyup", (e) => keys.delete(e.code));
  window.addEventListener("mousedown", (e) => {
    if (screenMode === "playing" && e.button === 0) { dragging = true; lastMouseX = e.clientX; }
  });
  window.addEventListener("mouseup", () => { dragging = false; });
  window.addEventListener("mousemove", (e) => {
    if (!dragging || screenMode !== "playing") return;
    camYawDeg = (camYawDeg - (e.clientX - lastMouseX) * settings.sensitivity) % 360;
    lastMouseX = e.clientX;
  });
  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  function showModal(mode, title, kicker, desc, primaryText, showSecondary, showMenuBtn) {
    screenMode = mode;
    overlay.classList.remove("hidden");
    modalKicker.textContent = kicker;
    modalTitle.textContent = title;
    modalDesc.textContent = desc;
    btnPrimary.textContent = primaryText;
    btnSecondary.classList.toggle("hidden", !showSecondary);
    btnMenu.classList.toggle("hidden", !showMenuBtn);
    settingsPanel.classList.add("hidden");
    controlsPanel.classList.toggle("hidden", mode !== "menu" && mode !== "intro");
  }

  function connectWS(onOpen) {
    if (ws && ws.readyState === WebSocket.OPEN) { onOpen(); return; }
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws`);
    ws.onopen = onOpen;
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.events) {
        for (const e of msg.events) handleEvent(e);
      }
      if (msg.state) {
        lastState = msg.state;
        syncScene(msg.state);
        syncHUD(msg.state);
      }
    };
  }

  function startNight(night) {
    ensureAudio();
    currentNight = night;
    currentSeed = Math.floor(Math.random() * 100000) + 1;
    clearEntityPools();
    buildNightGeometry(night);
    connectWS(() => {
      ws.send(JSON.stringify({ cmd: "start", night, seed: currentSeed }));
      screenMode = "playing";
      overlay.classList.add("hidden");
      saveScorePanel.classList.add("hidden");
      leaderboardPanel.classList.add("hidden");
    });
  }

  btnSettings.addEventListener("click", () => {
    leaderboardPanel.classList.add("hidden");
    settingsPanel.classList.toggle("hidden");
  });

  btnLeaderboard.addEventListener("click", () => {
    settingsPanel.classList.add("hidden");
    leaderboardPanel.classList.toggle("hidden");
    if (!leaderboardPanel.classList.contains("hidden")) refreshLeaderboard();
  });

  btnSaveScore.addEventListener("click", async () => {
    const name = lbName.value.trim();
    lbSaveMsg.textContent = "";
    try {
      const res = await fetch("/api/leaderboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, score: totalGameScore, nights_won: nightsWon, seed: currentSeed }),
      });
      const data = await res.json();
      if (!res.ok) {
        lbSaveMsg.textContent = data.error || "Tên không hợp lệ.";
      } else {
        lbSaveMsg.textContent = "Đã lưu vào bảng xếp hạng!";
        btnSaveScore.disabled = true;
        refreshLeaderboard();
        leaderboardPanel.classList.remove("hidden");
      }
    } catch (_) {
      lbSaveMsg.textContent = "Không thể lưu điểm lúc này.";
    }
  });

  btnMenu.addEventListener("click", () => {
    totalGameScore = 0;
    nightsWon = 0;
    currentNight = 1;
    saveScorePanel.classList.add("hidden");
    showModal("menu", "Đảo Đèn Lồng", "Đảo Đèn Lồng · Ba Hòn Đảo", NIGHT_INTROS[1].quote, "Bắt đầu Đêm 1", false, false);
  });

  btnSecondary.addEventListener("click", () => startNight(currentNight));

  btnPrimary.addEventListener("click", () => {
    ensureAudio();
    if (screenMode === "menu") {
      showModal("intro", NIGHT_INTROS[currentNight].title, "Giới thiệu Đêm", NIGHT_INTROS[currentNight].quote, `Vào ${NIGHT_INTROS[currentNight].title}`, false, true);
    } else if (screenMode === "intro") {
      startNight(currentNight);
    } else if (screenMode === "paused") {
      pendingPauseToggle = true;
    } else if (screenMode === "result") {
      if (lastState && lastState.state === "won" && currentNight < 3) {
        currentNight += 1;
        showModal("intro", NIGHT_INTROS[currentNight].title, "Đêm kế tiếp", NIGHT_INTROS[currentNight].quote, `Vào ${NIGHT_INTROS[currentNight].title}`, false, true);
      } else {
        startNight(currentNight);
      }
    } else if (screenMode === "dawn") {
      totalGameScore = 0;
      nightsWon = 0;
      currentNight = 1;
      startNight(1);
    }
  });

  function handleEvent(ev) {
    if (ev.name === "mote_picked") playTone(740, 0.11, "sine", 0.08);
    else if (ev.name === "charm_picked") playTone(980, 0.25, "triangle", 0.11);
    else if (ev.name === "deposit") playTone(520, 0.14, "triangle", 0.09);
    else if (ev.name === "lantern_lit") { playTone(660, 0.22); setTimeout(() => playTone(880, 0.3), 100); }
    else if (ev.name === "pulse") { pulseAnim = 1.0; playTone(440, 0.32, "sine", 0.12); }
    else if (ev.name === "dash") playTone(320, 0.12, "triangle", 0.09);
    else if (ev.name === "player_hit") playTone(150, 0.3, "sawtooth", 0.11);
    else if (ev.name === "shade_spawned") {
      playTone(110, 0.25, "sawtooth", 0.06);
      showSubtitle("⚠ Bóng Mực xuất hiện!");
      if (ev.data && ev.data.pos) { lastSpawnedShadePos = ev.data.pos; shadeArrowUntil = performance.now() + 3500; }
    }
    else if (ev.name === "paused") {
      showModal("paused", "Tạm dừng", `Đêm ${currentNight}`, "Logic trò chơi đang dừng hoàn toàn.", "Tiếp tục", true, true);
    } else if (ev.name === "resumed") {
      screenMode = "playing";
      overlay.classList.add("hidden");
    } else if (ev.name === "game_over") {
      playTone(ev.data.result === "won" ? 880 : 180, 0.45, "triangle", 0.13);
    }
  }

  setInterval(() => {
    if ((screenMode === "playing" || screenMode === "paused") && ws && ws.readyState === WebSocket.OPEN) {
      if (screenMode === "playing") {
        if (keys.has("KeyJ")) camYawDeg = (camYawDeg + 2.2) % 360;
        if (keys.has("KeyL")) camYawDeg = (camYawDeg - 2.2) % 360;
      }
      const mx = (keys.has(keybinds.right) || keys.has("ArrowRight") ? 1 : 0) - (keys.has(keybinds.left) || keys.has("ArrowLeft") ? 1 : 0);
      const mz = (keys.has(keybinds.down) || keys.has("ArrowDown") ? 1 : 0) - (keys.has(keybinds.up) || keys.has("ArrowUp") ? 1 : 0);
      ws.send(JSON.stringify({
        move: [mx, mz],
        cam_yaw_deg: camYawDeg,
        jump: keys.has(keybinds.jump),
        interact: keys.has(keybinds.interact),
        pulse: keys.has(keybinds.pulse),
        dash: keys.has(keybinds.dash),
        pause: pendingPauseToggle,
      }));
      pendingPauseToggle = false;
    }
  }, 1000 / 60);

  function syncScene(s) {
    buildNightGeometry(s.night);
    const [px, py, pz] = s.player.pos;
    playerGroup.position.set(px, py, pz);
    if (s.player_extra) playerGroup.rotation.y = (s.player_extra.yaw_deg * Math.PI) / 180;

    let litCount = 0;
    const blinkOn = (Math.floor(s.tick / 30) % 2) === 0; // 1 Hz blink
    for (const lan of s.lanterns) {
      const v = ensureLanternView(lan);
      v.grp.position.set(lan.pos[0], lan.pos[1], lan.pos[2]);
      v.fuelBg.lookAt(camera.position);
      v.fuelBar.lookAt(camera.position);
      if (lan.lit) {
        litCount += 1;
        const fuel = typeof lan.fuel === "number" ? lan.fuel : 100;
        const low = fuel < 30;
        v.core.scale.set(1, 1, 1);
        v.coreMat.color.setHex(low && !blinkOn ? 0xff5a5f : 0xffe9b0);
        v.coreMat.emissive.setHex(low ? (settings.colorblind ? 0xffffff : 0xff5a5f) : 0xffb347);
        v.coreMat.emissiveIntensity = low ? (blinkOn ? 1.35 : 0.35) : 1.25;
        v.light.intensity = low ? (blinkOn ? 2.0 : 0.8) : 2.2;
        v.safeRing.material.opacity = low ? 0.0 : 0.28;
        v.fuelBg.visible = true;
        v.fuelBar.visible = true;
        v.fuelBar.scale.x = Math.max(0.01, fuel / 100);
        v.fuelBarMat.color.setHex(low ? (settings.colorblind ? 0xffffff : 0xff5a5f) : 0xffb347);
      } else {
        const cost = lan.ever_lit ? 5 : 10;
        const ratio = lan.deposited / cost;
        // Unlit lantern shrunk 20% + distinct dim look when ever_lit (Ticket-03)
        v.core.scale.set(0.8, 0.8, 0.8);
        v.coreMat.color.setHex(lan.ever_lit ? 0x3b354a : 0x5b5f6e);
        v.coreMat.emissive.setHex(0xffb347);
        v.coreMat.emissiveIntensity = ratio * 0.6;
        v.light.intensity = ratio * 0.6;
        v.safeRing.material.opacity = 0.0;
        v.fuelBg.visible = false;
        v.fuelBar.visible = false;
      }
    }
    // Ticket-02 ambient formula: 0.15 + 0.55 * (lit / total)
    ambientLight.intensity = 0.15 + 0.55 * (litCount / Math.max(1, s.lanterns.length));

    // Sync motes, shades, drifters, charms
    syncPool(moteViews, s.motes || [], () => {
      const g = new THREE.Group();
      g.add(new THREE.Mesh(new THREE.SphereGeometry(0.18, 10, 10), new THREE.MeshBasicMaterial({ color: 0xfff6c2 })));
      g.add(new THREE.Mesh(new THREE.SphereGeometry(0.34, 10, 10), new THREE.MeshBasicMaterial({ color: 0xffe58a, transparent: true, opacity: 0.35 })));
      scene.add(g);
      return g;
    }, (g, m) => {
      g.position.set(m.pos[0], m.pos[1] + 0.65 + 0.15 * Math.sin(s.tick / 15 + m.pos[0]), m.pos[2]);
    });

    syncPool(shadeViews, s.shades || [], () => {
      const mat = new THREE.MeshStandardMaterial({ color: 0x120a1a, emissive: 0x7a3cff, emissiveIntensity: 0.6 });
      const grp = new THREE.Mesh(new THREE.SphereGeometry(0.58, 14, 14), mat);
      scene.add(grp);
      return { grp, mat };
    }, (v, sh) => {
      v.grp.position.set(sh.pos[0], sh.pos[1] + 0.85, sh.pos[2]);
      v.mat.color.setHex(sh.state === "stunned" ? 0x3a3450 : 0x120a1a);
      v.mat.emissive.setHex(settings.colorblind ? 0x00b3ff : 0x7a3cff);
      v.mat.emissiveIntensity = sh.state === "stunned" ? 0.1 : (sh.state === "chase" || sh.state === "drain" ? 0.95 : 0.45);
    });

    syncPool(drifterViews, s.drifters || [], () => {
      const grp = new THREE.Mesh(
        new THREE.BoxGeometry(1.1, 0.2, 0.45),
        new THREE.MeshStandardMaterial({ color: 0x8fa3b8, emissive: 0x8fa3b8, emissiveIntensity: 0.35 })
      );
      scene.add(grp);
      return grp;
    }, (g, d) => {
      g.position.set(d.pos[0], d.pos[1] + 1.4, d.pos[2]);
      g.rotation.y = s.tick * 0.08;
    });

    syncPool(charmViews, (s.charms || []).filter((c) => c.available), () => {
      const grp = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.35, 0),
        new THREE.MeshStandardMaterial({ color: 0xc8102e, emissive: 0xf2c14e, emissiveIntensity: 0.6 })
      );
      scene.add(grp);
      return grp;
    }, (g, c) => {
      g.position.set(c.pos[0], c.pos[1] + 1.0 + 0.15 * Math.sin(s.tick / 12), c.pos[2]);
      g.rotation.y = s.tick * 0.05;
    });

    const rad = (camYawDeg * Math.PI) / 180;
    camera.position.set(px + Math.sin(rad) * 9.5, Math.max(1.5, py + 4.8), pz + Math.cos(rad) * 9.5);
    camera.lookAt(px, py + 1.1, pz);
    updateOffscreenArrow(s);
  }

  function syncPool(pool, items, createFn, updateFn) {
    const keep = new Set();
    for (const item of items) {
      keep.add(item.id);
      let v = pool.get(item.id);
      if (!v) { v = createFn(); pool.set(item.id, v); }
      updateFn(v, item);
    }
    for (const [id, v] of pool.entries()) {
      if (!keep.has(id)) { scene.remove(v.grp || v); pool.delete(id); }
    }
  }

  function updateOffscreenArrow(s) {
    const unlit = s.lanterns.filter((l) => !l.lit);
    if (!unlit.length || s.state !== "playing") { elArrow.classList.add("hidden"); return; }
    unlit.sort((a, b) => Math.hypot(a.pos[0] - s.player.pos[0], a.pos[2] - s.player.pos[2]) - Math.hypot(b.pos[0] - s.player.pos[0], b.pos[2] - s.player.pos[2]));
    const target = new THREE.Vector3(unlit[0].pos[0], unlit[0].pos[1] + 2.5, unlit[0].pos[2]).project(camera);
    const onScreen = target.z < 1 && Math.abs(target.x) <= 0.95 && Math.abs(target.y) <= 0.95;
    if (onScreen) { elArrow.classList.add("hidden"); return; }
    let x = target.x, y = target.y;
    if (target.z > 1) { x = -x; y = -y; }
    const ang = Math.atan2(y, x);
    const cx = window.innerWidth / 2 + Math.cos(ang) * (window.innerWidth * 0.42);
    const cy = window.innerHeight / 2 - Math.sin(ang) * (window.innerHeight * 0.38);
    elArrow.style.left = `${cx}px`;
    elArrow.style.top = `${cy}px`;
    elArrow.style.transform = `translate(-50%, -50%) rotate(${90 - (ang * 180) / Math.PI}deg)`;
    elArrow.classList.remove("hidden");
  }

  function syncHUD(s) {
    elNightLabel.textContent = s.night_name || `Đêm ${s.night}`;
    elFlames.innerHTML = "";
    for (let i = 0; i < 3; i++) {
      const d = document.createElement("div");
      d.className = "flame" + (i < s.player.flames ? "" : " off");
      elFlames.appendChild(d);
    }

    const totalSec = Math.max(0, Math.ceil(s.time_left_s));
    elTimer.textContent = `${String(Math.floor(totalSec / 60)).padStart(2, "0")}:${String(totalSec % 60).padStart(2, "0")}`;
    elTimer.className = totalSec <= 30 ? "warn" : "";
    if (totalSec <= 10 && totalSec > 0 && totalSec !== lastCountdownSec && s.state === "playing") {
      lastCountdownSec = totalSec;
      playTone(620, 0.08, "sine", 0.07);
      showSubtitle(`Bình minh sau ${totalSec} giây!`, 1100);
    }

    elWind.classList.toggle("hidden", !(s.wind.active || s.wind_warning));
    elWind.textContent = s.wind.active ? `Gió mạnh (${Math.round(s.wind.dir_deg)}°)` : "Sắp có gió mạnh...";
    if (s.wind_warning) showSubtitle("⚠ Gió lớn sắp thổi!", 1500);

    // Shade spawn directional arrow
    if (lastSpawnedShadePos && performance.now() < shadeArrowUntil && s.state === "playing") {
      const sp = new THREE.Vector3(lastSpawnedShadePos[0], lastSpawnedShadePos[1] + 1.0, lastSpawnedShadePos[2]).project(camera);
      let sx = sp.x, sy = sp.y;
      if (sp.z > 1) { sx = -sx; sy = -sy; }
      const ang = Math.atan2(sy, sx);
      elShadeArrow.style.left = `${window.innerWidth / 2 + Math.cos(ang) * (window.innerWidth * 0.44)}px`;
      elShadeArrow.style.top = `${window.innerHeight / 2 - Math.sin(ang) * (window.innerHeight * 0.40)}px`;
      elShadeArrow.style.transform = `translate(-50%, -50%) rotate(${90 - (ang * 180) / Math.PI}deg)`;
      elShadeArrow.classList.remove("hidden");
    } else {
      elShadeArrow.classList.add("hidden");
    }

    const litCount = s.lanterns.filter((l) => l.lit).length;
    const targetLit = Math.ceil(0.6 * s.lanterns.length);
    const hasLowFuel = s.lanterns.some((l) => l.lit && typeof l.fuel === "number" && l.fuel < 30);
    elLit.textContent = `${litCount}/${s.lanterns.length}`;
    elLitTarget.textContent = `(cần ${targetLit})`;
    elLowFuel.classList.toggle("hidden", !hasLowFuel);
    if (hasLowFuel && s.state === "playing" && s.tick % 300 === 1) showSubtitle("⚠ Đèn sắp cạn dầu (fuel < 30)!", 2500);
    elScore.textContent = String(s.score);

    const cap = s.player.capacity || 10;
    elCarried.textContent = `${s.player.carried}/${cap}`;
    elCharmTag.classList.toggle("hidden", s.player.charm_s <= 0);
    if (s.player.charm_s > 0) elCharmTag.textContent = `Bùa Gió ${s.player.charm_s.toFixed(1)}s`;
    elPips.innerHTML = "";
    for (let i = 0; i < cap; i++) {
      const pip = document.createElement("div");
      pip.className = "pip" + (i < s.player.carried ? " on" : "");
      elPips.appendChild(pip);
    }

    elDashCd.textContent = s.player.dash_cd_s > 0 ? `${s.player.dash_cd_s.toFixed(1)}s` : "Sẵn sàng";
    elPulseCd.textContent = s.player.pulse_cd_s > 0 ? `${s.player.pulse_cd_s.toFixed(1)}s` : (s.player.carried >= 3 ? "Sẵn sàng" : "Thiếu sáng");

    let nearLan = null;
    for (const lan of s.lanterns) {
      if (Math.hypot(lan.pos[0] - s.player.pos[0], lan.pos[2] - s.player.pos[2]) <= 2.0 && Math.abs(lan.pos[1] - s.player.pos[1]) <= 1.5) {
        if (!lan.lit || (typeof lan.fuel === "number" && lan.fuel < 100)) {
          nearLan = lan; break;
        }
      }
    }
    if (nearLan && s.state === "playing") {
      if (nearLan.lit) {
        elPrompt.textContent = `E — Châm dầu (${Math.floor(nearLan.fuel)}/100)`;
      } else {
        const cost = nearLan.ever_lit ? 5 : 10;
        elPrompt.textContent = nearLan.ever_lit ? `E — Thắp lại (${nearLan.deposited}/${cost})` : `E — Nạp ánh sáng (${nearLan.deposited}/${cost})`;
      }
      elPrompt.classList.remove("hidden");
    } else {
      elPrompt.classList.add("hidden");
    }

    if ((s.state === "won" || s.state === "lost") && screenMode === "playing") {
      btnSaveScore.disabled = false;
      lbSaveMsg.textContent = "";
      if (s.state === "won") {
        totalGameScore += s.score;
        nightsWon += 1;
        if (currentNight === 3) {
          showModal("dawn", "Bình Minh Lên!", "Hoàn thành cả 3 Đêm", `Đảo Đèn Lồng đã sáng trở lại! Tổng điểm: ${totalGameScore}`, "Chơi lại từ Đêm 1", false, true);
          saveScorePanel.classList.remove("hidden");
        } else {
          showModal("result", `Hoàn thành Đêm ${currentNight}!`, "Chiến thắng", `Điểm Đêm ${currentNight}: ${s.score} · Tổng điểm: ${totalGameScore}`, `Đêm ${currentNight + 1} →`, true, true);
          saveScorePanel.classList.add("hidden");
        }
      } else {
        showModal("result", `Thất bại ở Đêm ${currentNight}`, "Sương đen bao phủ", `Tổng điểm các Đêm thắng: ${totalGameScore} · Đèn Đêm này: ${litCount}/${s.lanterns.length}`, "Chơi lại Đêm này", false, true);
        saveScorePanel.classList.remove("hidden");
      }
    }
  }

  // Optional browser WebGL 1280x720 Benchmark Mode (?bench=1&seed=42&duration=30)
  const params = new URLSearchParams(window.location.search);
  const isBench = params.get("bench") === "1";
  let benchData = null;

  if (isBench) {
    const tLoad0 = performance.now();
    const durationS = Math.max(1, parseFloat(params.get("duration") || "30"));
    overlay.classList.add("hidden");
    renderer.setSize(1280, 720);
    camera.aspect = 1280 / 720;
    camera.updateProjectionMatrix();
    buildNightGeometry(1);
    const lanterns = [
      { id: "L1", pos: [0, 0, 25], lit: true, fuel: 100, deposited: 10, ever_lit: true },
      { id: "L2", pos: [23.8, 0, 7.7], lit: true, fuel: 100, deposited: 10, ever_lit: true },
      { id: "L3", pos: [14.7, 0, -20.2], lit: true, fuel: 100, deposited: 10, ever_lit: true },
      { id: "L4", pos: [-14.7, 0, -20.2], lit: false, fuel: 0, deposited: 0, ever_lit: false },
      { id: "L5", pos: [-23.8, 0, 7.7], lit: false, fuel: 0, deposited: 0, ever_lit: false },
    ];
    const motes = Array.from({ length: 100 }, (_, i) => {
      const r = 36 * Math.sqrt((i + 0.5) / 100);
      const a = (i + 1) * 2.3999632297;
      return { id: `M${i + 1}`, pos: [r * Math.cos(a), 0, r * Math.sin(a)] };
    });
    const shades = Array.from({ length: 200 }, (_, i) => {
      const r = 37 * Math.sqrt((i + 0.5) / 200);
      const a = (i + 1) * 2.3999632297;
      return { id: `S${i + 1}`, pos: [r * Math.cos(a), 0, r * Math.sin(a)], state: "wander", ang: a };
    });
    benchData = {
      tLoad0, loadMs: null, tWarmStart: null, tMeasStart: null, lastFrame: null,
      durationS, dts: [], done: false, lanterns, motes, shades,
    };
  }

  function animate(nowMs) {
    requestAnimationFrame(animate);
    if (benchData) {
      const now = nowMs || performance.now();
      if (benchData.loadMs === null) {
        benchData.loadMs = now - benchData.tLoad0;
        benchData.tWarmStart = now;
        benchData.lastFrame = now;
      }
      const dtMs = Math.max(0.1, now - benchData.lastFrame);
      benchData.lastFrame = now;
      const elapsedS = (now - benchData.tWarmStart) / 1000;
      for (const sh of benchData.shades) {
        sh.ang += 0.4 * (dtMs / 1000);
        sh.pos[0] += Math.cos(sh.ang) * 2.0 * (dtMs / 1000);
        sh.pos[2] += Math.sin(sh.ang) * 2.0 * (dtMs / 1000);
        const rad = Math.hypot(sh.pos[0], sh.pos[2]);
        if (rad > 39) { sh.pos[0] *= 39 / rad; sh.pos[2] *= 39 / rad; }
      }
      syncScene({
        night: 1, tick: Math.floor(elapsedS * 60), state: "playing",
        player: { pos: [0, 0, 0] }, lanterns: benchData.lanterns,
        motes: benchData.motes, shades: benchData.shades, drifters: [], charms: [],
      });
      const angle = (elapsedS / 15.0) * Math.PI * 2;
      camera.position.set(30 * Math.cos(angle), 15, -30 * Math.sin(angle));
      camera.lookAt(0, 0, 0);
      if (elapsedS >= 3.0 && !benchData.done) {
        if (benchData.tMeasStart === null) benchData.tMeasStart = now;
        benchData.dts.push(dtMs);
        if ((now - benchData.tMeasStart) / 1000 >= benchData.durationS) {
          benchData.done = true;
          const n = benchData.dts.length;
          const sum = benchData.dts.reduce((a, b) => a + b, 0);
          const desc = [...benchData.dts].sort((a, b) => b - a);
          const k = Math.max(1, Math.ceil(0.01 * n));
          const p1 = 1000 / (desc.slice(0, k).reduce((a, b) => a + b, 0) / k);
          const asc = [...benchData.dts].sort((a, b) => a - b);
          const p95 = asc[Math.min(n - 1, Math.ceil(0.95 * n) - 1)];
          const out = {
            contract_version: "1.3", avg_fps: +(1000 * n / sum).toFixed(2),
            p1_low_fps: +p1.toFixed(2), frame_ms_p95: +p95.toFixed(3), frames: n,
            load_ms: +benchData.loadMs.toFixed(2), peak_mem_mb: null,
            vsync_off: false, renderer: "Three.js r128 WebGL (Browser 1280x720)", os: navigator.platform,
          };
          showSubtitle(`Bench xong: avg=${out.avg_fps} FPS, 1%low=${out.p1_low_fps} FPS`, 60000);
          window.__BENCH_RESULT__ = out;
        }
      }
      renderer.render(scene, camera);
      return;
    }
    if (pulseAnim > 0) {
      pulseAnim = Math.max(0, pulseAnim - 0.04);
      const scale = 1 + (1 - pulseAnim) * 9.5;
      pulseRing.position.set(playerGroup.position.x, playerGroup.position.y + 0.15, playerGroup.position.z);
      pulseRing.scale.set(scale, scale, 1);
      pulseRing.material.opacity = settings.reducedMotion ? 0 : pulseAnim * 0.85;
    }
    renderer.render(scene, camera);
  }
  animate();
})();
