import sys
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class CSVImshowGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Imshow Viewer")
        self.setGeometry(200, 100, 1100, 800)

        layout = QtWidgets.QVBoxLayout()

        # ファイル選択
        file_layout = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("CSVファイルを選択")
        self.load_btn.clicked.connect(self.load_csv)
        file_layout.addWidget(self.load_btn)
        self.file_label = QtWidgets.QLabel("ファイル未選択")
        file_layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        # プルダウンで波長範囲指定
        select_layout = QtWidgets.QHBoxLayout()
        select_layout.addWidget(QtWidgets.QLabel("波長範囲:"))
        self.wl_min_combo = QtWidgets.QComboBox()
        self.wl_max_combo = QtWidgets.QComboBox()
        self.range_plot_btn = QtWidgets.QPushButton("この範囲で時間プロット")
        self.range_plot_btn.clicked.connect(self.plot_intensity_vs_time)
        select_layout.addWidget(self.wl_min_combo)
        select_layout.addWidget(QtWidgets.QLabel("〜"))
        select_layout.addWidget(self.wl_max_combo)
        select_layout.addWidget(self.range_plot_btn)
        layout.addLayout(select_layout)

        # matplotlib FigureとToolbar
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.setLayout(layout)
        self.wavelengths = None
        self.t_axis = None
        self.data = None

    def load_csv(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, "CSVファイルを開く", "", "CSV files (*.csv)")
        if not fname:
            return
        self.file_label.setText(fname)
        try:
            df = pd.read_csv(fname, index_col=None)
            if df.shape[1] < 3:
                QtWidgets.QMessageBox.warning(self, "エラー", "列数が不足しています。")
                return

            # 1列目：波長, 2列目以降：各時刻(fs)の強度
            self.wavelengths = np.array(df.iloc[:, 0].values.astype(float))
            self.t_axis = np.array([float(h) for h in df.columns[1:]])
            self.data = df.iloc[:, 1:].values.astype(float)

            # 波長を昇順でリストにしてプルダウンへ
            wl_list = list(np.round(np.sort(self.wavelengths), 2))
            self.wl_min_combo.clear()
            self.wl_max_combo.clear()
            for w in wl_list:
                self.wl_min_combo.addItem(f"{w:.2f}")
                self.wl_max_combo.addItem(f"{w:.2f}")
            # デフォルト：最小、最大
            self.wl_min_combo.setCurrentIndex(0)
            self.wl_max_combo.setCurrentIndex(len(wl_list) - 1)

            self.show_imshow()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "読み込みエラー", f"エラー内容: {e}")

    def show_imshow(self):
        self.figure.clf()
        ax = self.figure.add_subplot(111)
        im = ax.imshow(
            self.data,
            aspect='auto',
            origin='lower',
            extent=[self.t_axis[0], self.t_axis[-1], self.wavelengths[0], self.wavelengths[-1]],
            interpolation='nearest'
        )
        ax.set_xlabel("Delay [fs]")
        ax.set_ylabel("Wavelength [nm]")
        ax.set_title("CSVからの2Dスペクトル")
        cbar = self.figure.colorbar(im, ax=ax, orientation='vertical')
        cbar.set_label("Intensity")
        self.canvas.draw()

    def plot_intensity_vs_time(self):
        if self.data is None or self.wavelengths is None or self.t_axis is None:
            QtWidgets.QMessageBox.warning(self, "エラー", "まずCSVファイルを読み込んでください。")
            return
        try:
            wl_min = float(self.wl_min_combo.currentText())
            wl_max = float(self.wl_max_combo.currentText())
        except Exception:
            QtWidgets.QMessageBox.warning(self, "エラー", "波長の選択が不正です。")
            return
        if wl_min > wl_max:
            wl_min, wl_max = wl_max, wl_min
        idx = np.where((self.wavelengths >= wl_min) & (self.wavelengths <= wl_max))[0]
        if len(idx) == 0:
            QtWidgets.QMessageBox.warning(self, "エラー", "指定範囲にデータがありません。")
            return
        selected = self.data[idx, :]  # shape: [波長本数, 時刻本数]
        mean_intensity = np.mean(selected, axis=0)

        # 別ウィンドウで描画
        win = QtWidgets.QWidget()
        win.setWindowTitle(f"Intensity vs Time（{wl_min:.2f}〜{wl_max:.2f} nm）")
        vlayout = QtWidgets.QVBoxLayout()
        fig = Figure(figsize=(7, 3.5))
        canvas = FigureCanvas(fig)
        vlayout.addWidget(canvas)
        ax = fig.add_subplot(111)
        ax.plot(self.t_axis, mean_intensity, marker='o')
        ax.set_xlabel("Delay [fs]")
        ax.set_ylabel("Mean Intensity")
        ax.set_title(f"平均強度 vs 時間\n（波長 {wl_min:.2f}〜{wl_max:.2f} nm）")
        ax.grid(True)
        canvas.draw()
        win.setLayout(vlayout)
        win.resize(600, 350)
        win.show()
        self._popup = win

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = CSVImshowGUI()
    window.show()
    sys.exit(app.exec_())
