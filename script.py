# import slicer


# #Segmentationの取得
# segmentationNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
# segmentationNode = segmentationNodes[0]

# node_id = segmentationNode.GetID()
    
# # print(f"ノード名: {segmentationNode.GetName()}")
# # print(f"ノードID: {node_id}")

# import vtk
# import numpy as np
# import scipy.ndimage

# # --- 設定項目 ---
# TARGET_Z_MM = -160.0  # 回転させたいスライスのZ座標 (mm)
# ROTATION_ANGLE_DEG = 90  # 回転角度（度）
# # --- 設定はここまで ---

# def rotate_single_slice():
#     # 1. 準備：編集対象のセグメンテーションノード(vtkMRMLSegmentationNode)を取得
#     # ※vtkMRMLSegmentationNodeは書かれていないが情報は取得されている
#     segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
#     sourceSegmentationNode = segmentEditorWidget.mrmlSegmentEditorNode().GetSegmentationNode()

#     if not sourceSegmentationNode:
#         print("エラー: Segment Editorでセグメンテーションが選択されていません。")
#         return

#     print(f"処理対象ノード: '{sourceSegmentationNode.GetName()}'")

#     # 2. セグメンテーションを一時的なラベルマップボリュームに変換
#     # これにより、形状をピクセルの集まりとして確実に扱えるようになる
#     print("セグメンテーションをラベルマップに変換中...")
#     labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', 'temp_labelmap')
#     if not slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(sourceSegmentationNode, labelmapVolumeNode):
#         print("エラー: ラベルマップへの変換に失敗しました。")
#         slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
#         return
#     print("セグメンテーションをラベルマップに変換が完了しました")
    
#     # 3. 座標計算：物理座標(mm)からピクセル座標(IJK)へAdd commentMore actions
#     # ラベルマップのジオメトリ情報（原点、間隔、方向）を取得
#     ijkToRasMatrix = vtk.vtkMatrix4x4()
#     labelmapVolumeNode.GetIJKToRASMatrix(ijkToRasMatrix)
#     rasToIjkMatrix = vtk.vtkMatrix4x4()
#     rasToIjkMatrix.DeepCopy(ijkToRasMatrix)
#     rasToIjkMatrix.Invert()

#     # Z=-160mmの点が、IJK座標のどこに当たるかを計算
#     # 点の座標は[R, A, S, 1]形式で指定
#     rasPoint = [0, 0, TARGET_Z_MM, 1]
#     ijkPoint = rasToIjkMatrix.MultiplyPoint(rasPoint)
#     k_slice_index = int(round(ijkPoint[2])) # K座標がZスライスのインデックス

#     imageData = labelmapVolumeNode.GetImageData()
#     dims = imageData.GetDimensions()

#     if not (0 <= k_slice_index < dims[2]):
#         print(f"エラー: Z={TARGET_Z_MM}mm はセグメンテーションの範囲外です。")
#         slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
#         return

#     print(f"Z={TARGET_Z_MM}mm は {k_slice_index} 番目のスライスに相当します。")

#     # 4. NumPy配列としてデータにアクセスし、スライスを回転させる
#     print("NumPy配列としてデータを取得し、スライスを回転中...")
#     # arrayFromVolumeはメモリを共有するビューを返すので効率的
#     volumeArray = slicer.util.arrayFromVolume(labelmapVolumeNode)

#     # 該当スライスを2Dデータとして抽出 (SlicerのNumpy配列はK,J,Iの順)
#     slice_2d = volumeArray[k_slice_index, :, :]

#     # SciPyを使って2Dスライスを回転させる
#     # reshape=Falseにすることで、回転後に画像のサイズが変わるのを防ぐ
#     # mode='constant', cval=0 は、はみ出た部分を0（背景）で埋める設定
#     rotated_slice_2d = scipy.ndimage.rotate(slice_2d, ROTATION_ANGLE_DEG, reshape=False, mode='constant', cval=0)

#     # 回転させたスライスを元のボリューム配列に書き戻す
#     volumeArray[k_slice_index, :, :] = rotated_slice_2d
    
#     # メモリ上のデータが変更されたことをSlicerに通知
#     slicer.util.arrayFromVolumeModified(labelmapVolumeNode)
#     print("スライスの回転が完了しました。")

#     # 5. 結果を新しいセグメンテーションとしてインポート
#     print("結果を新しいセグメンテーションとしてインポート中...")
#     outputSegmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", sourceSegmentationNode.GetName() + "_SliceRotated")
#     slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, outputSegmentationNode)
#     # 元のセグメンテーションの色をコピー
#     segment = sourceSegmentationNode.GetSegmentation().GetNthSegment(0)
#     outputSegment = outputSegmentationNode.GetSegmentation().GetNthSegment(0)
#     if segment and outputSegment:
#         outputSegment.SetColor(segment.GetColor())
    
#     # 変更されたラベルマップから、3D表示用の表面モデルを再生成する
#     print("3Dモデルを再生成しています...")
#     outputSegmentationNode.CreateClosedSurfaceRepresentation()

#     # 6. 後片付け
#     print("一時ファイルを削除しています。")
#     slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
    
