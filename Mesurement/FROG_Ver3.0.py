#mm,m,#-*- coding:utf-8 -*-
'''
Created on 2023/11/08
@author: Kitayama Daisuke
''' 

import time,serial,os,datetime
import serial.tools.list_ports
import pyvisa as visa
import seabreeze.spectrometers as sb
import matplotlib.pyplot as plt
from tqdm import tqdm

#ログファイルの設定。ログファイルは同じディレクトリ内のlogというフォルダに保存。フォルダがなければ作成
current_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(current_dir, "log")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_FROG.log")
log_path = os.path.join(log_dir, log_file)

def log(message):
    with open(log_path, "a",encoding='utf-8') as lf:
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        lf.write(f"[{timestamp}] {message}\n")

print("╔════════════════════════════════════════════╗")
print("║    ~ FROG Measurement Program ~  ver 3.0   ║")
print("╚════════════════════════════════════════════╝")

log("Program start")
def calculate_dt(step_size):
    c = 299792458  # 光速
    dt = 2 * step_size * 10**(-6) / c * 10**15  # 定pulseごとの遅延時間(/fs)
    return dt

def check_current_position(ser):
    check_parameter(ser, "AXIs1:POS?\r", "Current Position")


def check_device_parameters(ser):
    print("\n>> Check parameters")
    check_parameter(ser, "AXIs1:DRiverDIVision?\r", "DriverDivision (Full[0], HALF[1])")
    check_parameter(ser, "AXIs1:UNIT?\r", "UNIT(PULSE[0], um[1])")
    check_parameter(ser, "AXIs1:HOMEPosition?\r", "HomePosition")
    check_parameter(ser, "AXIs1:RESOLUTion?\r", "Resolution/pulse")
    check_parameter(ser, "AXIs1:MEMorySWitch0?\r", "Originating type")
    check_parameter(ser, "AXIs1:SELectSPeed?\r", "Speed table type")
    check_parameter(ser, "CWSoftLimitEnable?\r", "CWSoftLimitEnable (Disable[0], Enable[1])")
    check_parameter(ser, "CCWSoftLimitEnable?\r", "CCWSoftLimitEnable (Disable[0], Enable[1])")


def check_parameter(ser, command, parameter_name):
    ser.write(command.encode('utf-8'))
    response = ser.readline().decode('utf-8')
    print(f"{parameter_name}: {response}")
    log(f"{parameter_name}: {response}")


def find_device_port(device_name):
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in ports:
        if device_name in desc:
            return port
    return None


def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def initialize_device(ser): 
    print(">> Initializing ...")
    send_command(ser, "AXIs1:DRiverDIVision 0\r")  # ドライバ分割数をFullに設定
    print("Set DRiverDIVision to [ Full ]")
    send_command(ser, "MEMorySWitch0 3\r")  # 原点復帰モードを3に設定
    print("Set MEMorySWitch0 to [Type 3]")


def open_serial_connection(com_port):
    try:
        ser = serial.Serial(com_port, baudrate=9600, timeout=1)
        response = ser.readline().decode('utf-8')
        return ser
    except Exception as e:
        print(f"Error: COMポートを開く際にエラーが発生しました: {e}")
        return None


def move_stage(ser, fspeed, pulses, direction):
    send_command(ser, f"AXIs1:Fspeed0 {fspeed}\r")
    send_command(ser, f"AXIs1:PULS {pulses}:GO {direction}\r")
    print(" Moving...")

    while True:
        command = "AXIs1:MOTION?\r" 
        ser.write(command.encode('utf-8'))
        response = ser.readline().decode('utf-8').strip()
        if "0" in response:
            print(f" Paused")
            break


def send_command(ser, command):
    ser.write(command.encode('utf-8'))


