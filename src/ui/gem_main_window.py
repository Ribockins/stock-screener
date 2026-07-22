"""GEM Platform desktop UI — watchlist, live scan, GEM Logic signals."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from PyQt6.QtCore import Qt, QTimer
from threading import Thread
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gem.models import GEMAnalysis
from src.gem_platform import GEMPlatform
from src.watchlist import load_watchlist, save_watchlist, watchlist_path

logger = logging.getLogger(__name__)


class GemMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEM Logic Platform")
        self.setGeometry(80, 80, 1500, 850)

        self.platform = GEMPlatform()
        self.current_results: List[GEMAnalysis] = []
        self._scan_running = False

        self._build_ui()
        self._setup_timer()
        self._load_watchlist_hint()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        controls = QHBoxLayout()
        self.scan_btn = QPushButton("Scan watchlist now")
        self.scan_btn.clicked.connect(self.run_scan)
        controls.addWidget(self.scan_btn)

        self.auto_cb = QCheckBox("Auto-refresh")
        self.auto_cb.setChecked(True)
        self.auto_cb.stateChanged.connect(self._toggle_timer)
        controls.addWidget(self.auto_cb)

        controls.addWidget(QLabel("Interval (min):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(5)
        self.interval_spin.valueChanged.connect(self._reset_timer)
        controls.addWidget(self.interval_spin)

        self.edit_watchlist_btn = QPushButton("Edit watchlist…")
        self.edit_watchlist_btn.clicked.connect(self._edit_watchlist)
        controls.addWidget(self.edit_watchlist_btn)

        self.status_label = QLabel("Ready")
        controls.addStretch()
        controls.addWidget(self.status_label)
        layout.addLayout(controls)

        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Price", "RSI", "Signal", "Exec", "GEM",
            "Setup", "Entry", "Score", "Div events", "S/R", "Updated",
        ])
        self.table.itemDoubleClicked.connect(self._show_detail)
        layout.addWidget(self.table)

        self.timer = QTimer()
        self.timer.timeout.connect(self.run_scan)

    def _setup_timer(self):
        self._reset_timer()
        if self.auto_cb.isChecked():
            self.timer.start()

    def _toggle_timer(self):
        if self.auto_cb.isChecked():
            self._reset_timer()
        else:
            self.timer.stop()

    def _reset_timer(self):
        self.timer.stop()
        if self.auto_cb.isChecked():
            ms = self.interval_spin.value() * 60 * 1000
            self.timer.start(ms)

    def _load_watchlist_hint(self):
        wl = load_watchlist()
        n = len(wl.get("instruments", []))
        self.status_label.setText(f"Watchlist: {n} symbols — {watchlist_path()}")

    def run_scan(self):
        if self._scan_running:
            return
        self._scan_running = True
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning…")
        self.statusBar().showMessage("Fetching live data and running GEM Logic…")
        Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            results = self.platform.scan_watchlist()
            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            # use signal via invoke - simpler: schedule on main thread
            self._results_pending = results
            QTimer.singleShot(0, lambda: self._on_scan_done(results))
        except Exception as e:
            logger.exception("GEM scan failed")
            QTimer.singleShot(0, lambda: self._on_scan_error(str(e)))

    def _on_scan_done(self, results: list):
        self._scan_running = False
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan watchlist now")
        self.current_results = results
        self._fill_table(results)
        ts = datetime.now().strftime("%H:%M:%S")
        actionable = len(self.platform.priority_signals(results))
        self.statusBar().showMessage(
            f"Last scan {ts} — {len(results)} symbols, {actionable} actionable"
        )

    def _on_scan_error(self, msg: str):
        self._scan_running = False
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan watchlist now")
        QMessageBox.warning(self, "Scan error", msg)

    def _signal_label(self, r: GEMAnalysis) -> str:
        if r.buy_gem:
            return "EMERALD GEM"
        if r.sell_gem:
            return "RUBY GEM"
        if r.buy_entry:
            return "LONG ENTRY"
        if r.sell_entry:
            return "SHORT ENTRY"
        if r.buy_setup:
            return "BUY SETUP (3 div)"
        if r.sell_setup:
            return "SELL SETUP (3 div)"
        if r.in_oversold:
            return "Oversold"
        if r.in_overbought:
            return "Overbought"
        return "—"

    def _fill_table(self, results: List[GEMAnalysis]):
        self.table.setRowCount(0)
        for row, r in enumerate(results):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r.symbol))
            self.table.setItem(row, 1, QTableWidgetItem(f"{r.price:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{r.rsi:.1f}"))

            sig_item = QTableWidgetItem(self._signal_label(r))
            if r.buy_gem:
                sig_item.setBackground(QColor(0, 180, 120))
            elif r.sell_gem:
                sig_item.setBackground(QColor(200, 40, 80))
            elif r.buy_entry or r.buy_setup:
                sig_item.setBackground(QColor(80, 140, 220))
            elif r.sell_entry or r.sell_setup:
                sig_item.setBackground(QColor(220, 120, 80))
            self.table.setItem(row, 3, sig_item)

            self.table.setItem(row, 4, QTableWidgetItem(r.exec_state))
            gem_txt = "BUY" if r.buy_gem else "SELL" if r.sell_gem else "—"
            self.table.setItem(row, 5, QTableWidgetItem(gem_txt))
            setup = "BUY" if r.buy_setup else "SELL" if r.sell_setup else "—"
            self.table.setItem(row, 6, QTableWidgetItem(setup))
            entry = "LONG" if r.buy_entry else "SHORT" if r.sell_entry else "—"
            self.table.setItem(row, 7, QTableWidgetItem(entry))
            self.table.setItem(row, 8, QTableWidgetItem(str(r.gem_score)))
            self.table.setItem(
                row, 9,
                QTableWidgetItem(f"B{r.buy_div_events}/S{r.sell_div_events}"),
            )
            sr = []
            if r.near_support:
                sr.append("S")
            if r.near_resistance:
                sr.append("R")
            self.table.setItem(row, 10, QTableWidgetItem("".join(sr) or "—"))
            self.table.setItem(row, 11, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def _show_detail(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.current_results):
            return
        r = self.current_results[row]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"GEM — {r.symbol}")
        dlg.resize(520, 480)
        lay = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        d = r.to_dict()
        lines = [
            f"<h2>{r.symbol}</h2>",
            f"<b>{r.recommendation}</b><p>",
            f"Price: ${r.price:.2f} | RSI: {r.rsi:.1f}<br>",
            f"Exec: {r.exec_state} | Divergence: {r.divergence_state}<br>",
            f"Buy div events (lookback): {r.buy_div_events} | Sell: {r.sell_div_events}<br>",
            f"GEM score: {r.gem_score}<br>",
            f"Bull candle: {r.bull_candle} | Bear: {r.bear_candle}<br>",
            f"Near support: {r.near_support} | Near resistance: {r.near_resistance}<br>",
        ]
        if r.stop_price:
            lines.append(
                f"Stop: {r.stop_price:.2f} | TP1: {r.tp1_price:.2f} | TP2: {r.tp2_price:.2f}<br>"
            )
        lines.append(f"<small>Data: {r.data_source}</small>")
        text.setHtml("\n".join(lines))
        lay.addWidget(text)
        dlg.exec()

    def _edit_watchlist(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit watchlist (JSON)")
        dlg.resize(600, 400)
        lay = QVBoxLayout(dlg)
        editor = QTextEdit()
        wl = load_watchlist()
        editor.setPlainText(json.dumps(wl, indent=2))
        lay.addWidget(editor)
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

        def do_save():
            try:
                data = json.loads(editor.toPlainText())
                save_watchlist(data)
                self._load_watchlist_hint()
                dlg.accept()
            except json.JSONDecodeError as e:
                QMessageBox.warning(dlg, "Invalid JSON", str(e))

        save_btn.clicked.connect(do_save)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
