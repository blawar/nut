# Nut
This is a program  that automatically downloads all games from the CDN, and organizes them on the file system as backups.  You can only play games that you have legally purchased / have a title key for.  Nut also provides a web interface for browsing your collection.

You should copy nut.default.conf to nut.conf and make all of your local edits in nut.conf.

**If you only wish to rename / organize files, and not download anything, edit `nut.conf` and set all downloading options to false.** Your NSP files should have the titleid as a part of the filename in brackets.

It can download any titles you do not have a key for (for archiving), by enabling `sansTitleKey` in `nut.conf`.  These titles are saved with the `.nsx` file extension, and can be unlocked at a later time when a title key is found.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/ss.jpg)

---------

## Usage
 - Download [`nut`](https://github.com/blawar/nut/archive/master.zip)
 - If you'd like to download from the CDN, place everything in your already configured CDNSP directory. Specifically, you'll need:
	- `Certificate.cert`
	- `nx_tls_client_cert.pem`
	- `keys.txt`
 - Install Python 3.6+
 - Install the following modules via `pip`:
 	 - `pip3 install colorama pyopenssl requests tqdm unidecode image bs4 urllib3 flask pyqt5`
 - Configure `nut.conf` (see below)
 - Run `python3 nut.py --help` to understand options
 
## Docker
The docker entrypoint will automatically scrape the delta images, scan for new local items, and start the server. 

- Clone the repository and run `docker build -t nut .`
- Create a local nut.conf using the example
- Create a folder to store your nsps
- You should mount your local nsp folder into the docker container along with the config and map a port like so: `docker run -p 9000:9000 -v /path/to/conf/nut.conf:/var/opt/nut/conf/nut.conf -v /path/to/nsps:/var/opt/nut/titles`
- You can now connect using localhost:9000


## USB Install for Tinfoil
Run server.py or Windows users can use the precompiled nut.exe in the release section.

Follow the directions found in the release page to install the USB driver.

After you run the server, ensure NSP's are visible in the list.  If they are not, change the path and click the "scan" button.

Connect your USB cable from your switch to your PC.

Start Tinfoil, and all of the NSP's listed in nut server should now be available to install in Tinfoil.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/nutserver.png)

## NUT Server Install for Tinfoil
Run server.py or Windows users can use the precompiled nut.exe in the release section.

After you run the server, ensure NSP's are visible in the list.  If they are not, change the path and click the "scan" button.

Start Tinfoil, then go to locations, then select "Add New" location.  Enter the ip, port, username, and password that is displayed in the nut server application, then press save.

All of the NSP's listed in nut server should now be available to install in Tinfoil.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/public_html/images/nutserver.png)
 
## Server GUI
If you wish to run the server GUI, you must first download the images from nintendo.  You may do so with this command:
nut.py -s --scrape

This will take some time.  When it is complete, you can start the web server with:
nut.py --server

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

### Title Lists
`nut` will download, parse, and combine titlekey lists for URLs defined in `titleUrls` and `titledb\*.txt`. They will be loaded preferentially: first local lists (in alphabetical order), then remote lists. This is useful in case you'd like to maintain custom title naming (ie. in a `titledb\z.titlekeys.txt`

Acceptable formats:
```
Rights ID|Title Key|Title Name
01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|1-2-Switch

or

id|rightsId|key|isUpdate|isDLC|isDemo|name|version|region|retailOnly
01000320000cc000|01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|0|0|0|1-2-Switch™|0|US|0

or

id|name
01000320000cc000|1-2-Switch™

etc
```

### Whitelist
Place any title ids that you want to download in `whitelist.txt`, separated with a newline.

*If you want to download all games, leave the file empty.*

### Blacklist
Place any title ids that you do **not** want to download in `blacklist.txt`, separated with a newline.

# Help
```
nut.py -h
usage: nut.py [-h] [--base {0,1}] [--demo {0,1}] [--update {0,1}]
              [--dlc {0,1}] [--nsx {0,1}] [-D] [-d DOWNLOAD [DOWNLOAD ...]]
              [-i INFO] [-u UNLOCK] [--unlock-all]
              [--set-masterkey1 SET_MASTERKEY1]
              [--set-masterkey2 SET_MASTERKEY2]
              [--set-masterkey3 SET_MASTERKEY3]
              [--set-masterkey4 SET_MASTERKEY4]
              [--set-masterkey5 SET_MASTERKEY5]
              [--remove-title-rights REMOVE_TITLE_RIGHTS] [-s] [-Z] [-z] [-V]
              [-o] [-U] [-r] [-x EXTRACT [EXTRACT ...]] [-c CREATE]
              [--export-missing EXPORT_MISSING] [-M MISSING]
              [--nca-deltas NCA_DELTAS] [--silent] [--json] [-S] [-m] [-p]
              [--scrape] [--scrape-delta] [--scrape-title SCRAPE_TITLE]
              [file [file ...]]

positional arguments:
  file

optional arguments:
  -h, --help            show this help message and exit
  --base {0,1}          download base titles
  --demo {0,1}          download demo titles
  --update {0,1}        download title updates
  --dlc {0,1}           download DLC titles
  --nsx {0,1}           download titles without the title key
  -D, --download-all    download ALL title(s)
  -d DOWNLOAD [DOWNLOAD ...], --download DOWNLOAD [DOWNLOAD ...]
                        download title(s)
  -i INFO, --info INFO  show info about title or file
  -u UNLOCK, --unlock UNLOCK
                        install available title key into NSX / NSP
  --unlock-all          install available title keys into all NSX files
  --set-masterkey1 SET_MASTERKEY1
                        Changes the master key encryption for NSP.
  --set-masterkey2 SET_MASTERKEY2
                        Changes the master key encryption for NSP.
  --set-masterkey3 SET_MASTERKEY3
                        Changes the master key encryption for NSP.
  --set-masterkey4 SET_MASTERKEY4
                        Changes the master key encryption for NSP.
  --set-masterkey5 SET_MASTERKEY5
                        Changes the master key encryption for NSP.
  --remove-title-rights REMOVE_TITLE_RIGHTS
                        Removes title rights encryption from all NCA's in the
                        NSP.
  -s, --scan            scan for new NSP files
  -Z                    update ALL title versions from nintendo
  -z                    update newest title versions from nintendo
  -V                    scan latest title updates from nintendo
  -o, --organize        rename and move all NSP files
  -U, --update-titles   update titles db from urls
  -r, --refresh         reads all meta from NSP files and queries CDN for
                        latest version information
  -x EXTRACT [EXTRACT ...], --extract EXTRACT [EXTRACT ...]
                        extract / unpack a NSP
  -c CREATE, --create CREATE
                        create / pack a NSP
  --export-missing EXPORT_MISSING
                        export title database in csv format
  -M MISSING, --missing MISSING
                        export title database of titles you have not
                        downloaded in csv format
  --nca-deltas NCA_DELTAS
                        export list of NSPs containing delta updates
  --silent              Suppress stdout/stderr output
  --json                JSON output
  -S, --server          Run server daemon
  -m, --hostname        Set server hostname
  -p, --port            Set server port
  --scrape              Scrape ALL titles from Nintendo servers
  --scrape-delta        Scrape ALL titles from Nintendo servers that have not
                        been scraped yet
  --scrape-title SCRAPE_TITLE
                        Scrape title from Nintendo servers
```

# Credits
- Original CDNSP
- Hactool by SciresM (https://github.com/SciresM/)
- Simon (https://github.com/simontime/) for his seemingly endless CDN knowledge and help.