def main():
    # USB4000, DS102への接続を確認
    print("###############################################")
    print("Connection check for USB4000 and DS102")
    print("###############################################")
    log("Connection check for USB4000 and DS102")

    rm = visa.ResourceManager()
    time.sleep(1)

    # USB4000への接続
    target_model_name = 'USB4000'
    print("\n>> Connection test for USB4000....")
    while True:
        try:
            devices = sb.list_devices()
            if len(devices) == 0:
                print("Spectrometer not found. We will attempt to search again...")
                time.sleep(5)
            else:
                target_device = None
                for device in devices:
                    spectrometer = sb.Spectrometer(device)
                    if spectrometer.model == target_model_name:
                        target_device = device
                        break

                if target_device is not None:
                    break
                else:
                    print(f" '{target_model_name}' Spectrometer not found. We will attempt to search again...")
                    time.sleep(5)
        except Exception as e:
            print(f"Error.: {e}")
            time.sleep(5)

    time.sleep(0.1)
    print("-----------------------------------------")
    print("Connected to spectrometer USB4000.")
    print("-----------------------------------------")
    log("Connected to spectrometer USB4000.")

    # DS102への接続
    print("\n>> Connection test for SURUGA SEIKI DS102 USB Serial Port....")
    device_name = "SURUGA SEIKI DS102 USB Serial Port"
    com_port = find_device_port(device_name)

    if com_port is None:
        print(f">> Error: {device_name} could not find the COM port to which it is connected.")
        return

    print("---------------------------------------------------------")
    print(f"Connect to {device_name} by [ {com_port} ].")
    print("---------------------------------------------------------")

    ser = open_serial_connection(com_port)
    log(f"Connected to {device_name} by [ {com_port} ].")
    if ser is None:
        return

    # DS102の初期化確認
    print("\n#####################################################################")
    print("DS102 Initialization ~Stage Position Adjustment~")
    print("#####################################################################")
    log("DS102 Initialization ~Stage Position Adjustment~")
    user_input = input(">> Do you want to initialise? (yes/pass) : ")

    if user_input.lower() != 'pass':
        log("DS102 initialisation started.")
        print("Initializing DS102...")
        initialize_device(ser)  # パラメーター初期化
        check_device_parameters(ser)  # パラメーター確認
        # ステージポジションの初期化
        print("\n>> Initializing Stage Position")
        log("Initializing Stage Position")
        print("Check current position")
        check_current_position(ser)
        # ステージをフルフロント(CW)
        print("\n>> Move stage to [ full front ]")
        log("Move stage to [ full front ]")
        move_stage(ser, fspeed=5000, pulses=50000, direction=0)
        check_current_position(ser)
        # ステージをフルバック（CCW)
        print("\n>> Move stage to [ full back ]")
        log("Move stage to [ full back ]")
        move_stage(ser, fspeed=5000, pulses=50000, direction=1)
        check_current_position(ser)
        # ステージのフルバック位置を微調整
        print("\n>> position adjustment")
        log("position adjustment")
        for i in range(3):
            move_stage(ser, fspeed=100, pulses=100, direction=0)
            check_current_position(ser)
            move_stage(ser, fspeed=100, pulses=200, direction=1)
            check_current_position(ser)
    else:
        print(">> DS102 initialisation passed.")
        log("DS102 initialisation passed.")
    time.sleep(1)

