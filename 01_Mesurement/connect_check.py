#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
connect_check.py

Windows / Mac 両対応の USB & シリアル機器検出スクリプト
"""

import subprocess
import sys
import platform

try:
    from serial.tools import list_ports
except ImportError:
    print("Error: pyserial がインストールされていません。")
    print("  $ pip install pyserial")
    sys.exit(1)

def list_usb_devices():
    """OSごとにUSB機器を表示"""
    os_type = platform.system()
    print("\n=== USB Devices ===\n")
    if os_type == "Darwin":
        # macOS
        try:
            output = subprocess.check_output(
                ["system_profiler", "SPUSBDataType"],
                text=True,
                stderr=subprocess.STDOUT
            )
            print(output)
        except Exception as e:
            print("system_profiler の実行中にエラーが発生しました:")
            print(e)
    elif os_type == "Windows":
        try:
            # Windows用：WMICでUSBデバイス取得
            output = subprocess.check_output(
                ["wmic", "path", "Win32_USBControllerDevice", "get", "Dependent"],
                text=True,
                stderr=subprocess.STDOUT
            )
            print(output)
        except Exception as e:
            print("wmic の実行中にエラーが発生しました:")
            print(e)
    else:
        print("このOSはサポートされていません。")

def list_serial_ports():
    """pyserial を使ってシリアルポートを一覧表示"""
    print("\n=== Serial Ports ===\n")
    ports = list_ports.comports()
    if not ports:
        print("シリアルポートが見つかりませんでした。")
    else:
        for port in ports:
            print(f"■ ポート名: {port.device}")
            print(f"  Description:  {port.description}")
            print(f"  HWID:         {port.hwid}")
            if hasattr(port, "manufacturer") and port.manufacturer:
                print(f"  Manufacturer: {port.manufacturer}")
            if hasattr(port, "product") and port.product:
                print(f"  Product:      {port.product}")
            if hasattr(port, "vid") and port.vid is not None and hasattr(port, "pid") and port.pid is not None:
                print(f"  VID:PID:      {hex(port.vid)}:{hex(port.pid)}")
            print()

def main():
    print("Device Detector for Windows / macOS\n")
    list_usb_devices()
    list_serial_ports()

if __name__ == "__main__":
    main()
