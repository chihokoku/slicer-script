## 使用方法

1. vs code に 3D slicer で実行したい処理を記述
2. 3D slicer を起動 →view→python console
3. slicer の python script に下記を記述(pandas のインストール※一度だけ行えば良い)
   pip_install('pandas openpyxl')
   下記が出れば完了
   Successfully installed et-xmlfile-2.0.0 openpyxl-3.1.5 pandas-2.3.0 pytz-2025.2 tzdata-2025.2
4. コンソールに下記を記述 ↓↓↓↓(macOS 用)
   exec(open("/Users/m.saito/Desktop/slicer-script/script.py" , encoding="utf-8").read())

## 注意

- エクスポートする際は必ず stl 形式で出力(obj 形式だと変更前のモデルが残ってしまうため)
- 最初の実行では落ちることがよくある
- 左脚をのエクセルデータを読み込ませる時は、必ず x 座標を負の値にする
- 「処理中にエラーが発生しました」＝　読み込ませたエクセルファイルの z の値が間違っている可能性が高い
- モデルが変形されていない時 → エクセルファイルの髄腔データと前縁データが逆の可能性
