# NUT [![Github all releases](https://img.shields.io/github/downloads/blawar/nut/total.svg)](https://GitHub.com/blawar/nut/releases/)

Nut is a multi-purpose utility to organize, manage, and install Nintendo Switch files (NSP, NSZ, XCI, XCZ).
It has the ability to act as a USB and network server for [Tinfoil](https://tinfoil.io/Download#download).

------

![NUT GUI Image](./images/gui_files.jpg)


## Buttons
 - **Scan** - populates file list
 - **Organize Files** - moves files on disk to match the format specified in the configuration
 - **Pull** - gets new files that match your filters from the remote locations (see configuration)
 - **Update TitleDB** - force-reloads the latest [title database](https://github.com/blawar/titledb)
 - **Decompress NSZ** - for any NSZ.XCZ files found, uncompresses them to NSP/XCI
 - **Compress NSP** - for any NSP/XCI files found, compresses them to NSZ/XCZ **CPU INTENSIVE**
 - **Setup GDrive OAuth** - see below

## Configuration

The GUI has the ability to set the most common configuration options, see the below images. You can also create a custom configuration by creating `conf/nut.conf`. The format should mirror [nut.default.conf](https://github.com/blawar/nut/blob/master/conf/nut.default.conf).

<details>
<summary>Images</summary>

![Filters](./images/gui_filters.jpg)
![Local Paths](./images/gui_scan1.jpg)
![Local Scan](./images/gui_scan1.jpg)
![Remote Scan](./images/gui_scan2.jpg)
</details>

The IP/Port/User/Password are the information needed to login to the NUT server. To the right of those, you can also see a `USB Status` indicator, indicating whether a Tinfoil client is connected via USB with the server.

THe body shows a table containing a list of files that were detected by NUT from the scanned paths. It shows the title count, file name, title ID, title type and title size for each scanned file.

The footer shows the progress information of any file that is currently being downloaded from the server.

## Google Drive Integration
NUT has the ability to interact with Google Drive. For this to work, you will need to download a `credentials.json`, using the guide found [here](https://developers.google.com/workspace/guides/create-credentials). Once you have this file placed either in NUT's root or conf directory, click the **Setup GDrive OAuth** button in the GUI and follow the prompts. You will be able to access your GDrive through Tinfoil via the `gdrive:/` protocol after copying `credentials.json` and `token.json` to `/switch/tinfoil` on your microSD card. (*This is automatically done if you connect Tinfoil to nut*)

------

## Usage guide (Windows users)
* Download `tinfoil_driver.exe` and `nut.exe` from [here](https://github.com/blawar/nut/releases/latest).
* Install the drivers by running the `tinfoil_driver.exe` in the previous step.
* Run `nut.exe`. You should be presented with a GUI as shown in the picture above.
* Install the latest version of [Tinfoil](https://tinfoil.io/Download#download) and open it.


## Usage guide (UNIX users)

### Requirements
* Python 3.9+ (tested: `3.9.7`)
* OpenSSL-backed curl (for pycurl)
* Python modules as listed in [`requirements.txt`](requirements.txt)

### Installation guide (Linux)

<details>
<summary>Details</summary>

* Install Python 3.9+ from your preferred package manager, along with the `libusb`, `python3-pip` & `python3-pyqt6` packages
* Install `curl` with the openssl backend - install `libssl-dev` (ie, `apt install libssl-dev libcurl4-openssl-dev`)
* Clone this repository to desired directory and change your working directory to the cloned repository
* Install the PIP modules with the following command `pip3 install -r requirements.txt`. If you previously tried installing pycurl and get the error `libcurl link-time ssl backend (openssl) is different from compile-time ssl backend (none/other)`, uninstall it, make sure to follow step 2 again (installing curl with the openssl backend), and `pip3 install pycurl --no-cache-dir`
* Add the following code snippet to `/etc/udev/rules.d/99-switch.rules` using your favorite editor and reload (`udevadm control --reload`). Note: you may need to *Disable MTP* within Tinfoil and replace the group user with another that exists on your system. (based on [this comment](https://github.com/blawar/nut/issues/284#issuecomment-866059890))
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="057e", ATTRS{idProduct}=="3000", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="16c0", ATTRS{idProduct}=="27e2", GROUP="plugdev"
```
* Run `python3 nut_gui.py` to launch the application. (`python3 nut.py` for CLI)
</details>

### Installation guide (macOS)

<details>
<summary>Details</summary>

* Install Python 3.9 and PyQt6 via Homebrew (`brew install python@3.9 pyqt@6`)
* Install pyenv: [pyenv](https://github.com/pyenv/pyenv) + [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) (`brew install pyenv pyenv-virtualenv` and follow install directions)
* Install `libusb` (`brew install libusb`)
* Install `curl` with the openssl backend (`brew uninstall --ignore-dependencies curl && brew install curl`)
* Install Python 3.9.7 with pyenv and set it as the default (`pyenv install 3.9.7 && pyenv global 3.9.7`)
* Load the system python's site-packages via pyenv's python. This is required to use PyQT6 from Homebrew.
  - Get the Homebrew Python site-packages path (via `brew info python@3.9`).
  - Add it to the load path of your pyenv's Python install (cd `pyenv root`).
  - To do this, go to the site packages directory of your pyenv install (ie. `$HOME/.pyenv/versions/3.9.7/lib/python3.9/site-packages`) and create an file named `homebrew.pth` containing the path for Homebrew Python's site packages directory (ie. `/opt/homebrew/lib/python3.9/site-packages`)
  - For example, for M1, it would be: `cd $HOME/.pyenv/versions/3.9.7/lib/python3.9/site-packages && echo "/opt/homebrew/lib/python3.9/site-packages" >> homebrew.pth`
* Clone this repository to desired directory and change your working directory to the cloned repository
* Create a virtualenv and activate it. Note that your python path will be different if not on M1. (`pyenv virtualenv --system-site-packages --python=/opt/homebrew/bin/python3.9 nut && source activate nut`)
* Install wheel (`pip install wheel`)
* Install pycurl using the below.
```
on M1:
PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L/opt/homebrew/opt/openssl/lib" CPPFLAGS="-I/opt/homebrew/opt/openssl/include" pip install pycurl --no-cache-dir
on Intel:
PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L/usr/local/opt/openssl/lib" CPPFLAGS="-I/usr/local/opt/openssl/include" pip install pycurl --compile --no-cache-dir
```
* Install all other dependencies (`pip install -r requirements.txt`)
* Run `python nut.py` for CLI. Run `python3 nut_gui.py` to launch the application (this will *only* work if PyQT from Homebrew was succesfully installed via directions above)
</details>

### Docker

```console
$ docker build --tag nut https://github.com/blawar/nut.git
$ docker run --rm -it --network=host --env=DISPLAY --volume=/tmp/.X11-unix:/tmp/.X11-unix --volume="$PWD:$PWD" --workdir="$PWD" --user=$(id -u):$(id -g) nut
```

------

## License
This software is licensed under the terms of the GPLv3, with exemptions for specific projects noted below.
You can find a copy of the license in the [LICENSE](./LICENSE) file.

Exemptions:
* [nsz](https://github.com/nicoboss/nsz) is exempt from GPLv3 licensing and can license any source code from this project under the MIT License instead. In doing so, they may alter, supplement, or entirely remove the copyright notice for each file they choose to relicense.

## Contributing

Contributions are welcome, and there is a [pre-commit hook](https://pre-commit.com/#install) - run `pip3 install -r requirements_dev.txt`
