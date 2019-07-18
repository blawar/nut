# Nut
This is a program that can organize (Nintendo Switch) NSPs on your file system. It can also act as a USB and web server for use with [Tinfoil](https://tinfoil.io/Download).

## USB Install for Tinfoil
Run `python server.py` after installing the required pip modules or Windows users can use the precompiled nut.exe in the release section.

Follow the directions found in the release page to install the USB driver.

After you run the server, ensure NSP's are visible in the list.  If they are not, change the path and click the "scan" button.

Connect your USB cable from your switch to your PC.

Start Tinfoil, and all of the NSP's listed in nut server should now be available to install in Tinfoil.

Headless server: `python nut.py --usb`

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/nutserver.png)

---------

## Usage
 - Download [`nut`](https://github.com/blawar/nut/archive/master.zip)
 - Install Python 3.6+
 - Install the following modules via `pip`:
 	 - `pip3 install colorama pyopenssl requests tqdm unidecode Pillow BeautifulSoup4 urllib3 Flask pyusb pyqt5`
 - Configure `nut.conf` (see below)
 - Run `python3 nut.py --help` to understand options

Notes: 
 - If you are comfortable with git and also want updated metadata for your own purposes (Tinfoil updates itself automatically), you can use `git clone --depth 1 https://github.com/blawar/nut.git`
 - If you want to do NCA operations (verify, unpack, etc), you'll need a `keys.txt` from [Lockpick_RCM](https://github.com/shchmue/Lockpick_RCM) or elsewhere.

## NUT Server Install for Tinfoil
Run server.py or Windows users can use the precompiled nut.exe in the release section.

After you run the server, ensure NSP's are visible in the list.  If they are not, change the path and click the "scan" button.

Start Tinfoil, then go to locations, then select "Add New" location.  Enter the ip, port, username, and password that is displayed in the nut server application, then press save.

All of the NSP's listed in nut server should now be available to install in Tinfoil.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/ss.jpg)

## Server GUI
If you wish to run the server GUI, you must first download the images from nintendo.  You may do so with this command:
nut.py -s --scrape

This will take some time.  When it is complete, you can start the web server with:
server.py

Then point your web browser to localhost:9000

---------

## Configuration
All configuration is done via `nut.conf`.

### Paths
Configures how you want `nut` to store (and organize) your files. By default:
```
Base Games:		titles/{name}[{id}][v{version}].nsp
DLC:			titles/DLC/{name}[{id}][v{version}].nsp
Updates:		titles/updates/{name}[{id}][v{version}].nsp
Demos: 			titles/demos/{name}[{id}][v{version}].nsp
Demo Updates:		titles/demos/updates/{name}[{id}][v{version}].nsp

nspOut			_NSPOUT
scan (folder)		.
```

# Selected Help
Run `python nut.py --help` for all flags
```
  -i INFO, --info INFO  show info about title or file
  -s, --scan            scan for new NSP files
  -o, --organize        rename and move all NSP files
  -U, --update-titles   update titles db from urls
  --update-check        check for existing titles needing updates
  -x EXTRACT [EXTRACT ...], --extract EXTRACT [EXTRACT ...]
                        extract / unpack a NSP
  --export EXPORT       export title database in csv format
  --silent              Suppress stdout/stderr output
  --usb                 Run usb daemon
  -S, --server          Run server daemon
  -m HOSTNAME, --hostname HOSTNAME
                        Set server hostname
  -p PORT, --port PORT  Set server port
```

# Credits
- Original CDNSP
- Hactool by SciresM (https://github.com/SciresM/)
- Simon (https://github.com/simontime/) for his seemingly endless CDN knowledge and help.
- SplatGamer
