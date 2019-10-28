import os
import socket
import sys
import time
import urllib
import json

from nut import Config
from nut import Nsps
from nut import Status
from nut import Usb
from nut import Users

import Server

from PIL import ImageTk, Image

from gui.format import * 
import gui.customwidgets as cw
import gui.framework as fw
import gui.tinfoilapi as api

import tkinter as tk
from tkinter.ttk import Style
from tkinter.ttk import Progressbar
from tkinter.constants import *

GITHUBURL = "https://github.com/blawar/nut"
TINFOILURL = "https://tinfoil.io/"

QUICKSTARTTEXT = """#ADDING NSP/NSX
- Click the folder button, select a folder containing nsps that you would like to track
- Click the magnifying glass to scan the folder and it's subdirectories, any nsps found will be tracked and remembered

#USB
- Connect your USB cable from your switch to your PC.
- Start Tinfoil, and all of the NSP's listed in nut server should now be available to install in Tinfoil or Lithium.

#Network
- Start Tinfoil, then go to locations, select "Add New" location.  
- Enter ip, port, username, password displayed in the nut server application, then press save.
        
"""

BACKUPGUIDETEXT = """
You deleted the readme didn't you?
tsk, tsk, now you're stuck with this.

{}

#Credits
- Original CDNSP
- Hactool by SciresM (https://github.com/SciresM/)
- Simon (https://github.com/simontime/) for his seemingly endless CDN knowledge and help.
- SplatGamer
- LyfeOnEdge (https://github.com/LyfeOnEdge/) for the updated gui
""".format(QUICKSTARTTEXT)


