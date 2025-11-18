from pymodbus.client import ModbusSerialClient

port = "COM3"        # Your COM port
baud = 9600          # EM511 default
parity = "E"         # IMPORTANT: Even parity for EM511
stopbits = 1
unit = 1             # Slave address
timeout = 1.0

client = ModbusSerialClient(
    port=port,
    baudrate=baud,
    parity=parity,
    stopbits=stopbits,
    bytesize=8,
    timeout=timeout
)

print("Opening port...")
if not client.connect():
    print("❌ Failed to open serial port")
    exit()

try:
    print("Reading Active Power (0x0004)...")
    rr = client.read_holding_registers(address=0x0004, count=2, slave=unit)

    if rr.isError():
        print("❌ Modbus error:", rr)
    else:
        regs = rr.registers
        lsw = regs[0]
        msw = regs[1]

        raw32 = (msw << 16) | lsw

        # Convert signed 32-bit
        if raw32 & 0x80000000:
            raw32 -= 0x100000000

        watts = raw32 / 10.0
        print(f"✔ Active Power: {watts} W")
        print(f"(Raw INT32 = {raw32})")

finally:
    client.close()
