# -*- coding: utf-8 -*-
import sys
import csv
import codecs
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton,
    QVBoxLayout, QWidget, QMessageBox
)

def load_data(filename):
    """
    - UTF-8 BOM, Shift_JIS など自動判別
    - 空行スキップ
    - 1行目が全セル float なら「波長行」とみなす
    - 2行目以降を intensity rows として読み込み
    - 時間軸は行番号を使う
    """
    # 1) 文字コード判別＋CSV読み込み
    encodings = ['utf-8-sig', 'utf-8', 'cp932', 'shift_jis']
    rows = None
    for enc in encodings:
        try:
            with codecs.open(filename, 'r', encoding=enc) as f:
                reader = csv.reader(f)
                rows = [r for r in reader if any(cell.strip() for cell in r)]
            break
        except:
            rows = None
    if not rows or len(rows) < 2:
        raise ValueError("データ行がありません。\nファイルに2行目以降の数値があるかご確認ください。")

    # 2) 1行目を float にできるか試す
    first = rows[0]
    try:
        float_vals = list(map(float, first))
        # 全部 float に変換できた → 波長行とみなす
        wavelengths = float_vals
        data_rows = rows[1:]
        # 時間軸は行番号(0,1,2...)
        times = list(range(len(data_rows)))
    except:
        # 1行目がヘッダ文字列の場合 ("step", "178.2",...)
        header = [c.strip().lower() for c in first]
        if header[0] not in ('step','time','t'):
            raise ValueError("1行目がfloatでも'data'でもありません。\nstep,波長… の形式か、全floatの波長行を想定しています。")
        try:
            wavelengths = list(map(float, first[1:]))
        except Exception as e:
            raise ValueError(f"波長ヘッダのパース失敗: {e}")
        # 2行目以降は [time, ints…]
        data_rows = rows[1:]
        times = []
        for r in data_rows:
            try:
                times.append(float(r[0]))
            except:
                times.append(float('nan'))

    # 3) 強度データ部分を float 配列に
    intensity = []
    for r in data_rows:
        vals = r[1:] if len(r) > 1 else []
        try:
            intensity.append(list(map(float, vals)))
        except Exception as e:
            print(f"パースエラー: {e} 行={r}")
    if not intensity:
        raise ValueError("強度データが一つも読み込めませんでした")

    return wavelengths, times, intensity

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQt5 – FROG Data Viewer')
        self.setGeometry(100, 100, 400, 200)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        btn = QPushButton('Open FROG CSV', self)
        btn.clicked.connect(self._open_file)
        layout.addWidget(btn)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _open_file(self):
        opts = QFileDialog.Options()
        opts |= QFileDialog.ReadOnly
        fn, _ = QFileDialog.getOpenFileName(
            self, "Select FROG CSV", "", "CSV Files (*.csv);;All Files (*)", options=opts
        )
        if fn:
            self._plot_data(fn)

    def _plot_data(self, filename):
        try:
            wl, times, data = load_data(filename)
            arr = np.array(data)
            # バックグラウンド補正（最初の行を背景とみなす）
            bg = arr[0]
            adj = arr - bg
            adj[adj < 0] = 0

            plt.figure(figsize=(8,5))
            plt.imshow(
                adj.T,
                aspect='auto',
                cmap='nipy_spectral',
                origin='lower',
                extent=[times[0], times[-1], wl[0], wl[-1]]
            )
            plt.colorbar(label='Adjusted Intensity')
            plt.xlabel('Time / fs')
            plt.ylabel('Wavelength / nm')
            plt.ylim(min(wl), max(wl))
            plt.title('SHG-FROG')
            plt.tight_layout()
            plt.show()

        except Exception as e:
            QMessageBox.critical(
                self, "データエラー",
                f"ファイル読み込み／処理でエラーが発生しました:\n{e}"
            )

def main():
    app = QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
