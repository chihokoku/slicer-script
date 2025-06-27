import slicer

#            **********************************
#             segmentを取得するプログラム
#            **********************************

#Segmentationの取得
segmentationNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
segmentationNode = segmentationNodes[0]

node_id = segmentationNode.GetID()
    
print(f"ノード名: {segmentationNode.GetName()}")
print(f"ノードID: {node_id}")

import vtk
import numpy as np
import scipy.ndimage

# --- 設定項目 ---
TARGET_Z_MM = 100.0  # 回転させたいスライスのZ座標 (mm)
ROTATION_ANGLE_DEG = 90  # 回転角度（度）
# --- 設定はここまで ---

def rotate_single_slice():
    """
    現在選択中のセグメンテーションの指定したZスライスを回転させる関数
    """
    # 1. 準備：編集対象のセグメンテーションノードを取得
    segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    sourceSegmentationNode = segmentEditorWidget.mrmlSegmentEditorNode().GetSegmentationNode()

    if not sourceSegmentationNode:
        print("エラー: Segment Editorでセグメンテーションが選択されていません。")
        return

    print(f"処理対象ノード: '{sourceSegmentationNode.GetName()}'")

    # 2. セグメンテーションを一時的なラベルマップボリュームに変換
    # これにより、形状をピクセルの集まりとして確実に扱えるようになる
    print("セグメンテーションをラベルマップに変換中...")
    labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', 'temp_labelmap')
    if not slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(sourceSegmentationNode, labelmapVolumeNode):
        print("エラー: ラベルマップへの変換に失敗しました。")
        slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
        return
    print("セグメンテーションをラベルマップに変換が完了しました")
    
    # 3. 座標計算：物理座標(mm)からピクセル座標(IJK)へ
    # ラベルマップのジオメトリ情報（原点、間隔、方向）を取得
    ijkToRasMatrix = vtk.vtkMatrix4x4()
    labelmapVolumeNode.GetIJKToRASMatrix(ijkToRasMatrix)
    rasToIjkMatrix = vtk.vtkMatrix4x4()
    rasToIjkMatrix.DeepCopy(ijkToRasMatrix)
    rasToIjkMatrix.Invert()

    # Z=100mmの点が、IJK座標のどこに当たるかを計算
    # 点の座標は[R, A, S, 1]形式で指定
    rasPoint = [0, 0, TARGET_Z_MM, 1]
    ijkPoint = rasToIjkMatrix.MultiplyPoint(rasPoint)
    k_slice_index = int(round(ijkPoint[2])) # K座標がZスライスのインデックス

    imageData = labelmapVolumeNode.GetImageData()
    dims = imageData.GetDimensions()

    if not (0 <= k_slice_index < dims[2]):
        print(f"エラー: Z={TARGET_Z_MM}mm はセグメンテーションの範囲外です。")
        slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
        return

    print(f"Z={TARGET_Z_MM}mm は {k_slice_index} 番目のスライスに相当します。")

    # 4. NumPy配列としてデータにアクセスし、スライスを回転させる
    print("NumPy配列としてデータを取得し、スライスを回転中...")
    # arrayFromVolumeはメモリを共有するビューを返すので効率的
    volumeArray = slicer.util.arrayFromVolume(labelmapVolumeNode)

    # 該当スライスを2Dデータとして抽出 (SlicerのNumpy配列はK,J,Iの順)
    slice_2d = volumeArray[k_slice_index, :, :]

    # SciPyを使って2Dスライスを回転させる
    # reshape=Falseにすることで、回転後に画像のサイズが変わるのを防ぐ
    # mode='constant', cval=0 は、はみ出た部分を0（背景）で埋める設定
    rotated_slice_2d = scipy.ndimage.rotate(slice_2d, ROTATION_ANGLE_DEG, reshape=False, mode='constant', cval=0)

    # 回転させたスライスを元のボリューム配列に書き戻す
    volumeArray[k_slice_index, :, :] = rotated_slice_2d
    
    # メモリ上のデータが変更されたことをSlicerに通知
    slicer.util.arrayFromVolumeModified(labelmapVolumeNode)
    print("スライスの回転が完了しました。")

    # 5. 結果を新しいセグメンテーションとしてインポート
    print("結果を新しいセグメンテーションとしてインポート中...")
    outputSegmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", sourceSegmentationNode.GetName() + "_SliceRotated")
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, outputSegmentationNode)
    # 元のセグメンテーションの色をコピー
    segment = sourceSegmentationNode.GetSegmentation().GetNthSegment(0)
    outputSegment = outputSegmentationNode.GetSegmentation().GetNthSegment(0)
    if segment and outputSegment:
        outputSegment.SetColor(segment.GetColor())

    # 6. 後片付け
    print("一時ファイルを削除しています。")
    slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
    
    print(f"--- 処理完了 ---")
    print(f"'{outputSegmentationNode.GetName()}' が作成されました。")

# --- 関数の実行 ---
rotate_single_slice()