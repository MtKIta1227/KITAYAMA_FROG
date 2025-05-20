#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
device_detector.py

MacBook に接続されている USB 機器とシリアルポートを検出して表示するスクリプト
"""

import subprocess
import sys

try:
    from serial.tools import list_ports
except ImportError:
    print("Error: pyserial がインストールされていません。")
    print("  $ pip install pyserial")
    sys.exit(1)


def list_usb_devices():
    """system_profiler を呼び出して USB 機器を表示"""
    print("\n=== USB Devices ===\n")
    try:
        output = subprocess.check_output(
            ["system_profiler", "SPUSBDataType"],
            text=True,  # Python 3.7+
            stderr=subprocess.STDOUT
        )
        print(output)
    except subprocess.CalledProcessError as e:
        print("system_profiler の実行中にエラーが発生しました:")
        print(e.output)


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
            if port.manufacturer:
                print(f"  Manufacturer: {port.manufacturer}")
            if port.product:
                print(f"  Product:      {port.product}")
            if port.vid is not None and port.pid is not None:
                print(f"  VID:PID:      {hex(port.vid)}:{hex(port.pid)}")
            print()


def main():
    print("Device Detector for macOS\n")
    list_usb_devices()
    list_serial_ports()


if __name__ == "__main__":
    main()
