#!/usr/bin/env python3
"""Capture a cut-style three-night WebGL demo with short gameplay sections.

Requires Playwright Python + Chromium and ffmpeg. Example:
  python3 tools/capture_montage.py --play-seconds 60

Each stage shows one minute of autoplay, then a real Simulation dawn win state,
so the montage can move through the game's actual victory and stage screens.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    raise SystemExit("Install Playwright and Chromium first: python3 -m pip install playwright && python3 -m playwright install chromium") from exc

import src.server as game_server
from src.game.sim import Simulation as BaseSimulation


demo_state = {"active_night": 1, "cut_to_win": False}
demo_lock = threading.Lock()


def win_scenario(night: int) -> dict[str, object]:
    sim = BaseSimulation(seed=17, night=night)
    required = math.ceil(0.6 * len(sim.lanterns))
    return {
        "player": {"pos": list(sim.cfg.start_pos), "carried": 0, "flames": 3},
        "random_motes": False,
        "random_shades": False,
        "random_drifters": False,
        "wind_enabled": False,
        "time_left_s": 1.0,
        "lanterns": [
            {"id": lantern.id, "lit": index < required, "fuel": 80.0 if index < required else 0.0,
             "ever_lit": index < required}
            for index, lantern in enumerate(sim.lanterns)
        ],
    }


class MontageSimulation(BaseSimulation):
    """Apply the verified dawn-survival cut to the running stage simulation."""

    def __init__(self, seed: int = 1, night: int = 1, scenario: dict | None = None):
        super().__init__(seed=seed, night=night, scenario=scenario)
        self._montage_active = night == demo_state["active_night"]
        self._montage_cut_applied = False

    def step(self, frame_patch: dict | None = None):
        if not self._montage_active:
            return super().step(frame_patch)
        with demo_lock:
            cut_to_win = demo_state["cut_to_win"] and not self._montage_cut_applied
        if cut_to_win:
            # Configure the real dawn-survival condition, then let Simulation.step
            # emit its normal game_over event and the frontend's actual win screen.
            setup = win_scenario(self.night)
            self.time_left_ticks = 1
            self.random_motes = False
            self.random_shades = False
            self.random_drifters = False
            self.wind_enabled = False
            for item in setup["lanterns"]:
                lantern = next(l for l in self.lanterns if l.id == item["id"])
                lantern.lit = item["lit"]
                lantern.fuel_60 = int(item["fuel"] * 60)
                lantern.ever_lit = item["ever_lit"]
            self.shades.clear()
            self.drifters.clear()
            self._montage_cut_applied = True
        events = super().step(frame_patch)
        if self.state == "lost":
            # Keep the bot's segment in active gameplay; the edited cut then
            # supplies the verified win screen after its one-minute play section.
            self.state = "playing"
            self.player.pos = list(self.cfg.start_pos)
            self.player.vel = [0.0, 0.0, 0.0]
            self.player.flames = 3
            self.player.respawn_ticks = 0
            self.player.grounded = True
            self.player.launched = False
            events = [event for event in events if event.get("name") != "game_over"]
        return events


game_server.Simulation = MontageSimulation


def steer_for(page, seconds: int) -> None:
    pressed: set[str] = set()
    last_interact = 0.0
    stop_at = time.monotonic() + seconds
    initial = page.evaluate("window.__ddlState") or {}
    while time.monotonic() < stop_at:
        state = page.evaluate("window.__ddlState") or {}
        player = state.get("player", {})
        pos = player.get("pos", [0, 0, 0])
        px, pz = pos[0], pos[2]
        carried = player.get("carried", 0)
        lanterns = state.get("lanterns", [])
        motes = state.get("motes", [])
        if state.get("night") == 3:
            # The Bell Island has three vertical tiers; a flat waypoint bot
            # gets stuck chasing upper-tier motes from the lower spawn.
            same_tier = [mote for mote in motes if abs(mote["pos"][1] - pos[1]) <= 1.5]
            if same_tier:
                motes = same_tier
        if carried >= 8 or (carried >= 3 and not motes):
            options = [lan for lan in lanterns if not lan.get("lit") or lan.get("fuel", 0) < 90]
            targets = [(lan["id"], lan["pos"]) for lan in options]
        else:
            targets = [(mote["id"], mote["pos"]) for mote in motes]
        if not targets:
            targets = [(lan["id"], lan["pos"]) for lan in lanterns if not lan.get("lit")]
        if targets:
            _, target = min(targets, key=lambda item: (item[1][0] - px) ** 2 + (item[1][2] - pz) ** 2)
            dx, dz = target[0] - px, target[2] - pz
        else:
            dx, dz = 1.0, 0.0
        wanted: set[str] = set()
        if math.hypot(dx, dz) > 1.0:
            if dx > 0.35:
                wanted.add("KeyD")
            elif dx < -0.35:
                wanted.add("KeyA")
            if dz > 0.35:
                wanted.add("KeyS")
            elif dz < -0.35:
                wanted.add("KeyW")
        if any((shade["pos"][0] - px) ** 2 + (shade["pos"][2] - pz) ** 2 < 36 for shade in state.get("shades", [])) and player.get("pulse_cd_s", 1) == 0:
            wanted.add("KeyQ")
        if any((lan["pos"][0] - px) ** 2 + (lan["pos"][2] - pz) ** 2 < 9 for lan in lanterns) and time.monotonic() - last_interact > 0.5:
            wanted.add("KeyE")
            last_interact = time.monotonic()
        for key in pressed - wanted:
            page.keyboard.up(key)
        for key in wanted - pressed:
            page.keyboard.down(key)
        pressed = wanted
        page.wait_for_timeout(120)
    for key in pressed:
        page.keyboard.up(key)
    final = page.evaluate("window.__ddlState") or {}
    print(
        f"  movement check: {initial.get('night')} {initial.get('player', {}).get('pos')} -> "
        f"{final.get('player', {}).get('pos')}, carried {final.get('player', {}).get('carried')}, score {final.get('score')}",
        flush=True,
    )


def capture(play_seconds: int, destination: pathlib.Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required to record the browser montage.") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = destination.parent / ".montage-raw"
    raw_dir.mkdir(exist_ok=True)
    server = game_server.start_server("127.0.0.1", 0)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader"],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=str(raw_dir),
                record_video_size={"width": 1280, "height": 720},
            )
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("""
              (() => {
                const Native = window.WebSocket;
                function TapSocket(...args) {
                  const ws = new Native(...args);
                  window.__ddlDemoSocket = ws;
                  ws.addEventListener('message', ev => {
                    try { const m=JSON.parse(ev.data); if(m.state) window.__ddlState=m.state; }
                    catch (_) {}
                  });
                  return ws;
                }
                TapSocket.prototype=Native.prototype;
                Object.setPrototypeOf(TapSocket,Native);
                window.WebSocket=TapSocket;
              })();
            """)
            page.goto(url, wait_until="networkidle", timeout=30_000)
            page.wait_for_timeout(1500)  # hold the opening menu for the cut

            for night in (1, 2, 3):
                if night == 1:
                    page.locator("#btn-primary").click()  # menu -> intro
                    page.wait_for_timeout(1500)
                    page.locator("#btn-primary").click()  # intro -> game
                else:
                    page.wait_for_function("(night) => document.getElementById('modal-title').textContent.includes('Đêm ' + night)", arg=night, timeout=10_000)
                    page.wait_for_timeout(1500)  # stage intro cut
                    page.locator("#btn-primary").click()

                page.wait_for_function("window.__ddlState && window.__ddlState.state === 'playing'", timeout=10_000)
                print(f"Night {night}: playing for {play_seconds}s", flush=True)
                steer_for(page, play_seconds)

                # Cut to a true in-game win state; Simulation's verified dawn rules
                # produce the same WebSocket event and authentic victory UI.
                with demo_lock:
                    demo_state["cut_to_win"] = True
                page.wait_for_function(
                    "(night) => document.getElementById('modal-title').textContent.includes('Hoàn thành Đêm ' + night + '!') || (night===3 && document.getElementById('modal-title').textContent.includes('Bình Minh Lên'))",
                    arg=night,
                    timeout=10_000,
                )
                print(f"Night {night}: victory screen", flush=True)
                page.wait_for_timeout(2500)
                if night < 3:
                    with demo_lock:
                        demo_state["active_night"] = night + 1
                        demo_state["cut_to_win"] = False
                    page.locator("#btn-primary").click()  # win -> next night intro
                    page.wait_for_timeout(1500)

            page.wait_for_timeout(4000)  # closing dawn screen
            video = page.video
            context.close()
            browser.close()
            raw_video = pathlib.Path(video.path())
            result = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_video), "-an", "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination)],
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip())
            raw_video.unlink(missing_ok=True)
            if errors:
                print("Browser errors: " + json.dumps(errors), file=sys.stderr)
            print(f"Wrote {destination}", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--play-seconds", type=int, default=60, help="autoplay duration per night (default: 60)")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "docs/demo/demo.mp4")
    args = parser.parse_args()
    if args.play_seconds < 1:
        parser.error("--play-seconds must be at least 1")
    capture(args.play_seconds, args.out)


if __name__ == "__main__":
    main()