class gui(fw.appFramework):
    def __init__(self, parent, controller, cwd = None):
        self.controller = controller        #Controller (most toplevel parent)
        self.cwd = cwd or controller.cwd or sys.path[0]
        self.softwarelist = []              #list to hold software data to populate table and more
        self.currentselection = 0           #Variable to track currently selected software in listbox
        self.needsRefresh = True            #Variable to track if reload is needed

        width = 640
        height = 480
        minwidth = infoframewidth
        minheight = 120
        self.controller.geometry("{}x{}".format(width,height)) 
        self.controller.minsize(width=minwidth, height=minheight) #minimum size currently supported
        self.controller.title("NUT")
        # self.controller.bind("<Configure>", self.reload)

        cw.ThemedFrame.__init__(self,parent) #Init frame
        self.bind("<<ShowFrame>>", self.on_show_frame) #Bind on_show_frame to showframe event so whenever the frame is raised by the controller it reloads

        #Full window frame, holds everything
        self.outer_frame = cw.ThemedFrame(self,frame_borderwidth=0,frame_highlightthickness= 0)
        self.outer_frame.place(relx=0.0, rely=0.0, relheight=1.0, relwidth=1.0)

        #Frame for main list, contains listboxes and scroll bar, and list titles
        self.content_frame = cw.ThemedFrame(self.outer_frame,frame_borderwidth=0,frame_highlightthickness= 0)
        self.content_frame.place(relx=0.0, rely=0.0, relheight=1, relwidth=1, width=-infoframewidth,)
        self.content_frame.configure(background=dark_color)

        #The contents of this frame are built backwards when self.setbutton() is called due to needing to align the searchbox with the icons
        self.searchbox_frame = cw.ButtonRow(self.content_frame, frame_highlightthickness= 0,background=light_color, frame_borderwidth = 0)
        self.searchbox_frame.Place(relx=0.0, rely=0.0,height=searchboxheight, relwidth=1,)

        #Holds the scan path, hidden when not needed
        self.scanpathbox_frame = cw.ButtonRow(self.content_frame,frame_highlightthickness= 0,background=light_color, frame_borderwidth = 0)
        self.scanpathbox_frame.Put(relx=0.0, rely=0.0,height=searchboxheight, relwidth=1,)

        #frame to hold far right column
        self.rightcolumn = cw.ThemedFrame(self, frame_borderwidth=0,frame_highlightthickness=0,background=light_color)
        self.rightcolumn.place(relx=1, x=-infoframewidth, rely=0.0, relheight=1, width=infoframewidth)

            
        #generate table with column labels from list with column widths
        columns = [["FILE", None], ["TITLEID", 150], ["TYPE", 60], ["SIZE", 100]]

        #Frame to hold primary lostbox
        self.list_frame = cw.ThemedFrame(self.content_frame,frame_highlightthickness=0,background=light_color)
        self.list_frame.place(relx=0,rely=0,y=searchboxheight, relheight=1, height=-(searchboxheight),relwidth=1)

        #vertical scroll bar (Not placed, trying to make it only appear when needed)
        self.vsb = tk.Scrollbar(self.content_frame,orient="vertical", command=self.OnVsb)
        # self.vsb.place(relx=0.975, rely=0.15, relheight=0.94, relwidth=0.025)

        self.listbox_list = []
        popupcommands = [
            ["Blacklist", self.blacklistTitle],
            ["Remove", self.removeTitle]
        ]
        self.maintable = cw.themedtable(self.list_frame, columns, popup_callback = self.refresh)
        self.maintable.place(relheight=1,relwidth=1, x=+separatorwidth, height=-separatorwidth,width=-separatorwidth)
        self.maintable.addpopupcommands(popupcommands)

        # bind listboxes to move with mouse scroll
        for column in columns:
            self.maintable.listboxes[column[0]].bind("<MouseWheel>", self.OnMouseWheel)

        #set listboxes to easy names
        for listbox in self.maintable.listboxes:
            self.listbox_list.append(self.maintable.listboxes[listbox])

        self.filelistbox = self.maintable.listboxes["FILE"]        
        self.titleidlistbox = self.maintable.listboxes["TITLEID"]
        self.typelistbox = self.maintable.listboxes["TYPE"]
        self.sizelistbox = self.maintable.listboxes["SIZE"]

        #Bind selecting an item to CurSelet
        self.filelistbox.bind('<<ListboxSelect>>',self.CurSelet)
        self.filelistbox.bind('<ButtonRelease-3>', self.on_right_click)

        for listbox in self.listbox_list:
            listbox.bind("<MouseWheel>", self.OnMouseWheel)
        
        self.infobox = infobox(self.rightcolumn)
        self.infobox.place(x=0,relwidth=1,y=0,relheight=1,height = -(stats_box_height + navbuttonheight + 2 * separatorwidth))

        self.left_context_button = cw.navbutton(self.rightcolumn,command_name=self.cursordown,text_string="PREV",background=dark_color)
        self.right_context_button = cw.navbutton(self.rightcolumn,command_name=self.cursorup,text_string="NEXT",background=dark_color)
        self.left_context_button.place(relx=0,rely=1, y=-(navbuttonheight+separatorwidth), x=+separatorwidth, relwidth=0.5, width=-(2*separatorwidth), height=navbuttonheight)
        self.right_context_button.place(relx=0.5,rely=1, y=-(navbuttonheight+separatorwidth), x=+0.5*separatorwidth, relwidth=0.5, width=-(2*separatorwidth), height=navbuttonheight)

        self.stats_box = statbox(self.rightcolumn)
        self.stats_box.place(x=0,rely=1,y=-(stats_box_height+ navbuttonheight + separatorwidth), relwidth=1, height=stats_box_height+separatorwidth)

        self.speed = cw.ThemedLabel(self.stats_box, "n/a mbps")
        # self.speed.place(y=75, x=+separatorwidth, relwidth = 0.8, height = 15)

        self.text = cw.ThemedLabel(self.stats_box, "n/a")
        # self.text.place(y=90, x=+separatorwidth, relwidth = 0.8, height = 15)


        self.progbar = cw.progBar(self.stats_box)
        self.progbar.Place(y=60, relx=0, relwidth = 1, width = -2*separatorwidth, x=+separatorwidth, height =15)
        self.progbar.hide()
        
        self.infoimage = tk.PhotoImage(file=os.path.join(self.cwd,"assets/info.png")).subsample(2)
        self.addimage = tk.PhotoImage(file=os.path.join(self.cwd,"assets/plus.png")).subsample(2)

        #Pil breaks this image
        self.scanimage = tk.PhotoImage(file=os.path.join(self.cwd,"assets/scan.png")).subsample(2)

        self.infoimage = ImageTk.PhotoImage(Image.open(os.path.join(self.cwd,"assets/info.png")).resize((40,40), Image.ANTIALIAS))
        self.addimage = ImageTk.PhotoImage(Image.open(os.path.join(self.cwd,"assets/plus.png")).resize((25,25), Image.ANTIALIAS))
        self.folderimage = ImageTk.PhotoImage(Image.open(os.path.join(self.cwd,"assets/folder.png")).resize((25,25), Image.ANTIALIAS))
        self.ximage = ImageTk.PhotoImage(Image.open(os.path.join(self.cwd,"assets/plus.png")).rotate(45).resize((25,25), Image.ANTIALIAS))
        #Set this to a list of buttons to appear next to the path bar
        buttonlist = [
            {
            "image" : self.addimage,
            "callback" : lambda: self.scanpathbox_frame.show(),
            "tooltip" : "Scan a folder",
            },
            {
            "image" : self.infoimage,
            "callback" : lambda: self.controller.show_frame("helpFrame"),
            "tooltip" : "Help",
            },
        ]

        scanbuttonlist = [
            {
            "image" : self.ximage,
            "callback" : lambda: self.scanpathbox_frame.hide(),
            "tooltip" : "Back",
            },
            {
            "image" : self.folderimage,
            "callback" : self.selectRomsFolder,
            "tooltip" : "Select Rom Folder",
            },
            {
            "image" : self.scanimage,
            "callback" : lambda: on_scan(self),
            "tooltip" : "Scan Rom Folder",
            },     
        ]

        self.searchbox_frame.setbuttons(buttonlist, set_pathbox = True, pathbox_placeholder = "Search", pathbox_callback = self.updatetable, pathbox_callback_on_keystroke = True,)
        self.scanpathbox_frame.setbuttons(scanbuttonlist, set_pathbox = True, pathbox_placeholder = "Path to scan")

        self.sp = self.scanpathbox_frame.sb
        self.sb = self.searchbox_frame.sb
        # self.searchbox_frame..set(str((os.path.abspath(Config.paths.scan))))

        self.showmainframe()
        self.refresh()
        self.klock()
        Users.export()

    def blacklistTitle(self):
        if self.softwarelist:
            sc = self.softwarelist[self.currentselection]
            id = sc["titleid"]
            name = Titles.get(id).name
            Config.addBlacklistedTitle("{}|{}".format(id,name))

    def removeTitle(self):
        if self.softwarelist:
            sc = self.softwarelist[self.currentselection]
            id = sc["titleid"]

            db = os.path.join(self.cwd, "titledb/files.json")
            with open(db, "r") as trackedfiles:
                tracked_files = json.load(trackedfiles)
            if type(tracked_files) == dict:
                tracked_files = [tracked_files]

            for entry in tracked_files:
                if entry["titleId"] == id:
                    tracked_files.remove(entry)

            with open(db, "w+") as trackedfiles:
                json.dump(tracked_files, trackedfiles, indent =4)



    def on_refresh(self, event=None):
        self.updatetable()
        self.updateinfobox()

    #On Clock Tick
    def on_tick(self):
        for i in Status.lst: 
            if i.isOpen():
                try:
                    self.progbar.setValue(i.i / i.size * 100)
                    self.text.set(i.desc)
                    self.speed.set(formatSpeed(i.a / (time.process_time() - i.ats)))
                except:
                    resetStatus(self)
                break
            else:
                resetStatus(self)
        if len(Status.lst) == 0:
            resetStatus(self)

        if self.needsRefresh or self.controller.needsRefresh:
            self.needsRefresh = False
            self.controller.needsRefresh = False
            self.updatetable()
            self.updateinfobox()

        self.stats_box.tick()

    def updatetable(self, search = None):
        self.maintable.clear()

        nsplist = []
        for k, f in Nsps.files.items():
            # print(json.dumps(f.dict(),indent=4))

            if f.path.endswith('.nsx'):
                continue

            nspchunk = {}
            tid = str(f.titleId)

            if tid:
                #api_dict = api.getTitle(tid)

                nspchunk["titleid"] = tid
                nspchunk["file"] = f.fileName()
                nspchunk["name"] = f.fileName()
                nspchunk["author"] = None
            
                try:
                    nspchunk["type"] = "UPD" if f.isUpdate() else ("DLC" if f.isDLC() else "BASE")
                except:
                    nspchunk["type"] = "n/a"

                nspchunk["size"] = formatBytes(os.path.getsize(f.path))
                nspchunk["photopath"] = None
                nspchunk["description"] = None #api_dict["description"]

                nsplist.append(nspchunk)

        for nsp in nsplist:
            f = nsp["file"]
            t = nsp["titleid"]
            k = nsp["type"]
            s = nsp["size"]

            fields = [f, t, k ,s]

            if not search:
                self.filelistbox.insert(END, f)
                self.titleidlistbox.insert(END, t)
                self.typelistbox.insert(END, k)
                self.sizelistbox.insert(END, s)
            else:
                for field in fields: 
                    if search.lower() in field.lower():
                        self.filelistbox.insert(END, f)
                        self.titleidlistbox.insert(END, t)
                        self.typelistbox.insert(END, k)
                        self.sizelistbox.insert(END, s)
                        break


        self.titleidlistbox.disable()
        self.typelistbox.disable()
        self.sizelistbox.disable()
        
        self.softwarelist = nsplist

        #Prevent index oob
        listlen = len(self.softwarelist)
        if self.currentselection > listlen:
            self.currentselection = listlen

    #listbox scrollbar 
    def OnVsb(self, *args):
        for listbox in self.listbox_list:
            listbox.yview(*args)

    def OnMouseWheel(self, event):
        for listbox in self.listbox_list:
            cw._on_mousewheel(event, listbox)

            if cw.getplatform() == 'Windows':
                listbox.yview("scroll",-1*int(event.delta/120),'units')
            elif cw.getplatform() == 'Darwin':
                listbox.yview("scroll", -event.delta,"units")
            else:
                if event.num == 4:
                    listbox.yview("scroll",-1, 'units')
                elif event.num == 5:
                    listbox.yview("scroll",1, 'units')

        # this prevents default bindings from firing, which
        # would end up scrolling the widget twice
        return "break"

    #INFOBOX UPDATE
    #update title information
    def updatetitle(self,title):
        self.infobox.titlevar.set(title)

    #update author information
    def updateauthor(self,author):
        self.infobox.authorvar.set("by {}".format(author))

    def updatedescription(self, description):
        self.infobox.updatedescription(description)

    #update all info in the info box
    def updateinfobox(self):
        self.updatelistboxcursor()
        if self.softwarelist:
            sc = self.softwarelist[self.currentselection]
            tid = sc["titleid"]

            # bid = Title.getBaseId(tid)
            # ttle = Titles.get(bid)
            
            api_dict = api.getTitle(Nsps.getBaseId(tid))
            self.updateAuthorImage(api_dict)

            typ = sc["type"] or None
            
            ttl = sc["name"] or "n/a"
            if typ:
                ttl += " [{}]".format(typ)
                
            if 'publisher' in api_dict:
                author = sc["author"] or "unknown"
            else:
                author = api_dict['publisher']
            
            if 'description' in api_dict:
                desc = api_dict['description']
            else:
                desc = sc["description"] or "no data"

            self.updatetitle(ttl)
            self.updateauthor(author)
            self.updatedescription(desc)

            self.controller.after(10, self.infobox.reset_placement)


    def updateAuthorImage(self, api_dict):
        notfound = "assets/notfound.png"
        if self.softwarelist:
            if self.currentselection > len(self.softwarelist): self.updatelistboxcursor()
            sc = self.softwarelist[self.currentselection]

            imag = None

            if sc["photopath"]:
                imag = sc["photopath"]

            if not imag or imag == notfound:
                tid = sc["titleid"]

                try:
                    imag = api.getTitleImage(api_dict)
                except:
                    raise
                    imag = None

                # #If no imag was found try again with the base title id
                # if not imag:
                #     tid = Title.getBaseId(tid)
                #     imag = Titles.get(tid).iconFile(infoframewidth) or Titles.get(tid).frontBoxArtFile(infoframewidth)

                if not imag: imag = notfound

                sc["photopath"] = imag

            self.infobox.updateimage(image_path = imag)
        else:
            self.infobox.updateimage(image_path = notfound)

    #movement button / cursor callbacks, moves up or down main list
    #get current selection from list box
    def on_right_click(self, event):
        try:
            self.currentselection = event.widget.nearest(event.y)
            self.updatelistboxcursor()
        finally:
            self.maintable.popup(event)

    def updatelistboxcursor(self):
        if self.currentselection > len(self.softwarelist): 
                self.currentselection = 0
        if self.listbox_list:
            for listbox in self.listbox_list:
                listbox.selection_clear(0,END)
                listbox.selection_set(self.currentselection)
                listbox.activate(self.currentselection)
                listbox.see(self.currentselection)
    def CurSelet(self, event):
        try:
            widget = event.widget
            selection=widget.curselection()
            picked = widget.get(selection[0])
            self.currentselection = widget.get(0, "end").index(picked)
            self.updateinfobox()
        except:
            pass
    def cursorup(self):
        if self.currentselection < self.filelistbox.size()-1:
            self.currentselection += 1
            self.updateinfobox()

    def cursordown(self):
        if self.currentselection > 0:
            self.currentselection -= 1
            self.updateinfobox()

    def showhelpframe(self):
        self.details_window.tkraise()
        self.details_window.event_generate("<<ShowFrame>>")

    def showmainframe(self):
        self.outer_frame.tkraise()
        self.outer_frame.event_generate("<<ShowFrame>>")
        self.rightcolumn.tkraise()



