# dora-openarm-mouse-teleop

[English](README.md) | 日本語

[OpenArm](https://openarm.dev/) の手先を、マウスとキーボードで動かす
[dora-rs](https://dora-rs.ai/) ノードです。[Dear PyGui](https://github.com/hoffstadt/DearPyGui)
を使っており(pip だけで入ります)、VR ヘッドセットもリーダーアームも不要です。
MuJoCo シミュレーション上でテレオペができます。

> **本リポジトリは二次的著作物です。** OpenArm のスライダー版テレオペノードと、
> note の dora-rs / OpenArm Cell 解説記事を参考にしています。何がどこから来ている
> かは [出典](#出典) に書いています。

## 適用範囲と安全上の注意

- **MuJoCo シミュレーションでのみ**動作を確認しています。**実機の OpenArm では
  試していません。**
- 例の dataflow は MuJoCo 向けの配線です(現在の手先位置はシミュレータから取って
  います)。実機で使うには、`dora-openarm-ik` を実機のフォロワーノードにつなぎ、
  `dora-openarm-fk` に実機の腕の状態を入力する必要があります。ここには含まれて
  いません。
- 実機で試す場合は、自己責任で行ってください。非常停止にいつでも手が届くように
  し、遅く小さな動きから始めてください。
- 下の手順では、実機用のパッケージ(`openarm-can`、`openarm-driver`)を入れません。
  CAN の環境や追加のシステムライブラリが必要になるためです。実機が必要なら、自分で
  入れてください。

## 操作

| 入力 | 動作 |
|---|---|
| パッドをドラッグ | 操作中の腕の手先を x / y に動かす |
| `↑` / `↓` キー(または `z` スライダー) | 手先を上下に動かす |
| マウスホイール | 操作中の腕のグリッパを開閉する |
| `←` / `→` キー | 操作する腕を切り替える(左 / 右) |
| `reset` ボタン | 操作中の腕のオフセットを初期姿勢に戻す |
| `R` キー | `button_x` を送る(MuJoCo のデモシーンで箱をリセット) |

動かせる範囲、z の範囲、滑らかさ、グリッパの刻み幅などの定数は、
[`main.py`](src/dora_openarm_mouse_teleop/main.py) の先頭にあります。

## 入出力

| 向き | 名前 | 型 |
|---|---|---|
| 入力 | `tick` | 任意(タイマー。例では 50 Hz) |
| 入力 | `pose_right`, `pose_left` | `dora-openarm-fk` が出す現在の手先姿勢 |
| 出力 | `target_right`, `target_left` | 構造体 `{pose: list<float32>}`。`dora-openarm-ik` への目標姿勢 |
| 出力 | `button_x` | bool |
| 出力 | `status` | 文字列(`ready`) |

ノードは、最初の `pose_right` と `pose_left` を受け取るまで待ち、それを基準姿勢にし
ます。その後は、基準姿勢にパッド・z 操作・グリッパのオフセットを足した値を出力しま
す。姿勢は `[x, y, z, qw, qx, qy, qz, グリッパ]` です。

## セットアップ

このリポジトリに入っているのは、マウスのノードだけです。dataflow のそれ以外の部分
(運動学、MuJoCo シミュレーション、データ収集 UI、レコーダー)は
[enactic/dora-openarm-data-collection](https://github.com/enactic/dora-openarm-data-collection)
のものを使います。[uv](https://docs.astral.sh/uv/) と Git が必要で、**数 GB の空き
ディスク容量**が必要です(MuJoCo、OpenCV などの依存のため)。

1. 元リポジトリをサブモジュールごと clone します。

   ```bash
   git clone https://github.com/enactic/dora-openarm-data-collection
   cd dora-openarm-data-collection
   git submodule update --init --recursive
   ```

2. このリポジトリを `nodes/` に clone します。

   ```bash
   git clone https://github.com/yt1970/dora-openarm-mouse-teleop nodes/dora-openarm-mouse-teleop
   ```

3. 実機用のパッケージを除いて依存を入れ、続けて同じ環境にマウスノードを入れます。

   ```bash
   uv sync --locked --no-install-package openarm-can --no-install-package openarm-driver
   source .venv/bin/activate
   uv pip install -e nodes/dora-openarm-mouse-teleop
   ```

   このあとは `uv sync` を実行しないでください。元リポのロックファイルにないパッ
   ケージ(このノードを含む)が消えます。実行してしまったときは、`uv pip install -e`
   の行をもう一度実行してください。

   2つのパッケージを除く理由: `openarm-can` は C++ からビルドされ、CLI11 という
   ライブラリが必要です。また CAN は主に Linux 向けです。元リポの CI は、Ubuntu で
   `libcli11-dev` を入れてから、そのまま `uv sync --locked` を実行しています。シミ
   ュレーションには不要です。

4. 例の dataflow を元リポのルートにコピーして、実行します。

   ```bash
   cp nodes/dora-openarm-mouse-teleop/examples/dataflow_mouse_teleop.yaml .
   UV_NO_SYNC=1 dora run dataflow_mouse_teleop.yaml --uv
   ```

   `UV_NO_SYNC=1` は、dora が `--uv` で使う `uv run` が、環境を再び同期しないよう
   にするためのものです。Dear PyGui のウィンドウ(パッドと `z` スライダー)と、
   MuJoCo のウィンドウが開きます。

   **macOS** で MuJoCo のウィンドウが開かない、またはノードが起動に失敗するとき
   は、`mjpython` を使うラッパー
   [`examples/mujoco_mac.sh`](examples/mujoco_mac.sh) を試してください(これは
   [出典](#出典) の note 記事で紹介されている macOS 向けの回避策です)。

   ```bash
   cp nodes/dora-openarm-mouse-teleop/examples/mujoco_mac.sh .
   chmod +x mujoco_mac.sh
   sed -i '' 's#path: dora-openarm-mujoco#path: ./mujoco_mac.sh#' dataflow_mouse_teleop.yaml
   ```

   私は macOS で、このラッパーを使って動作を確認しました。ラッパーが必須かどうか
   は確認していないため、この手順では必須にしていません。

`examples/dataflow_mouse_teleop_data_collection.yaml` は、データ収集の Web UI
(http://localhost:8000)とレコーダーを加えたものです。現在の元リポジトリでの動作は、
**まだ確認していません**。

## 動作確認した環境

- macOS、Python 3.12、dora-rs / dora-rs-cli 1.0.1。2026-10-18 に clone した元リポジ
  トリで確認しました(サブモジュールは、その版が指定するもの)。
- 実行したのは `examples/dataflow_mouse_teleop.yaml`(MuJoCo でのテレオペ)だけで、
  macOS で **`mujoco_mac.sh` を使って**動かしました(使わない場合は未確認です)。
  パッド、`z` 操作、グリッパ(マウスホイール)で腕を動かせることは確認しました。ほか
  のプラットフォーム、データ収集の dataflow、実機は確認していません。
- 最近の元リポジトリは、`dataflow.yaml` 1つと `leader-*.yaml` モジュール(出力は
  `follower_position_*`)の構成になっています。ここの例は単独の dataflow で、その構
  成にはまだ組み込めません。このノードと `dora-openarm-ik`、`dora-openarm-fk` を
  `leader-mouse.yaml` モジュールにまとめるのは、今後の課題です。

## 出典

このプロジェクトは、ほかの方々の成果を参考にして、改変して作りました。以下の著者の
方々に感謝します。

### 何を基にしているか

- **OpenArm スライダー版テレオペノード**:
  [k1000dai/dora-openarm-slider-teleop](https://github.com/k1000dai/dora-openarm-slider-teleop)
  (Apache-2.0、Copyright 2026 Enactic, Inc.)。
  このノードの全体の構造は、これに沿っています。メインスレッドで動く Dear PyGui の
  ウィンドウ、ワーカースレッドで動く dora のイベントループ、パッケージ構成
  (`pyproject.toml`、`src/` レイアウト、コンソールスクリプト)、`tick` ごとに値を送
  る考え方です。関節スライダーは、手先の目標をマウス・キーボードで操作する方式(パ
  ッド、`z`、グリッパ、腕の切り替え、箱のリセット)に**置き換え**ました。出力も、関節
  位置(`position_*`)から、逆運動学に渡す目標姿勢(`target_*`)に変えています。
- **note の記事**「OpenArm Cell で学ぶ dora-rs (MuJoCo)[起動~data collectionまで]」
  (chiyo_note さん、2026-05-20):
  <https://note.com/duckduck1836/n/nfb1b17e7e897>。
  `dataflow.yaml` の読み方、ノードの書き方、スライダー版テレオペを MuJoCo とデータ
  収集 UI で動かす方法が解説されています。このノードを作るときに従った手順書で、
  [`examples/`](examples) の dataflow は、記事が説明する dataflow を基にしていま
  す(記事で紹介されている macOS 向けの `mujoco_mac.sh` も含みます)。
- **元のデータ収集リポジトリ**:
  [enactic/dora-openarm-data-collection](https://github.com/enactic/dora-openarm-data-collection)
  (Apache-2.0、Copyright 2026 Enactic, Inc.)。
  このノードがつなぐノード(`dora-openarm-kinematics`、`dora-openarm-mujoco`、
  `dora-openarm-data-collection-ui`、`dora-openarm-dataset-recorder`)と
  `metadata_mujoco.yaml` は、このリポジトリと、そこがサブモジュールとして使っている
  Enactic のリポジトリのものです。このリポジトリには**含まれていません**。
- **OpenArm**([Enactic, Inc.](https://openarm.dev/))と、公式の
  [データ収集チュートリアル](https://docs.openarm.dev/tutorial/data-collection)
  (上の note 記事の元になったもの)。

### 新しく作った部分

[`main.py`](src/dora_openarm_mouse_teleop/main.py) の、手先のマウス・キーボード操作
のロジック、それを逆運動学・順運動学のノードにつなぐ例の dataflow、そして README です。

### サードパーティのライブラリ

[dora-rs](https://dora-rs.ai/)、[Dear PyGui](https://github.com/hoffstadt/DearPyGui)、
NumPy、PyArrow を依存として使っており、このリポジトリには含まれていません。

[NOTICE](NOTICE) も参照してください。

## ライセンス

Apache License 2.0 です。[LICENSE](LICENSE) を参照してください。

スライダー版ノードと元リポジトリから引き継いだ部分の著作権は Copyright 2026
Enactic, Inc. です。改変は yt1970 によるものです。
