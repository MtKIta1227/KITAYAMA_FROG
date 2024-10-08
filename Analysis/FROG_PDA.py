import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget

def load_data(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    # 波長軸を抽出A
    wavelengths = list(map(float, lines[0].strip().split()[1:]))

    # 強度のデータを抽出
    intensity_data = []
    times = []
    for line in lines[1:]:
        values = line.strip().split()
        # 1列目の時間を抽出
        time = float(values[0])
        # 時間軸を追加
        times.append(time)
        # 2列目以降の強度を抽出
        intensities = list(map(float, values[1:]))
        intensity_data.append(intensities)

    return wavelengths, times, intensity_data

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 - File Dialog'
        self.left = 100
        self.top = 100
        self.width = 800
        self.height = 600
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        layout = QVBoxLayout()

        self.button = QPushButton('Open file', self)
        self.button.clicked.connect(self.show_file_dialog)
        layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def show_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        filename, _ = QFileDialog.getOpenFileName(self, "Select a text file", "", "Text Files (*.txt);;All Files (*)", options=options)
        if filename:
            self.plot_data(filename)

    def plot_data(self, filename):
        wavelengths, times, intensity_data = load_data(filename)
        intensity_data = np.array(intensity_data)

        # バックグラウンドデータを取得
        background = intensity_data[0]  # 最初の時間の強度
        # バックグラウンドを引く
        adjusted_intensity_data = intensity_data - background
        # バックグラウンドを引いた後の強度が負の値にならないようにする
        adjusted_intensity_data[adjusted_intensity_data < 0] = 0
        # データを出力
        print(adjusted_intensity_data)

        # プロット
        plt.imshow(adjusted_intensity_data.T, aspect='auto', cmap='nipy_spectral', origin='lower', extent=[times[0], times[-1], wavelengths[0], wavelengths[-1]])
        plt.colorbar(label='Adjusted Intensity')
        plt.xlabel('Time / fs')  # x軸のラベルを変更
        plt.ylabel('Wavelength / nm')
        plt.ylim(400, 800)
        plt.title('Intensity after Background Subtraction')
        plt.show()

def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
