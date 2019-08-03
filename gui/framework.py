import gui.customwidgets as cw
from tkinter import filedialog

TICKDELAY = 250

class appFramework(cw.ThemedFrame):
#Redefine these clocks in layouts as needed
#----------------------------------------------
    #Call klock at end of each framework-based frame to start it
    def klock(self):
        self.controller.after(TICKDELAY, self.klock)
        self.tick()
    def tick(self):
        self.on_tick()
        if self.needsRefresh or self.controller.needsRefresh:
            self.on_refresh()
            self.needsRefresh = False
            self.controller.needsRefresh = False
    #On Clock Tick, re-define this per layout.
    def on_tick(self):
        return
    #Reload function, re-define this per layout.
    def on_refresh(self):
        return
#-----------------------------------------------
    def __init__(self, parent, controller):
        self.controller = controller        
        self.needsRefresh = False

        cw.ThemedFrame.__init__(self,parent) #Init frame
        self.bind("<<ShowFrame>>", self.on_show_frame) #Bind on_show_frame to showframe event so whenever the frame is raised by the controller it reloads

    #Ques refresh
    def refresh(self):
        self.needsRefresh = True
    
    #Generally forces a reload
    def on_show_frame(self,event=None):
        self.refresh()

    def selectRomsFolder(self):
        self.chosenfolder = filedialog.askdirectory(initialdir="/",  title='Please select your switch roms directory card')
        if self.chosenfolder:
            self.on_show_frame()
        try:
            self.sp.set(self.chosenfolder)
        except:
            pass

