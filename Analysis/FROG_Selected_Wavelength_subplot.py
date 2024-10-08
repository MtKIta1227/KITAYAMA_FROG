import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QLabel, QListWidget

def load_data(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    # 波長軸を抽出
    wavelengths = list(map(float, lines[0].strip().split()[1:]))

    # 強度のデータを抽出
    intensity_data = []
    times = []
    for line in lines[1:]:
        values = line.strip().split()
        # 1列目の時間を抽出
        time = float(values[0])
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

        self.wavelength_label = QLabel('Select Wavelengths:', self)
        layout.addWidget(self.wavelength_label)

        self.wavelength_list = QListWidget(self)
        self.wavelength_list.setSelectionMode(QListWidget.MultiSelection)  # 複数選択を許可
        layout.addWidget(self.wavelength_list)

        self.plot_button = QPushButton('Plot', self)
        self.plot_button.clicked.connect(self.plot_selected_wavelength)
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
            self.wavelength_list.clear()
            self.wavelength_list.addItems(map(str, self.wavelengths))  # 波長をリストに追加

    def plot_selected_wavelength(self):
        selected_items = self.wavelength_list.selectedItems()
        
        if not selected_items:
            return
        
        # 最初の時間における強度をバックグラウンドとして取得
        background_intensity = self.intensity_data[0, :]  # 最初の時間の強度

        plt.figure(figsize=(12, 6))
        
        for item in selected_items:
            selected_wavelength = float(item.text())
            selected_index = self.wavelengths.index(selected_wavelength)  # インデックスを取得
            selected_intensity = self.intensity_data[:, selected_index]

            # バックグラウンドを引く
            adjusted_intensity = selected_intensity - background_intensity[selected_index]

            # サブプロットにプロット
            plt.subplot(1, 2, 1)
            plt.plot(self.times, selected_intensity, label=f'{selected_wavelength:.2f} nm')
            plt.xlabel('Time / fs')
            plt.ylabel('Intensity')
            plt.title('Original Intensity')
            plt.legend()
            plt.grid()

            plt.subplot(1, 2, 2)
            plt.plot(self.times, adjusted_intensity, label=f'{selected_wavelength:.2f} nm')
            plt.xlabel('Time / fs')
            plt.ylabel('Adjusted Intensity')
            plt.title('Adjusted Intensity')
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
