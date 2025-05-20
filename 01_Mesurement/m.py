# -*- coding: utf-8 -*-
"""
FROG_Measure_GUI (ver.2.1)

2025-05-20
SURUGA SEIKI DS102 を含むデバイス自動検出ロジックを追加し、
VID/PID → Manufacturer → Description の優先度でシリアルポートを決定します。
他のロジックは ver.2.0 と同一です。
"""

import sys
import os
import datetime
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from scipy.optimize import curve_fit
import serial
import serial.tools.list_ports

try:
    import seabreeze.spectrometers as sb
    seabreeze_imported = True
except Exception:
    seabreeze_imported = False


def find_device_port(device_name: str | None = None, manufacturer: str | None = None, vid: int | None = None, pid: int | None = None):
    """Detect the serial port corresponding to a USB device.

    Priority order:
        (1) Exact match on VID & PID
        (2) Substring match on *manufacturer*
        (3) Substring match on *description*
    """
    ports = serial.tools.list_ports.comports()

    # 1. VID/PID
    if vid is not None and pid is not None:
        for p in ports:
            if p.vid == vid and p.pid == pid:
                return p.device

    # 2. Manufacturer substring
    if manufacturer:
        m_lower = manufacturer.lower()
        for p in ports:
            if p.manufacturer and m_lower in p.manufacturer.lower():
                return p.device

    # 3. Description substring
    if device_name:
        d_lower = device_name.lower()
        for p in ports:
            if p.description and d_lower in p.description.lower():
                return p.device

    return None


def log_to_file(logpath, message):
    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    with open(logpath, "a", encoding="utf-8") as lf:
        lf.write(f"[{now}] {message}\n")

# 以降は ver.2.0 の既存コードをそのまま保持 (GUI クラス定義など)
# ...

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # 既存の初期化処理 ...

    def check_usb4000(self):
        if not seabreeze_imported:
            self.log("seabreezeライブラリがインストールされていません")
            return
        try:
            devices = sb.list_devices()
            if devices:
                self.spectrometer = sb.Spectrometer(devices[0])
                self.status_label.setText("USB4000 接続済み")
                self.log("USB4000 に接続しました")
            else:
                self.status_label.setText("USB4000 未検出")
                self.log("USB4000 が見つかりません")
        except Exception as e:
            self.log(f"USB4000 エラー: {e}")

    def check_ds102(self):
        """SURUGA SEIKI DS102 シリアルポートを自動検出して接続します"""
        vid = 0x0DFD
        pid = 0x0002
        port = find_device_port(device_name="DS102", manufacturer="SURUGA SEIKI", vid=vid, pid=pid)
        if port:
            try:
                self.ser = serial.Serial(port, baudrate=9600, timeout=1)
                self.status_label.setText(f"DS102 接続: {port}")
                self.log(f"DS102 ({port}) に接続しました")
                self.update_position_label()
                return
            except Exception as e:
                self.log(f"DS102 シリアル接続失敗: {e}")
        self.status_label.setText("DS102 未検出")
        self.log("DS102 が見つかりません")

    # --- 以下、ver.2.0 から変更のないメソッドが続きます ---

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
