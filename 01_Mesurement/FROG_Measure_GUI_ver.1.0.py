import sys
import os
import datetime
import time
import numpy as np
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import serial
import serial.tools.list_ports

try:
    import seabreeze.spectrometers as sb
    seabreeze_imported = True
except Exception:
    seabreeze_imported = False

def log_to_file(logpath, message):
    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    with open(logpath, "a", encoding="utf-8") as lf:
        lf.write(f"[{now}] {message}\n")

def move_stage_and_wait(ser, fspeed, pulses, direction, gui_log=None, file_log=None):
    try:
        start_time = datetime.datetime.now()
        msg = f"ステージ移動開始: fspeed={fspeed}, pulses={pulses}, direction={direction}"
        if gui_log: gui_log(msg)
        if file_log: file_log(msg)
        cmd1 = f"AXIs1:Fspeed0 {fspeed}\r"
        cmd2 = f"AXIs1:PULS {pulses}:GO {direction}\r"
        ser.write(cmd1.encode('utf-8'))
        ser.write(cmd2.encode('utf-8'))
        for _ in range(120):
            ser.write("AXIs1:MOTION?\r".encode('utf-8'))
            resp = ser.readline().decode('utf-8').strip()
            if resp == "0":
                end_time = datetime.datetime.now()
                msg2 = f"ステージ停止検出: {end_time.strftime('%H:%M:%S.%f')[:-3]}（移動に{(end_time - start_time).total_seconds():.2f}秒）"
                if gui_log: gui_log(msg2)
                if file_log: file_log(msg2)
                return True
            time.sleep(0.1)
        msg3 = "ステージ移動タイムアウトエラー"
        if gui_log: gui_log(msg3)
        if file_log: file_log(msg3)
        return False
    except Exception as e:
        msg4 = f"ステージ移動例外エラー: {e}"
        if gui_log: gui_log(msg4)
        if file_log: file_log(msg4)
        return False

