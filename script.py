# --- モジュール検索パスを追加するための前処理 ---
import sys
import os
# このスクリプトがあるフォルダのパスを定義
script_directory = "/Users/m.saito/Desktop/slicer-script"
# Pythonがモジュールを探す場所のリスト(sys.path)に、このフォルダを追加
# これにより、同じフォルダにある他の.pyファイルをimportできるようになる
if script_directory not in sys.path:
    sys.path.append(script_directory)
# --- 前処理ここまで ---

import slicer 
import qt
import vtk
import pandas as pd
import numpy as np
from scipy.ndimage import affine_transform
import scipy.ndimage
import math
from scipy.interpolate import interp1d
import straight_line_equation

def message_box():
    # *********************************
    # ダイアログに表示するメッセージ
    # ********************************
    # 1. メッセージボックスのインスタンスを作成
    msgBox2 = qt.QMessageBox()
    msgBox2.setText("どのモデルを作成しますか？？")
    msgBox2.setWindowTitle("処理の確認")
    # 2. カスタムボタンを追加
    yesButton = msgBox2.addButton("ねじれ無しモデル", qt.QMessageBox.YesRole)
    noButton = msgBox2.addButton("ねじれ強調モデル", qt.QMessageBox.NoRole)
    cancelButton = msgBox2.addButton("外側にねじれ強調モデル", qt.QMessageBox.RejectRole)
    msgBox2.exec_()
    if msgBox2.clickedButton() == yesButton:
        print("ねじれ無しモデルを作成します")
        tibia_type = 0
        rotate_slice_in_place(tibia_type)
    elif msgBox2.clickedButton() == noButton:
        print("ねじれ強調モデルを作成します")
        tibia_type = 1
        rotate_slice_in_place(tibia_type)
    else:
        tibia_type = 2
        rotate_slice_in_place(tibia_type)
    
       


