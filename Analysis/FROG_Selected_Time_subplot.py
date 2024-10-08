import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QLabel, QListWidget

def load_data(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    # 波長軸を抽出
    wavelengths = list(map(float, lines[0].strip().split()[0:]))

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

    return wavelengths, times, np.array(intensity_data)

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 - Time-Intensity Plot'
        self.left = 100
        self.top = 100
        self.width = 800
        self.height = 600
        self.wavelengths = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        layout = QVBoxLayout()

        self.button = QPushButton('Open file', self)
        self.button.clicked.connect(self.show_file_dialog)
        layout.addWidget(self.button)

        self.time_label = QLabel('Select Time:', self)
        layout.addWidget(self.time_label)

        self.time_list = QListWidget(self)
        self.time_list.setSelectionMode(QListWidget.MultiSelection)  # マルチセレクションモードに変更
        layout.addWidget(self.time_list)

        self.plot_button = QPushButton('Plot', self)
        self.plot_button.clicked.connect(self.plot_selected_time)
        layout.addWidget(self.plot_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def show_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        filename, _ = QFileDialog.getOpenFileName(self, "Select a text file", "", "Text Files (*.txt);;All Files (*)", options=options)
        if filename:
            self.wavelengths, self.times, self.intensity_data = load_data(filename)
            self.time_list.clear()
            self.time_list.addItems(map(str, self.times))  # 時間をリストに追加

    def plot_selected_time(self):
        selected_items = self.time_list.selectedItems()
        if not selected_items:
            self.time_label.setText('Please select a time.')
            return

        # バックグラウンドデータを取得
        background = self.intensity_data[0, :]  # 最初の時間の強度

        plt.figure(figsize=(12, 6))
        for item in selected_items:
            selected_time = float(item.text())
            selected_index = self.times.index(selected_time)

            # オリジナルの強度データ
            original_intensity = self.intensity_data[selected_index, :]
            # バックグラウンドを引いた強度データ
            adjusted_intensity = original_intensity - background
            adjusted_intensity[adjusted_intensity < 0] = 0  # 負の値を0に設定

            # サブプロットにプロット
            plt.subplot(1, 2, 1)
            plt.plot(self.wavelengths, original_intensity, label=f'Time: {selected_time:.2f} fs')
            plt.xlabel('Wavelength / nm')
            plt.ylabel('Original Intensity')
            plt.title('Original Intensity at Selected Times')
            plt.legend()
            plt.grid()

            plt.subplot(1, 2, 2)
            plt.plot(self.wavelengths, adjusted_intensity, label=f'Time: {selected_time:.2f} fs')
            plt.xlabel('Wavelength / nm')
            plt.ylabel('Adjusted Intensity')
            plt.title('Adjusted Intensity (Background Subtracted)')
            plt.legend()
            plt.grid()

        plt.tight_layout()
        plt.show()

def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
