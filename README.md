# dora-openarm-mouse-teleop

English | [日本語](README.ja.md)

[dora-rs](https://dora-rs.ai/) nodes that teleoperate the end-effectors of
[OpenArm](https://openarm.dev/) with a **mouse and keyboard**
([Dear PyGui](https://github.com/hoffstadt/DearPyGui)) and with an **iPhone**
(ARKit), in the MuJoCo simulation. No VR headset and no leader arm are needed.

> **This is a derivative work, developed with AI assistance.**
> The mouse node is based on the OpenArm slider teleop node and on a note.com
> tutorial. The code and documentation were developed in dialogue with
> **Claude Sonnet 5.5** (Anthropic). See [Attribution](#attribution) and
> [AI assistance](#ai-assistance) for exactly what comes from where.

## Quick start

Mouse teleoperation in the simulation (macOS / Linux). You need
[uv](https://docs.astral.sh/uv/), Git and **several GB of free disk space**.

```bash
# 1. Upstream repository (kinematics, MuJoCo, UI, recorder) with submodules
git clone https://github.com/enactic/dora-openarm-data-collection
cd dora-openarm-data-collection
git submodule update --init --recursive

# 2. This repository, into nodes/
git clone https://github.com/yt1970/dora-openarm-mouse-teleop nodes/dora-openarm-mouse-teleop

# 3. Dependencies (without the real-hardware packages), then this repository
uv sync --locked --no-install-package openarm-can --no-install-package openarm-driver
source .venv/bin/activate
uv pip install -e "nodes/dora-openarm-mouse-teleop[iphone]"

# 4. Run
cp nodes/dora-openarm-mouse-teleop/examples/dataflow_mouse_teleop.yaml .
UV_NO_SYNC=1 dora run dataflow_mouse_teleop.yaml --uv
```

A Dear PyGui window (pad and `z` slider) and a MuJoCo window open. To stop,
press `Ctrl+C` in the terminal.

Notes:

- Do not run `uv sync` again after step 3: it removes packages that are not in
  the upstream lockfile, including these nodes. If you do, run the
  `uv pip install -e` line again.
- `UV_NO_SYNC=1` keeps `uv run` (used by dora with `--uv`) from syncing the
  environment again.
- `openarm-can` is built from C++ and needs the CLI11 library, and CAN is mainly
  for Linux. Upstream's CI installs `libcli11-dev` on Ubuntu and then runs a
  plain `uv sync --locked`. They are not needed for the simulation.
- **macOS**: if the MuJoCo viewer does not open or the node fails to start, try
  the `mjpython` wrapper [`examples/mujoco_mac.sh`](examples/mujoco_mac.sh) (the
  macOS workaround from the note article in [Attribution](#attribution)):

  ```bash
  cp nodes/dora-openarm-mouse-teleop/examples/mujoco_mac.sh .
  chmod +x mujoco_mac.sh
  sed -i '' 's#path: dora-openarm-mujoco#path: ./mujoco_mac.sh#' dataflow_mouse_teleop.yaml
  ```

  I ran my checks with this wrapper on macOS. I have not checked whether it is
  required, so it is not required by these instructions.

## Scope and safety

- Tested **only with the MuJoCo simulation**. It has **not** been tested with
  real OpenArm hardware.
- The example dataflows are wired for MuJoCo (the current pose comes from the
  simulator). Using real arms requires connecting `dora-openarm-ik` to the
  real follower nodes and feeding `dora-openarm-fk` from the real arm state.
  This is not provided here.
- If you try it on real hardware, do it at your own risk, keep the emergency
  stop within reach, and start with slow, small motions.
- The iPhone node listens on a UDP port **without authentication**: any device
  on the same network can send poses and move the arm. Use it only on a
  network you trust, never together with real hardware, or set `IPHONE_HOST`
  to a specific interface address.
- The setup above skips the real-hardware packages (`openarm-can`,
  `openarm-driver`). Install them yourself if you need real arms.

## Mouse teleoperation

| Input | Action |
|---|---|
| Drag on the pad | Move the active arm's end-effector in x / y |
| `Up` / `Down` keys (or the `z` slider) | Move the end-effector up / down |
| Left button held + mouse wheel | Move the end-effector up / down in small steps |
| Mouse wheel | Open / close the gripper of the active arm |
| `Left` / `Right` keys | Switch the active arm |
| `Reset` button | Return the active arm to the pose it had at startup |
| `R` key | Send `button_x` (reset the box in the MuJoCo demo scene) |

Tunable constants (reach, z range, smoothing, gripper step) are at the top of
[`main.py`](src/dora_openarm_mouse_teleop/main.py). `MOUSE_ARMS` (for example
`MOUSE_ARMS=left`) limits the arms the mouse may control.

### Inputs / outputs

| Direction | Name | Type |
|---|---|---|
| input | `tick` | any (timer, 50 Hz in the examples) |
| input | `pose_right`, `pose_left` | current end-effector pose from `dora-openarm-fk` |
| input | `phone_sides` (optional) | string: arms controlled by an iPhone, e.g. `right` |
| output | `target_right`, `target_left` | struct `{pose: list<float32>}` target pose for `dora-openarm-ik` |
| output | `button_x` | bool |
| output | `status` | string (`ready`) |

The node waits for the first `pose_right` and `pose_left`, uses them as the
base pose, and then outputs the base pose plus the offset from the pad, the z
control and the gripper. The pose is `[x, y, z, qw, qx, qy, qz, gripper]`.

## iPhone teleoperation

An iPhone controls an arm with its own 6DoF motion (position **and**
orientation, including wrist rotation, which a mouse cannot give). The iOS app
sends the ARKit camera pose over UDP to `dora-openarm-iphone-teleop`, which
turns it into a target pose for `dora-openarm-ik`.

```
iPhone (ARKit app) --UDP 5007--> iphone-teleop --> ik --> mujoco
                                      ^
                  mouse-teleop targets (for the arms the phone does not control)
```

- Each arm is controlled by the phone while that phone keeps sending packets
  for it, and by the mouse otherwise. If the phone stops for about 1.5 seconds,
  the arm returns to the mouse, restarting from its current pose.
- Zero, one or two phones are supported by the design. **Only one iPhone has
  been tested.**

### Network

The Mac and the iPhone must be on the **same Wi-Fi network (router)**.
Tethering the Mac to the iPhone's personal hotspot did **not** work in my setup
(the Mac got no IPv4 LAN address), so use a separate Wi-Fi network. Get the
Mac's address on macOS with:

```bash
ipconfig getifaddr en0
```

### Build the iOS app

[`ios/PhoneTeleop/PhoneTeleopApp.swift`](ios/PhoneTeleop/PhoneTeleopApp.swift)
is the whole app (SwiftUI + ARKit). No Xcode project is included.

1. In Xcode, create a new **iOS App** project (SwiftUI, Swift).
2. Delete the generated `ContentView.swift` and the generated `...App.swift`
   (which has its own `@main`), and add `PhoneTeleopApp.swift` instead.
3. Select your team under *Signing & Capabilities* (a free Apple ID works;
   such apps expire after 7 days and must be rebuilt).
4. Run it on a real iPhone. ARKit does not run in the simulator. On first
   launch, allow camera access and local network access.
   If the app stops when AR starts, check that the target has a camera usage
   description (`NSCameraUsageDescription`).

### Run

```bash
cp nodes/dora-openarm-mouse-teleop/examples/dataflow_mouse_iphone.yaml .
UV_NO_SYNC=1 dora run dataflow_mouse_iphone.yaml --uv
```

(Use the same macOS `mujoco_mac.sh` change as above if needed.) In the app:

| Control | Action |
|---|---|
| Mac IP field + `接続` (Connect) | Enter the Mac's address and connect. Hold the phone facing forward when you press it: that direction becomes "front" for this phone |
| `左腕` / `右腕` (Left / Right arm) | Choose the arm this phone controls |
| `追従 ON/OFF` (Follow ON/OFF) | While ON, the phone's motion since the moment you turned it ON moves the end-effector, starting from the real arm pose. Turn it OFF to reposition your hand, then ON again (ratchet-style operation) |
| Vertical slider | Gripper (the labels in the app are `開` = open on top and `閉` = close at the bottom) |
| `腕リセット` (Reset arm) | Return the arm to its startup pose |

Do not cover the rear camera with your fingers: ARKit tracking needs it. When
tracking is unstable the app shows a warning and following stops.

### Settings

Environment variables of `dora-openarm-iphone-teleop`:

| Variable | Default | Meaning |
|---|---|---|
| `IPHONE_HOST` | `0.0.0.0` | Interface address to listen on |
| `IPHONE_PORT` | `5007` | UDP port (the app uses 5007) |
| `IPHONE_POS_SCALE` | `1.0` | 1 m of phone motion = this many meters of robot motion |
| `IPHONE_SMOOTH` | `0.3` | Follow rate per tick (0-1, smaller = smoother) |

## Tested environment

- macOS, Python 3.12, dora-rs / dora-rs-cli 1.0.1, with the upstream
  repository cloned on 2026-10-18 (submodules as pinned by that revision).
- **Mouse teleoperation**: `examples/dataflow_mouse_teleop.yaml` was run on that
  fresh clone, on macOS **with the `mujoco_mac.sh` wrapper** (running without
  it has not been checked). Moving the arms with the pad, the `z` control and
  the gripper (mouse wheel) has been checked.
- **iPhone teleoperation**: used on the author's own setup (macOS, one iPhone 16
  without LiDAR) together with the mouse. The examples in this repository are
  cleaned copies of that wiring and have **not** been re-run on a fresh clone
  of the upstream repository. Two phones at the same time have not been tested.
- **Data collection** (`*_data_collection.yaml`): used on the author's own
  setup, **not** re-verified on a fresh clone.
- Other platforms and real hardware have not been tested.
- Recent upstream versions use a single `dataflow.yaml` with `leader-*.yaml`
  modules whose outputs are `follower_position_*`. The examples here are
  standalone dataflows and do not plug into that layout yet. Wrapping these
  nodes, `dora-openarm-ik` and `dora-openarm-fk` in a `leader-*.yaml` module is
  future work.

## AI assistance

The code and the documentation of this repository, including the iPhone node,
the iOS app and this README, were developed by yt1970 in dialogue with
**Claude Sonnet 5.5** (Anthropic). Please review the code yourself before you
rely on it, and especially before you use it with real hardware.

## Attribution

This project was made by following and modifying the work of others. Thank you
to the authors below.

### What this repository is based on

- **OpenArm slider teleop node**:
  [k1000dai/dora-openarm-slider-teleop](https://github.com/k1000dai/dora-openarm-slider-teleop)
  (Apache-2.0, Copyright 2026 Enactic, Inc.).
  The structure of the **mouse node** follows it: the Dear PyGui window running
  on the main thread, the dora event loop in a worker thread, the packaging
  (`pyproject.toml`, `src/` layout, console script), and the idea of sending
  values on every `tick`. The joint sliders were **replaced** with mouse /
  keyboard control of end-effector targets (pad, `z`, gripper, arm switching,
  box reset), and the output changed from joint positions
  (`position_*`) to target poses (`target_*`) for inverse kinematics.
- **note.com article** "OpenArm Cell で学ぶ dora-rs (MuJoCo)[起動~data collectionまで]"
  by chiyo_note (2026-05-20):
  <https://note.com/duckduck1836/n/nfb1b17e7e897>.
  This article explains how to read `dataflow.yaml`, how to write a node, and
  how to run the slider teleop with MuJoCo and the data collection UI. It was
  the guide I followed to build the mouse node, and the dataflow examples in
  [`examples/`](examples) are adapted from the dataflows it describes
  (including the macOS `mujoco_mac.sh` workaround shown there).
- **Upstream data collection repository**:
  [enactic/dora-openarm-data-collection](https://github.com/enactic/dora-openarm-data-collection)
  (Apache-2.0, Copyright 2026 Enactic, Inc.).
  The nodes that these nodes connect to (`dora-openarm-kinematics`,
  `dora-openarm-mujoco`, `dora-openarm-data-collection-ui`,
  `dora-openarm-dataset-recorder`) and `metadata_mujoco.yaml` come from it and
  from the Enactic repositories it uses as submodules. They are **not**
  included in this repository.
- **OpenArm** by [Enactic, Inc.](https://openarm.dev/) and the official
  [data collection tutorial](https://docs.openarm.dev/tutorial/data-collection),
  on which the note article above is based.

### What is new here

- The **iPhone node** (`dora-openarm-iphone-teleop`) and the **iOS app**
  (`PhoneTeleopApp.swift`) are original work. No article or repository was used
  as a direct reference for them. They use Apple's ARKit, SwiftUI and Network
  frameworks.
- The end-effector mouse / keyboard control logic in
  [`main.py`](src/dora_openarm_mouse_teleop/main.py), the example dataflows that
  wire the nodes to the inverse / forward kinematics nodes, and this README.

### Third-party libraries

[dora-rs](https://dora-rs.ai/), [Dear PyGui](https://github.com/hoffstadt/DearPyGui),
NumPy, SciPy and PyArrow are used as dependencies and are not included.

See also [NOTICE](NOTICE).

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

Copyright 2026 Enactic, Inc. for the portions derived from the slider teleop
node and the upstream repository. Copyright 2026 yt1970 for the iPhone node, the
iOS app and the other modifications.