class tinyGui(cw.ThemedFrame):
    def __init__(self, parent, controller):
        self.controller = controller        #Controller (most toplevel parent)
        self.needsRefresh = True            #Variable to track if reload is needed

        width = infoframewidth + 10
        height = 95
        minwidth = infoframewidth + 10
        minheight = 95
        self.controller.geometry("{}x{}".format(width,height)) 
        self.controller.minsize(width=minwidth, height=minheight) #minimum size currently supported
        self.controller.resizable(False, False)
        self.controller.title("MUNK")

        cw.ThemedFrame.__init__(self,parent) #Init frame
        self.bind("<<ShowFrame>>", self.on_show_frame) #Bind on_show_frame to showframe event so whenever the frame is raised by the controller it reloads

        #Box to hold nut transfer info
    #-----------------------------------------------------------------------------------
        self.stats_box = statbox(self)
        self.stats_box.place(relwidth=1, relheight=1)

        self.speed = cw.ThemedLabel(self, "n/a mbps")
        # self.speed.place(y=75, x=+separatorwidth, relwidth = 0.8, height = 15)

        self.text = cw.ThemedLabel(self, "n/a")
        # self.text.place(y=90, x=+separatorwidth, relwidth = 0.8, height = 15)

        self.progbar = cw.ProgressBar(self)
        #self.progbar.special_place()
        # self.progbar.place(y = 115, x=+separatorwidth, relwidth = 0.8, height =15)
    #-----------------------------------------------------------------------------------
        self.scanpathbox_frame = cw.ButtonRow(self.stats_box)
        self.scanpathbox_frame.place(x=0,y=75,relwidth=1,height=20)

        #Images for buttons
        self.folderimage = ImageTk.PhotoImage(Image.open("assets/folder.png").resize((20, 20), Image.ANTIALIAS))
        self.scanimage = tk.PhotoImage(file="assets/scan.png").subsample(3)

        

        buttonlist = [
            {
            "image" : self.scanimage,
            "callback" : lambda: on_scan(self),
            "tooltip" : "Scan Rom Folder",
            },
            {
            "image" : self.folderimage,
            "callback" : self.selectRomsFolder,
            "tooltip" : "Select Rom Folder",
            },
        ]

        self.scanpathbox_frame.setbuttons(buttonlist, set_pathbox = True, pathbox_placeholder = "Scan", frame_height = 75, sep_width = separatorwidth/2, background=light_color, font=smallertext)
        self.sp = self.scanpathbox_frame.sb

        Users.export()

    def on_tick(self):
        for i in Status.lst: 
            if i.isOpen():
                try:
                    self.progbar.setValue(i.i / i.size * 100)
                    self.text.set(i.desc)
                    self.speed.set(formatSpeed(i.a / (time.process_time() - i.ats)))
                except:
                    resetStatus(self)
                break
            else:
                resetStatus(self)
        if len(Status.lst) == 0:
            resetStatus(self)

        self.statbox.tick()

    #Update page whenever it is raised
    def on_refresh(self):
        return






