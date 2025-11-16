
import pyvisa as visa
import sys

#  ################################################################
# Programmatically query the Python version and print information
print('\nSystem version fn(sys.ver)):\n\t{}'.format(sys.version))

# VISA address for a USB connection:
VISA_ADDRESS = 'USB0::0x0957::0x1107::MY55000177::0::INSTR' # AC_SAS


# Define VISA Resource Manager
rm = visa.ResourceManager('C:\\Windows\\System32\\visa64.dll')

# Open connection to the instrument via the related VISA address:
try:
    print('\nConnecting to: {}'.format(VISA_ADDRESS))
    inst = rm.open_resource(VISA_ADDRESS)
except Exception:
    print('Unable to connect to Instrument at {}.  Aborting.\n'
          .format(VISA_ADDRESS))
    sys.exit()

# Set I/O timeout to 5 seconds
inst.timeout = 5000

# Clear the remote interface
inst.clear()

IDN = str(inst.query('*IDN?'))
print('Connected to: {}'.format(IDN))

# -----------------------------------------------------------
# Query DAC table (SAS simulator I-V data)
# -----------------------------------------------------------
try:
    print('\nQuerying DAC table (current)...')
    #dac_data = inst.query('SOUR:CURR:DTAB:SASim:IMMediate?')
    dac_data = inst.query('SOURce:CURRENT:DTABle:SASimulator:IMMediate?')
    dac_values = [float(x) for x in dac_data.split(',') if x.strip()]
    print('Received {} DAC points.'.format(len(dac_values)))
    print('All 4096 values:', dac_values[:4096])
except Exception as e:
    print('Error querying DAC table:', e)

try:
    print('\nQuerying DAC table Imp...')
    imp_value = inst.query('SOURce:CURRent:DTABle:SASimulator:IMMediate:IMP?')
    # dac_values = [float(x) for x in dac_data.split(',') if x.strip()]
    # print('Received {} DAC points.'.format(len(dac_values)))
    print('Calculated Imp:', imp_value)
except Exception as e:
    print('Error querying DAC table Imp:', e)

try:
    print('\nQuerying DAC table Isc...')
    isc_value = inst.query('SOURce:CURRent:DTABle:SASimulator:IMMediate:ISC?')
    print('Calculated Imp:', isc_value)
except Exception as e:
    print('Error querying DAC table Isc:', e)

print("================================================================================")

try:
    print('\nQuerying DAC table (voltage)...')
    dac_data = inst.query('SOURce:VOLTage:DTABle:SASimulator:IMMediate?')
    dac_values_Volt = [float(x) for x in dac_data.split(',') if x.strip()]
    print('Received {} DAC points.'.format(len(dac_values_Volt)))
    print('All 4096 values:', dac_values_Volt[:4096])
except Exception as e:
    print('Error querying DAC table (volt):', e)

try:
    print('\nQuerying DAC table Vmp...')
    vmp_value = inst.query('SOURce:VOLTage:DTABle:SASimulator:IMMediate:VMP?')
    print('Calculated Vmp:', vmp_value)
except Exception as e:
    print('Error querying DAC table Vmp:', e)

try:
    print('\nQuerying DAC table Voc...')
    voc_value = inst.query('SOURce:VOLTage:DTABle:SASimulator:IMMediate:VOC?')
    print('Calculated Voc:', voc_value)
except Exception as e:
    print('Error querying DAC table Vmp:', e)

    



# Close instrument connection
inst.close()

print('Done.')