# Nut
This is a program  that automatically downloads all games from the CDN, and organizes them on the file system.

# Organization
It saves the games in the following dir structure: titles/{name}/{name}[{title_id}].nsp

DLC are saved to: titles/{name}/DLC/{name}[{title_id}].nsp

Updates  are saved to: titles/{name}/updates/{name}[{title_id}].nsp

# Titlelist
I added an example titlekeys.txt, the titlekeys are zero'd out, do not try to download games with this.  If you already have this file, do not overwrite it with this file.  This is included only for those who do not have CDNSP but want to rename files.

# Whitelist
Place title id's that you want to download in whitelist.txt, separated with a newline.

If you want to download all games, leave the file empty.

# Blacklist 
Place title id's that you do not want to download in blacklist.txt, separated with a newline.

# Installation
Place these files in your already configured CDNSP directory if you want it to download from the CDN.

If all you want is to organize your existing NSP's, just place all of these files EXCEPT CDNSP.py in a dir that contains your NSP files (or sub directory) with the titleid in the filename in brackets, no CDNSP is required.  CDNSP.py Must not be present if all you want to do is organize.

run nut.py

if you get an error about AutoUpdatedb, you need to add the following key value to CDNSPconfig.json:

"AutoUpdatedb": false
