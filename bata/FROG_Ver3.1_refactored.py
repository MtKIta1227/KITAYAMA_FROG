# -*- coding:utf-8 -*-
'''
Created on 2023/11/08
@author: Kitayama Daisuke
Improved & refactored 2025/05/15
'''

import time, serial, os, datetime
import serial.tools.list_ports
import pyvisa as visa
import seabreeze.spectrometers as sb
import matplotlib.pyplot as plt
from tqdm import tqdm

# ログファイル設定
current_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(current_dir, "log")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_FROG.log")
log_path = os.path.join(log_dir, log_file)

def log(message):
    with open(log_path, "a", encoding='utf-8') as lf:
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        lf.write(f"[{timestamp}] {message}\n")

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def calculate_dt(step_size):
    c = 299792458  # 光速 (m/s)
    dt = 2 * step_size * 1e-6 / c * 1e15  # /fs
    return dt

class StageController:
    def __init__(self, device_name="SURUGA SEIKI DS102 USB Serial Port"):
        self.device_name = device_name
        self.com_port = self.find_device_port()
        self.ser = None

    def find_device_port(self):
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in ports:
            if self.device_name in desc:
                return port
        return None

    def open(self):
        if self.com_port is None:
            raise RuntimeError(f"Device port for '{self.device_name}' not found.")
        try:
            self.ser = serial.Serial(self.com_port, baudrate=9600, timeout=1)
            return True
        except Exception as e:
            log(f"Error opening serial port: {e}")
            return False

    def send_command(self, command):
        self.ser.write(command.encode('utf-8'))

    def readline(self):
        return self.ser.readline().decode('utf-8').strip()

    def move_stage(self, fspeed, pulses, direction):
        self.send_command(f"AXIs1:Fspeed0 {fspeed}\r")
        self.send_command(f"AXIs1:PULS {pulses}:GO {direction}\r")
        print(" Moving stage...")
        while True:
            self.send_command("AXIs1:MOTION?\r")
            response = self.readline()
            if "0" in response:
                print(" Paused")
                break

    def check_current_position(self):
        self.send_command("AXIs1:POS?\r")
        response = self.readline()
        print(f"Current Position: {response}")
        log(f"Current Position: {response}")
        return int(response)

    def set_current_position_as_origin(self):
        self.send_command("AXIs1:POS 0\r")
        print(">> Set current position to 'ORIGIN POINT'")
        self.check_current_position()
        log("Set current position to 'ORIGIN POINT'")

    def set_home_position(self, pos):
        self.send_command(f"AXIs1:HOMEP {pos}\r")
        log(f"Set HOME POSITION: {pos}")

    def get_home_position(self):
        self.send_command("AXIs1:HOMEPosition?\r")
        response = self.readline()
        return int(response)

    def get_origin_position(self):
        self.send_command("AXIs1:ORG?\r")
        response = self.readline()
        return int(response)

    def close(self):
        if self.ser:
            self.ser.close()

class SpectrometerController:
    def __init__(self, target_model_name='USB4000'):
        self.target_model_name = target_model_name
        self.spectrometer = None

    def connect(self):
        devices = sb.list_devices()
        for device in devices:
            spec = sb.Spectrometer(device)
            if spec.model == self.target_model_name:
                self.spectrometer = spec
                return True
        return False

    def set_integration_time(self, integration_time_ms):
        self.spectrometer.integration_time_micros(integration_time_ms * 1000)

    def get_spectrum(self):
        return self.spectrometer.spectrum()

    def get_wavelengths(self):
        return self.spectrometer.wavelengths()

    def get_intensities(self):
        return self.spectrometer.intensities()

    def close(self):
        if self.spectrometer:
            self.spectrometer.close()

