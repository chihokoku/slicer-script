# # Markupsノードの作成Add commentMore actions
# markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "MyPoints")
# # 任意の座標に点を追加（例：x=10, y=20, z=30）
# markupsNode.AddControlPoint([50, 50, -10])
# # 必要なら表示設定を調整（サイズ、ラベルなど）
# markupsNode.GetDisplayNode().SetTextScale(2)  # ラベルの大きさ
# markupsNode.GetDisplayNode().SetGlyphScale(1) # 点の大きさ


# import slicer
# import vtk
# import numpy as np
# import scipy.ndimage

# # --- 設定項目 ---
# TARGET_Z_MM = -160.0  # 回転させたいスライスのZ座標 (mm)
# ROTATION_ANGLE_DEG = 90  # 回転角度（度）
# # --- 設定はここまで ---

# def rotate_slice_in_place():
#     # 1. 準備：編集対象のセグメンテーションノードを取得
#     segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
#     segmentationNode = segmentEditorWidget.mrmlSegmentEditorNode().GetSegmentationNode()

#     if not segmentationNode:
#         print("エラー: Segment Editorでセグメンテーションが選択されていません。")
#         return
        
#     print(f"処理対象ノード: '{segmentationNode.GetName()}'")
    
#     # 処理を一つの塊としてSlicerに通知（アンドゥ機能のため）
#     segmentationNode.StartModify()

#     try:
#         # 2. セグメンテーションを一時的なラベルマップボリュームに変換
#         print("セグメンテーションをラベルマップに変換中...")
#         # 参照ボリュームとして、シーン内の最初のボリュームを使用（より安定）
#         referenceVolume = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
#         labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', 'temp_labelmap_for_rotation')
#         if not slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(segmentationNode, labelmapVolumeNode, slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY):
#             raise ValueError("エラー: ラベルマップへの変換に失敗しました。")
        
#         # 3. z=-160というras座標系(脛骨座標系)の値がijk座標系のsegmentationの何スライス目に当たるかを計算
#         bounds = [0.0] * 6
#         segmentationNode.GetRASBounds(bounds)
#         if not (bounds[4] <= TARGET_Z_MM <= bounds[5]):
#             raise ValueError(f"エラー: Z={TARGET_Z_MM}mm はモデルのZ方向の範囲外です。")
            
#         r_center = (bounds[0] + bounds[1]) / 2.0
#         a_center = (bounds[2] + bounds[3]) / 2.0
#         rasPoint = [r_center, a_center, TARGET_Z_MM, 1]
        
#         ijkToRasMatrix = vtk.vtkMatrix4x4()
#         labelmapVolumeNode.GetIJKToRASMatrix(ijkToRasMatrix)
#         rasToIjkMatrix = vtk.vtkMatrix4x4()#ras座標系からijk座標系に変換する翻訳機のようなものを作成
#         rasToIjkMatrix.DeepCopy(ijkToRasMatrix)
#         rasToIjkMatrix.Invert()
        
#         ijkPoint = rasToIjkMatrix.MultiplyPoint(rasPoint)
#         k_slice_index = int(round(ijkPoint[2]))#ras座標の値がsegmentationの何スライス目か判定
        
#         imageData = labelmapVolumeNode.GetImageData()
#         dims = imageData.GetDimensions()
#         if not (0 <= k_slice_index < dims[2]):
#             raise ValueError(f"エラー: Z={TARGET_Z_MM}mm は計算の結果、範囲外のインデックスになりました。")
#         print(f"Z={TARGET_Z_MM}mm は {k_slice_index} 番目のスライスに相当します。")

#         # 4. NumPy配列としてデータを取得し、スライスを回転
#         print("スライスを回転中...")
#         volumeArray = slicer.util.arrayFromVolume(labelmapVolumeNode)
#         slice_2d = volumeArray[k_slice_index, :, :]
#         rotated_slice_2d = scipy.ndimage.rotate(slice_2d, ROTATION_ANGLE_DEG, reshape=False, mode='constant', cval=0)
#         volumeArray[k_slice_index, :, :] = rotated_slice_2d
#         slicer.util.arrayFromVolumeModified(labelmapVolumeNode)

