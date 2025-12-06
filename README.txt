Follow Directions on keysight page:
https://docs.keysight.com/kkbopen/getting-started-automate-keysight-instruments-using-python-3-9-845872587.html

Important note from page**
(For best interoperatibilty with NI-VISA, it is recommended to install NI-VISA first through NI Package Manager and then Keysight IO Libraries Suite.)
_______________________________________________________________________________________________________________________________________________________
Use anaconda env in repo
conda env create -f environment.yml 
conda activate sas_env
_____________________________________________________

Convert gui, and resource files to .py

pyuic5 -x guiTest.ui -o guiTest.py
pyrcc5 resource.qrc -o resource_rc.py
_____________________________________________________

Update com port # for power meter in code (line 98)
Device Manager\ports (COM and LPT)\USB-SERIAL CH340 (COMX)
_____________________________________________________

Run mainTest.py
python SRC/mainTest.py

Additionally, if using a TV or a large display, adjust the aspect ratio and zoom for the best appearance. For me, 1920x1080 and 175% zoom worked well.

