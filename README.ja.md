# dora-openarm-mouse-teleop

[English](README.md) | 日本語

[OpenArm](https://openarm.dev/) の手先を、**マウスとキーボード**
([Dear PyGui](https://github.com/hoffstadt/DearPyGui))と **iPhone**(ARKit)で動かす
[dora-rs](https://dora-rs.ai/) ノードです。MuJoCo シミュレーション上で使えます。VR
ヘッドセットもリーダーアームも不要です。

> **本リポジトリは二次的著作物で、AI の支援を受けて開発しました。**
> マウスノードは、OpenArm のスライダー版テレオペノードと、note の解説記事を基にして
> います。コードとドキュメントは、**Claude Sonnet 5.5**(Anthropic)との対話で作りまし
> た。何がどこから来ているかは、[出典](#出典)と [AI の使用](#ai-の使用)に書いています。

## クイックスタート

シミュレーションでのマウス操作です(macOS / Linux)。[uv](https://docs.astral.sh/uv/)
と Git、**数 GB の空きディスク容量**が必要です。

```bash
# 1. 元リポジトリ(運動学、MuJoCo、UI、レコーダー)をサブモジュールごと clone
git clone https://github.com/enactic/dora-openarm-data-collection
cd dora-openarm-data-collection
git submodule update --init --recursive

# 2. このリポジトリを nodes/ に clone
git clone https://github.com/yt1970/dora-openarm-mouse-teleop nodes/dora-openarm-mouse-teleop

# 3. 依存を入れる(実機用パッケージを除く)。そのあとにこのリポジトリを入れる
uv sync --locked --no-install-package openarm-can --no-install-package openarm-driver
source .venv/bin/activate
uv pip install -e "nodes/dora-openarm-mouse-teleop[iphone]"

# 4. 実行
cp nodes/dora-openarm-mouse-teleop/examples/dataflow_mouse_teleop.yaml .
UV_NO_SYNC=1 dora run dataflow_mouse_teleop.yaml --uv
```

Dear PyGui のウィンドウ(パッドと `z` スライダー)と、MuJoCo のウィンドウが開きます。
止めるときは、ターミナルで `Ctrl+C` を押します。

補足:

- 手順3のあとに `uv sync` を実行しないでください。元リポのロックファイルにないパッケ
  ージ(これらのノードを含む)が消えます。実行してしまったときは、`uv pip install -e`
  の行をもう一度実行してください。
- `UV_NO_SYNC=1` は、dora が `--uv` で使う `uv run` が、環境を再び同期しないようにす
  るものです。
- `openarm-can` は C++ からビルドされ、CLI11 というライブラリが必要です。また CAN は
  主に Linux 向けです。元リポの CI は、Ubuntu で `libcli11-dev` を入れてから、そのま
  ま `uv sync --locked` を実行しています。シミュレーションには不要です。
- **macOS**: MuJoCo のウィンドウが開かない、またはノードが起動に失敗するときは、
  `mjpython` を使うラッパー [`examples/mujoco_mac.sh`](examples/mujoco_mac.sh) を試
  してください(これは [出典](#出典) の note 記事で紹介されている macOS 向けの回避策
  です)。

  ```bash
  cp nodes/dora-openarm-mouse-teleop/examples/mujoco_mac.sh .
  chmod +x mujoco_mac.sh
  sed -i '' 's#path: dora-openarm-mujoco#path: ./mujoco_mac.sh#' dataflow_mouse_teleop.yaml
  ```

  私は macOS で、このラッパーを使って動作を確認しました。ラッパーが必須かどうかは確
  認していないため、この手順では必須にしていません。

## 適用範囲と安全上の注意

- **MuJoCo シミュレーションでのみ**動作を確認しています。**実機の OpenArm では試し
  ていません。**
- 例の dataflow は MuJoCo 向けの配線です(現在の手先位置はシミュレータから取ってい
  ます)。実機で使うには、`dora-openarm-ik` を実機のフォロワーノードにつなぎ、
  `dora-openarm-fk` に実機の腕の状態を入力する必要があります。ここには含まれていま
  せん。
- 実機で試す場合は、自己責任で行ってください。非常停止にいつでも手が届くようにし、遅
  く小さな動きから始めてください。
- iPhone ノードは、**認証なし**の UDP ポートで待ち受けます。同じネットワークにいる
  どの端末からでも、姿勢を送って腕を動かせます。信頼できるネットワークでだけ使い、実
  機とは一緒に使わないでください。`IPHONE_HOST` に特定のインターフェースのアドレスを
  指定することもできます。
- 上の手順では、実機用のパッケージ(`openarm-can`、`openarm-driver`)を入れません。
  実機が必要なら、自分で入れてください。

## マウス操作

| 入力 | 動作 |
|---|---|
| パッドをドラッグ | 操作中の腕の手先を x / y に動かす |
| `↑` / `↓` キー(または `z` スライダー) | 手先を上下に動かす |
| 左ボタンを押したままホイール | 手先を少しずつ上下に動かす |
| マウスホイール | 操作中の腕のグリッパを開閉する |
| `←` / `→` キー | 操作する腕を切り替える |
| `Reset` ボタン | 操作中の腕を、起動時の姿勢に戻す |
| `R` キー | `button_x` を送る(MuJoCo のデモシーンで箱をリセット) |

動かせる範囲、z の範囲、滑らかさ、グリッパの刻み幅などの定数は、
[`main.py`](src/dora_openarm_mouse_teleop/main.py) の先頭にあります。`MOUSE_ARMS`
(例: `MOUSE_ARMS=left`)で、マウスが操作できる腕を限定できます。

### 入出力

| 向き | 名前 | 型 |
|---|---|---|
| 入力 | `tick` | 任意(タイマー。例では 50 Hz) |
| 入力 | `pose_right`, `pose_left` | `dora-openarm-fk` が出す現在の手先姿勢 |
| 入力 | `phone_sides`(省略可) | 文字列。iPhone が担当する腕(例: `right`) |
| 出力 | `target_right`, `target_left` | 構造体 `{pose: list<float32>}`。`dora-openarm-ik` への目標姿勢 |
| 出力 | `button_x` | bool |
| 出力 | `status` | 文字列(`ready`) |

ノードは、最初の `pose_right` と `pose_left` を受け取るまで待ち、それを基準姿勢にしま
す。その後は、基準姿勢にパッド・z 操作・グリッパのオフセットを足した値を出力します。
姿勢は `[x, y, z, qw, qx, qy, qz, グリッパ]` です。

## iPhone 操作

iPhone を動かして、腕を 6 自由度(位置**と**向き。マウスでは取れない手首の回転も含み
ます)で操作します。iOS アプリが、ARKit のカメラ姿勢を UDP で
`dora-openarm-iphone-teleop` に送り、ノードが `dora-openarm-ik` への目標姿勢に変換し
ます。

```
iPhone (ARKit アプリ) --UDP 5007--> iphone-teleop --> ik --> mujoco
                                         ^
                  mouse-teleop の目標(スマホが担当しない腕の分)
```

- 腕ごとに、スマホがその腕のパケットを送り続けている間はスマホが、それ以外はマウス
  が担当します。スマホが約 1.5 秒途切れると、その腕はマウスに戻り、現在の姿勢から再
  スタートします。
- 設計上は、スマホ 0 台、1 台、2 台に対応しています。**試したのは iPhone 1 台だけ**
  です。

### ネットワーク

Mac と iPhone は、**同じ Wi-Fi ネットワーク(ルーター)**につなぎます。Mac を
iPhone のテザリング(インターネット共有)につなぐ方法は、私の環境では**動きません
でした**(Mac に IPv4 の LAN アドレスが付きませんでした)。別の Wi-Fi ネットワーク
を使ってください。macOS での Mac のアドレスは、次で分かります。

```bash
ipconfig getifaddr en0
```

### iOS アプリのビルド

[`ios/PhoneTeleop/PhoneTeleopApp.swift`](ios/PhoneTeleop/PhoneTeleopApp.swift) が
アプリのすべてです(SwiftUI + ARKit)。Xcode プロジェクトは含まれていません。

1. Xcode で、新しい **iOS App** プロジェクト(SwiftUI、Swift)を作ります。
2. 自動生成された `ContentView.swift` と `...App.swift`(それ自体に `@main` がありま
   す)を削除し、代わりに `PhoneTeleopApp.swift` を追加します。
3. *Signing & Capabilities* で Team を選びます(無料の Apple ID でも動きますが、7 日
   で期限が切れるので、作り直す必要があります)。
4. 実機の iPhone で実行します。ARKit はシミュレータでは動きません。初回の起動時に、
   カメラとローカルネットワークへのアクセスを許可してください。AR の開始時にアプリが
   止まる場合は、ターゲットにカメラの使用目的(`NSCameraUsageDescription`)が設定さ
   れているか確認してください。

### 実行

```bash
cp nodes/dora-openarm-mouse-teleop/examples/dataflow_mouse_iphone.yaml .
UV_NO_SYNC=1 dora run dataflow_mouse_iphone.yaml --uv
```

(必要なら、上と同じ macOS 用の `mujoco_mac.sh` の変更をしてください。)アプリでの操作:

| 操作 | 動作 |
|---|---|
| Mac IP 欄 と `接続` | Mac のアドレスを入れて接続する。押すときは、iPhone を前方に向けます。その向きが、この端末の「前」になります |
| `左腕` / `右腕` | この端末が操作する腕を選ぶ |
| `追従 ON/OFF` | ON の間、ON にした瞬間からの iPhone の動きが手先の動きになります(実際の腕の姿勢から開始)。手を持ち直したいときは OFF にしてから、もう一度 ON にします(ラチェット式) |
| 縦スライダー | グリッパ(アプリのラベルは、上が `開`、下が `閉`) |
| `腕リセット` | 腕を起動時の姿勢に戻す |

背面カメラを指でふさがないでください。ARKit の追跡に使われます。追跡が不安定なとき
は、アプリに警告が出て、追従が止まります。

### 設定

`dora-openarm-iphone-teleop` の環境変数:

| 変数 | 既定値 | 意味 |
|---|---|---|
| `IPHONE_HOST` | `0.0.0.0` | 待ち受けるインターフェースのアドレス |
| `IPHONE_PORT` | `5007` | UDP ポート(アプリは 5007 を使います) |
| `IPHONE_POS_SCALE` | `1.0` | iPhone の 1 m の動きが、ロボットの何 m になるか |
| `IPHONE_SMOOTH` | `0.3` | 1 tick あたりの追従率(0〜1。小さいほど滑らか) |

## 動作確認した環境

- macOS、Python 3.12、dora-rs / dora-rs-cli 1.0.1。2026-10-18 に clone した元リポジ
  トリで確認しました(サブモジュールは、その版が指定するもの)。
- **マウス操作**: その新しい clone で `examples/dataflow_mouse_teleop.yaml` を実行し
  ました。macOS で **`mujoco_mac.sh` を使って**動かしています(使わない場合は未確認
  です)。パッド、`z` 操作、グリッパ(マウスホイール)で腕を動かせることは確認しまし
  た。
- **iPhone 操作**: 作者の環境(macOS、LiDAR なしの iPhone 16 を 1 台)で、マウスと組
  み合わせて使いました。このリポジトリの例は、その配線を整理したコピーで、元リポジ
  トリの新しい clone では**再実行していません**。スマホ 2 台の同時使用も試していま
  せん。
- **データ収集**(`*_data_collection.yaml`): 作者の環境では使いましたが、新しい
  clone では**再確認していません**。
- ほかのプラットフォームと実機は、確認していません。
- 最近の元リポジトリは、`dataflow.yaml` 1つと `leader-*.yaml` モジュール(出力は
  `follower_position_*`)の構成になっています。ここの例は単独の dataflow で、その構
  成にはまだ組み込めません。これらのノードと `dora-openarm-ik`、`dora-openarm-fk`
  を `leader-*.yaml` モジュールにまとめるのは、今後の課題です。

## AI の使用

iPhone ノード、iOS アプリ、この README を含む、このリポジトリのコードとドキュメント
は、yt1970 が **Claude Sonnet 5.5**(Anthropic)と対話しながら作りました。使う前
に、ご自身でコードを確認してください。特に、実機で使う場合は必ず確認してください。

## 出典

このプロジェクトは、ほかの方々の成果を参考にして、改変して作りました。以下の著者の
方々に感謝します。

### 何を基にしているか

- **OpenArm スライダー版テレオペノード**:
  [k1000dai/dora-openarm-slider-teleop](https://github.com/k1000dai/dora-openarm-slider-teleop)
  (Apache-2.0、Copyright 2026 Enactic, Inc.)。
  **マウスノード**の構造は、これに沿っています。メインスレッドで動く Dear PyGui のウ
  ィンドウ、ワーカースレッドで動く dora のイベントループ、パッケージ構成
  (`pyproject.toml`、`src/` レイアウト、コンソールスクリプト)、`tick` ごとに値を送
  る考え方です。関節スライダーは、手先の目標をマウス・キーボードで操作する方式(パッ
  ド、`z`、グリッパ、腕の切り替え、箱のリセット)に**置き換え**ました。出力も、関節位
  置(`position_*`)から、逆運動学に渡す目標姿勢(`target_*`)に変えています。
- **note の記事**「OpenArm Cell で学ぶ dora-rs (MuJoCo)[起動~data collectionまで]」
  (chiyo_note さん、2026-05-20):
  <https://note.com/duckduck1836/n/nfb1b17e7e897>。
  `dataflow.yaml` の読み方、ノードの書き方、スライダー版テレオペを MuJoCo とデータ収
  集 UI で動かす方法が解説されています。マウスノードを作るときに従った手順書で、
  [`examples/`](examples) の dataflow は、記事が説明する dataflow を基にしています
  (記事で紹介されている macOS 向けの `mujoco_mac.sh` も含みます)。
- **元のデータ収集リポジトリ**:
  [enactic/dora-openarm-data-collection](https://github.com/enactic/dora-openarm-data-collection)
  (Apache-2.0、Copyright 2026 Enactic, Inc.)。
  これらのノードがつなぐノード(`dora-openarm-kinematics`、`dora-openarm-mujoco`、
  `dora-openarm-data-collection-ui`、`dora-openarm-dataset-recorder`)と
  `metadata_mujoco.yaml` は、このリポジトリと、そこがサブモジュールとして使っている
  Enactic のリポジトリのものです。このリポジトリには**含まれていません**。
- **OpenArm**([Enactic, Inc.](https://openarm.dev/))と、公式の
  [データ収集チュートリアル](https://docs.openarm.dev/tutorial/data-collection)
  (上の note 記事の元になったもの)。

### 新しく作った部分

- **iPhone ノード**(`dora-openarm-iphone-teleop`)と **iOS アプリ**
  (`PhoneTeleopApp.swift`)は、オリジナルです。直接参考にした記事やリポジトリはあり
  ません。Apple の ARKit、SwiftUI、Network フレームワークを使っています。
- [`main.py`](src/dora_openarm_mouse_teleop/main.py) の、手先のマウス・キーボード操
  作のロジック、ノードを逆運動学・順運動学のノードにつなぐ例の dataflow、そしてこの
  README です。

### サードパーティのライブラリ

[dora-rs](https://dora-rs.ai/)、[Dear PyGui](https://github.com/hoffstadt/DearPyGui)、
NumPy、SciPy、PyArrow を依存として使っており、このリポジトリには含まれていません。

[NOTICE](NOTICE) も参照してください。

## ライセンス

Apache License 2.0 です。[LICENSE](LICENSE) を参照してください。

スライダー版ノードと元リポジトリから引き継いだ部分の著作権は Copyright 2026
Enactic, Inc. です。iPhone ノード、iOS アプリ、そのほかの改変の著作権は Copyright
2026 yt1970 です。
