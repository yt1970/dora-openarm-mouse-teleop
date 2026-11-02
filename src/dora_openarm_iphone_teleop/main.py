# Copyright 2026 yt1970
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Developed in dialogue with Claude Sonnet 5.5 (Anthropic). No external
# article or repository was used as a reference for the pose handling.

"""iPhone (ARKit) 6DoF pose teleoperation hub for OpenArm.

Receives JSON packets from the iPhone app over UDP and outputs target poses
for ``dora-openarm-ik``. It also takes the mouse node's targets and forwards
them for the arms that no phone controls, because an input of the IK node can
have only one source.

An arm is controlled by the phone while packets for that arm keep arriving
(``OWNER`` seconds), otherwise by the mouse.
"""

import json
import math
import os
import socket
import threading
import time

import dora
import numpy as np
import pyarrow as pa
from scipy.spatial.transform import Rotation as R
from scipy.spatial.transform import Slerp

SIDES = ("right", "left")
HOST = os.environ.get("IPHONE_HOST", "0.0.0.0")   # interface to listen on
PORT = int(os.environ.get("IPHONE_PORT", "5007"))
POS_SCALE = float(os.environ.get("IPHONE_POS_SCALE", "1.0"))  # 1 m of phone motion = this many m of robot motion
SMOOTH = float(os.environ.get("IPHONE_SMOOTH", "0.3"))        # follow rate per tick
HOME_SMOOTH = 0.1                                             # speed of the return to the start pose on reset
GRIP_SMOOTH = 0.2
FRESH = 0.5     # packets newer than this many seconds are used for control (older ones: hold)
OWNER = 1.5     # an arm with packets newer than this many seconds is controlled by the phone
GRIP_END = {"right": -math.pi / 4, "left": math.pi / 4}       # gripper angle at g=1

# ARKit world (x right, y up, z backward) -> robot (x forward, y left, z up)
C = np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]], dtype=float)


def _target(pose):
    return pa.array(
        [{"pose": [float(v) for v in pose]}],
        type=pa.struct([("pose", pa.list_(pa.float32()))]),
    )


def _pose_to_list(value):
    first = value.to_pylist()[0]
    return list(first["pose"]) if isinstance(first, dict) else list(value.to_pylist())


def _quat(p):
    return R.from_quat([p[4], p[5], p[6], p[3]])  # [qw,qx,qy,qz] -> xyzw


def _slerp(r0, r1, t):
    return Slerp([0, 1], R.concatenate([r0, r1]))([t])[0]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _valid_packet(pkt):
    """Check a decoded packet so that malformed ones cannot stop the node."""
    if not isinstance(pkt, dict) or pkt.get("side") not in SIDES:
        return False
    p, q = pkt.get("p"), pkt.get("q")
    if not (isinstance(p, list) and len(p) == 3 and all(_num(v) for v in p)):
        return False
    if not (isinstance(q, list) and len(q) == 4 and all(_num(v) for v in q)):
        return False
    return math.sqrt(sum(v * v for v in q)) > 1e-6


class Arm:
    def __init__(self):
        self.pose = None      # latest fk pose [px,py,pz,qw,qx,qy,qz,grip]
        self.home = None      # pose at startup
        self.mouse = None     # latest mouse target
        self.pos = self.rot = None
        self.grip = 0.0
        self.owned = False
        self.engaged = False
        self.homing = False
        self.rc = None
        self.p0 = self.q0 = self.t0_pos = self.t0_rot = None

    def load(self, pose):
        self.pos = np.array(pose[:3], dtype=float)
        self.rot = _quat(pose)
        self.grip = pose[7]


def _udp_loop(latest, lock):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    while True:
        data, addr = sock.recvfrom(2048)
        try:
            pkt = json.loads(data)
        except ValueError:
            continue
        if not _valid_packet(pkt):
            continue
        side = pkt["side"]
        now = time.monotonic()
        with lock:
            cur = latest[side]
            # If another device is using the same arm, ignore this one
            # (first come, first served).
            if cur is not None and cur["addr"] != addr[0] and now - cur["rt"] < OWNER:
                continue
            latest[side] = {"pkt": pkt, "rt": now, "addr": addr[0]}


