# dora-openarm-mouse-teleop

A [dora-rs](https://dora-rs.ai/) node that teleoperates the end-effectors of
[OpenArm](https://openarm.dev/) with a mouse and keyboard, using
[Dear PyGui](https://github.com/hoffstadt/DearPyGui) (pure pip, no VR headset,
no leader arm).

OpenArm の手先をマウスとキーボードで動かす dora-rs ノードです。VR ヘッドセットも
リーダーアームも不要で、MuJoCo シミュレーション上でテレオペとデータ収集ができます。

> **This is a derivative work.** It is based on the OpenArm slider teleop node
> and on the dora-rs / OpenArm Cell tutorial in a note.com article. See
> [Attribution](#attribution) for exactly what comes from where.
>
> **本リポジトリは二次的著作物です。** スライダー版ノードと note の解説記事を参考に
> しています。何がどこから来ているかは [Attribution](#attribution) に書いています。

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
control and the gripper. The first three elements of the pose are the position
and the eighth element is the gripper.

## Setup

This repository contains only the mouse node. The rest of the dataflow
(kinematics, MuJoCo simulation, data collection UI, recorder) comes from
[enactic/dora-openarm-data-collection](https://github.com/enactic/dora-openarm-data-collection).

1. Clone the upstream repository with its submodules and follow its setup.

   ```bash
   git clone https://github.com/enactic/dora-openarm-data-collection
   cd dora-openarm-data-collection
   git submodule update --init --recursive
   ```

2. Clone this repository into `nodes/`.

   ```bash
   git clone https://github.com/yt1970/dora-openarm-mouse-teleop nodes/dora-openarm-mouse-teleop
   ```

3. Copy an example dataflow to the upstream root and run it. The `build:` paths
   in the examples are relative to the upstream root.

   ```bash
   cp nodes/dora-openarm-mouse-teleop/examples/dataflow_mouse_teleop.yaml .
   uv venv && uv pip install dora-rs-cli && source .venv/bin/activate
   dora build dataflow_mouse_teleop.yaml --uv
   dora run dataflow_mouse_teleop.yaml --uv
   ```

   For data collection with the web UI (open http://localhost:8000), use
   `dataflow_mouse_teleop_data_collection.yaml` instead. Recorded datasets are
   saved to `mouse_mujoco_data/`.

   On macOS, MuJoCo's viewer needs `mjpython`. Copy
   [`examples/mujoco_mac.sh`](examples/mujoco_mac.sh) to the upstream root, run
   `chmod +x mujoco_mac.sh`, and set `path: ./mujoco_mac.sh` on the
   `mujoco-collect` node.

## Compatibility

- Developed on macOS with MuJoCo against the upstream layout that has one
  `dataflow-*.yaml` file per setup. It has not been tested on other platforms.
- Recent upstream versions use a single `dataflow.yaml` with `leader-*.yaml`
  modules whose outputs are `follower_position_*`. The examples here do not
  target that layout yet. Wrapping this node, `dora-openarm-ik` and
  `dora-openarm-fk` in a `leader-mouse.yaml` module is future work.

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