# # USB4000のORIGIN POINT設定
# print("\n#####################################################################")
# print("~Setting up the ORIGIN POINT~")
# print("#####################################################################")
#
# ##ステージの位置調整 必要なければ後で削除
# print("Move the stage to the desired coordinates.")
# while True:
#     # ステージの移動
#     X = input(">> Input the step size ('ok' to finish): ")
#     if X == "ok":
#         break     
#     step_size = int(X)  # 入力を整数に変換
#     if step_size > 0:
#         direction = 0  # 前進CW
#     else:
#         direction = 1  # 後進CCW
#         step_size = abs(step_size)  # 負の値を正の値に変換
#
#     move_stage(ser, fspeed=1000, pulses=step_size, direction=direction)
#     check_current_position(ser)
#     print("")
# print("-----------------------------------------")
# check_current_position(ser)
# print("Set current position to 'ORIGIN POINT'")
# send_command(ser, "AXIs1:POS 0\r")
# check_current_position(ser)
# print("-----------------------------------------")
# print(">> Finish the setting of the ORIGIN POINT")
# time.sleep(0.1)
    # ORG設定
    print("\n########################################################")
    print("USB4000 initialization ~Searching for the peak intensity and setting the ORG~")
    print("########################################################")
    log("USB4000 initialization ~Searching for the peak intensity and setting the ORG~")
    check_current_position(ser)
    print(">> Move the stage to any position and measure with USB4000.")

    while True:
        input_time = input(">> Set the [Integration time (/ms)]: ")
        try:
            integration_time_ms = int(input_time)
            break
        except ValueError:
            print("Invalid input. Please enter an integer.")

    previous_integration_time_ms = integration_time_ms
    log(f"Set Integration Time: {integration_time_ms} ms")

    while True:
        X = input(">> Input the [STEP SIZE] (type 'ok' to finish, 'ORG' to set the ORIGINAL POINT): ")
        if X.lower() == "ok":
            print("Current position is set to the HOME POINT.")
            #現在の座標を確認し、ホームポジションに設定
            ser.write("AXIs1:POS?\r".encode('utf-8'))
            current_position = int(ser.readline().decode('utf-8').strip())
            ser.write(f"AXIs1:HOMEP {current_position}\r".encode('utf-8'))
            log(f"Set HOME POSITION: {current_position}")

            #ホームポジションの確認
            ser.write("AXIs1:HOMEPosition?\r".encode('utf-8'))
            home_position = int(ser.readline().decode('utf-8').strip())
            log(f"HOME POSITION: {home_position}")

            break
        elif X.lower() == "org":
            send_command(ser, "AXIs1:POS 0\r")
            print(">> Set current position to 'ORIGIN POINT'")
            check_current_position(ser)
            print("")
            log(f"Set current position to 'ORIGIN POINT'")
            continue

        try:
            step_size = int(X)
        except ValueError:
            print("Invalid input. Please enter an integer.")
            continue

        direction = 0 if step_size > 0 else 1 #CWは0、CCWは1
        step_size = abs(step_size)

        move_stage(ser, fspeed=1000, pulses=step_size, direction=direction)
        check_current_position(ser)
        input_time = input(">> Press Enter to measurement (or input the new integration time): ")

        if input_time == "":
            integration_time_ms = previous_integration_time_ms
        else:
            try:
                integration_time_ms = int(input_time)
                previous_integration_time_ms = integration_time_ms  
                log(f"Set Integration Time: {integration_time_ms} ms")
            except ValueError:
                print("Invalid input. Please enter an integer.")
                continue

        spectrometer.integration_time_micros(integration_time_ms)
        print("Measuring...")
        time.sleep(integration_time_ms / 1000 + 0.2)

        spectrum = spectrometer.spectrum()
        spectrum_max = spectrum[1]

        max_intensity = max(spectrum_max[1000:])

        # 現在の座標をCPとする
        ser.write("AXIs1:POS?\r".encode('utf-8'))
        CP = int(ser.readline().decode('utf-8').strip())
        # 座標を時間軸に変換
        CP_time = 2 * CP * 10**(-6) / 299792458 * 10**15

        print("-------------------------------------------")
        check_current_position(ser)
        print(f"Time axis: {CP_time:.2f} fs")
        print(f"Integration time: {integration_time_ms} ms")
        print(f"Max intensity: {max_intensity:.2f}")
        print("-------------------------------------------\n")
        log("-------------------------------------------")
        log(f"Time axis: {CP_time:.2f} fs")
        log(f"Integration time: {integration_time_ms} ms")
        log(f"Max intensity: {max_intensity:.2f}")
        log("-------------------------------------------")

    
    #original pointの確認
    ser.write("AXIs1:ORG?\r".encode('utf-8'))
    original_position = int(ser.readline().decode('utf-8').strip())

    print("\n>> Finish the setting of the ORIGIN POINT")
    print("-----------------------------------------")
    print(f"ORIGINAL POINT: {original_position}")
    print(f"HOME POSITION: {home_position}")
    check_current_position(ser)
    print("-----------------------------------------")
    log("-----------------------------------------")
    log(f"ORIGINAL POINT: {original_position}")
    log(f"HOME POSITION: {home_position}")
    log("-----------------------------------------")

    #FROG測定
    print("\n###############################################")
    print("SETTING UP FOR FROG MEASUREMENT")
    print("###############################################")
    log("SETTING UP FOR FROG MEASUREMENT")
    ##ステップサイズの設定
    default_step_size = 3  # デフォルトのステップサイズ
    print(">> Set the step size (default is 3 pulse)")
    
    step_size_input = input(f"Step size (or press Enter for default 20 fs[3 pulse]): ")
    
    if step_size_input.strip() == "":
        step_size = default_step_size
    else:
        step_size = int(step_size_input)

    dt = calculate_dt(step_size)
    
    print("-----------------------------------------------")
    print(f"Measurement interval is '{dt:.2f} fs'")
    print("-----------------------------------------------")

    while True:
        change = input("Do you want to change the step size? (yes/no): ").strip().lower()
        if change == 'yes':
            log("Change the step size")
            step_size_input = input(f"New step size (or press Enter for default 6.67 fs): ")
            if step_size_input.strip() == "":
                step_size = default_step_size
            else:
                step_size = int(step_size_input)
                log(f"Set step size: {step_size}")

            dt = calculate_dt(step_size)
            print(f"Measurement interval is now '{dt:.2f} fs'")
        elif change == 'no':
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")
    ##測定範囲の設定
    ##rangeをstepsizeで割って余りが0になるときだけ測定可能
    print("\n>> Set the measurement range")
    log("Set the measurement range")
    log(f"Step size: {step_size}")
    log(f"Measurement interval: {dt:.2f} fs")
    
    while True:
        range_input = input("Input measurement range [/pulse] (or press Enter for default 500 fs 75 pulse): ")
        if range_input.strip() == "":
            range_input = 75  # デフォルトの測定範囲 500fs 
            break
        try:
            range_input = int(range_input)
            if range_input % step_size == 0:
                range
                print(f"Measurement range is '{range_input * dt:.2f} fs'")

                break
            else:
                print("Invalid input. Please enter a value that is divisible by the step size.")
        except ValueError:
            print("Invalid input. Please enter an integer.")
    
    while True:
        change = input("Do you want to change the measurement range? (yes/no): ").strip().lower()
        if change == 'yes':
            while True:
                range_input = input("New measurement range [/pulse]: ")
                try:
                    range_input = int(range_input)
                    if range_input % step_size == 0:
                        log(f"Change the measurement range to {range_input} pulse")
                        break
                    else:
                        print("Invalid input. Please enter a value that is divisible by the step size.")
                except ValueError:
                    print("Invalid input. Please enter an integer.")
        elif change == 'no':
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")
    log(f"Measurement range is '{range_input * dt:.2f} fs'")    
    end_point = range_input + int(home_position)

    ##測定範囲の確認
    print("-----------------------------------------------")
    print(f"Measurement range is '{range_input * dt:.2f} fs'")
    print(f"Start point: {home_position}")
    print(f"End point: {end_point}")
    print("-----------------------------------------------")
    log("-----------------------------------------------")
    log(f"Start point: {home_position}")
    log(f"End point: {end_point}")
    log("-----------------------------------------------")

    time.sleep(0.1)
    print('\n###############################################')
    print('FROG Measurement')
    print('###############################################')
    log('FROG Measurement')
    time.sleep(0.1)
    print("\n>> Check the Mesurement Setup")
    print("-----------------------------------------------")
    print(f"Step size: {step_size}")
    print(f"Measurement interval: {dt:.2f} fs")
    print(f"Measurement range is '{range_input * dt:.2f} fs'")
    print(f"Integration time: {integration_time_ms} ms")
    print(f"Start point: {home_position}")
    print(f"End point: {end_point}")
    print("-----------------------------------------------")
    log("Check the Mesurement Setup")
    log("-----------------------------------------------")
    log(f"Step size: {step_size}")
    log(f"Measurement interval: {dt:.2f} fs")
    log(f"Measurement range is '{range_input * dt:.2f} fs'")
    log(f"Integration time: {integration_time_ms} ms")
    log(f"Start point: {home_position}")
    log(f"End point: {end_point}")
    log("-----------------------------------------------")


    while True:
        user_input = input("PRESS ENTER to start the measurement (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            return
        elif user_input == "":
            log("Measurement started")
            break
        else:
            print("Invalid input. Please press ENTER to start the measurement.")
    
    #測定開始
    # 実行しているファイルと同じ階層のdataというフォルダに保存。フォルダがなければ作成
    data_dir = os.path.join(current_dir, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    file_name = os.path.join(data_dir, f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_FROG.txt")
    log(f"Data saved as '{file_name}'")
    print("\n>> Measurement started")
    log("Measurement started")
    
    start = time.time()
    loop_num = range_input / step_size
    # プログレスバーの設定
    bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'

    with open(file_name, "w") as f:
        f.write("\t")
        x = spectrometer.wavelengths()[1002:]
        for x_value in x:
            f.write(str(x_value) + "\t")
        f.write("\n")

        for i in tqdm(range(int(loop_num)), bar_format=bar_format, ncols=75):
            spectrometer.integration_time_micros(int(integration_time_ms))
            time.sleep(int(integration_time_ms)/1000 + 1)

            y = spectrometer.intensities()[1002:]  # 390nm以降の範囲のintensityを取得

            # スペクトラム書き込み
            delay = int(i) * dt
            f.write(str(delay) + "\t")
            for y_value in y:
                f.write(str(y_value) + "\t")
            f.write("\n")

            # ステージ移動
            move_stage(ser, fspeed=1000, pulses=step_size, direction=0)
            log(f"Measuring at {i * step_size} pulse")
            log(f"Move stage {step_size} pulse")
            check_current_position(ser)

    elapsed_time = time.time() - start
    print("-----------------------------------------------")
    print("\nMeasurement completed !!.")
    print("-----------------------------------------------")
    print(f"Elapsed time: {format_time(elapsed_time)}")
    print(f"Data saved as '{file_name}'")
    log("-----------------------------------------------")
    log("Measurement completed !!.")
    log("-----------------------------------------------")
    log(f"Elapsed time: {format_time(elapsed_time)}")
    log(f"Data saved as '{file_name}'")

    # ホームポジションに戻る
    print("\n>> Move to the HOME POSITION")
    log("Move to the HOME POSITION")
    send_command(ser, f"AXIs1:GO 3\r")
    print("Moving...")
    while True:
        send_command(ser, f"AXIs1:MOTION?\r")    
        response = ser.readline().decode('utf-8').strip()
        if "0" in response:
            print(f"Paused")
            break

    check_current_position(ser)
    
    time.sleep(1)
    print("\n>> Program exit")
    log("Program exit")
    ser.close()
    spectrometer.close()



if __name__ == "__main__":
    main()









