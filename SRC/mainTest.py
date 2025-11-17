import sys
import pyvisa
import numpy as np
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
from guiTesting import Ui_MainWindow  # your converted .ui -> python file

# ----------------------------------------------------------------
# Background worker thread
# ----------------------------------------------------------------
class DataWorker(QtCore.QThread):
    data_ready = QtCore.pyqtSignal(dict)

    def __init__(self, inst_ac=None, inst_grid=None):
        super().__init__()
        self.inst_ac = inst_ac
        self.inst_grid = inst_grid
        self._running = True

    def run(self):
        while self._running:
            data = {}
            try:
                if self.inst_ac:
                    v_ac = float(self.inst_ac.query("MEAS:VOLT?"))
                    i_ac = float(self.inst_ac.query("MEAS:CURR?"))
                    data["sas_voltage"] = v_ac
                    data["sas_current"] = i_ac
                    data["sas_power"]   = v_ac * i_ac

                if self.inst_grid:
                    data["grid_power"] = float(self.inst_grid.query("MEAS:POW:AC?"))

            except Exception as e:
                print("Worker read error:", e)

            if data:
                self.data_ready.emit(data)

            self.msleep(250)

    def stop(self):
        self._running = False
        self.wait(1000)


# ----------------------------------------------------------------
# Main GUI Window
# ----------------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # VISA
        self.rm = pyvisa.ResourceManager(r"C:\\Windows\\System32\\visa64.dll")
        print("VISA resources visible:", self.rm.list_resources())

        # instrument addresses
        self.visa_sas = "USB0::0x0957::0x1107::MY55000177::0::INSTR"
        self.visa_grid = "USB0::0x2A8D::0x1A02::JPCQ005523::0::INSTR"

        self.inst_ac = self.connect_instrument(self.visa_sas, "SAS")
        self.inst_grid = self.connect_instrument(self.visa_grid, "Grid Source")

        # background worker
        self.worker = DataWorker(inst_ac=self.inst_ac, inst_grid=self.inst_grid)
        self.worker.data_ready.connect(self.update_display)
        self.worker.start()

        # nominal parameters
        self.isc_max = 4.25
        self.imp_max = 4.25 * 0.9
        self.voc_nom = 65.0
        self.vmp_nom = 60.0

        # graph bounds (fixed)
        self.x_max = 70.0
        self.y_max = 5.0

        # PV scale from your QGraphics version 
        self.PV_SCALE_FACTOR = 0.6 / 60.0  # ≈ 0.008333

        # iv graph setup
        self.init_iv_graphs()

        # slider debounce
        self.last_slider_val = None
        self.slider_timer = QtCore.QTimer()
        self.slider_timer.setSingleShot(True)
        self.slider_timer.timeout.connect(self.apply_slider_update)
        self.Irradiance_Slider.valueChanged.connect(self.on_slider_changed)

        # holds last SAS real MPP
        self.last_real_mpp_v = 0
        self.last_real_mpp_i = 0


    # ----------------------------------------------------------------
    def connect_instrument(self, visa_address, label):
        try:
            inst = self.rm.open_resource(visa_address)
            inst.timeout = 10000
            inst.clear()
            idn = inst.query("*IDN?").strip()
            print(f"Connected to {label}: {idn}")
            return inst
        except Exception as e:
            print(f"Failed to connect to {label} ({visa_address}):", e)
            return None


    # ----------------------------------------------------------------
    def on_slider_changed(self, value):
        self.last_slider_val = value
        self.slider_timer.start(250)


    # ----------------------------------------------------------------
    def apply_slider_update(self):
        if not self.inst_ac or self.last_slider_val is None:
            return

        try:
            scale = self.last_slider_val / 100.0
            isc = self.isc_max * scale
            imp = self.imp_max * scale
            voc = self.voc_nom * (0.98 + 0.02 * scale)
            vmp = self.vmp_nom * (0.98 + 0.02 * scale)

            if imp >= isc:
                imp = isc * 0.95

            # write SAS
            cmd = (
                f"CURR:SAS:ISC {isc:.3f},(@1);"
                f"IMP {imp:.3f},(@1);"
                f":VOLT:SAS:VMP {vmp:.3f},(@1);"
                f"VOC {voc:.3f},(@1)"
            )

            self.inst_ac.write(cmd)
            self.inst_ac.query("*OPC?")

            # regenerate theoretical I–V/P–V
            V, I, P = self.sas_iv_curve(voc, isc, vmp, imp)

            if len(V) == 0:
                return

            # -----------------------------
            # POWER CURVE SCALING 
            # -----------------------------
            P_scaled = P * self.PV_SCALE_FACTOR

            self.ac_curve_IV.setData(V, I)
            self.ac_curve_PV.setData(V, P_scaled)

        except Exception as e:
            print("Error applying irradiance scale:", e)


    # ----------------------------------------------------------------
    def sas_iv_curve(self, Voc, Isc, Vmp, Imp, points=2048):
        try:
            if Isc <= 0:
                return np.array([]), np.array([]), np.array([])

            if Imp >= Isc:
                Imp = Isc * 0.95

            Rs = (Voc - Vmp) / Imp
            a = (Vmp * (1 + (Rs * Isc / Voc)) + Rs * (Imp - Isc)) / Voc

            ratio = np.clip(Imp / Isc, 1e-9, 0.999999)

            baseN = np.clip(2 - 2**a, 1e-12, None)
            N = np.log(baseN) / np.log(ratio)

            I = np.linspace(Isc, 0, points)
            term = 2 - (I / Isc)**N
            term = np.clip(term, 1e-12, None)

            V = ((Voc * np.log(term) / np.log(2)) - Rs * (I - Isc)) / (1 + (Rs * Isc / Voc))
            P = V * I

            mask = np.isfinite(V) & (V >= 0)
            return V[mask], I[mask], P[mask]

        except Exception as e:
            print("IV error:", e)
            return np.array([]), np.array([]), np.array([])


    # ----------------------------------------------------------------
    def init_iv_graphs(self):
        self.pg_AC = pg.PlotWidget()
        layout_ac = QtWidgets.QVBoxLayout(self.AC_IV)
        layout_ac.addWidget(self.pg_AC)

        self.pg_AC.setBackground("w")
        self.pg_AC.addLegend()
        self.pg_AC.showGrid(x=True, y=True)
        self.pg_AC.setLabel("bottom", "Voltage (V)")
        self.pg_AC.setLabel("left", "Current (A) / Power (scaled)")
        self.pg_AC.setTitle("AC SAS I-V and P-V Curve")

        self.pg_AC.setXRange(0, self.x_max)
        self.pg_AC.setYRange(0, self.y_max)
        self.pg_AC.enableAutoRange(False, False)

        self.ac_curve_IV = self.pg_AC.plot(pen=pg.mkPen("b", width=2), name="I-V")
        self.ac_curve_PV = self.pg_AC.plot(pen=pg.mkPen("orange", width=2), name="P-V (scaled)")

        # REAL SAS MPP marker (new behavior)
        self.ac_mpp_real = self.pg_AC.plot(symbol="x", symbolBrush="g", symbolSize=14, name="SAS MPP")


    # ----------------------------------------------------------------
    def update_display(self, data):

        # update SAS values
        if "sas_power" in data:
            p = data["sas_power"]
            v = data["sas_voltage"]
            i = data["sas_current"]

            self.AC_SAS_Power.setText(f"{p:.2f} W")

            # update *real* MPP marker (SAS live)
            self.ac_mpp_real.setData([v], [i])


        # update grid if present
        if "grid_power" in data:
            self.Grid_Power.setText(f"{data['grid_power']:.2f} W")


    # ----------------------------------------------------------------
    def closeEvent(self, event):
        print("Closing application...")
        self.worker.stop()
        for inst, label in [(self.inst_ac, "SAS"), (self.inst_grid, "Grid Source")]:
            if inst:
                try:
                    inst.write("OUTP OFF")
                    inst.close()
                    print(f"{label} connection closed.")
                except Exception as e:
                    print(f"Error closing {label}:", e)
        event.accept()


# ----------------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