def rotate_slice_in_place(tibia_type):
    # 0. segment editorを初期化する
    slicer.util.selectModule("SegmentEditor")
    # 1. 準備：編集対象のセグメンテーションノードを取得
    segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    if not segmentEditorWidget:
        print('segmentEditorWidgetがありません')
        return
    segmentationNode = segmentEditorWidget.mrmlSegmentEditorNode().GetSegmentationNode()
    if segmentationNode is None:
        print("エラー: Segment Editorでセグメンテーションが選択されていません。")
        return 
    print(f"処理対象ノード: '{segmentationNode.GetName()}'")
    # 処理を一つの塊としてSlicerに通知（アンドゥ機能のため）
    segmentationNode.StartModify()


    # # **************************************
    # # sclicerのapiを使って回転させるプログラム
    # # **************************************
    # ROTATION_ANGLE_DEG = 180
    # # 2. VTKを使って変換ルール(Transform)を作成
    # transform = vtk.vtkTransform()
    # # 原点を中心にZ軸周りで回転
    # # 平行移動の処理を省くことで、回転の中心はデフォルトで原点(0,0,0)になる
    # transform.RotateZ(ROTATION_ANGLE_DEG)
    # # # 3. 作成した変換を、新しいTransformノードとしてシーンに追加
    # transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "MyRotationTransform")
    # transformNode.SetMatrixTransformToParent(transform.GetMatrix())
    # # # 4. モデルに、このTransformノードを一時的に適用
    # segmentationNode.SetAndObserveTransformNodeID(transformNode.GetID())
    # # # 5. 【最重要】変換をモデルのジオメトリに「焼き付け(Harden)」て、恒久的な変更にする
    # print("変換をモデルに焼き付けています...")
    # slicer.vtkSlicerTransformLogic().hardenTransform(segmentationNode)
    # print(f"回転が完了しました")


    # ユーザーにExcelファイルを選択させる
    # あなたの環境に合わせて、返り値を一つの変数で受け取る
    file_path = qt.QFileDialog.getOpenFileName(None, "座標データのあるExcelファイルを選択", "", "Excel Files (*.xlsx *.xls)")
    #     # ファイル選択がキャンセルされた場合は処理を終了
    if not file_path:
        print("ファイルが選択されませんでした。")
        return
    print(f"選択されたファイル: {file_path}")
    # Excelファイルを読み込む
    df = pd.read_excel(file_path)


    # ***************************
    # 髄腔中心点をスプライン補間するプログラム
    # ***************************
    # データがあるかチェック
    # 2,3,4列目のデータをX,Y,Z座標として取得し,11行目 = インデックス10と列数(9列目 = インデックス8)があるかチェック
    if df.shape[1] < 4:
        raise ValueError("エラー: 選択されたExcelファイルには4列以上のデータがありません。")
    # .iloc[:, [1, 2, 3]] で2,3,4列目(インデックス1,2,3)をまとめて取得
    coords_data = df.iloc[:, [1, 2, 3]]
    # 分かりやすいように列名を'x', 'y', 'z'に設定
    coords_data.columns = ['x', 'y', 'z']
    # 不正なデータ（数値でないもの）を削除
    coords_data = coords_data.apply(pd.to_numeric, errors='coerce').dropna()
    if coords_data.empty:
        raise ValueError("有効な数値座標データが見つかりませんでした。")
    
    # 一旦表示してみる
    print('excelのz座標')
    print(coords_data['z'].iloc[0])


    # 【重要】スプライン補間を行う前に、必ずZ座標でデータを並び替える
    sorted_coords = coords_data.sort_values(by='z').to_numpy()
    # NumPy配列に変換
    x_coords = sorted_coords[:, 0]
    y_coords = sorted_coords[:, 1]
    z_coords = sorted_coords[:, 2]
    print(f"{len(z_coords)}個の有効な3D座標点を取得しました。")
    # 2b. Z座標が最小/最大の行の座標を取得して表示
    # Z座標が最小値を持つ行のインデックス(元のExcelの行番号ではない)を取得
    min_z_row_index = coords_data['z'].idxmin()
    # Z座標が最大値を持つ行のインデックスを取得
    max_z_row_index = coords_data['z'].idxmax()
    # インデックスを使って、該当する行のデータを取得
    min_z_row = coords_data.loc[min_z_row_index]
    max_z_row = coords_data.loc[max_z_row_index]
    print("\n--- 元データ内のZ座標 最小/最大情報 ---")
    print(f"Z座標が最小の行の座標 (X, Y, Z): ({min_z_row['x']}, {min_z_row['y']}, {min_z_row['z']})")
    print(f"Z座標が最大の行の座標 (X, Y, Z): ({max_z_row['x']}, {max_z_row['y']}, {max_z_row['z']})")
    # 3. ここで3次スプライン補間する曲線の方程式を求める
    # Z座標を基準に、XとYがどう変化するかをそれぞれ補間する
    f_x = interp1d(z_coords, x_coords, kind='cubic', fill_value="extrapolate")
    f_y = interp1d(z_coords, y_coords, kind='cubic', fill_value="extrapolate")
    # 4. 元のデータの最小Z座標と最大Z座標を取得Z軸に対して1mm間隔の点列リストを作成
    z_min = z_coords.min()
    z_max = z_coords.max()
    # ↓↓ここでリストを作成(z_minからz_maxまで、1mm間隔のZ座標のリストを生成)
    new_z_points = np.arange(z_min, z_max, 1.0)
    # 5. 曲線の方程式にリストを代入して点を求めるを使って、新しいZ座標に対応するX, Y座標を計算
    spline_x_points = f_x(new_z_points)  #スプライン補間した点列のx座標を格納
    spline_y_points = f_y(new_z_points)  #スプライン補間した点列のy座標を格納

    print(f"Z軸方向に1mm間隔で、{len(new_z_points)}個の補間点を生成しました。")

    # 6. 結果をSlicerのMarkupsノードとして表示
    output_node_name = slicer.mrmlScene.GenerateUniqueName("Interpolated_Points")
    markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", output_node_name)
    # 点の表示設定を調整（点を小さく、ラベルは非表示に）
    displayNode = markupsNode.GetDisplayNode()
    displayNode.SetGlyphScale(0.5)
    displayNode.SetTextScale(0)
    # 生成した点群を一つずつ追加
    for i in range(len(new_z_points)):
        markupsNode.AddControlPoint([spline_x_points[i], spline_y_points[i], new_z_points[i]])
    print("\n--- 処理完了 ---")
    print(f"結果が '{output_node_name}' という名前でシーンに追加されました。")



    # ***************************
    # 脛骨前凌点をスプライン補間するプログラム
    # ***************************
    # .iloc[:, [1, 2, 3]] で7,8,9列目(インデックス1,2,3)をまとめて取得
    tibia_coords_data = df.iloc[:, [6, 7, 8]]
    # 分かりやすいように列名を'x', 'y', 'z'に設定
    tibia_coords_data.columns = ['x', 'y', 'z']
    # 不正なデータ（数値でないもの）を削除
    tibia_coords_data = tibia_coords_data.apply(pd.to_numeric, errors='coerce').dropna()
    if tibia_coords_data.empty:
        raise ValueError("有効な数値座標データが見つかりませんでした。")
    # 【重要】スプライン補間を行う前に、必ずZ座標でデータを並び替える
    tibia_sorted_coords = tibia_coords_data.sort_values(by='z').to_numpy()
    # print("ソートした脛骨前凌点：",tibia_sorted_coords)
    # NumPy配列に変換
    tibia_x_coords = tibia_sorted_coords[:, 0]
    tibia_y_coords = tibia_sorted_coords[:, 1]
    tibia_z_coords = tibia_sorted_coords[:, 2]
    # 3. ここで3次スプライン補間する曲線の方程式を求める
    # Z座標を基準に、XとYがどう変化するかをそれぞれ補間する
    tibia_f_x = interp1d(tibia_z_coords, tibia_x_coords, kind='cubic', fill_value="extrapolate")
    tibia_f_y = interp1d(tibia_z_coords, tibia_y_coords, kind='cubic', fill_value="extrapolate")
    # 4. 元のデータの最小Z座標と最大Z座標を取得Z軸に対して1mm間隔の点列リストを作成
    tibia_z_min = tibia_z_coords.min()
    tibia_z_max = tibia_z_coords.max()
    # ↓↓ここでリストを作成(z_minからz_maxまで、1mm間隔のZ座標のリストを生成)
    tibia_new_z_points = np.arange(tibia_z_min, tibia_z_max, 1.0)
    # 5. 曲線の方程式にリストを代入して点を求めるを使って、新しいZ座標に対応するX, Y座標を計算
    tibia_spline_x_points = tibia_f_x(tibia_new_z_points)  #スプライン補間した点列のx座標を格納
    tibia_spline_y_points = tibia_f_y(tibia_new_z_points)  #スプライン補間した点列のy座標を格納
    # 6. 結果をSlicerのMarkupsノードとして表示
    output_node_name = slicer.mrmlScene.GenerateUniqueName("Interpolated_Points")
    markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", output_node_name)
    # 点の表示設定を調整（点を小さく、ラベルは非表示に）
    displayNode = markupsNode.GetDisplayNode()
    displayNode.SetGlyphScale(0.5)
    displayNode.SetTextScale(0)
    # 生成した点群を一つずつ追加
    for i in range(len(tibia_new_z_points)):
        markupsNode.AddControlPoint([tibia_spline_x_points[i], tibia_spline_y_points[i],  tibia_new_z_points[i]])

  

    # # ***************************
    # # 直線方程式を求める関数
    # # ***************************
    # 行と列の存在を確認
    # 11行目(インデックス10)と9列目(インデックス8)があるかチェック
    if df.shape[0] < 11:
        raise IndexError("エラー: Excelファイルに11行以上のデータがありません。")
    if df.shape[1] < 9:
        raise IndexError("エラー: Excelファイルに9列以上のデータがありません。")
    # 前縁の座標値を取得(iloc[行インデックス, 列インデックス] を使用)
    crest_maxZ_xyz = df.iloc[0, [6, 7, 8]].to_numpy()
    crest_minZ_xyz = df.iloc[9, [6, 7, 8]].to_numpy()
    # 取得した値を表示
    print("\n--- 処理結果 ---")
    print(f"1点目 (2行目の7,8,9列) の座標 (X, Y, Z): {crest_maxZ_xyz}")
    print(f"2点目 (11行目の7,8,9列) の座標 (X, Y, Z): {crest_minZ_xyz}")
    # 取得した値をSlicerの点として表示する例
    markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "前縁点")
    markupsNode.AddControlPoint(crest_maxZ_xyz)
    markupsNode.AddControlPoint(crest_minZ_xyz)
    #「方程式を計算する道具」を取り出して使う
    base_point, direction_vec = straight_line_equation.calculate_line_parameters(crest_minZ_xyz, crest_maxZ_xyz)
    
    # 測定する脛骨前縁の座標を格納する変数
    anterior_border_of_tibia = []
    list = [round(tibia_coords_data['x'].iloc[0],2),round(tibia_coords_data['y'].iloc[0],2),round(tibia_coords_data['z'].iloc[0],2)]
    anterior_border_of_tibia.append(list)


    try:
        # **************************************
        # sclicerのapiを使って回転させるプログラム
        # **************************************
        ROTATION_ANGLE_DEG = 180
        # 2. VTKを使って変換ルール(Transform)を作成
        transform = vtk.vtkTransform()
        # 原点を中心にZ軸周りで回転
        # 平行移動の処理を省くことで、回転の中心はデフォルトで原点(0,0,0)になる
        transform.RotateZ(ROTATION_ANGLE_DEG)
        # # 3. 作成した変換を、新しいTransformノードとしてシーンに追加
        transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "MyRotationTransform")
        transformNode.SetMatrixTransformToParent(transform.GetMatrix())
        # # 4. モデルに、このTransformノードを一時的に適用
        segmentationNode.SetAndObserveTransformNodeID(transformNode.GetID())
        # # 5. 【最重要】変換をモデルのジオメトリに「焼き付け(Harden)」て、恒久的な変更にする
        print("変換をモデルに焼き付けています...")
        slicer.vtkSlicerTransformLogic().hardenTransform(segmentationNode)
        

        # 2. セグメンテーションを一時的なラベルマップボリュームに変換
        print("セグメンテーションをラベルマップに変換中...")
        # 参照ボリュームとして、シーン内の最初のボリュームを使用（より安定）
        # referenceVolume = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', 'temp_labelmap_for_rotation')
        if not slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(segmentationNode, labelmapVolumeNode, slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY):
            raise ValueError("エラー: ラベルマップへの変換に失敗しました。")
        
        # NumPy配列に変換
        volumeArray = slicer.util.arrayFromVolume(labelmapVolumeNode)

        for i in range(1, len(new_z_points)):
            # Z座標値が格納されている変数
            slice_value = new_z_points[i]
            # あるz座標値から直線上の点を求める
            straight_line_x_points, straight_line_y_points= straight_line_equation.find_xy_at_z(slice_value,base_point, direction_vec)
            # *******************************
            # 髄腔中心点と直線上の点とのベクトルの成す角度を計算
            # *******************************
            # 1. ABベクトルの成分を計算
            # ベクトルの成分 = (終点のx - 始点のx, 終点のy - 始点のy)
            straight_line_vx = straight_line_x_points - spline_x_points[i]
            straight_line_vy = straight_line_y_points - spline_y_points[i]
            
            # 2. ベクトルの成分(vx, vy)から角度を計算
            # atan2は、ベクトルの向きから正しい象限の角度を返してくれる
            straight_line_angle_rad = math.atan2(straight_line_vy, straight_line_vx)
            # 3. ラジアンを度数法に変換して返す
            straight_line_angle_deg = math.degrees(straight_line_angle_rad)
            print("髄腔点と直線の角度：",straight_line_angle_deg)
            print("z座標値：",slice_value)
            print("スプライン補間した髄腔中心点：",spline_x_points[i],spline_y_points[i])
            print("直線上の点:",straight_line_x_points, straight_line_y_points)

            # 4. あるz座標値からsegmentationの何スライス目に当たるかを計算
            bounds = [0.0] * 6
            segmentationNode.GetRASBounds(bounds)
            if not (bounds[4] <= slice_value <= bounds[5]):
                raise ValueError(f"エラー: Z={slice_value}mm はモデルのZ方向の範囲外です。")
            r_center = (bounds[0] + bounds[1]) / 2.0
            a_center = (bounds[2] + bounds[3]) / 2.0
            rasPoint = [r_center, a_center, slice_value, 1]
            ijkToRasMatrix = vtk.vtkMatrix4x4()
            labelmapVolumeNode.GetIJKToRASMatrix(ijkToRasMatrix)
            rasToIjkMatrix = vtk.vtkMatrix4x4()#ras座標系からijk座標系に変換する翻訳機のようなものを作成
            rasToIjkMatrix.DeepCopy(ijkToRasMatrix)
            rasToIjkMatrix.Invert()
            ijkPoint = rasToIjkMatrix.MultiplyPoint(rasPoint)
            k_slice_index = int(round(ijkPoint[2]))#ras座標の値がsegmentationの何スライス目か判定
            imageData = labelmapVolumeNode.GetImageData()
            dims = imageData.GetDimensions()
            if not (0 <= k_slice_index < dims[2]):
                raise ValueError(f"エラー: Z={slice_value}mm は計算の結果、範囲外のインデックスになりました。")
            # print(f"Z={slice_value}mm は {k_slice_index} 番目のスライスに相当します。")

            # 5. 髄腔中心点と前凌点を結んだベクトルの角度を求める
            # ベクトルの成分 = (前凌のx - 髄腔のx, 前凌のy - 髄腔のy)
            tibia_vx = tibia_spline_x_points[i] - spline_x_points[i]
            tibia_vy = tibia_spline_y_points[i] - spline_y_points[i]
            # ベクトルの成分(vx, vy)から角度を計算
            # atan2は、ベクトルの向きから正しい象限の角度を返してくれる
            tibia_angle_rad = math.atan2(tibia_vy, tibia_vx)
            # ラジアンを度数法に変換して返す
            tibia_angle_deg = math.degrees(tibia_angle_rad)
            print("髄腔点と前凌の角度：",tibia_angle_deg)

            # 6. スライスを回転させる
            slice_2d = volumeArray[k_slice_index, :, :]#ここでスライス画像を取得
            # 右脚か左脚かで回転させる角度を変える
            if(tibia_type == 0):
              ROTATION_DEG = straight_line_angle_deg - tibia_angle_deg
            elif(tibia_type == 1):
              ROTATION_DEG = tibia_angle_deg - straight_line_angle_deg
            elif(tibia_type == 2):
              ROTATION_DEG = (straight_line_angle_deg - tibia_angle_deg) * 1.5
            round_ROTATION_DEG = round(ROTATION_DEG, 2)
            print("回転させる角度：",round_ROTATION_DEG)
            # 回転後の前凌の座標を求める
            dx = tibia_spline_x_points[i] - spline_x_points[i]
            dy = tibia_spline_y_points[i] - spline_y_points[i]
            tibia_angle_radian = math.radians(round_ROTATION_DEG)
            rotate_dx = dx * math.cos(tibia_angle_radian) - dy * math.sin(tibia_angle_radian)
            rotate_dy = dx * math.sin(tibia_angle_radian) + dy * math.cos(tibia_angle_radian)
            new_tibia_x_point = rotate_dx + spline_x_points[i]
            new_tibia_y_point = rotate_dy + spline_y_points[i]
            round_new_tibia_x_point = round(new_tibia_x_point, 2)
            round_new_tibia_y_point = round(new_tibia_y_point, 2)
            print("回転前の前凌座標:",tibia_spline_x_points[i],tibia_spline_y_points[i])
            print("回転後の前凌座標:",round_new_tibia_x_point,round_new_tibia_y_point)

            # 測定する場所のz座標がきたらリストに追加する
            if slice_value in coords_data['z'].values:
              print(f"値 {slice_value} は、Z座標のリストの中に存在します。")
              list = [round_new_tibia_x_point, round_new_tibia_y_point, slice_value]
              anterior_border_of_tibia.append(list)
              


            print("---------------------------")
            # 7. スライスを回転させる
            # 基準点(髄腔中心点)のRAS座標を、ラベルマップのIJK座標（ピクセル番地）に変換
            center_ras_vtk = [spline_x_points[i], spline_y_points[i], slice_value, 1]
            center_ijk_vtk = rasToIjkMatrix.MultiplyPoint(center_ras_vtk)
            # NumPyの座標系は [行, 列] (y, x) なので、中心座標の順序を合わせる
            center_yx = np.array([center_ijk_vtk[1], center_ijk_vtk[0]])
            # アフィン変換を実行（以前のロジックと同じ）
            angle_rad = np.deg2rad(round_ROTATION_DEG)
            cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
            rotation_matrix = np.array([[cos_a, -sin_a], [sin_a,  cos_a]])
            offset = center_yx - np.dot(rotation_matrix, center_yx)
            affine_slice_2d= affine_transform(
                slice_2d,
                matrix=rotation_matrix,
                offset=offset,
                output_shape=slice_2d.shape,
                mode='constant',
                cval=0
            )
            volumeArray[k_slice_index, :, :] = affine_slice_2d
            slicer.util.arrayFromVolumeModified(labelmapVolumeNode)

        # 5. 【最重要】編集済みのラベルマップを、元のセグメンテーションにインポートして上書き
        print("編集結果を元のセグメンテーションに書き戻しています...")
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, segmentationNode)

        # 6. 【重要】3D表示用の表面モデルを強制的に再生成させる
        print("3Dモデルを再生成しています...")
        segmentationNode.CreateClosedSurfaceRepresentation()

        print(f"--- 処理完了 ---")
        print(f"'{segmentationNode.GetName()}' が正常に更新されました。")


        print('----回転後の測定位置------')
        list = [round(tibia_coords_data['x'].iloc[9],2), round(tibia_coords_data['y'].iloc[9],2), round(tibia_coords_data['z'].iloc[9],2)]
        anterior_border_of_tibia.append(list)
        # ************35%〜70%部分が逆順に表示させる*****************
        anterior_border_of_tibia[1:9] = anterior_border_of_tibia[1:9][::-1]
        # ***********************************************************
        # 取り出した item を1行ずつ表示する
        for item in anterior_border_of_tibia:
          print(*item) #*により[]が表示されなくなる

    except Exception as e:
        # もし途中でエラーが起きても、変更を元に戻す
        print(f"処理中にエラーが発生しました: {e}")
        segmentationNode.EndModify(True) # Trueは変更を破棄する
    finally:
        # 7. 後片付け
        if 'labelmapVolumeNode' in locals() and labelmapVolumeNode:
            slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
        # 変更を確定
        segmentationNode.EndModify(False)
  

  # **************************************
    # sclicerのapiを使って回転させるプログラム
    # **************************************
    ROTATION_ANGLE_DEG = 180
    # 2. VTKを使って変換ルール(Transform)を作成
    transform = vtk.vtkTransform()
    # 原点を中心にZ軸周りで回転
    # 平行移動の処理を省くことで、回転の中心はデフォルトで原点(0,0,0)になる
    transform.RotateZ(ROTATION_ANGLE_DEG)
    # # 3. 作成した変換を、新しいTransformノードとしてシーンに追加
    transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "MyRotationTransform")
    transformNode.SetMatrixTransformToParent(transform.GetMatrix())
    # # 4. モデルに、このTransformノードを一時的に適用
    segmentationNode.SetAndObserveTransformNodeID(transformNode.GetID())
    # # 5. 【最重要】変換をモデルのジオメトリに「焼き付け(Harden)」て、恒久的な変更にする
    logic = slicer.vtkSlicerTransformLogic()
    logic.hardenTransform(segmentationNode)
    print("このノードを右クリックしてエクスポートしてください。")
    if(tibia_type == 0):
        print("ねじれ無しモデルを作成しました")
    elif(tibia_type == 1):
        print("ねじれ強調モデルを作成しました")

# --- 関数の実行 ---
message_box()


