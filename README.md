# Nut
This is a program that acts as a USB and network server for use with [Tinfoil](https://tinfoil.io/Download).

## GDrive Auth
Nut will authenticate with gdrive if you create a gdrive application, and place its credentials.json file either in nut's root directory, or in the conf directory.  You can generate / download credentials.json from https://developers.google.com/drive/api/v3/quickstart/go

Once this is set up, you can access your gdrive through tinfoil, by using either the usbfs, nutfs, or gdrive protocol

## USB Install for Tinfoil
Run `python nut.py` after installing the required pip modules or Windows users can use the precompiled nut.exe in the release section.

Follow the directions found in the release page to install the USB driver.

After you run the server, ensure NSP's are visible in the list.  If they are not, change the path and click the "scan" button.

Connect your USB cable from your switch to your PC.

Start Tinfoil, and all of the NSP's listed in nut server should now be available to install in Tinfoil.

Headless server: `python nut.py --usb`

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/nutserver.png)

---------

## Usage
 - Download [`nut`](https://github.com/blawar/nut/archive/master.zip)
 - Install Python 3.6+ to your PATH (make sure `python` opens up a Python 3 shell)
 - Install the following modules via `pip`:
 	 - `pip3 install colorama pyopenssl requests tqdm unidecode Pillow BeautifulSoup4 urllib3 Flask pyusb pyqt5 google-api-python-client google-auth-oauthlib`
 - Configure `nut.conf` (see below)
 - Run `python3 nut.py --help` to understand options

## NUT Server Install for Tinfoil
Run `server.py` or Windows users can use the precompiled nut.exe in the release section.

After you run the server, ensure NSP's are visible in the list.  If they are not, change the path and click the "scan" button.

Start Tinfoil, then go to locations, then select "Add New" location.  Enter the ip, port, username, and password that is displayed in the nut server application, then press save.

All of the NSP's listed in nut server should now be available to install in Tinfoil.

---------

## USB Driver Install
- Download Zadig from https://zadig.akeo.ie/.
- With your switch plugged in and Tinfoil running, choose "List All Devices" under the options menu in Zadig, and select libnx USB comms.
- Choose libusbK from the driver list and click the "Replace Driver" button.
- run nut.exe or server.py
- Start tinfoil on the switch, and either connect the USB cable from the switch to your PC, or set up a nut server location using the information displayed in nut server.


## Title Database
The title databse was moved to https://github.com/blawar/titledb
