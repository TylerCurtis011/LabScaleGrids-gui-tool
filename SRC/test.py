import pyvisa

# Configuration
SAS_VISA_ADDRESS = "USB0::0x0957::0x1107::MY55000177::0::INSTR"
CHANNEL = 1

# Initial full-power values
ISC_FULL = 4.25
IMP_FULL = 4.25
VMP_FULL = 60.0
VOC_FULL = 65.0

# Half-power currents
ISC_HALF = 2.0
IMP_HALF = 2.0

# Connect to SAS
rm = pyvisa.ResourceManager(r"C:\\Windows\\System32\\visa64.dll")
sas = rm.open_resource(SAS_VISA_ADDRESS)
sas.timeout = 5000
sas.clear()

print("Connected to SAS:", sas.query("*IDN?").strip())

# --- Read initial voltage/current ---
voltage = float(sas.query("MEAS:VOLT?"))
current = float(sas.query("MEAS:CURR?"))
print(f"Initial readings -> Voltage: {voltage:.2f} V, Current: {current:.2f} A")

# --- Coupled command: set ISC and IMP together ---
cmd = (f"CURR:SAS:ISC {ISC_HALF},(@{CHANNEL});"
       f"IMP {IMP_HALF},(@{CHANNEL});"
       f":VOLT:SAS:VMP {VMP_FULL},(@{CHANNEL});"
       f"VOC {VOC_FULL},(@{CHANNEL})")
sas.write(cmd)
sas.query("*OPC?")
print("SAS set with coupled parameters (ISC/IMP/VMP/VOC)")

# --- Read updated voltage/current ---
voltage = float(sas.query("MEAS:VOLT?"))
current = float(sas.query("MEAS:CURR?"))
print(f"Updated readings -> Voltage: {voltage:.2f} V, Current: {current:.2f} A")

# Close connection
sas.close()
print("SAS connection closed.")
