# Nut
This is a program  that automatically downloads all games from the CDN, and organizes them on the file system.

It will also download any titles you do not have a key for (for archiving), by enabling sansTitleKey in nut.json.  These titles are saved with the .nsx file extension, and can be unlocked at a later time when a title key is found.

# Organization
It saves the titles in the following format by default:

base games:  titles/{name}[{id}][v{version}].nsp

DLC:         titles/DLC/{baseName}/{name}[{id}][v{version}].nsp

updates:     titles/updates/{baseName}/{name}[{id}][v{version}].nsp

demos:       titles/demos/{name}[{id}][v{version}].nsp

demo upd:    titles/demos/updates/{baseName}/{name}[{id}][v{version}].nsp

# Titlelist
This program will load any titlekeys files named \*.titlekeys.txt including titlekeys.txt

# Whitelist
Place title id's that you want to download in whitelist.txt, separated with a newline.

If you want to download all games, leave the file empty.

# Blacklist 
Place title id's that you do not want to download in blacklist.txt, separated with a newline.

# Installation
Place all of these files in your already configured CDNSP directory if you want it to download from the CDN.

If all you want is to organize your existing NSP's, just place all of these files in a dir that contains your NSP files (or sub directory) with the titleid in the filename in brackets.

run nut.py