def main():
    print("╔════════════════════════════════════════════╗")
    print("║    ~ FROG Measurement Program ~  ver 3.0   ║")
    print("╚════════════════════════════════════════════╝")
    log("Program start")

    # Spectrometer接続
    spectro = SpectrometerController()
    while not spectro.connect():
        print("USB4000 not found. Retrying in 5 seconds...")
        time.sleep(5)
    print("Connected to spectrometer USB4000.")
    log("Connected to spectrometer USB4000.")

    # DS102接続
    stage = StageController()
    if not stage.open():
        print(f">> Error: {stage.device_name} could not find the COM port to which it is connected.")
        return
    print(f"Connect to {stage.device_name} by [ {stage.com_port} ].")
    log(f"Connected to {stage.device_name} by [ {stage.com_port} ].")

    # 初期化処理
    print("\n#####################################################################")
    print("DS102 Initialization ~Stage Position Adjustment~")
    print("#####################################################################")
    log("DS102 Initialization ~Stage Position Adjustment~")
    user_input = input(">> Do you want to initialise? (yes/pass) : ")

    if user_input.lower() != 'pass':
        print("Initializing DS102...")
        stage.send_command("AXIs1:DRiverDIVision 0\r")
        print("Set DRiverDIVision to [ Full ]")
        stage.send_command("MEMorySWitch0 3\r")
        print("Set MEMorySWitch0 to [Type 3]")
        # ステージをフルフロント
        print("\n>> Move stage to [ full front ]")
        stage.move_stage(fspeed=5000, pulses=50000, direction=0)
        stage.check_current_position()
        # ステージをフルバック
        print("\n>> Move stage to [ full back ]")
        stage.move_stage(fspeed=5000, pulses=50000, direction=1)
        stage.check_current_position()

    # インテグレーションタイム設定
    print("\n########################################################")
    print("Set Integration time")
    print("########################################################")
    integration_time_ms = int(input(">> Integration time (/ms): "))
    log(f"Set Integration Time: {integration_time_ms} ms")

    # サンプリングポイント設定
    print("\n>> Set the STEP SIZE (pulse)")
    default_step_size = 1
    step_size_input = input(f"STEP SIZE (default 1 pulse [6.67 fs]): ")
    step_size = int(step_size_input) if step_size_input.strip() else default_step_size
    dt = calculate_dt(step_size)
    print(f"Measurement interval is '{dt:.2f} fs'")

    # 測定範囲設定
    print("\n>> Set the measurement range (pulse)")
    range_input = input("Input measurement range [/pulse] (default 75 pulse [500 fs]): ")
    measurement_range = int(range_input) if range_input.strip() else 75
    loop_num = measurement_range // step_size
    print(f"Measurement range is '{measurement_range * dt:.2f} fs'")

    # 現在位置をホームポジションに設定
    print("\n>> Setting current position as HOME POINT")
    current_pos = stage.check_current_position()
    stage.set_home_position(current_pos)
    home_position = stage.get_home_position()
    print(f"HOME POSITION: {home_position}")

    # origin位置も確認
    origin_position = stage.get_origin_position()
    print(f"ORIGINAL POINT: {origin_position}")

    # データ保存ディレクトリ準備
    data_dir = os.path.join(current_dir, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    file_name = os.path.join(data_dir, f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_FROG.txt")

    # 測定スタート
    print('\n###############################################')
    print('FROG Measurement')
    print('###############################################')
    print(f"Step size: {step_size}")
    print(f"Measurement interval: {dt:.2f} fs")
    print(f"Measurement range is '{measurement_range * dt:.2f} fs'")
    print(f"Integration time: {integration_time_ms} ms")
    print(f"Start point: {home_position}")
    print(f"End point: {home_position + measurement_range}")
    log("Measurement started")

    start = time.time()
    bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'

    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\t")
        x = spectro.get_wavelengths()[1002:]
        for x_value in x:
            f.write(str(x_value) + "\t")
        f.write("\n")
        for i in tqdm(range(int(loop_num)), bar_format=bar_format, ncols=75):
            spectro.set_integration_time(integration_time_ms)
            time.sleep(integration_time_ms/1000 + 1)
            elapsed_time = time.time() - start
            remaining_time = (elapsed_time / (i + 1)) * (loop_num - i - 1)
            remaining_time = divmod(remaining_time, 60)
            remaining_time = f"{int(remaining_time[0]):02d}:{int(remaining_time[1]):02d}"
            print(f"Remaining time: {remaining_time}")
            y = spectro.get_intensities()[1002:]
            delay = int(i) * dt
            f.write(str(delay) + "\t")
            for y_value in y:
                f.write(str(y_value) + "\t")
            f.write("\n")
            # ステージ移動
            stage.move_stage(fspeed=1000, pulses=step_size, direction=0)
            log(f"Measuring at {i * step_size} pulse")
            log(f"Move stage {step_size} pulse")
            stage.check_current_position()

    elapsed_time = time.time() - start
    print("-----------------------------------------------")
    print("\nMeasurement completed !!.")
    print("-----------------------------------------------")
    print(f"Elapsed time: {format_time(elapsed_time)}")
    print(f"Data saved as '{file_name}'")
    log("Measurement completed !!.")
    log(f"Elapsed time: {format_time(elapsed_time)}")
    log(f"Data saved as '{file_name}'")

    # ホームポジションに戻る
    print("\n>> Move to the HOME POSITION")
    log("Move to the HOME POSITION")
    stage.send_command(f"AXIs1:GO 3\r")
    print("Moving...")
    while True:
        stage.send_command(f"AXIs1:MOTION?\r")
        response = stage.readline()
        if "0" in response:
            print("Paused")
            break
    stage.check_current_position()

    print("\n>> Program exit")
    log("Program exit")
    stage.close()
    spectro.close()

if __name__ == "__main__":
    main()
