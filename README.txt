
Download Keysight IO-libraries (x64 IOLS)
Follow Directions on keysight page:
Important note**
(For best interoperatibilty with NI-VISA, it is recommended to install NI-VISA first through NI Package Manager and then Keysight IO Libraries Suite.)

https://www.keysight.com/us/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html
____________________________________________________________________________________________________________________

Use anaconda env in repo
conda env create -f environment.yml NEED TO UPDATE YML FILE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
_____________________________________________________

Convert gui, and resource files to .py

pyuic5 -x test.ui -o test.py
pyrcc5 resource.qrc -o resource_rc.py
_____________________________________________________

Activate conda env, and run main.py

conda activate sas_env
python SRC/main.py

test