# main.py
# -*- coding: utf-8 -*-
# Combined GUI + SAS Power Readout
import sys
import pyvisa as visa
from PyQt5 import QtWidgets, QtCore
from gui import Ui_MainWindow


class SASReader(QtCore.QThread):
    """Thread to continuously read voltage and current from the SAS."""
    data_ready = QtCore.pyqtSignal(float, float, float)  # voltage, current, power

    def __init__(self, visa_address, parent=None):
        super().__init__(parent)
        self.visa_address = visa_address
        self.running = True

    def run(self):
        rm = visa.ResourceManager(r"C:\Windows\System32\visa32.dll")

        try:
            inst = rm.open_resource(self.visa_address)
            inst.timeout = 5000
            inst.clear()
            print(f"Connected to: {inst.query('*IDN?').strip()}")
        except Exception as e:
            print(f"Connection failed: {e}")
            return

        while self.running:
            try:
                # Query voltage and current
                voltage = float(inst.query("MEAS:VOLT?"))
                current = float(inst.query("MEAS:CURR?"))
                power = voltage * current

                # Emit to GUI
                self.data_ready.emit(voltage, current, power)

                # Update every 1 second (adjust as needed)
                self.msleep(1000)

            except Exception as e:
                print(f"Read error: {e}")
                self.running = False

        inst.close()
        print("SAS connection closed.")

    def stop(self):
        self.running = False
        self.wait()


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # VISA address for the SAS
        self.visa_address = 'USB0::0x0957::0x1107::MY55000176::0::INSTR'

        # Start SAS reading thread
        self.sas_thread = SASReader(self.visa_address)
        self.sas_thread.data_ready.connect(self.update_power_display)
        self.sas_thread.start()

    def update_power_display(self, voltage, current, power):
        """Update GUI labels with SAS readings."""
        self.DC_SAS_Power.setText(f"{power:.2f} W")

    def closeEvent(self, event):
        """Ensure clean thread shutdown on window close."""
        self.sas_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
