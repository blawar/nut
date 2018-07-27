# Nut
This is a program  that automatically downloads all games from the CDN, and organizes them on the file system.

it saves the games in the following dir structure: titles/{name}/{name}[{title_id}].nsp

dlc are saved to: titles/{name}/DLC/{name}[{title_id}].nsp

updates  are saved to: titles/{name}/updates/{name}[{title_id}].nsp

# Whitelist
Place title id's that you want to download in whitelist.txt, separated with a newline.

If you want to download all games, leave the file empty.

# Blacklist 
Place title id's that you do not want to download in blacklist.txt, separated with a newline.

# Installation
place these files in your already configured CDNSP directory

add the following line to the top of your CDNSP.py file:

from tqdm import tqdm

run nut.py
