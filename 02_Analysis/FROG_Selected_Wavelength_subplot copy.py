import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, QWidget, QLabel, QListWidget

def load_data(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    wavelengths = list(map(float, lines[0].strip().split()[1:]))
    intensity_data = []
    times = []
    for line in lines[1:]:
        values = line.strip().split()
        time = float(values[0])
        times.append(time)
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
        self.wavelength_list.setSelectionMode(QListWidget.MultiSelection)
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
            self.wavelength_list.addItems(map(str, self.wavelengths))

    def plot_selected_wavelength(self):
        selected_items = self.wavelength_list.selectedItems()
        
        if not selected_items:
            return
        
        background_intensity = self.intensity_data[0, :]
        plt.figure(figsize=(12, 6))
        
        for item in selected_items:
            selected_wavelength = float(item.text())
            selected_index = self.wavelengths.index(selected_wavelength)
            selected_intensity = self.intensity_data[:, selected_index]
            adjusted_intensity = selected_intensity - background_intensity[selected_index]

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

            # FWHMの計算
            fwhm_start, fwhm_end = self.calculate_fwhm(self.times, adjusted_intensity)
            plt.axvline(fwhm_start, color='red', linestyle='--')
            plt.axvline(fwhm_end, color='red', linestyle='--')
            plt.text(fwhm_start, max(adjusted_intensity) * 0.8, 'Start', color='red')
            plt.text(fwhm_end, max(adjusted_intensity) * 0.8, 'End', color='red')

            # FWHMの値を表示
            fwhm_value = fwhm_end - fwhm_start
            plt.text((fwhm_start + fwhm_end) / 2, max(adjusted_intensity) * 0.6, f'FWHM: {fwhm_value:.2f} fs', color='blue', fontsize=12, ha='center')

        plt.tight_layout()
        plt.show()

    def calculate_fwhm(self, times, intensity):
        max_intensity = np.max(intensity)
        half_max = max_intensity / 2

        # 最大強度のインデックスを取得
        max_index = np.argmax(intensity)

        # FWHMの開始時間と終了時間を見つける
        start_index = max_index
        end_index = max_index

        # 半分の強度を超える最初のインデックスを見つける
        while start_index > 0 and intensity[start_index] >= half_max:
            start_index -= 1
        if intensity[start_index] < half_max:
            start_index += 1

        # 半分の強度を超える最後のインデックスを見つける
        while end_index < len(intensity) - 1 and intensity[end_index] >= half_max:
            end_index += 1
        if intensity[end_index] < half_max:
            end_index -= 1

        fwhm_start = times[start_index]
        fwhm_end = times[end_index]
        
        return fwhm_start, fwhm_end

def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
