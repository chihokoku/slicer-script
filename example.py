import slicer
import qt
import pandas as pd
import numpy as np
import vtk
import scipy.ndimage
from scipy.interpolate import interp1d
import straight_line_equation

# --- 設定項目 ---
TARGET_Z_MM = -160.0  # 回転させたいスライスのZ座標 (mm)
ROTATION_ANGLE_DEG = 90  # 回転角度（度）

def interpolate_points_from_excel():
    """
    Excelファイルを読み込み、2,3,4列目をX,Y,Z座標として扱い、
    Z軸方向に1mm間隔でスプライン補間した点列を生成・表示する関数。
    """
    # 1. ユーザーにExcelファイルを選択させる
    # あなたの環境に合わせて、返り値を一つの変数で受け取る
    file_path = qt.QFileDialog.getOpenFileName(None, "座標データのあるExcelファイルを選択", "", "Excel Files (*.xlsx *.xls)")

    # ファイル選択がキャンセルされた場合は処理を終了
    if not file_path:
        print("ファイルが選択されませんでした。")
        return

    print(f"選択されたファイル: {file_path}")

    # **********************************
    # segmentationの取得など
    # **********************************
    # 1. 準備：編集対象のセグメンテーションノードを取得
    segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    segmentationNode = segmentEditorWidget.mrmlSegmentEditorNode().GetSegmentationNode()
    if not segmentationNode:
        print("エラー: Segment Editorでセグメンテーションが選択されていません。")
        return
    print(f"処理対象ノード: '{segmentationNode.GetName()}'")
    # 処理を一つの塊としてSlicerに通知（アンドゥ機能のため）
    segmentationNode.StartModify()

    try:
        # 2. セグメンテーションを一時的なラベルマップボリュームに変換
        print("セグメンテーションをラベルマップに変換中...")
        # 参照ボリュームとして、シーン内の最初のボリュームを使用（より安定）
        # referenceVolume = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', 'temp_labelmap_for_rotation')
        if not slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(segmentationNode, labelmapVolumeNode, slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY):
            raise ValueError("エラー: ラベルマップへの変換に失敗しました。")
        print("セグメンテーションをラベルマップに変換しました")

        # 3. NumPy配列としてデータを取得
        volumeArray = slicer.util.arrayFromVolume(labelmapVolumeNode)
        print('NumPy配列に変換できました')


        # Excelファイルを読み込む
        df = pd.read_excel(file_path)

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


        # ***************************
        # 髄腔中心点をスプライン補間するプログラム
        # ***************************
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



        # print("z座標が入っているか？？")
        # print(new_z_points[0])


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

        # カメラを生成した点群の中心に移動させる
        slicer.modules.markups.logic().JumpSlicesToNthPointInMarkup(markupsNode.GetID(), 0)

        print("\n--- 処理完了 ---")
        print(f"結果が '{output_node_name}' という名前でシーンに追加されました。")

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
        #「直線を表示する道具」を取り出して使う
        line_node = straight_line_equation.display_line_in_slicer(crest_minZ_xyz, crest_maxZ_xyz, "前縁の3次元直線")




        # 3. z=-160というras座標系(脛骨座標系)の値がijk座標系のsegmentationの何スライス目に当たるかを計算
        bounds = [0.0] * 6
        segmentationNode.GetRASBounds(bounds)
        if not (bounds[4] <= TARGET_Z_MM <= bounds[5]):
            raise ValueError(f"エラー: Z={TARGET_Z_MM}mm はモデルのZ方向の範囲外です。")

        r_center = (bounds[0] + bounds[1]) / 2.0
        a_center = (bounds[2] + bounds[3]) / 2.0
        rasPoint = [r_center, a_center, TARGET_Z_MM, 1]

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
            raise ValueError(f"エラー: Z={TARGET_Z_MM}mm は計算の結果、範囲外のインデックスになりました。")
        print(f"Z={TARGET_Z_MM}mm は {k_slice_index} 番目のスライスに相当します。")

        # 4. スライスを回転
        print("スライスを回転中...")
        slice_2d = volumeArray[k_slice_index, :, :]
        rotated_slice_2d = scipy.ndimage.rotate(slice_2d, ROTATION_ANGLE_DEG, reshape=False, mode='constant', cval=0)
        volumeArray[k_slice_index, :, :] = rotated_slice_2d
        slicer.util.arrayFromVolumeModified(labelmapVolumeNode)

        # 5. 【最重要】編集済みのラベルマップを、元のセグメンテーションにインポートして上書き
        print("編集結果を元のセグメンテーションに書き戻しています...")
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, segmentationNode)

        # 6. 【重要】3D表示用の表面モデルを強制的に再生成させる
        print("3Dモデルを再生成しています...")
        segmentationNode.CreateClosedSurfaceRepresentation()

        print(f"--- 処理完了 ---")
        print(f"'{segmentationNode.GetName()}' が正常に更新されました。")
        print("Dataモジュールからこのノードを右クリックしてエクスポートしてください。")

        # 4.new_z_pointsの配列の長さ-1回のループを回す、かつループの初めはnew_z_points[0]からではなくnew_z_points[1]から
        for i in range(1, len(new_z_points)):
          slice_value = new_z_points[i]
          # print(f"インデックス {i} の値: {slice_value}")
          # 5. slice_valueというras座標系(脛骨座標系)の値がijk座標系のsegmentationの何スライス目に当たるかを計算
          #.   スライスの情報はk_slice_indexに格納されている
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


          # スライスの番号がわかったら、そのスライス番号の断面を取得
          ROTATION_ANGLE_DEG = 90 #回転させる角度
          slice_2d = volumeArray[k_slice_index, :, :]
          rotated_slice_2d = scipy.ndimage.rotate(slice_2d, 90, reshape=False, mode='constant', cval=0)
          volumeArray[k_slice_index, :, :] = rotated_slice_2d
          slicer.util.arrayFromVolumeModified(labelmapVolumeNode)





        print("処理が終わりました")



    except Exception as e:
        print(f"処理中にエラーが発生しました: {e}")





# --- 関数の実行 ---
interpolate_points_from_excel()
