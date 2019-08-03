#!/usr/bin/python3
# -*- coding: utf-8 -*-

#Standard
import argparse
import imp
import json
import os
import pathlib
import platform
import pprint
import random
import re
import shutil
import socket
import sys
import threading
import time
import urllib
import urllib3
from collections import OrderedDict

#Backend
import nut
from nut import Config
from nut import Nsps
from nut import Status
from nut import Usb
from nut import Users

import Server

#Gui
from PIL import ImageTk, Image
from gui.format import * 
import gui.customwidgets as cw
import gui.layouts as layouts
import tkinter as tk
from tkinter.constants import *
from tkinter import filedialog

#Function to start gui, called at bottom of file if __main__
def startGUI():
    urllib3.disable_warnings()

    print('                        ,;:;;,')
    print('                       ;;;;;')
    print('               .=\',    ;:;;:,')
    print('              /_\', "=. \';:;:;')
    print('              @=:__,  \,;:;:\'')
    print('                _(\.=  ;:;;\'')
    print('               `"_(  _/="`')
    print('                `"\'')

    nut.initFiles()

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--munk', action="store_true", help='launch in small (chipmunk) mode')
    args = parser.parse_args()

    #Check if gui should be full or minimal
    if args.munk:
        guistyle = layouts.tinyGui
    else:
        guistyle = layouts.gui

    app = FrameManager(guistyle)
    
    startThreads(app)

    app.mainloop()

#Broken out for use when importing 
def startThreads(app):
    threads = [] 
    threads.append(threading.Thread(target=initThread, args=[]))
    threads.append(threading.Thread(target=usbThread, args=[]))
    threads.append(threading.Thread(target=nutThread, args=[]))
    threads.append(threading.Thread(target=loadDB, args = [app]))
    for t in threads:
        t.start()

def usbThread():
    Usb.daemon()

def nutThread():
    Server.run()

def initThread():
    nut.scan()

def loadDB(app):
    global TITLEDB
    with open(os.path.join(sys.path[0],"titledb\\titles.US.en.json")) as dbjson:
        TITLEDB = json.load(dbjson)
    app.refresh()

#Main frame handler, raises pages in z layer
class FrameManager(tk.Tk):
    def __init__(self,guistyle):
        tk.Tk.__init__(self)
        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        container = cw.ThemedFrame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
     
        self.cwd = os.path.dirname(os.path.realpath(__file__))
        self.cachefolder = os.path.join(self.cwd, "cache")

        if not os.path.isdir(self.cachefolder):
            os.mkdir(self.cachefolder)
     
        if guistyle == layouts.gui:
            pages = [
                layouts.gui,
                layouts.helpFrame,
            ]
        elif guistyle == layouts.tinyGui:
            pages = [
                layouts.tinyGui
            ]
        else:
            sys.exit("Unable to find gui init pattern for {}".format(guistyle))

        #Add pages as frames to dict, with keyword being the name of the frame
        #Uses an ordered dict to remember first item added
        self.frames = OrderedDict()
        for F in (pages):
            page_name = F.__name__
            frame = F(parent=container, controller=self) 
            self.frames[page_name] = frame

            frame.grid(row=0, column=0, sticky="nsew")
        
        #Set icon
        if platform.system() == 'Windows':
            try:
                print("Windows detected, setting icon")
                self.iconbitmap("public_html/images/favicon.ico")
            except:
                print("Failed to set icon")

        ##TODO: CREATE LINUX SQUIRREL ICON
        # elif platform.system() == "Linux":
        #     try:
        #         print("Linux detected, setting icon")
        #         self.iconbitmap()
        #     except:
        #         print("Failed to set icon")

        self.needsRefresh = True

        #Get first frame added and raise it
        for frame in self.frames:
            self.show_frame(frame)
            break
        
    def show_frame(self, page_name):
        #Show a frame for the given page name
        frame = self.frames[page_name]
        frame.event_generate("<<ShowFrame>>")
        frame.tkraise()

    def refresh(self):
        self.needsRefresh = True

if __name__ == '__main__':
    print("Using Python {}.{}".format(sys.version_info[0],sys.version_info[1]))
    print("Using tkinter version {}".format(tk.Tcl().eval('info patchlevel')))
    startGUI()