class statbox(cw.ThemedFrame):
    def __init__(self, frame):
        cw.ThemedFrame.__init__(self,frame,background=light_color,frame_borderwidth=0)

        self.iplabel = cw.ThemedLabel(self, "IP:", label_font = smallboldtext)
        self.iplabel.place(y=0, x=+separatorwidth, relwidth = 0.5, height =15)
        self.iptext = cw.ThemedLabel(self, "unknown",anchor="e")
        self.iptext.place(y=0, relx=0.5, relwidth = 0.5, width = -separatorwidth, height =15)

        self.portlabel = cw.ThemedLabel(self, "Port:", label_font = smallboldtext)
        self.portlabel.place(y=15, x=+separatorwidth, relwidth = 0.5, height =15)
        self.porttext = cw.ThemedLabel(self, "unknown",anchor="e")
        self.porttext.place(y=15, relx=0.5, relwidth = 0.5, width = -separatorwidth, height =15)

        self.userlabel = cw.ThemedLabel(self, "User:", label_font = smallboldtext)
        self.userlabel.place(y=30, x=+separatorwidth, relwidth = 0.5, height =15)
        self.usertext = cw.ThemedLabel(self, "unknown",anchor="e")
        self.usertext.place(y=30, relx=0.5, relwidth = 0.5, width = -separatorwidth, height =15)

        self.passwordlabel = cw.ThemedLabel(self, "Password:", label_font = smallboldtext)
        self.passwordlabel.place(y=45, x=+separatorwidth, relwidth = 0.5, height =15)
        self.passwordtext = cw.ThemedLabel(self, "unknown",anchor="e")
        self.passwordtext.place(y=45, relx=0.5, relwidth = 0.5, width = -separatorwidth, height =15)

        self.usblabel = cw.ThemedLabel(self, "USB:", label_font = smallboldtext)
        self.usblabel.place(y=60, x=+separatorwidth, relwidth = 0.5, height =15)
        self.usbstatus = cw.ThemedLabel(self, "unknown",anchor="e")
        self.usbstatus.place(y=60, relx=0.5, relwidth = 0.5, width = -separatorwidth, height =15)

    def updateIP(self, ip):
        self.iptext.set("{}".format(ip))

    def updatePort(self, port):
        self.porttext.set("{}".format(port))

    def updateUser(self,user):
        self.usertext.set("{}".format(user))

    def updatePassword(self, passw):
        self.passwordtext.set("{}".format(passw))

    def updateUSB(self, usbstat):
        self.usbstatus.set("{}".format(usbstat))

    def tick(self):
        ip = getIpAddress()
        port = str(Config.server.port)
        user = Users.first().id
        passw = Users.first().password
        usbstat = str(Usb.status)

        self.updateIP(ip)
        self.updatePort(port)
        self.updateUser(user)
        self.updatePassword(passw)
        self.updateUSB(usbstat)









