Homebrew game, update, and DLC installer, and title key dumper.

If the app hangs when you launch it, it means you didnt edit the junk info out of locations.conf and its hung up waiting for timeout.

![alt text](https://raw.githubusercontent.com/blawar/nut/master/dz/ss.jpg)

# Supported Protocols #
### FTP ###
Regular FTP, not FTPS, not SFTP, normal plain jane FTP.

### HTTP ###
Http requires directory listing / browsing be enabled!

# Installation

 - Create the directory /switch/dz/ on your switch's SD card.
 
 - Copy dz.nro to /switch/dz/dz.nro .
 
 - Obtain or generate a keys.txt file and place it in /switch/dz/keys.txt .  keys.txt is a text file containing various switch encryption keys.  If you plan to generate it yourself, you can find instructions here:  https://gbatemp.net/threads/how-to-get-switch-keys-for-hactool-xci-decrypting.506978/
 
 - Copy locations.conf to /switch/dz/locations.conf .  You should edit this file, it is only an example, and points to the various local and network locations hosting your switch content.  You can view an example of how ot add network install locations by looking at locations.conf.example

# Disclaimer

Use at your own risk, and always have a NAND backup.'

# Dumping Title Keys

Title keys are saved to sdmc:/switch/dz/titlekeys.txt when dumped.

# Backing up title keys

You can place a single http url into /switch/dz/titlekeys.url.txt , to automatically submit your keys to that url to back them up.

# Changelog

- Added CURL error logging to console window for troublshooting network issues.
- Added scroll bars to the menu, for those souls who add a million locations.
- Added colored background to finished queue entries.
- Fixed issue installing updates above 0x1000 / 65536
- Added scrollbars to console
- Removed Pepe icon.
- Fixed minor scrollbar graphical glitches.
- Fixed naming issues with apostrophes and ampersands.
- Added icons / tiled layout option and a switchable view for games.
- Added collapsable menu when browsing the panels.
- Fixed a few memory leaks
- Removed system version check for installs
- Fixed data corruption error when checking through the OS.
- Optimized UI icon performance some.
- Fixed out of memory issue while installing certain titles.
- Optimized opening of certain file types.
- Improved download speed a little.
- Added icons for DLC and updates.
- Fixed issue downloading small DLC.
- Added window for deleting application records.
- UI Tweaks
- Added sorting for network directories.
- Added file size and modified date for FTP locations.
- Added free space indicators.
- Moved progress bar to stop
- Added version and language to title list, and cleaned up the names
- Fixed early failed install bug from last commit, caused by slow SD cards.
- Fixed small DLC installs
- Added example location for SD installs

# Credits

Ideas from Adubbz:
https://github.com/Adubbz/

HACTOOL source code was reverse-engineered, with small bits of code lifted here and there:
https://github.com/SciresM/hactool

Random JSON parser:
https://github.com/nlohmann/json
