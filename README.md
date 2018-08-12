# Nut
This is a program  that automatically downloads all games from the CDN, and organizes them on the file system.

**If you only wish to rename / organize files, and not download anything, edit `nut.json` and set all downloading options to false.** Your NSP files should have the titleid as a part of the filename in brackets.

It can download any titles you do not have a key for (for archiving), by enabling `sansTitleKey` in `nut.json`.  These titles are saved with the `.nsx` file extension, and can be unlocked at a later time when a title key is found.

---------

## Usage
 - Download [`nut`](https://github.com/blawar/nut/archive/master.zip)
 - If you'd like to download from the CDN, place everything in your already configured CDNSP directory. Specifically, you'll need:
	- `Certificate.cert`
	- `Ticket.tik`
	- `nx_tls_client_cert.pem`
	- `keys.txt`
 - Install Python 3
 - Install the following modules via `pip`:
 	 - `pip3 install colorama pyopenssl requests tqdm unidecode`
 - Configure `nut.json` (see below)
 - Run `python3 nut.py --help` to understand options

---------

## Configuration
All configuration is done via `nut.json`.

### Paths
Configures how you want `nut` to store (and organize) your files. By default:
```
Base Games:		titles/{name}[{id}][v{version}].nsp
DLC:			titles/DLC/{name}[{id}][v{version}].nsp
Updates:		titles/updates/{name}[{id}][v{version}].nsp
Demos: 			titles/demos/{name}[{id}][v{version}].nsp
Demo Updates:	titles/demos/updates/{name}[{id}][v{version}].nsp

nspOut			_NSPOUT
scan (folder)	.
```

### Title Lists
`nut` will download, parse, and combine titlekey lists for URLs defined in `titleUrls` and `titledb\*.titlekeys.txt`. They will be loaded preferentially: first remote lists, then local lists (in alphabetical order). This is useful in case you'd like to maintain custom title naming (ie. in a `titledb\z.titlekeys.txt`

Acceptable formats:
```
Rights ID|Title Key|Title Name
01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|1-2-Switch

or

id|rightsId|key|isUpdate|isDLC|isDemo|name|version|region|retailOnly
01000320000cc000|01000320000cc0000000000000000000|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|0|0|0|1-2-Switch™|0|US|0
```

### Whitelist
Place any title ids that you want to download in `whitelist.txt`, separated with a newline.

*If you want to download all games, leave the file empty.*

### Blacklist
Place any title ids that you do **not** want to download in `blacklist.txt`, separated with a newline.
