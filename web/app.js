(() => {
  "use strict";

  const wrap = document.getElementById("canvas-wrap");
  const overlay = document.getElementById("overlay");
  const btnStart = document.getElementById("btn-start");
  const modalKicker = document.getElementById("modal-kicker");
  const modalTitle = document.getElementById("modal-title");
  const modalDesc = document.getElementById("modal-desc");

  const elFlames = document.getElementById("flames");
  const elTimer = document.getElementById("timer");
  const elLit = document.getElementById("lit-count");
  const elScore = document.getElementById("score");
  const elCarried = document.getElementById("carried-text");
  const elPips = document.getElementById("pips");
  const elPulseCd = document.getElementById("pulse-cd");
  const elPrompt = document.getElementById("interact-prompt");
  const elPromptProg = document.getElementById("prompt-progress");

  // Procedural Web Audio chimes (subtle fairy-tale feedback, starts on user click)
  let audioCtx = null;
  function playTone(freq, dur, type = "sine", vol = 0.08) {
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(vol, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + dur);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
  }

  // Three.js scene setup
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0e1430);
  scene.fog = new THREE.FogExp2(0x1b2350, 0.022);

  const camera = new THREE.PerspectiveCamera(58, window.innerWidth / window.innerHeight, 0.1, 300);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  wrap.appendChild(renderer.domElement);

  const hemiLight = new THREE.HemisphereLight(0x8899dd, 0x162038, 0.35);
  scene.add(hemiLight);
  const moonLight = new THREE.DirectionalLight(0xbcd0ff, 0.45);
  moonLight.position.set(20, 40, 15);
  scene.add(moonLight);

  // Island ground (radius 40 m) + sea of clouds below
  const islandMesh = new THREE.Mesh(
    new THREE.CylinderGeometry(40, 38.5, 2.5, 64),
    new THREE.MeshStandardMaterial({ color: 0x2f5d50, roughness: 0.9 })
  );
  islandMesh.position.y = -1.25;
  scene.add(islandMesh);

  const rimMesh = new THREE.Mesh(
    new THREE.TorusGeometry(40, 0.4, 8, 64),
    new THREE.MeshStandardMaterial({ color: 0xc9b48a, roughness: 0.85 })
  );
  rimMesh.rotation.x = Math.PI / 2;
  scene.add(rimMesh);

  const seaMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(400, 400),
    new THREE.MeshBasicMaterial({ color: 0x12384a, transparent: true, opacity: 0.85 })
  );
  seaMesh.rotation.x = -Math.PI / 2;
  seaMesh.position.y = -12;
  scene.add(seaMesh);

  // Player (Mây): cloak, head, conical hat (nón lá), small hanging lantern
  const playerGroup = new THREE.Group();
  const cloak = new THREE.Mesh(
    new THREE.ConeGeometry(0.42, 1.15, 16),
    new THREE.MeshStandardMaterial({ color: 0xe8e2d0 })
  );
  cloak.position.y = 0.6;
  playerGroup.add(cloak);

  const scarf = new THREE.Mesh(
    new THREE.TorusGeometry(0.24, 0.07, 8, 16),
    new THREE.MeshStandardMaterial({ color: 0xc8102e })
  );
  scarf.rotation.x = Math.PI / 2;
  scarf.position.y = 1.05;
  playerGroup.add(scarf);

  const hat = new THREE.Mesh(
    new THREE.ConeGeometry(0.56, 0.34, 24),
    new THREE.MeshStandardMaterial({ color: 0xd9c28e })
  );
  hat.position.y = 1.48;
  playerGroup.add(hat);

  const smallLantern = new THREE.Mesh(
    new THREE.SphereGeometry(0.11, 12, 12),
    new THREE.MeshBasicMaterial({ color: 0xffe9b0 })
  );
  smallLantern.position.set(0.45, 1.22, 0.25);
  playerGroup.add(smallLantern);
  const playerLight = new THREE.PointLight(0xffb347, 1.2, 10);
  playerLight.position.set(0, 1.3, 0.3);
  playerGroup.add(playerLight);
  scene.add(playerGroup);

  // Pulse shockwave ring
  const pulseRing = new THREE.Mesh(
    new THREE.RingGeometry(0.4, 0.65, 36),
    new THREE.MeshBasicMaterial({ color: 0xffe58a, side: THREE.DoubleSide, transparent: true, opacity: 0 })
  );
  pulseRing.rotation.x = -Math.PI / 2;
  pulseRing.position.y = 0.15;
  scene.add(pulseRing);
  let pulseAnim = 0;

  // Dynamic entity pools keyed by id
  const lanternViews = new Map();
  const moteViews = new Map();
  const shadeViews = new Map();

  function ensureLanternView(lan) {
    if (lanternViews.has(lan.id)) return lanternViews.get(lan.id);
    const grp = new THREE.Group();
    grp.position.set(lan.pos[0], lan.pos[1], lan.pos[2]);

    const pillar = new THREE.Mesh(
      new THREE.CylinderGeometry(0.42, 0.58, 2.2, 12),
      new THREE.MeshStandardMaterial({ color: 0x6b4a2f })
    );
    pillar.position.y = 1.1;
    grp.add(pillar);

    const coreMat = new THREE.MeshStandardMaterial({
      color: 0x5b5f6e,
      emissive: 0x000000,
      emissiveIntensity: 0,
    });
    const core = new THREE.Mesh(new THREE.OctahedronGeometry(0.48, 0), coreMat);
    core.position.y = 2.6;
    grp.add(core);

    const roof = new THREE.Mesh(
      new THREE.ConeGeometry(0.85, 0.5, 6),
      new THREE.MeshStandardMaterial({ color: 0x4c3523 })
    );
    roof.position.y = 3.25;
    grp.add(roof);

    const safeRing = new THREE.Mesh(
      new THREE.RingGeometry(5.85, 6.0, 48),
      new THREE.MeshBasicMaterial({ color: 0xffb347, side: THREE.DoubleSide, transparent: true, opacity: 0.0 })
    );
    safeRing.rotation.x = -Math.PI / 2;
    safeRing.position.y = 0.04;
    grp.add(safeRing);

    const light = new THREE.PointLight(0xffb347, 0, 18);
    light.position.y = 2.7;
    grp.add(light);

    scene.add(grp);
    const entry = { grp, coreMat, safeRing, light };
    lanternViews.set(lan.id, entry);
    return entry;
  }

  function createMoteMesh() {
    const grp = new THREE.Group();
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.18, 10, 10),
      new THREE.MeshBasicMaterial({ color: 0xfff6c2 })
    );
    const halo = new THREE.Mesh(
      new THREE.SphereGeometry(0.34, 10, 10),
      new THREE.MeshBasicMaterial({ color: 0xffe58a, transparent: true, opacity: 0.32 })
    );
    grp.add(core);
    grp.add(halo);
    scene.add(grp);
    return grp;
  }

  function createShadeMesh() {
    const grp = new THREE.Group();
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x120a1a,
      emissive: 0x7a3cff,
      emissiveIntensity: 0.55,
      roughness: 0.5,
    });
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.58, 14, 14), bodyMat);
    body.position.y = 0.85;
    grp.add(body);
    scene.add(grp);
    return { grp, bodyMat };
  }

  // Input state
  const keys = new Set();
  let camYawDeg = 0;
  let dragging = false;
  let lastMouseX = 0;
  let active = false;
  let lastState = null;

  window.addEventListener("keydown", (e) => {
    keys.add(e.code);
    if (e.code === "KeyR" && lastState && lastState.state !== "playing") {
      sendRestart();
    }
  });
  window.addEventListener("keyup", (e) => keys.delete(e.code));
  window.addEventListener("mousedown", (e) => {
    if (!active) return;
    if (e.button === 0) {
      dragging = true;
      lastMouseX = e.clientX;
    }
  });
  window.addEventListener("mouseup", () => { dragging = false; });
  window.addEventListener("mousemove", (e) => {
    if (!dragging || !active) return;
    const dx = e.clientX - lastMouseX;
    lastMouseX = e.clientX;
    camYawDeg = (camYawDeg - dx * 0.35) % 360;
  });
  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // WebSocket bridge to authoritative Python simulation
  let ws = null;
  function connectWS() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.events) {
        for (const e of msg.events) handleEventAudio(e);
      }
      if (msg.state) {
        lastState = msg.state;
        syncScene(msg.state);
        syncHUD(msg.state);
      }
    };
  }

  function sendRestart() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ cmd: "restart", seed: Math.floor(Math.random() * 100000) + 1 }));
      active = true;
      overlay.classList.add("hidden");
    }
  }

  btnStart.addEventListener("click", () => {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      connectWS();
    } else if (lastState && lastState.state !== "playing") {
      sendRestart();
    }
    active = true;
    overlay.classList.add("hidden");
  });

  function handleEventAudio(ev) {
    if (ev.name === "mote_picked") playTone(740, 0.12, "sine", 0.06);
    else if (ev.name === "deposit") playTone(520, 0.16, "triangle", 0.08);
    else if (ev.name === "lantern_lit") {
      playTone(660, 0.25, "sine", 0.1);
      setTimeout(() => playTone(880, 0.35, "sine", 0.1), 100);
    } else if (ev.name === "pulse") {
      pulseAnim = 1.0;
      playTone(440, 0.35, "sine", 0.12);
    } else if (ev.name === "player_hit") {
      playTone(150, 0.3, "sawtooth", 0.09);
    } else if (ev.name === "game_over") {
      playTone(ev.data.result === "won" ? 880 : 180, 0.5, "triangle", 0.12);
    }
  }

  function sendInputLoop() {
    if (active && ws && ws.readyState === WebSocket.OPEN) {
      if (keys.has("KeyJ")) camYawDeg = (camYawDeg + 2.2) % 360;
      if (keys.has("KeyL")) camYawDeg = (camYawDeg - 2.2) % 360;
      const mx = (keys.has("KeyD") || keys.has("ArrowRight") ? 1 : 0) - (keys.has("KeyA") || keys.has("ArrowLeft") ? 1 : 0);
      const mz = (keys.has("KeyS") || keys.has("ArrowDown") ? 1 : 0) - (keys.has("KeyW") || keys.has("ArrowUp") ? 1 : 0);
      ws.send(JSON.stringify({
        move: [mx, mz],
        cam_yaw_deg: camYawDeg,
        jump: keys.has("Space"),
        interact: keys.has("KeyE"),
        pulse: keys.has("KeyQ") || keys.has("KeyF"),
      }));
    }
  }
  setInterval(sendInputLoop, 1000 / 60);

  function syncScene(s) {
    const px = s.player.pos[0], py = s.player.pos[1], pz = s.player.pos[2];
    playerGroup.position.set(px, py, pz);
    if (s.player_extra) {
      playerGroup.rotation.y = (s.player_extra.yaw_deg * Math.PI) / 180;
    }

    // Lanterns + progressive island brightness
    let litCount = 0;
    for (const lan of s.lanterns) {
      const v = ensureLanternView(lan);
      if (lan.lit) {
        litCount += 1;
        v.coreMat.color.setHex(0xffe9b0);
        v.coreMat.emissive.setHex(0xffb347);
        v.coreMat.emissiveIntensity = 1.25;
        v.light.intensity = 2.2;
        v.safeRing.material.opacity = 0.28;
      } else {
        const ratio = lan.deposited / (s.tuning ? s.tuning.lantern_cost : 10);
        v.coreMat.color.setHex(0x5b5f6e);
        v.coreMat.emissive.setHex(0xffb347);
        v.coreMat.emissiveIntensity = ratio * 0.6;
        v.light.intensity = ratio * 0.6;
        v.safeRing.material.opacity = 0.0;
      }
    }
    const progress = litCount / Math.max(1, s.lanterns.length);
    hemiLight.intensity = 0.25 + 0.65 * progress;
    scene.fog.density = 0.025 - 0.015 * progress;

    // Motes
    const activeMoteIds = new Set();
    const tSec = s.tick / 60;
    for (const m of s.motes || []) {
      activeMoteIds.add(m.id);
      let mesh = moteViews.get(m.id);
      if (!mesh) {
        mesh = createMoteMesh();
        moteViews.set(m.id, mesh);
      }
      mesh.position.set(m.pos[0], m.pos[1] + 0.65 + 0.16 * Math.sin(tSec * 3.5 + m.pos[0]), m.pos[2]);
    }
    for (const [id, mesh] of moteViews.entries()) {
      if (!activeMoteIds.has(id)) {
        scene.remove(mesh);
        moteViews.delete(id);
      }
    }

    // Shades
    const activeShadeIds = new Set();
    for (const sh of s.shades || []) {
      activeShadeIds.add(sh.id);
      let entry = shadeViews.get(sh.id);
      if (!entry) {
        entry = createShadeMesh();
        shadeViews.set(sh.id, entry);
      }
      entry.grp.position.set(sh.pos[0], sh.pos[1], sh.pos[2]);
      if (sh.state === "stunned") {
        entry.bodyMat.color.setHex(0x3a3450);
        entry.bodyMat.emissiveIntensity = 0.1;
      } else {
        entry.bodyMat.color.setHex(0x120a1a);
        entry.bodyMat.emissiveIntensity = sh.state === "chase" ? 0.95 : 0.45;
      }
    }
    for (const [id, entry] of shadeViews.entries()) {
      if (!activeShadeIds.has(id)) {
        scene.remove(entry.grp);
        shadeViews.delete(id);
      }
    }

    // Third-person camera follow
    const rad = (camYawDeg * Math.PI) / 180;
    const camDist = 9.0;
    const camHeight = 4.5;
    camera.position.set(px + Math.sin(rad) * camDist, Math.max(1.5, py + camHeight), pz + Math.cos(rad) * camDist);
    camera.lookAt(px, py + 1.1, pz);
  }

  function syncHUD(s) {
    elFlames.innerHTML = "";
    for (let i = 0; i < 3; i++) {
      const d = document.createElement("div");
      d.className = "flame" + (i < s.player.flames ? "" : " off");
      elFlames.appendChild(d);
    }

    const totalSec = Math.max(0, Math.ceil(s.time_left_s));
    const mm = String(Math.floor(totalSec / 60)).padStart(2, "0");
    const ss = String(totalSec % 60).padStart(2, "0");
    elTimer.textContent = `${mm}:${ss}`;
    elTimer.className = totalSec <= 30 ? "warn" : "";

    const litCount = s.lanterns.filter((l) => l.lit).length;
    elLit.textContent = `${litCount}/${s.lanterns.length}`;
    elScore.textContent = String(s.score);

    const cap = s.tuning ? s.tuning.carry_capacity : 10;
    elCarried.textContent = `${s.player.carried}/${cap}`;
    elPips.innerHTML = "";
    for (let i = 0; i < cap; i++) {
      const pip = document.createElement("div");
      pip.className = "pip" + (i < s.player.carried ? " on" : "");
      elPips.appendChild(pip);
    }

    const cd = s.player_extra ? s.player_extra.pulse_cd_s : 0;
    elPulseCd.textContent = cd > 0 ? `${cd.toFixed(1)}s` : (s.player.carried >= 3 ? "Sẵn sàng" : "Thiếu sáng");

    // Nearby unlit lantern prompt
    let nearLan = null;
    for (const lan of s.lanterns) {
      if (lan.lit) continue;
      const d = Math.hypot(lan.pos[0] - s.player.pos[0], lan.pos[2] - s.player.pos[2]);
      if (d <= 2.0) { nearLan = lan; break; }
    }
    if (nearLan && s.state === "playing") {
      elPromptProg.textContent = `${nearLan.deposited}/${s.tuning ? s.tuning.lantern_cost : 10}`;
      elPrompt.classList.remove("hidden");
    } else {
      elPrompt.classList.add("hidden");
    }

    if (s.state !== "playing") {
      active = false;
      overlay.classList.remove("hidden");
      if (s.state === "won") {
        modalKicker.textContent = "Bình minh lên!";
        modalTitle.textContent = "Đảo Đèn Lồng đã sáng";
        modalDesc.textContent = `Tổng điểm: ${s.score} · Đèn đã thắp: ${litCount}/${s.lanterns.length}`;
      } else {
        modalKicker.textContent = "Sương đen bao phủ";
        modalTitle.textContent = "Thử lại Đêm 1";
        modalDesc.textContent = `Điểm đạt được: ${s.score} · Đèn đã thắp: ${litCount}/${s.lanterns.length}`;
      }
      btnStart.textContent = "Chơi lại (R)";
    }
  }

  function animate() {
    requestAnimationFrame(animate);
    if (pulseAnim > 0) {
      pulseAnim = Math.max(0, pulseAnim - 0.04);
      const scale = 1 + (1 - pulseAnim) * 9.5;
      pulseRing.position.set(playerGroup.position.x, playerGroup.position.y + 0.15, playerGroup.position.z);
      pulseRing.scale.set(scale, scale, 1);
      pulseRing.material.opacity = pulseAnim * 0.85;
    }
    renderer.render(scene, camera);
  }
  animate();
})();