class MeasurementWorker(QtCore.QThread):
    progressChanged = QtCore.pyqtSignal(int)
    logSignal = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    dataSaved = QtCore.pyqtSignal(str)
    dataUpdated = QtCore.pyqtSignal(int, object, object, object)
    posUpdated = QtCore.pyqtSignal(int)

    def __init__(self, ser, spectrometer, params, bg_data, parent=None):
        super().__init__(parent)
        self.ser = ser
        self.spectrometer = spectrometer
        self.params = params
        self.bg_data = bg_data
        self._is_running = True

        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(current_dir, "log")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.logpath = os.path.join(self.log_dir, f"{now}_FROG_gui.log")

    def stop(self):
        self._is_running = False

    def get_position(self):
        try:
            self.ser.write("AXIs1:POS?\r".encode('utf-8'))
            pos = self.ser.readline().decode('utf-8').strip()
            return int(pos)
        except Exception:
            return None

    def run(self):
        step_size = self.params['step_size']
        range_input = self.params['range_input']
        integration_time_ms = self.params['integration_time_ms']
        home_position = self.params['home_position']
        dt = self.params['dt']
        fspeed = self.params['fspeed']

        loop_num = range_input // step_size

        wavelengths = self.spectrometer.wavelengths()[1002:]
        n_wl = len(wavelengths)
        t_axis = [i * dt for i in range(loop_num)]
        data2d = np.zeros((loop_num, n_wl))  # shape: (loop_num, n_wl)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.join(data_dir, f"{now}_FROG.txt")
        file_name_csv = os.path.join(data_dir, f"{now}_FROG.csv")
        self.logSignal.emit(f"測定データを {file_name} (txt) および {file_name_csv} (csv) に保存します")
        log_to_file(self.logpath, f"測定データ保存先: {file_name} , {file_name_csv}")

        try:
            with open(file_name, "w", encoding="utf-8") as f, \
                 open(file_name_csv, "w", encoding="utf-8", newline='') as fcsv:
                # テキスト出力（従来形式）
                header = "#delay/fs\t" + "\t".join(str(x) for x in wavelengths) + "\tmax_intensity\ttimestamp\n"
                f.write(header)
                # CSV形式ヘッダー
                header_csv = ["Wavelength[nm]"] + [f"{t:.2f}" for t in t_axis]
                fcsv.write(",".join(header_csv) + "\n")
                y_mat = []
                for i in range(loop_num):
                    if not self._is_running:
                        msg = "測定をユーザーが中断しました。"
                        self.logSignal.emit(msg)
                        log_to_file(self.logpath, msg)
                        break
                    if i > 0:
                        ok = move_stage_and_wait(
                            self.ser, fspeed, step_size, 0,
                            gui_log=self.logSignal.emit,
                            file_log=lambda m: log_to_file(self.logpath, m)
                        )
                        if not ok:
                            msg = "ステージ移動失敗により測定中断"
                            self.logSignal.emit(msg)
                            log_to_file(self.logpath, msg)
                            break
                    cur_pos = self.get_position()
                    self.posUpdated.emit(cur_pos if cur_pos is not None else -999999)
                    measure_start = datetime.datetime.now()
                    msg1 = f"測定開始: index={i}, delay={t_axis[i]:.2f}fs, {measure_start.strftime('%H:%M:%S.%f')[:-3]}"
                    self.logSignal.emit(msg1)
                    log_to_file(self.logpath, msg1)
                    self.spectrometer.integration_time_micros(integration_time_ms)
                    time.sleep(integration_time_ms / 1000 + 0.2)
                    y = self.spectrometer.intensities()[1002:]
                    if self.bg_data is not None and len(y) == len(self.bg_data):
                        y = np.array(y) - np.array(self.bg_data)
                        msg_bg = f"BG減算: 測定点 {i} でBGスペクトルを引きました"
                        self.logSignal.emit(msg_bg)
                        log_to_file(self.logpath, msg_bg)
                    max_int = np.nanmax(y)
                    measure_end = datetime.datetime.now()
                    msg2 = f"測定完了: index={i}, max_intensity={max_int:.2f}, {measure_end.strftime('%H:%M:%S.%f')[:-3]}（測定{(measure_end-measure_start).total_seconds():.2f}秒）"
                    self.logSignal.emit(msg2)
                    log_to_file(self.logpath, msg2)
                    data2d[i, :] = y
                    delay = t_axis[i]
                    # テキスト形式
                    f.write(
                        f"{delay:.2f}\t" +
                        "\t".join(str(v) for v in y) +
                        f"\t{max_int:.2f}\t{measure_end.strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]}\n"
                    )
                    y_mat.append(list(y))
                    self.progressChanged.emit(int((i + 1) / loop_num * 100))
                    self.dataUpdated.emit(i, data2d, t_axis, wavelengths)
                # ==== CSV形式出力 ====
                if len(y_mat) > 0:
                    y_mat = np.array(y_mat).T  # shape: (n_wl, n_times)
                    for iw, wl in enumerate(wavelengths):
                        vals = [f"{y:.4f}" for y in y_mat[iw]] if y_mat.shape[1] > 0 else []
                        line = [f"{wl:.1f}"] + vals
                        fcsv.write(",".join(line) + "\n")
                cur_pos = self.get_position()
                self.posUpdated.emit(cur_pos if cur_pos is not None else -999999)
                msg_fin = "測定完了"
                self.logSignal.emit(msg_fin)
                log_to_file(self.logpath, msg_fin)
                self.dataSaved.emit(file_name_csv)
        except Exception as e:
            msg_err = f"測定中エラー: {e}"
            self.logSignal.emit(msg_err)
            log_to_file(self.logpath, msg_err)
        self.finished.emit()

