import slicer
import numpy as np

def calculate_line_parameters(point_p0, point_p1):
    """
    2つの点から、直線の方程式の「基点」と「方向ベクトル」を計算して返す。
        point_p0 (np.array): 直線の基点となる点 (例: Z最小点)
        point_p1 (np.array): 直線が通過するもう一つの点 (例: Z最大点)
    """
    # 方向ベクトル v = P1 - P0 を計算
    direction_vector = point_p1 - point_p0

    print("\n--- 直線の方程式---")
    print(f"基点 P0: {point_p0}")
    print(f"方向ベクトル v: {direction_vector}")
    print("直線上の任意の点 r は、パラメータ t を使って r = P0 + t * v と表せる")
    return point_p0, direction_vector

def display_line_in_slicer(point_p0, point_p1, line_name="Line"):
    """
    2点間に直線をMarkupsLineとして表示する。
    
    Args:
        point_p0 (np.array): 直線の始点
        point_p1 (np.array): 直線の終点
        line_name (str): 作成するノードの名前
 
    Returns:
        vtkMRMLMarkupsLineNode: 作成されたMarkupsLineノード
    """
    line_node_name = slicer.mrmlScene.GenerateUniqueName(line_name)
    lineNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", line_node_name)
    
    # 線の表示設定
    displayNode = lineNode.GetDisplayNode()
    displayNode.SetSelectedColor(1, 1, 0) # 黄色に設定
    displayNode.SetLineThickness(0.5)

    # 2つの制御点を追加して直線を定義
    lineNode.AddControlPoint(point_p0)
    lineNode.AddControlPoint(point_p1)

    return lineNode

# find_xy_at_z(ここはz座標,base_point, direction_vec )←これで任意のz座標における直線上の値が求められる
# 直線のパラメータから、特定のzにおけるx,y座標を計算する
def find_xy_at_z(target_z, p0, v):
    p0_x, p0_y, p0_z = p0
    v_x, v_y, v_z = v

    if abs(v_z) < 1e-9:
        return None # 計算不能

    t = (target_z - p0_z) / v_z
    x = p0_x + t * v_x
    y = p0_y + t * v_y
    
    return (x, y)