#Displays author photo, name, project name, and project description in a column
class infobox(cw.ThemedFrame):
    def __init__(self,frame):
        cw.ThemedFrame.__init__(self,frame,background=light_color,frame_borderwidth=0)

        #holds author picture
        self.project_art_label = cw.ThemedLabel(self,label_text = "project_art",anchor="n")
        #Homebrew Title
        self.titlevar = tk.StringVar()
        self.titlevar.set("")
        self.project_title_label = cw.ThemedLabel(self, 
            label_text = "Welcome to NUT", 
            text_variable = self.titlevar, 
            foreground=info_softwarename_color, 
            label_font=mediumboldtext,
            anchor="n",
            wraplength=infoframewidth
            )
        #Description
        self.project_description = cw.ScrolledText(self,
            background=light_color,
            foreground=info_description_color,
            font=info_description_font,
            borderwidth=0,
            state=NORMAL,
            wrap="word",
            )
        #author name
        self.authorvar = tk.StringVar()
        self.authorvar.set("")
        self.author_name_label = cw.ThemedLabel(self,
            label_text = "", 
            text_variable = self.authorvar, 
            foreground=info_author_color, 
            label_font=info_author_font,
            anchor="n"
            )
        #Separator
        self.topsep = cw.ThemedFrame(self,
            background = lgray,
            frame_borderwidth = 2,
            )
        # self.botsep = cw.ThemedFrame(self,
        #     background = lgray,
        #     frame_borderwidth = 2,
        #     )

        self.topsep.place(x = (infoframewidth / 2), y = infoframewidth+52, height = 4, relwidth = 0.9, anchor="center")
        self.project_art_label.place(relx=0.0, rely=0.0, height=infoframewidth, relwidth=1)
        self.project_title_label.place(relx=0.0, rely=0.0, y=infoframewidth, relwidth=1.0)
        self.author_name_label.place(relx=0.0, rely=0, y=infoframewidth + self.project_title_label.winfo_height(),  relwidth=1.0)
        self.project_description.place(relx=0.5, rely=0.0, y=+infoframewidth+75, relheight = 1, height=-(infoframewidth + self.project_title_label.winfo_height() + self.author_name_label.winfo_height() + separatorwidth), relwidth=0.95, anchor = "n")

        self.project_description.delete('1.0', END)
        self.project_description.insert(END, QUICKSTARTTEXT)
        self.project_description.configure(state=DISABLED)


    #update project description
    def updatedescription(self, desc):
        self.project_description.configure(state=NORMAL)
        self.project_description.delete('1.0', END)
        try:
            self.project_description.insert(END, desc)
        except:
            self.project_description.insert(END, "No data")
        self.project_description.configure(state=DISABLED)


    def updatetitle(self,title):
        self.titlevar.set(title)

    #update author information
    def updateauthor(self,author):
        self.authorvar.set("by {}".format(author))

    def updateimage(self,image_path):
        art_image = Image.open(image_path)
        art_image = art_image.resize((infoframewidth, infoframewidth), Image.ANTIALIAS)
        art_image = ImageTk.PhotoImage(art_image)
    
        self.project_art_label.configure(image=art_image)
        self.project_art_label.image = art_image

        
    def reset_placement(self):
        self.project_art_label.place(relx=0.0, rely=0.0, height=infoframewidth, relwidth=1)
        self.project_title_label.place(relx=0.0, rely=0.0, y=infoframewidth, relwidth=1.0)
        self.author_name_label.place(relx=0.0, rely=0, y=infoframewidth + self.project_title_label.winfo_height(),  relwidth=1.0)
        self.topsep.place(x = (infoframewidth / 2), y = infoframewidth + self.project_title_label.winfo_height() + self.author_name_label.winfo_height() + 2*separatorwidth, height = 4, relwidth = 0.9, anchor="center")
        
        self.project_description.place(
            relx=0.5, 
            rely=0.0, 
            y=infoframewidth + self.project_title_label.winfo_height() + self.author_name_label.winfo_height() + 3*separatorwidth, 
            relheight = 1, 
            height=-(infoframewidth + self.project_title_label.winfo_height() + self.author_name_label.winfo_height() + 3*separatorwidth), 
            relwidth=0.95, 
            anchor = "n"
        )