class FROG_GUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FROG Measurement GUI")
        self.setGeometry(200, 100, 1280, 900)

        # デバイス・データ
        self.spectrometer = None
        self.ser = None
        self.measure_thread = None
        self.home_position = 0
        self.im = None
        self.cbar = None
        self.bg_data = None
        self.current_position = None

        layout = QtWidgets.QVBoxLayout()

        # デバイス接続部
        dev_layout = QtWidgets.QHBoxLayout()
        self.usb4000_btn = QtWidgets.QPushButton("USB4000接続確認")
        self.usb4000_btn.clicked.connect(self.check_usb4000)
        dev_layout.addWidget(self.usb4000_btn)
        self.ds102_btn = QtWidgets.QPushButton("DS102接続確認")
        self.ds102_btn.clicked.connect(self.check_ds102)
        dev_layout.addWidget(self.ds102_btn)
        self.status_label = QtWidgets.QLabel("デバイス未接続")
        dev_layout.addWidget(self.status_label)
        layout.addLayout(dev_layout)

        # ======= ステージ制御部を集約 =======
        stage_group = QtWidgets.QGroupBox("ステージ制御")
        stage_layout = QtWidgets.QGridLayout()

        # 現在位置表示
        self.position_label = QtWidgets.QLabel("現在位置: 未取得")
        stage_layout.addWidget(self.position_label, 0, 0, 1, 2)

        # 現在位置手動セット
        stage_layout.addWidget(QtWidgets.QLabel("手動で現在位置をセット:"), 1, 0)
        self.position_input = QtWidgets.QSpinBox()
        self.position_input.setRange(-1000000, 1000000)
        self.position_input.setValue(0)
        stage_layout.addWidget(self.position_input, 1, 1)
        self.setpos_btn = QtWidgets.QPushButton("位置をセット")
        self.setpos_btn.clicked.connect(self.set_stage_position_manual)
        stage_layout.addWidget(self.setpos_btn, 1, 2)

        # HOME設定
        self.home_btn = QtWidgets.QPushButton("現在位置をHOMEに設定")
        self.home_btn.clicked.connect(self.set_home_position)
        stage_layout.addWidget(self.home_btn, 2, 0, 1, 2)
        self.home_label = QtWidgets.QLabel("HOME: 未設定")
        stage_layout.addWidget(self.home_label, 2, 2)

        # 手動パルス移動
        stage_layout.addWidget(QtWidgets.QLabel("遅延ステージ移動 (パルス):"), 3, 0)
        self.move_input = QtWidgets.QSpinBox()
        self.move_input.setRange(-100000, 100000)
        self.move_input.setValue(0)
        stage_layout.addWidget(self.move_input, 3, 1)
        self.move_btn = QtWidgets.QPushButton("移動")
        self.move_btn.clicked.connect(self.move_stage_manual)
        stage_layout.addWidget(self.move_btn, 3, 2)

        stage_group.setLayout(stage_layout)
        layout.addWidget(stage_group)

        # パラメータ入力
        param_layout = QtWidgets.QFormLayout()
        self.integration_time_input = QtWidgets.QSpinBox()
        self.integration_time_input.setRange(1, 5000)
        self.integration_time_input.setValue(100)
        param_layout.addRow("積分時間 [ms]", self.integration_time_input)
        self.step_size_input = QtWidgets.QSpinBox()
        self.step_size_input.setValue(1)
        self.step_size_input.setRange(1, 10000)
        param_layout.addRow("ステップサイズ [pulse]", self.step_size_input)
        self.range_input = QtWidgets.QSpinBox()
        self.range_input.setValue(75)
        self.range_input.setRange(1, 10000)
        param_layout.addRow("測定範囲 [pulse]", self.range_input)
        self.fspeed_input = QtWidgets.QSpinBox()
        self.fspeed_input.setValue(1000)
        self.fspeed_input.setRange(10, 20000)
        param_layout.addRow("移動速度 [fspeed]", self.fspeed_input)
        layout.addLayout(param_layout)

        # BG測定
        bg_layout = QtWidgets.QHBoxLayout()
        self.bg_btn = QtWidgets.QPushButton("BG測定")
        self.bg_btn.clicked.connect(self.measure_bg)
        bg_layout.addWidget(self.bg_btn)
        layout.addLayout(bg_layout)

        # matplotlib Figure・ツールバー
        self.figure = Figure(figsize=(9, 4.5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # 1Dグラフ用
        self.ax = self.figure.add_subplot(121)
        self.ax.set_title("Test Spectrum (1D)")
        self.ax.set_xlabel("Wavelength [nm]")
        self.ax.set_ylabel("Intensity")

        # 2D imshow用
        self.im_ax = self.figure.add_subplot(122)
        self.im_ax.set_title("Time-Wavelength Map (FROG)")
        self.im_ax.set_xlabel("Delay [fs]")
        self.im_ax.set_ylabel("Wavelength [nm]")

        # 測定コントロール
        ctrl_layout = QtWidgets.QHBoxLayout()
        self.measure_btn = QtWidgets.QPushButton("測定開始")
        self.measure_btn.clicked.connect(self.start_measurement)
        ctrl_layout.addWidget(self.measure_btn)
        self.stop_btn = QtWidgets.QPushButton("中断")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        ctrl_layout.addWidget(self.stop_btn)
        self.test_btn = QtWidgets.QPushButton("テスト測定（1点取得）")
        self.test_btn.clicked.connect(self.test_measurement)
        ctrl_layout.addWidget(self.test_btn)
        layout.addLayout(ctrl_layout)

        # 進捗
        self.progress = QtWidgets.QProgressBar()
        layout.addWidget(self.progress)

        # ログ
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def log(self, message):
        now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.log_text.append(f"[{now}] {message}")

    def update_position_label(self, pos=None):
        if pos is not None and isinstance(pos, int):
            self.current_position = pos
            self.position_label.setText(f"現在位置: {pos}")
            self.position_input.setValue(pos)
            return
        if not self.ser:
            self.position_label.setText("現在位置: 未取得")
            return
        try:
            self.ser.write("AXIs1:POS?\r".encode('utf-8'))
            cur = self.ser.readline().decode('utf-8').strip()
            self.current_position = int(cur)
            self.position_label.setText(f"現在位置: {cur}")
            self.position_input.setValue(int(cur))
        except Exception as e:
            self.position_label.setText("位置取得エラー")
            self.log(f"位置取得エラー: {e}")

    def set_stage_position_manual(self):
        if not self.ser:
            self.log("DS102が接続されていません")
            return
        val = self.position_input.value()
        try:
            cmd = f"AXIs1:POS={val}\r"
            self.ser.write(cmd.encode('utf-8'))
            self.log(f"現在位置を {val} に手動設定しました")
            time.sleep(0.3)
            self.ser.write("AXIs1:POS?\r".encode('utf-8'))
            cur = self.ser.readline().decode('utf-8').strip()
            try:
                new_pos = int(cur)
            except Exception:
                new_pos = val
            if new_pos != val:
                self.log(f"DS102側の現在位置応答({cur})が入力値({val})と異なるため、ソフト側のみ値を上書きします")
                new_pos = val
            self.current_position = new_pos
            self.position_label.setText(f"現在位置: {new_pos}")
            self.position_input.setValue(new_pos)
        except Exception as e:
            self.log(f"位置手動設定エラー: {e}")
            self.current_position = val
            self.position_label.setText(f"現在位置: {val}")
            self.position_input.setValue(val)

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
        device_name = "SURUGA SEIKI DS102 USB Serial Port"
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if device_name in port.description:
                try:
                    self.ser = serial.Serial(port.device, baudrate=9600, timeout=1)
                    self.status_label.setText(f"DS102 接続: {port.device}")
                    self.log(f"DS102 ({port.device}) に接続しました")
                    self.update_position_label()
                    return
                except Exception as e:
                    self.log(f"DS102 シリアル接続失敗: {e}")
        self.status_label.setText("DS102 未検出")
        self.log("DS102 が見つかりません")

    def set_home_position(self):
        if not self.ser:
            self.log("DS102が接続されていません")
            return
        try:
            self.ser.write("AXIs1:POS?\r".encode('utf-8'))
            cur = self.ser.readline().decode('utf-8').strip()
            self.home_position = int(cur)
            self.home_label.setText(f"HOME: {self.home_position}")
            self.log(f"HOME位置を {self.home_position} に設定しました")
            self.update_position_label()
        except Exception as e:
            self.log(f"HOME位置設定エラー: {e}")

    def measure_bg(self):
        if not self.spectrometer:
            self.log("USB4000が接続されていません")
            return
        integration_time_ms = self.integration_time_input.value()
        self.spectrometer.integration_time_micros(integration_time_ms)
        time.sleep(integration_time_ms / 1000 + 0.2)
        self.bg_data = self.spectrometer.intensities()[1002:]
        self.log("BG測定完了・BGスペクトルを記憶しました")

    def move_stage_manual(self):
        if not self.ser:
            self.log("DS102が接続されていません")
            return
        pulses = self.move_input.value()
        if pulses == 0:
            self.log("移動パルス数が0です")
            return
        fspeed = self.fspeed_input.value()
        msg = f"手動ステージ移動: {pulses} パルス (fspeed={fspeed})"
        self.log(msg)
        move_stage_and_wait(
            self.ser, fspeed, abs(pulses),
            0 if pulses >= 0 else 1,
            gui_log=self.log
        )
        self.update_position_label()

    def test_measurement(self):
        if not self.spectrometer:
            self.log("USB4000が接続されていません")
            return
        integration_time_ms = self.integration_time_input.value()
        try:
            self.spectrometer.integration_time_micros(integration_time_ms)
            time.sleep(integration_time_ms / 1000 + 0.2)
            wavelengths = self.spectrometer.wavelengths()[1002:]
            intensities = self.spectrometer.intensities()[1002:]
            if self.bg_data is not None and len(intensities) == len(self.bg_data):
                intensities = np.array(intensities) - np.array(self.bg_data)
                self.log("BG減算：テスト測定でBGスペクトルを引きました")
            self.ax.clear()
            self.ax.plot(wavelengths, intensities, label="Test Spectrum")
            self.ax.set_title("Test Spectrum (1D)")
            self.ax.set_xlabel("Wavelength [nm]")
            self.ax.set_ylabel("Intensity")
            self.ax.legend()

            self.im_ax.clear()
            self.im_ax.set_title("Time-Wavelength Map (FROG)")
            self.im_ax.set_xlabel("Delay [fs]")
            self.im_ax.set_ylabel("Wavelength [nm]")
            self.im = None
            self.cbar = None

            self.canvas.draw()
            max_int = np.nanmax(intensities)
            self.log(f"テスト測定完了: 最大強度={max_int:.1f}")
            self.update_position_label()
        except Exception as e:
            self.log(f"テスト測定エラー: {e}")

    def start_measurement(self):
        if not self.spectrometer or not self.ser:
            self.log("デバイスが接続されていません")
            return
        self.im = None
        self.cbar = None
        params = {
            'integration_time_ms': self.integration_time_input.value(),
            'step_size': self.step_size_input.value(),
            'range_input': self.range_input.value(),
            'home_position': self.home_position,
            'fspeed': self.fspeed_input.value(),
            'dt': 2 * self.step_size_input.value() * 10 ** (-6) / 299792458 * 10 ** 15
        }
        self.measure_thread = MeasurementWorker(self.ser, self.spectrometer, params, self.bg_data)
        self.measure_thread.progressChanged.connect(self.progress.setValue)
        self.measure_thread.logSignal.connect(self.log)
        self.measure_thread.finished.connect(self.measurement_finished)
        self.measure_thread.dataSaved.connect(self.data_saved)
        self.measure_thread.dataUpdated.connect(self.update_imshow)
        self.measure_thread.posUpdated.connect(self.update_position_label)
        self.progress.setValue(0)
        self.measure_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log("測定を開始します")
        self.measure_thread.start()

    def stop_measurement(self):
        if self.measure_thread:
            self.measure_thread.stop()
            self.log("中断要求を送信しました")

    def measurement_finished(self):
        self.measure_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log("測定スレッド終了")
        self.update_position_label()

    def data_saved(self, filepath):
        self.log(f"データ保存完了: {filepath}")

    def update_imshow(self, idx, arr, t_axis, wavelengths):
        arr = np.array(arr)
        if arr.shape[0] < 2:
            return
        vmax = np.nanmax(arr)
        vmin = np.nanmin(arr)
        if self.im is None or self.cbar is None:
            self.im_ax.clear()
            self.im = self.im_ax.imshow(
                arr.T, aspect='auto', origin='lower',
                extent=[t_axis[0], t_axis[arr.shape[0]-1], wavelengths[0], wavelengths[-1]],
                interpolation='nearest', vmin=vmin, vmax=vmax
            )
            self.im_ax.set_title("Time-Wavelength Map (FROG)")
            self.im_ax.set_xlabel("Delay [fs]")
            self.im_ax.set_ylabel("Wavelength [nm]")
            self.cbar = self.figure.colorbar(self.im, ax=self.im_ax, orientation='vertical')
        else:
            self.im.set_data(arr.T)
            self.im.set_extent([t_axis[0], t_axis[arr.shape[0]-1], wavelengths[0], wavelengths[-1]])
            self.im.set_clim(vmin, vmax)
            self.cbar.update_normal(self.im)
        self.canvas.draw()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = FROG_GUI()
    window.show()
    sys.exit(app.exec_())
