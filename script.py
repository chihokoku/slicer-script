import slicer

#            **********************************
#             segmentを取得するプログラム
#            **********************************

#Segmentationの取得
# segmentationNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
# segmentationNode = segmentationNodes[0]

# Segment Editorモジュールのウィジェット（UI部分）を取得
segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor

# Segment Editorで現在選択されているセグメンテーションノードを取得
segmentationNode = segmentEditorWidget.mrmlSegmentEditorNode().GetSegmentationNode()

if segmentationNode:
  print(f"現在Segment Editorで選択中のノード '{segmentationNode.GetName()}' を取得しました。")
else:
  print("Segment Editorでノードが選択されていません。")

if segmentationNode:
  # マスター表現の名前を取得（"ClosedSurface" または "BinaryLabelmap" などが返る）
  masterRepName = segmentationNode.GetSegmentation().GetMasterRepresentationName()
  print(f"現在のマスター表現: {masterRepName}")

  # すべてのセグメントIDを取得
  segmentIDs = vtk.vtkStringArray()
  segmentationNode.GetSegmentation().GetSegmentIDs(segmentIDs)
  
  if segmentIDs.GetNumberOfValues() > 0:
    # 最初のセグメントのIDを取得
    firstSegmentID = segmentIDs.GetValue(0)

    # マスター表現がポリゴンモデル（ClosedSurface）の場合、そのポリゴンデータを取得
    if masterRepName == slicer.vtkSegmentation.CLOSED_SURFACE:
      # vtkPolyDataオブジェクトを取得
      polyData = vtk.vtkPolyData()
      segmentationNode.GetSegmentClosedSurfaceRepresentation(firstSegmentID, polyData)
      
      if polyData:
        print(f"編集対象のポリゴンデータを取得しました。")
        print(f"  - セグメントID: {firstSegmentID}")
        print(f"  - 頂点数: {polyData.GetNumberOfPoints()}")
        print(f"  - ポリゴン数: {polyData.GetNumberOfCells()}")

# 　　　　　　 **********************************
#             sceneに点を表示させるプログラム
#            **********************************
# Markupsノードの作成
# markupsNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "MyPoints")
# 任意の座標に点を追加（例：x=10, y=20, z=30）
# markupsNode.AddControlPoint([10, 20, 30])
# 必要なら表示設定を調整（サイズ、ラベルなど）
# markupsNode.GetDisplayNode().SetTextScale(2)  # ラベルの大きさ
# markupsNode.GetDisplayNode().SetGlyphScale(1) # 点の大きさ