#         # 5. 【最重要】編集済みのラベルマップを、元のセグメンテーションにインポートして上書き
#         print("編集結果を元のセグメンテーションに書き戻しています...")
#         slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, segmentationNode)

#         # 6. 【重要】3D表示用の表面モデルを強制的に再生成させる
#         print("3Dモデルを再生成しています...")
#         segmentationNode.CreateClosedSurfaceRepresentation()

#         print(f"--- 処理完了 ---")
#         print(f"'{segmentationNode.GetName()}' が正常に更新されました。")
#         print("Dataモジュールからこのノードを右クリックしてエクスポートしてください。")

#     except Exception as e:
#         # もし途中でエラーが起きても、変更を元に戻す
#         print(f"処理中にエラーが発生しました: {e}")
#         segmentationNode.EndModify(True) # Trueは変更を破棄する
#     finally:
#         # 7. 後片付け
#         if 'labelmapVolumeNode' in locals() and labelmapVolumeNode:
#             slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
#         # 変更を確定
#         segmentationNode.EndModify(False)

# # --- 関数の実行 ---
# rotate_slice_in_place()



import slicer
import qt
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

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

    try:
        # Excelファイルを読み込む
        df = pd.read_excel(file_path)

        # 2. 2,3,4列目のデータをX,Y,Z座標として取得
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

        # 【重要】スプライン補間を行う前に、必ずZ座標でデータを並び替える
        sorted_coords = coords_data.sort_values(by='z').to_numpy()
        
        # NumPy配列に変換
        x_coords = sorted_coords[:, 0]
        y_coords = sorted_coords[:, 1]
        z_coords = sorted_coords[:, 2]

        print(f"{len(z_coords)}個の有効な3D座標点を取得しました。")

        # 3. 3次スプライン補間器を作成
        # Z座標を基準に、XとYがどう変化するかをそれぞれ補間する
        # fill_value="extrapolate"は、範囲外も少しだけ計算してくれるオプション
        f_x = interp1d(z_coords, x_coords, kind='cubic', fill_value="extrapolate")
        f_y = interp1d(z_coords, y_coords, kind='cubic', fill_value="extrapolate")

        # 4. Z軸に対して1mm間隔の新しい点列を求める
        # 元のデータの最小Z座標と最大Z座標を取得
        z_min = z_coords.min()
        z_max = z_coords.max()
        
        # z_minからz_maxまで、1mm間隔のZ座標のリストを生成
        new_z_points = np.arange(z_min, z_max, 1.0)
        
        # 補間器を使って、新しいZ座標に対応するX, Y座標を計算
        new_x_points = f_x(new_z_points)
        new_y_points = f_y(new_z_points)

        print(f"Z軸方向に1mm間隔で、{len(new_z_points)}個の補間点を生成しました。")

        # 5. 結果をSlicerのMarkupsノードとして表示
        output_node_name = slicer.mrmlScene.GenerateUniqueName("Interpolated_Points")
        markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", output_node_name)
        
        # 点の表示設定を調整（点を小さく、ラベルは非表示に）
        displayNode = markupsNode.GetDisplayNode()
        displayNode.SetGlyphScale(0.5)
        displayNode.SetTextScale(0)

        # 生成した点群を一つずつ追加
        for i in range(len(new_z_points)):
            markupsNode.AddControlPoint([new_x_points[i], new_y_points[i], new_z_points[i]])
        
        # カメラを生成した点群の中心に移動させる
        slicer.modules.markups.logic().JumpSlicesToNthPointInMarkup(markupsNode.GetID(), 0)

        print(f"--- 処理完了 ---")
        print(f"結果が '{output_node_name}' という名前でシーンに追加されました。")


    except Exception as e:
        print(f"処理中にエラーが発生しました: {e}")


# --- 関数の実行 ---
interpolate_points_from_excel()