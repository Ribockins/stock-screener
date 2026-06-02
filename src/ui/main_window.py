"""Desktop Application Main Window - Real-time Stock Signal Monitor"""

import sys
import logging
from datetime import datetime
from typing import List, Dict, Optional
from threading import Thread, Lock
import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QSpinBox, QCheckBox, QDialog, QTabWidget,
    QStatusBar, QMenu, QMenuBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QColor, QIcon, QFont, QSystemTrayIcon
from PyQt6.QtWidgets import QApplication

from src.screener import StockScreener
import rsiconfig

logger = logging.getLogger(__name__)


class ScannerWorker(QObject):
    """Worker thread for running screener without blocking UI"""
    
    scan_finished = pyqtSignal(dict)  # Emits results
    scan_error = pyqtSignal(str)      # Emits error message
    
    def __init__(self):
        super().__init__()
        self.screener = StockScreener()
    
    def run_scan(self):
        """Run full market scan"""
        try:
            logger.info("Starting scan from worker thread...")
            results = self.screener.scan_all_markets()
            self.scan_finished.emit(results)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.scan_error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Signal Monitor v1.0")
        self.setGeometry(100, 100, 1400, 800)
        
        # Data
        self.current_results = {}
        self.scan_lock = Lock()
        
        # Setup UI
        self.setup_ui()
        self.setup_tray()
        self.setup_threads()
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.run_scan)
        
        logger.info("Main window initialized")
    
    def setup_ui(self):
        """Setup main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Top control panel
        control_layout = QHBoxLayout()
        
        # Scan button
        self.scan_btn = QPushButton("🔍 Scan Now")
        self.scan_btn.clicked.connect(self.run_scan)
        self.scan_btn.setFixedSize(120, 40)
        control_layout.addWidget(self.scan_btn)
        
        # Auto-scan checkbox
        self.auto_scan_cb = QCheckBox("Auto-scan")
        self.auto_scan_cb.setChecked(True)
        self.auto_scan_cb.stateChanged.connect(self.toggle_auto_scan)
        control_layout.addWidget(self.auto_scan_cb)
        
        # Update interval spinbox
        control_layout.addWidget(QLabel("Update interval (min):"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(120)
        self.interval_spinbox.setValue(30)  # 30 minutes default
        self.interval_spinbox.valueChanged.connect(self.update_interval_changed)
        control_layout.addWidget(self.interval_spinbox)
        
        # Filter by strength
        control_layout.addWidget(QLabel("Filter by strength:"))
        self.strength_filter = QComboBox()
        self.strength_filter.addItems(["ALL", "PREMIUM_WARNING", "VERY_STRONG", "STRONG", "MEDIUM", "WEAK"])
        self.strength_filter.currentTextChanged.connect(self.apply_filters)
        control_layout.addWidget(self.strength_filter)
        
        # Filter by market
        control_layout.addWidget(QLabel("Market:"))
        self.market_filter = QComboBox()
        self.market_filter.addItems(["ALL"] + list(rsiconfig.STOCK_LISTS.keys()))
        self.market_filter.currentTextChanged.connect(self.apply_filters)
        control_layout.addWidget(self.market_filter)
        
        # Stats label
        self.stats_label = QLabel("Ready")
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        control_layout.addStretch()
        control_layout.addWidget(self.stats_label)
        
        layout.addLayout(control_layout)
        
        # Signals table
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(11)
        self.signals_table.setHorizontalHeaderLabels([
            "Symbol", "Market", "Price", "RSI", "Signal Strength",
            "Confidence", "MACD Div", "Vol Div", "Key Level", "Wick", "Updated"
        ])
        self.signals_table.setColumnWidth(0, 80)    # Symbol
        self.signals_table.setColumnWidth(1, 80)    # Market
        self.signals_table.setColumnWidth(2, 80)    # Price
        self.signals_table.setColumnWidth(3, 60)    # RSI
        self.signals_table.setColumnWidth(4, 140)   # Signal Strength
        self.signals_table.setColumnWidth(5, 100)   # Confidence
        self.signals_table.setColumnWidth(6, 80)    # MACD Div
        self.signals_table.setColumnWidth(7, 80)    # Vol Div
        self.signals_table.setColumnWidth(8, 80)    # Key Level
        self.signals_table.setColumnWidth(9, 60)    # Wick
        self.signals_table.setColumnWidth(10, 120)  # Updated
        
        self.signals_table.itemDoubleClicked.connect(self.show_signal_details)
        layout.addWidget(self.signals_table)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_tray(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Stock Signal Monitor")
        
        # Tray menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        hide_action = tray_menu.addAction("Hide")
        hide_action.triggered.connect(self.hide)
        tray_menu.addSeparator()
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def setup_threads(self):
        """Setup worker threads"""
        self.scanner_thread = QThread()
        self.scanner_worker = ScannerWorker()
        self.scanner_worker.moveToThread(self.scanner_thread)
        
        self.scanner_worker.scan_finished.connect(self.on_scan_finished)
        self.scanner_worker.scan_error.connect(self.on_scan_error)
        
        self.scanner_thread.start()
    
    def run_scan(self):
        """Trigger a scan"""
        if not self.scan_lock.acquire(blocking=False):
            logger.warning("Scan already in progress")
            return
        
        try:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("⏳ Scanning...")
            self.statusBar().showMessage("Scanning markets...")
            
            # Run scan in worker thread
            self.scanner_worker.run_scan()
        finally:
            self.scan_lock.release()
    
    def on_scan_finished(self, results: dict):
        """Handle scan completion"""
        try:
            with self.scan_lock:
                self.current_results = results
            
            self.update_table()
            self.update_stats()
            
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("🔍 Scan Now")
            self.statusBar().showMessage(f"Scan complete - {datetime.now().strftime('%H:%M:%S')}")
            
            logger.info(f"Scan finished: {sum(len(r) for r in results.values())} signals found")
            
            # Play sound if PREMIUM signals found
            self.check_premium_signals()
            
        except Exception as e:
            logger.error(f"Error processing scan results: {e}")
    
    def on_scan_error(self, error_msg: str):
        """Handle scan error"""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔍 Scan Now")
        self.statusBar().showMessage(f"Scan error: {error_msg}")
        logger.error(f"Scan failed: {error_msg}")
    
    def update_table(self):
        """Update signals table with current results"""
        try:
            self.signals_table.setRowCount(0)
            
            all_signals = []
            for market, signals in self.current_results.items():
                for signal in signals:
                    signal['market'] = market
                    all_signals.append(signal)
            
            # Sort by confidence (descending)
            all_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Apply filters
            all_signals = self.apply_filters_to_signals(all_signals)
            
            # Add rows
            for row_idx, signal in enumerate(all_signals):
                self.signals_table.insertRow(row_idx)
                
                # Symbol
                symbol_item = QTableWidgetItem(signal.get('symbol', ''))
                self.signals_table.setItem(row_idx, 0, symbol_item)
                
                # Market
                market_item = QTableWidgetItem(signal.get('market', ''))
                self.signals_table.setItem(row_idx, 1, market_item)
                
                # Price
                price_item = QTableWidgetItem(f"{signal.get('price', 0):.2f}")
                self.signals_table.setItem(row_idx, 2, price_item)
                
                # RSI
                rsi_item = QTableWidgetItem(f"{signal.get('rsi', 0):.1f}")
                self.signals_table.setItem(row_idx, 3, rsi_item)
                
                # Signal Strength
                strength = signal.get('signal_strength', 'UNKNOWN')
                strength_item = QTableWidgetItem(strength)
                strength_item.setText(strength)
                
                # Color code by strength
                if strength == 'PREMIUM_WARNING':
                    strength_item.setBackground(QColor(0, 200, 0))  # Green
                    strength_item.setForeground(QColor(255, 255, 255))
                elif strength == 'VERY_STRONG':
                    strength_item.setBackground(QColor(255, 200, 0))  # Yellow
                elif strength == 'STRONG':
                    strength_item.setBackground(QColor(255, 150, 0))  # Orange
                elif strength == 'MEDIUM':
                    strength_item.setBackground(QColor(200, 200, 200))  # Gray
                
                self.signals_table.setItem(row_idx, 4, strength_item)
                
                # Confidence
                conf_item = QTableWidgetItem(f"{signal.get('confidence', 0):.0%}")
                self.signals_table.setItem(row_idx, 5, conf_item)
                
                # MACD Divergence
                macd_div = "✓" if signal.get('macd_divergence') else "✗"
                self.signals_table.setItem(row_idx, 6, QTableWidgetItem(macd_div))
                
                # Volume Divergence
                vol_div = "✓" if signal.get('volume_divergence') else "✗"
                self.signals_table.setItem(row_idx, 7, QTableWidgetItem(vol_div))
                
                # Key Level
                key_level = "✓" if signal.get('key_level_nearby') else "✗"
                self.signals_table.setItem(row_idx, 8, QTableWidgetItem(key_level))
                
                # Wick
                wick = "✓" if signal.get('wick_present') else "✗"
                self.signals_table.setItem(row_idx, 9, QTableWidgetItem(wick))
                
                # Updated time
                timestamp = signal.get('timestamp')
                if timestamp:
                    time_str = timestamp.strftime('%H:%M:%S')
                else:
                    time_str = datetime.now().strftime('%H:%M:%S')
                self.signals_table.setItem(row_idx, 10, QTableWidgetItem(time_str))
        
        except Exception as e:
            logger.error(f"Error updating table: {e}")
    
    def apply_filters_to_signals(self, signals: List[Dict]) -> List[Dict]:
        """Apply active filters to signals list"""
        strength_filter = self.strength_filter.currentText()
        market_filter = self.market_filter.currentText()
        
        filtered = signals
        
        if strength_filter != "ALL":
            filtered = [s for s in filtered if s.get('signal_strength') == strength_filter]
        
        if market_filter != "ALL":
            filtered = [s for s in filtered if s.get('market') == market_filter]
        
        return filtered
    
    def apply_filters(self):
        """Re-apply filters and update table"""
        self.update_table()
    
    def update_stats(self):
        """Update statistics label"""
        try:
            total_signals = sum(len(signals) for signals in self.current_results.values())
            
            premium_count = 0
            very_strong_count = 0
            strong_count = 0
            
            for signals in self.current_results.values():
                for sig in signals:
                    if sig.get('signal_strength') == 'PREMIUM_WARNING':
                        premium_count += 1
                    elif sig.get('signal_strength') == 'VERY_STRONG':
                        very_strong_count += 1
                    elif sig.get('signal_strength') == 'STRONG':
                        strong_count += 1
            
            stats_text = (
                f"Total: {total_signals} | "
                f"🟢 Premium: {premium_count} | "
                f"🟡 V.Strong: {very_strong_count} | "
                f"🟠 Strong: {strong_count}"
            )
            self.stats_label.setText(stats_text)
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
    
    def check_premium_signals(self):
        """Check for PREMIUM signals and play sound"""
        try:
            premium_count = 0
            for signals in self.current_results.values():
                for sig in signals:
                    if sig.get('signal_strength') == 'PREMIUM_WARNING':
                        premium_count += 1
            
            if premium_count > 0:
                self.play_notification_sound()
                self.tray_icon.showMessage(
                    "🟢 Premium Signal Found!",
                    f"{premium_count} premium signals detected!",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000  # 5 seconds
                )
        except Exception as e:
            logger.error(f"Error checking premium signals: {e}")
    
    def play_notification_sound(self):
        """Play notification sound"""
        try:
            import winsound
            winsound.Beep(1000, 500)  # Frequency=1000Hz, Duration=500ms
        except ImportError:
            logger.warning("winsound not available on this platform")
        except Exception as e:
            logger.error(f"Error playing sound: {e}")
    
    def show_signal_details(self, item):
        """Show detailed signal information"""
        row = item.row()
        symbol = self.signals_table.item(row, 0).text()
        
        # Find signal in current results
        target_signal = None
        for signals in self.current_results.values():
            for sig in signals:
                if sig.get('symbol') == symbol:
                    target_signal = sig
                    break
        
        if target_signal:
            self.show_details_dialog(target_signal)
    
    def show_details_dialog(self, signal: Dict):
        """Show detailed signal dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Signal Details - {signal.get('symbol')}")
        dialog.setGeometry(300, 300, 600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Create details text
        details_text = f"""
        <h2>{signal.get('symbol')}</h2>
        
        <b>Price:</b> ${signal.get('price', 0):.2f}<br>
        <b>Market:</b> {signal.get('market', 'N/A')}<br>
        <br>
        
        <b style="font-size: 14px; color: #0066cc;">Signal Strength Analysis</b><br>
        <b>Overall Strength:</b> <span style="color: #009900; font-weight: bold;">{signal.get('signal_strength')}</span><br>
        <b>Confidence:</b> {signal.get('confidence', 0):.0%}<br>
        <b>Factors Aligned:</b> {signal.get('factors_count', 0)}/7<br>
        <b>Recommendation:</b> {signal.get('recommendation', 'N/A')}<br>
        <br>
        
        <b style="font-size: 14px; color: #0066cc;">RSI Analysis</b><br>
        <b>RSI Value:</b> {signal.get('rsi', 0):.2f}<br>
        <b>RSI Signal:</b> {signal.get('rsi_signal', 'N/A')}<br>
        <b>RSI Divergence:</b> {'✓ Yes' if signal.get('rsi_divergence') else '✗ No'}<br>
        <br>
        
        <b style="font-size: 14px; color: #0066cc;">MACD Analysis</b><br>
        <b>MACD Histogram:</b> {signal.get('macd_histogram', 0):.4f}<br>
        <b>MACD Weakening:</b> {'✓ Yes' if signal.get('macd_weakening') else '✗ No'}<br>
        <b>MACD Divergence:</b> {'✓ Yes' if signal.get('macd_divergence') else '✗ No'}<br>
        <br>
        
        <b style="font-size: 14px; color: #0066cc;">Additional Factors</b><br>
        <b>Volume Divergence:</b> {'✓ Yes' if signal.get('volume_divergence') else '✗ No'}<br>
        <b>Key Level Nearby:</b> {'✓ Yes' if signal.get('key_level_nearby') else '✗ No'}<br>
        <b>Key Level Distance:</b> {signal.get('key_level_distance', 0):.2f}%<br>
        <b>Wick Present:</b> {'✓ Yes' if signal.get('wick_present') else '✗ No'}<br>
        <b>Wick Strength:</b> {signal.get('wick_strength', 'N/A')}<br>
        <br>
        
        <b style="font-size: 14px; color: #0066cc;">Price Action</b><br>
        <b>Divergence Type:</b> {signal.get('divergence_type', 'NONE')}<br>
        <b>Divergence Strength:</b> {signal.get('divergence_strength', 'N/A')}<br>
        """
        
        label = QLabel(details_text)
        label.setStyleSheet("QLabel { padding: 10px; }")
        layout.addWidget(label)
        
        dialog.exec()
    
    def toggle_auto_scan(self):
        """Toggle auto-scanning"""
        if self.auto_scan_cb.isChecked():
            self.update_timer.start(self.interval_spinbox.value() * 60 * 1000)
            self.statusBar().showMessage("Auto-scan enabled")
        else:
            self.update_timer.stop()
            self.statusBar().showMessage("Auto-scan disabled")
    
    def update_interval_changed(self):
        """Update auto-scan interval"""
        if self.auto_scan_cb.isChecked():
            self.update_timer.stop()
            self.update_timer.start(self.interval_spinbox.value() * 60 * 1000)
    
    def closeEvent(self, event):
        """Handle window close"""
        self.scanner_thread.quit()
        self.scanner_thread.wait()
        super().closeEvent(event)