class helpFrame(cw.ThemedFrame):
    def __init__(self, parent, controller):
        self.controller = controller        #Controller (most toplevel parent)
        cw.ThemedFrame.__init__(self,parent, background=light_color) #Init frame

        self.project_description = cw.ScrolledText(self,
            background=light_color,
            foreground=info_description_color,
            font=info_description_font,
            borderwidth=0,
            state=NORMAL,
            wrap="word",
            )
        self.project_description.place(
            relx=0,
            rely=0,
            relwidth=1,
            relheight=1,
            height = -(navbuttonheight + 2*separatorwidth)
            )
        self.bottom_bar = cw.ButtonRow(self,
            background=dark_color
            )
        self.bottom_bar.place(
            relx=0,
            rely=1,
            y=-(navbuttonheight+2*separatorwidth),
            height = (navbuttonheight+2*separatorwidth),
            relwidth=1
            )

        self.backimage = tk.PhotoImage(file="assets/returnbutton.png").subsample(2)
        self.githubimage = tk.PhotoImage(file="assets/github.png").subsample(2)
        self.tinfoilimage = tk.PhotoImage(file="assets/tinfoil.png").subsample(2)
        buttonlist = [
            {
            "image" : self.backimage,
            "callback" : lambda: raise_primary_frame(self),
            "tooltip" : "Back",
            },
            {
            "image" : self.githubimage,
            "callback" : openGithub,
            "tooltip" : "Open NUT Github in web browser",
            },
            {
            "image" : self.tinfoilimage,
            "callback" : openTinfoil,
            "tooltip" : "Open tinfoil.io in web browser",
            }, 
        ]

        self.bottom_bar.setbuttons(buttonlist, set_pathbox = False, background=light_color)
        self.set_guide_text()

    def set_guide_text(self):
        global BACKUPGUIDETEXT

        readme = getReadme(self) or BACKUPGUIDETEXT
        
        self.project_description.configure(state=NORMAL)
        self.project_description.delete('1.0',END)
        self.project_description.insert(END, readme)
        self.project_description.configure(state=DISABLED)




