import sys
import time
import pyvisa
from PyQt5 import QtWidgets, QtCore
from gui import Ui_MainWindow  # GUI file


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # --- VISA Initialization ---
        self.rm = pyvisa.ResourceManager(r"C:\Windows\System32\visa64.dll")
        print("VISA resources visible:", self.rm.list_resources())

        # --- Device VISA Addresses ---
        self.visa_dc = 'USB0::0x0957::0x1107::MY55000176::0::INSTR'  # DC SAS
        self.visa_ac = 'USB0::0x0957::0x1107::MY55000177::0::INSTR'  # AC SAS
        self.visa_grid = 'USB0::0x2A8D::0x1A02::JPCQ005523::0::INSTR'# Grid

        # --- Connect to instruments ---
        self.inst_dc = self.connect_instrument(self.visa_dc, "DC SAS")
        self.inst_ac = self.connect_instrument(self.visa_ac, "AC SAS")
        self.inst_grid = self.connect_instrument(self.visa_grid, "Grid")

        # --- Start periodic updates ---
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_power_display)
        self.timer.start(1000)  # 1-second refresh interval

    # ---------------------------------------------------------------
    def connect_instrument(self, visa_address, label):
        """Connect to a VISA instrument and return its handle."""
        try:
            inst = self.rm.open_resource(visa_address)
            inst.timeout = 3000  # ms
            inst.clear()
            idn = inst.query("*IDN?").strip()
            print(f"Connected to {label}: {idn}")
            return inst
        except Exception as e:
            print(f"Failed to connect to {label} ({visa_address}):", e)
            return None

    # ---------------------------------------------------------------
    def update_power_display(self):
        """Query each instrument for its power and update GUI labels."""

        # --- DC SAS ---
        if self.inst_dc:
            try:
                v_dc = float(self.inst_dc.query("MEAS:VOLT?"))
                i_dc = float(self.inst_dc.query("MEAS:CURR?"))
                p_dc = v_dc * i_dc
                self.DC_SAS_Power.setText(f"{p_dc:.2f} W")
            except Exception as e:
                print("DC SAS read error:", e)
            time.sleep(0.05)

        # --- AC SAS ---
        if self.inst_ac:
            try:
                v_ac = float(self.inst_ac.query("MEAS:VOLT?"))
                i_ac = float(self.inst_ac.query("MEAS:CURR?"))
                p_ac = v_ac * i_ac
                self.AC_SAS_Power.setText(f"{p_ac:.2f} W")
            except Exception as e:
                print("AC SAS read error:", e)
            time.sleep(0.05)

        # --- AC6801B Grid Source ---
        if self.inst_grid:
            try:
                # The AC6801B supports a direct power measurement
                p_grid = float(self.inst_grid.query("MEAS:POW:AC?"))
                self.Grid_Power.setText(f"{p_grid:.2f} W")
            except Exception as e:
                print("Grid Source read error:", e)

    # ---------------------------------------------------------------
    def closeEvent(self, event):
        """Safely close VISA sessions and stop updates."""
        self.timer.stop()
        instruments = [
            (self.inst_dc, "DC SAS"),
            (self.inst_ac, "AC SAS"),
            (self.inst_grid, "Grid Source")
        ]
        for inst, label in instruments:
            if inst:
                try:
                    inst.close()
                    print(f"{label} connection closed.")
                except Exception as e:
                    print(f"Error closing {label}:", e)
        event.accept()


# ---------------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