#     print(f"--- 処理完了 ---")
#     print(f"'{outputSegmentationNode.GetName()}' が作成されました。")

    

#     # 7. 最終的な形状を、エクスポート用の単純なモデルノードに変換
#     print("最終的な形状をエクスポート用のモデルに変換しています...")
    
#     # 7a. 編集済みのセグメンテーションデータオブジェクトとセグメントIDを取得
#     segmentation = outputSegmentationNode.GetSegmentation()
#     segmentID = segmentation.GetNthSegmentID(0)
    
#     # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ ここからが最終修正点 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
#     # 7b. 表示用のポリゴンデータ(vtkPolyData)を直接取得
#     #    表現名は、Slicerが内部で使う単純な文字列 "Closed surface" を直接使用します
#     representationName = "Closed surface"
    
#     # 正しい関数 'GetSegmentRepresentation' を、2つの引数で呼び出し、
#     # 戻り値としてポリゴンデータを受け取ります。
#     polyData = segmentation.GetSegmentRepresentation(segmentID, representationName)
#     # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ ここまでが最終修正点 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    
#     # 7c. 新しいモデルノードを作成し、取得したポリゴンデータをセットする
#     #    取得したpolyDataがNoneでないことを確認
#     if polyData:
#         finalModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", outputSegmentationNode.GetName() + "_ExportModel")
#         finalModelNode.SetAndObservePolyData(polyData)
        
#         # 7d. 表示色を合わせる
#         displayNode = sourceSegmentationNode.GetDisplayNode()
#         # 元のセグメンテーションからセグメントオブジェクトを取得
#         sourceSegment = sourceSegmentationNode.GetSegmentation().GetSegment(segmentID)
#         if displayNode and sourceSegment:
#             color = sourceSegment.GetColor()
#             finalModelNode.CreateDefaultDisplayNodes()
#             finalModelNode.GetDisplayNode().SetColor(color)

#         print(f"エクスポート用のモデル '{finalModelNode.GetName()}' が作成されました。")
#         print("Dataモジュールからこのモデルを右クリックしてエクスポートしてください。")
#     else:
#         print(f"エラー: '{representationName}' 表現からポリゴンデータを取得できませんでした。")
    
#     print(f"--- 処理完了 ---")
#     print(f"'{outputSegmentationNode.GetName()}' が作成されました。")

# rotate_single_slice()


# # Markupsノードの作成Add commentMore actions
# markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "MyPoints")
# # 任意の座標に点を追加（例：x=10, y=20, z=30）
# markupsNode.AddControlPoint([50, 50, -10])
# # 必要なら表示設定を調整（サイズ、ラベルなど）
# markupsNode.GetDisplayNode().SetTextScale(2)  # ラベルの大きさ
# markupsNode.GetDisplayNode().SetGlyphScale(1) # 点の大きさ


import slicer
import vtk
import numpy as np
import scipy.ndimage

# --- 設定項目 ---
TARGET_Z_MM = -160.0  # 回転させたいスライスのZ座標 (mm)
ROTATION_ANGLE_DEG = 90  # 回転角度（度）
# --- 設定はここまで ---

def rotate_slice_in_place():
    """
    現在選択中のセグメンテーションを、直接その場で編集し、
    指定したZスライスを回転させる。
    """
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
        referenceVolume = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', 'temp_labelmap_for_rotation')
        if not slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(segmentationNode, labelmapVolumeNode, slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY):
            raise ValueError("エラー: ラベルマップへの変換に失敗しました。")
        
        # 3. 座標計算 (モデル自身の位置を基準に)
        bounds = [0.0] * 6
        segmentationNode.GetRASBounds(bounds)
        if not (bounds[4] <= TARGET_Z_MM <= bounds[5]):
            raise ValueError(f"エラー: Z={TARGET_Z_MM}mm はモデルのZ方向の範囲外です。")
            
        r_center = (bounds[0] + bounds[1]) / 2.0
        a_center = (bounds[2] + bounds[3]) / 2.0
        rasPoint = [r_center, a_center, TARGET_Z_MM, 1]
        
        ijkToRasMatrix = vtk.vtkMatrix4x4()
        labelmapVolumeNode.GetIJKToRASMatrix(ijkToRasMatrix)
        rasToIjkMatrix = vtk.vtkMatrix4x4()
        rasToIjkMatrix.DeepCopy(ijkToRasMatrix)
        rasToIjkMatrix.Invert()
        
        ijkPoint = rasToIjkMatrix.MultiplyPoint(rasPoint)
        k_slice_index = int(round(ijkPoint[2]))
        
        imageData = labelmapVolumeNode.GetImageData()
        dims = imageData.GetDimensions()
        if not (0 <= k_slice_index < dims[2]):
            raise ValueError(f"エラー: Z={TARGET_Z_MM}mm は計算の結果、範囲外のインデックスになりました。")
        print(f"Z={TARGET_Z_MM}mm は {k_slice_index} 番目のスライスに相当します。")

        # 4. NumPy配列としてデータを取得し、スライスを回転
        print("スライスを回転中...")
        volumeArray = slicer.util.arrayFromVolume(labelmapVolumeNode)
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

# --- 関数の実行 ---
rotate_slice_in_place()