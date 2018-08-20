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
 - Install Python 3
 - Install the following modules via `pip`:
 	 - `pip3 install colorama pyopenssl requests tqdm unidecode image bs4`
 - Configure `nut.conf` (see below)
 - Run `python3 nut.py --help` to understand options
 
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