def resetStatus(self):
    self.progbar.setValue(0)
    self.text.set('')
    self.speed.set('')

def raise_primary_frame(self):
    for frame in self.controller.frames:
        self.controller.show_frame(frame)
        break

def openTinfoil():
    global TINFOILURL
    import webbrowser
    webbrowser.open_new_tab(TINFOILURL)

def openGithub():
    global GITHUBURL
    import webbrowser
    webbrowser.open_new_tab(GITHUBURL)


def getReadme(self):
    global CWD

    try:
        with open(os.path.join(self.controller.cwd, "README.md")) as readme:
            newreadme = ""
            for line in readme:
                if not "![alt text]" in line:
                    newreadme = newreadme + line
    except:
        newreadme = None

    return newreadme

def getIpAddress():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def scan(path):
    if path:
        Nsps.scan(path, True)
def on_scan(self):
    path = self.sp.get()
    scan(path)
    self.refresh()

def updatePath(scanPath):
    if scanPath:
        Config.paths.scan = scanPath
        Config.save()

##Formatting functions
#Format mbs from bytes
def formatSpeed(n):
    return str(round(n / 1000 / 1000, 1)) + 'MB/s'

#Make bytes sizes print friendly
def formatBytes(size):
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'k', 2: 'm', 3: 'g', 4: 't'}
    while size > power:
        size /= power
        n += 1
    size = round(size,2)
    size = str(size)
    if size.endswith(".0"):
        size = size.replace(".0","")
    size = size + " " + power_labels[n]+'b'
    if size == "1024 kb":
        size = "1 mb"
    return size
