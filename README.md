# dora-openarm-mouse-teleop

A [dora-rs](https://dora-rs.ai/) node that teleoperates the end-effectors of
[OpenArm](https://openarm.dev/) with a mouse and keyboard, using
[Dear PyGui](https://github.com/hoffstadt/DearPyGui) (pure pip, no VR headset,
no leader arm).

English | [日本語](README.ja.md)

> **This is a derivative work.** It is based on the OpenArm slider teleop node
> and on the dora-rs / OpenArm Cell tutorial in a note.com article. See
> [Attribution](#attribution) for exactly what comes from where.

## Scope and safety

- Tested **only with the MuJoCo simulation**. It has **not** been tested with
  real OpenArm hardware.
- The example dataflows are wired for MuJoCo (the current pose comes from the
  simulator). Using real arms requires connecting `dora-openarm-ik` to the
  real follower nodes and feeding `dora-openarm-fk` from the real arm state.
  This is not provided here.
- If you try it on real hardware, do it at your own risk, keep the emergency
  stop within reach, and start with slow, small motions.
- The setup below skips the real-hardware packages (`openarm-can`,
  `openarm-driver`) because they need a CAN environment and extra system
  libraries. Install them yourself if you need real arms.

## Controls

| Input | Action |
|---|---|
| Drag on the pad | Move the active arm's end-effector in x / y |
| `↑` / `↓` keys (or the `z` slider) | Move the end-effector up / down |
| Mouse wheel | Open / close the gripper of the active arm |
| `←` / `→` keys | Switch the active arm (left / right) |
| `reset` button | Reset the active arm's offsets to the home pose |
| `R` key | Send `button_x` (reset the box in the MuJoCo demo scene) |

Tunable constants (reach, z range, smoothing, gripper step) are at the top of
[`main.py`](src/dora_openarm_mouse_teleop/main.py).

## Inputs / outputs

| Direction | Name | Type |
|---|---|---|
| input | `tick` | any (timer, 50 Hz in the examples) |
| input | `pose_right`, `pose_left` | current end-effector pose from `dora-openarm-fk` |
| output | `target_right`, `target_left` | struct `{pose: list<float32>}` target pose for `dora-openarm-ik` |
| output | `button_x` | bool |
| output | `status` | string (`ready`) |

The node waits for the first `pose_right` and `pose_left`, uses them as the
base pose, and then outputs the base pose plus the offset from the pad, the z
control and the gripper. The pose is `[x, y, z, qw, qx, qy, qz, gripper]`.

## Setup

This repository contains only the mouse node. The rest of the dataflow
(kinematics, MuJoCo simulation, data collection UI, recorder) comes from
[enactic/dora-openarm-data-collection](https://github.com/enactic/dora-openarm-data-collection).
You need [uv](https://docs.astral.sh/uv/) and Git, and **several GB of free
disk space** (MuJoCo, OpenCV and other dependencies).

1. Clone the upstream repository with its submodules.

   ```bash
   git clone https://github.com/enactic/dora-openarm-data-collection
   cd dora-openarm-data-collection
   git submodule update --init --recursive
   ```

2. Clone this repository into `nodes/`.

   ```bash
   git clone https://github.com/yt1970/dora-openarm-mouse-teleop nodes/dora-openarm-mouse-teleop
   ```

3. Install the dependencies, without the real-hardware packages, and then the
   mouse node into the same environment.

   ```bash
   uv sync --locked --no-install-package openarm-can --no-install-package openarm-driver
   source .venv/bin/activate
   uv pip install -e nodes/dora-openarm-mouse-teleop
   ```

   Do not run `uv sync` again after this: it removes packages that are not in
   the upstream lockfile, including this node. If you do, run the
   `uv pip install -e` line again.

   Why the two packages are skipped: `openarm-can` is built from C++ and needs
   the CLI11 library, and CAN is mainly for Linux. Upstream's CI installs
   `libcli11-dev` on Ubuntu and then runs a plain `uv sync --locked`. For the
   simulation they are not needed.

4. Copy the example dataflow to the upstream root and run it.

   ```bash
   cp nodes/dora-openarm-mouse-teleop/examples/dataflow_mouse_teleop.yaml .
   UV_NO_SYNC=1 dora run dataflow_mouse_teleop.yaml --uv
   ```

   `UV_NO_SYNC=1` keeps `uv run` (used by dora with `--uv`) from syncing the
   environment again. A Dear PyGui window (pad and `z` slider) and a MuJoCo
   window should open.

   **On macOS**, if the MuJoCo viewer does not open or the node fails to
   start, try the `mjpython` wrapper
   [`examples/mujoco_mac.sh`](examples/mujoco_mac.sh) (the macOS workaround from
   the note article in [Attribution](#attribution)):

   ```bash
   cp nodes/dora-openarm-mouse-teleop/examples/mujoco_mac.sh .
   chmod +x mujoco_mac.sh
   sed -i '' 's#path: dora-openarm-mujoco#path: ./mujoco_mac.sh#' dataflow_mouse_teleop.yaml
   ```

   I ran my checks with this wrapper on macOS. I have not checked whether it is
   required, so it is not required by these instructions.

`examples/dataflow_mouse_teleop_data_collection.yaml` adds the data collection
web UI (http://localhost:8000) and the recorder. It has **not been verified
yet** with the current upstream version.

## Tested environment

- macOS, Python 3.12, dora-rs / dora-rs-cli 1.0.1, with the upstream
  repository cloned on 2026-10-18 (submodules as pinned by that revision).
- Only `examples/dataflow_mouse_teleop.yaml` (teleoperation in MuJoCo) has
  been run, on macOS **with the `mujoco_mac.sh` wrapper** (running without it
  has not been checked). Moving the arms with the pad, the `z` control and the
  gripper (mouse wheel) has been checked. Other platforms, the data collection
  dataflow and real hardware have not been tested.
- Recent upstream versions use a single `dataflow.yaml` with `leader-*.yaml`
  modules whose outputs are `follower_position_*`. The examples here are
  standalone dataflows and do not plug into that layout yet. Wrapping this node,
  `dora-openarm-ik` and `dora-openarm-fk` in a `leader-mouse.yaml` module is
  future work.

## Attribution

This project was made by following and modifying the work of others. Thank you
to the authors below.

### What this repository is based on

- **OpenArm slider teleop node**:
  [k1000dai/dora-openarm-slider-teleop](https://github.com/k1000dai/dora-openarm-slider-teleop)
  (Apache-2.0, Copyright 2026 Enactic, Inc.).
  The overall structure of this node follows it: the Dear PyGui window running
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
  the guide I followed to build this node, and the dataflow examples in
  [`examples/`](examples) are adapted from the dataflows it describes
  (including the macOS `mujoco_mac.sh` workaround shown there).
- **Upstream data collection repository**:
  [enactic/dora-openarm-data-collection](https://github.com/enactic/dora-openarm-data-collection)
  (Apache-2.0, Copyright 2026 Enactic, Inc.).
  The nodes that this node connects to (`dora-openarm-kinematics`,
  `dora-openarm-mujoco`, `dora-openarm-data-collection-ui`,
  `dora-openarm-dataset-recorder`) and `metadata_mujoco.yaml` come from it and
  from the Enactic repositories it uses as submodules. They are **not**
  included in this repository.
- **OpenArm** by [Enactic, Inc.](https://openarm.dev/) and the official
  [data collection tutorial](https://docs.openarm.dev/tutorial/data-collection),
  on which the note article above is based.

### What is new here

The end-effector mouse / keyboard control logic in
[`main.py`](src/dora_openarm_mouse_teleop/main.py), the example dataflows that
wire it to the inverse / forward kinematics nodes, and this README.

### Third-party libraries

[dora-rs](https://dora-rs.ai/), [Dear PyGui](https://github.com/hoffstadt/DearPyGui),
NumPy and PyArrow are used as dependencies and are not included.

See also [NOTICE](NOTICE).

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

Copyright 2026 Enactic, Inc. for the portions derived from the slider teleop
node and the upstream repository. Modifications by yt1970.