def main():
    latest = {s: None for s in SIDES}
    lock = threading.Lock()
    threading.Thread(target=_udp_loop, args=(latest, lock), daemon=True).start()

    arms = {s: Arm() for s in SIDES}

    node = dora.Node()
    node.send_output("status", pa.array(["ready"]))

    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT":
            continue
        eid = event["id"]

        if eid in ("pose_right", "pose_left"):
            a = arms[eid.split("_")[1]]
            a.pose = _pose_to_list(event["value"])
            if a.home is None:
                a.home = list(a.pose)
                a.load(a.pose)
            continue

        if eid in ("mouse_target_right", "mouse_target_left"):
            arms[eid.split("_")[-1]].mouse = _pose_to_list(event["value"])
            continue

        if eid != "tick":
            continue

        now = time.monotonic()
        with lock:
            snap = {s: latest[s] for s in SIDES}

        owned_sides = []
        outs = {}
        for side in SIDES:
            a = arms[side]
            if a.pose is None:
                continue
            entry = snap[side]
            active = entry is not None and now - entry["rt"] < OWNER

            if active and not a.owned:          # the phone started controlling this arm
                a.owned = True
                a.load(a.pose)                  # restart from the current pose (no jump)
                a.engaged = False
                a.homing = False
                a.rc = None
            elif not active and a.owned:        # the phone left -> back to the mouse
                a.owned = False
                a.mouse = None
                a.engaged = False

            if not a.owned:
                outs[side] = a.mouse if a.mouse is not None else a.pose
                continue

            owned_sides.append(side)
            pkt = entry["pkt"]
            fresh = now - entry["rt"] < FRESH and pkt.get("ok") == 1

            rc = pkt.get("rc")
            if a.rc is None:
                a.rc = rc
            elif rc != a.rc:                    # reset button
                a.rc = rc
                a.homing = True
                a.engaged = False

            if a.homing:
                hp = np.array(a.home[:3], dtype=float)
                hr = _quat(a.home)
                a.pos = a.pos + (hp - a.pos) * HOME_SMOOTH
                a.rot = _slerp(a.rot, hr, HOME_SMOOTH)
                if np.linalg.norm(hp - a.pos) < 1e-3 and (a.rot.inv() * hr).magnitude() < 0.01:
                    a.homing = False
            elif fresh and pkt.get("c") == 1:   # follow is ON
                p = np.array(pkt["p"], dtype=float)
                q = R.from_quat(pkt["q"])       # [x,y,z,w]
                if not a.engaged:
                    a.engaged = True
                    a.pos = np.array(a.pose[:3], dtype=float)   # start from the real arm position
                    a.rot = _quat(a.pose)
                    a.p0, a.q0 = p, q
                    a.t0_pos, a.t0_rot = a.pos.copy(), a.rot
                goal_pos = a.t0_pos + POS_SCALE * (C @ (p - a.p0))
                d_ar = (q * a.q0.inv()).as_matrix()
                goal_rot = R.from_matrix(C @ d_ar @ C.T) * a.t0_rot
                a.pos = a.pos + (goal_pos - a.pos) * SMOOTH
                a.rot = _slerp(a.rot, goal_rot, SMOOTH)
            else:
                a.engaged = False

            if fresh:
                g = pkt.get("g", 0.0)
                g = min(1.0, max(0.0, float(g))) if _num(g) else 0.0
                goal_grip = g * GRIP_END[side]
                a.grip += (goal_grip - a.grip) * GRIP_SMOOTH

            x, y, z, w = a.rot.as_quat()
            outs[side] = [a.pos[0], a.pos[1], a.pos[2], w, x, y, z, a.grip]

        for side, pose in outs.items():
            node.send_output(f"target_{side}", _target(pose))
        node.send_output("phone_sides", pa.array([",".join(owned_sides)]))


if __name__ == "__main__":
    main()
