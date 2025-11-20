import sys
import pyvisa
import numpy as np
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

from guiTesting import Ui_MainWindow
from pymodbus.client import ModbusSerialClient


# ----------------------------------------------------------------
# Background worker thread
# ----------------------------------------------------------------
class DataWorker(QtCore.QThread):
    data_ready = QtCore.pyqtSignal(dict)

    def __init__(self, inst_ac=None, inst_grid=None, inst_pm=None):
        super().__init__()
        self.inst_ac = inst_ac
        self.inst_grid = inst_grid
        self.inst_pm = inst_pm     # EM511 Modbus client
        self._running = True

    def run(self):
        while self._running:
            data = {}

            try:
                # ------------------------------
                # SAS Power (DC)
                # ------------------------------
                if self.inst_ac:
                    v = float(self.inst_ac.query("MEAS:VOLT?"))
                    i = float(self.inst_ac.query("MEAS:CURR?"))
                    data["sas_voltage"] = v
                    data["sas_current"] = i
                    data["sas_power"] = v * i

                # ------------------------------
                # Grid Power
                # ------------------------------
                if self.inst_grid:
                    data["grid_power"] = float(self.inst_grid.query("MEAS:POW:AC?"))

                # ------------------------------
                # EM511 Microinverter Actual AC Power
                # ------------------------------
                if self.inst_pm:
                    rr = self.inst_pm.read_holding_registers(
                        address=0x0004, count=2, slave=1
                    )
                    if not rr.isError():
                        lsw, msw = rr.registers[0], rr.registers[1]
                        raw32 = (msw << 16) | lsw
                        if raw32 & 0x80000000:
                            raw32 -= 0x100000000
                        microinv_actual = raw32 / 10.0
                        data["microinv_actual"] = microinv_actual
                    else:
                        print("EM511 Modbus error:", rr)

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
        print("VISA:", self.rm.list_resources())

        # VISA Instruments
        self.visa_sas  = "USB0::0x0957::0x1107::MY55000177::0::INSTR"
        self.visa_grid = "USB0::0x2A8D::0x1A02::JPCQ005523::0::INSTR"

        self.inst_ac = self.connect_instrument(self.visa_sas, "SAS")
        self.inst_grid = self.connect_instrument(self.visa_grid, "Grid")

        # ---------------------------------------------------
        # EM511 Modbus RS485
        # ---------------------------------------------------
        self.pm = ModbusSerialClient(
            port="COM6",  # <-- UPDATE THIS---------------------------------------------------
            baudrate=9600,
            parity="E",
            stopbits=1,
            bytesize=8,
            timeout=1.0
        )

        if self.pm.connect():
            print("Connected to EM511.")
        else:
            print("Failed to connect to EM511.")

        # ---------------------------------------------------
        # Rolling average buffers (5-sample window)
        # ---------------------------------------------------
        self.sas_hist = []
        self.microinv_hist = []

        # ---------------------------------------------------
        # Worker thread
        # ---------------------------------------------------
        self.worker = DataWorker(
            inst_ac=self.inst_ac,
            inst_grid=self.inst_grid,
            inst_pm=self.pm
        )
        self.worker.data_ready.connect(self.update_display)
        self.worker.start()

        # -------------------------
        # IV curve setup (unchanged)
        # -------------------------
        self.isc_max = 4.25
        self.imp_max = 4.25 * 0.9
        self.voc_nom = 65.0
        self.vmp_nom = 60.0

        self.x_max = 70
        self.y_max = 5

        self.PV_SCALE_FACTOR = 0.6 / 60.0

        self.init_iv_graphs()

        self.last_slider_val = None
        self.slider_timer = QtCore.QTimer()
        self.slider_timer.setSingleShot(True)
        self.slider_timer.timeout.connect(self.apply_slider_update)
        self.Irradiance_Slider.valueChanged.connect(self.on_slider_changed)


    # ---------------------------------------------------
    def connect_instrument(self, visa_address, label):
        try:
            inst = self.rm.open_resource(visa_address)
            inst.timeout = 10000
            inst.clear()
            print(f"Connected to {label}: {inst.query('*IDN?').strip()}")
            return inst
        except Exception as e:
            print(f"Failed to connect to {label}:", e)
            return None

    # ---------------------------------------------------
    def on_slider_changed(self, value):
        self.last_slider_val = value
        self.slider_timer.start(250)

    # ---------------------------------------------------
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

            cmd = (
                f"CURR:SAS:ISC {isc:.3f},(@1);"
                f"IMP {imp:.3f},(@1);"
                f":VOLT:SAS:VMP {vmp:.3f},(@1);"
                f"VOC {voc:.3f},(@1)"
            )
            self.inst_ac.write(cmd)
            self.inst_ac.query("*OPC?")

            V, I, P = self.sas_iv_curve(voc, isc, vmp, imp)
            if len(V) > 0:
                self.ac_curve_IV.setData(V, I)
                self.ac_curve_PV.setData(V, P * self.PV_SCALE_FACTOR)

        except Exception as e:
            print("Irradiance error:", e)

    # ---------------------------------------------------
    def sas_iv_curve(self, Voc, Isc, Vmp, Imp, points=2048):
        try:
            if Isc <= 0:
                return np.array([]), np.array([]), np.array([])

            if Imp >= Isc:
                Imp = Isc * 0.95

            Rs = (Voc - Vmp) / Imp
            a = (Vmp*(1+(Rs*Isc/Voc)) + Rs*(Imp-Isc)) / Voc

            ratio = np.clip(Imp/Isc, 1e-9, 0.999999)
            N = np.log(np.clip(2 - 2**a, 1e-12, None)) / np.log(ratio)

            I = np.linspace(Isc, 0, points)
            term = np.clip(2 - (I/Isc)**N, 1e-12, None)

            V = ((Voc * np.log(term)/np.log(2)) - Rs*(I-Isc)) / (1 + (Rs*Isc/Voc))
            P = V * I

            mask = np.isfinite(V) & (V >= 0)
            return V[mask], I[mask], P[mask]

        except:
            return np.array([]), np.array([]), np.array([])

    # ---------------------------------------------------
    def init_iv_graphs(self):
        self.pg_AC = pg.PlotWidget()
        layout = QtWidgets.QVBoxLayout(self.AC_IV)
        layout.addWidget(self.pg_AC)

        self.pg_AC.setBackground("w")
        self.pg_AC.addLegend()
        self.pg_AC.showGrid(x=True, y=True)

        self.pg_AC.setLabel("left", "Current (A)")
        self.pg_AC.setLabel("bottom", "Voltage (V)")

        self.pg_AC.setXRange(0, self.x_max)
        self.pg_AC.setYRange(0, self.y_max)

        self.ac_curve_IV = self.pg_AC.plot(pen=pg.mkPen("b", width=2), name="I-V")
        self.ac_curve_PV = self.pg_AC.plot(pen=pg.mkPen("orange", width=2), name="P-V (scaled)")

        self.ac_mpp_real = self.pg_AC.plot(
            symbol="x", symbolBrush="g", symbolSize=14, name="MPP"
        )

    # ---------------------------------------------------
    def update_display(self, data):

        # --------------------------------------------
        # Update buffers (5 sample rolling average)
        # --------------------------------------------
        if "sas_power" in data:
            self.sas_hist.append(data["sas_power"])
            if len(self.sas_hist) > 5:
                self.sas_hist.pop(0)

        if "microinv_actual" in data:
            self.microinv_hist.append(data["microinv_actual"])
            if len(self.microinv_hist) > 5:
                self.microinv_hist.pop(0)

        # --------------------------------------------
        # Compute smoothed values
        # --------------------------------------------
        sas_smooth = np.mean(self.sas_hist) if self.sas_hist else None
        microinv_smooth = np.mean(self.microinv_hist) if self.microinv_hist else None

        # --------------------------------------------
        # Display SAS power
        # --------------------------------------------
        if sas_smooth is not None:
            self.AC_SAS_Power.setText(f"{sas_smooth:.2f} W")
            self.ac_mpp_real.setData([data["sas_voltage"]], [data["sas_current"]])

        # --------------------------------------------
        # Display Grid power
        # --------------------------------------------
        if "grid_power" in data:
            self.Grid_Power.setText(f"{data['grid_power']:.2f} W")

        # --------------------------------------------
        # Compute LOSSES = SAS - EM511
        # --------------------------------------------
        if sas_smooth is not None and microinv_smooth is not None:
            losses = sas_smooth - microinv_smooth

            # clip negative noise
            if losses < 0:
                losses = 0.0

            self.Microinverter_Power.setText(f"{losses:.2f} W")

            # ----------------------------------------
            # AC Load = SAS - losses + grid
            # ----------------------------------------
            if "grid_power" in data:
                ac_load = sas_smooth - losses + data["grid_power"]
                self.AC_Load_Power.setText(f"{ac_load:.2f} W")

    # ---------------------------------------------------
    def closeEvent(self, event):
        print("Closing...")
        self.worker.stop()
        if self.pm:
            self.pm.close()

        for inst in (self.inst_ac, self.inst_grid):
            if inst:
                try:
                    inst.write("OUTP OFF")
                    inst.close()
                except:
                    pass

        event.accept()


# ----------------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
