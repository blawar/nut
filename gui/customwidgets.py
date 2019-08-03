import platform, os
import tkinter as tk
from tkinter.constants import *
from gui.format import *

#Basic Widgets

#Frame to use instead of default tk.frame, by default themed with light_color
class ThemedFrame(tk.Frame):
	def __init__(self,parent,frame_borderwidth = 0,frame_highlightthickness = 0,background = dark_color,frame_highlightcolor=dark_color):
		tk.Frame.__init__(self,parent, 
			background = background,
			highlightcolor = frame_highlightcolor,
			highlightthickness=frame_highlightthickness,
			highlightbackground=light_color,
			borderwidth = frame_borderwidth,
			)

#listbox themed properly from format.py
class ThemedListbox(tk.Listbox):
	def __init__(self,frame,font=listbox_font, **kw,):
		tk.Listbox.__init__(self,frame,
			highlightthickness=0,
			highlightbackground=light_color,
			borderwidth=0,
			exportselection = False, 
			background=dark_color,
			foreground=listbox_font_color,
			font=font,
			disabledforeground=dark_listbox_font_color,
			selectbackground=listboxselectionbackground,
			selectforeground=listboxselectionforeground,
			)

#themed author/ etc label
class ThemedLabel(tk.Label):
	def __init__(self,frame,label_text,label_font=smalltext,text_variable=None,background = light_color,foreground=lgray,anchor="w",wraplength = None):
		tk.Label.__init__(self,frame,
			background = background,
			highlightthickness=0,
			anchor=anchor,
			text = label_text,
			font=label_font,
			foreground= foreground,
			textvariable = text_variable,
			)
		if not wraplength == None:
			self.configure(wraplength=wraplength)
	def set(self,text):
		self.configure(text=text)


#Separator, defaults to light color
class Separator(ThemedLabel):
	def __init__(self,frame,color = None):
		if color:
			bgc = color
		else:
			bgc = light_color
		ThemedLabel.__init__(self,frame,"",background=bgc)


#Custom button
#A tkinter label with a bound on-click event to fix some issues 
#that were happening with normal tkinter buttons on MacOS.
#Unfortunately MacOS was causing a weird white translucent
#effect to be applied to all classes that used the tk.Button Widget.
#This fixes it but making our own "button" by binding a callback to 
#an on_click event. Feel free to use this in other projects where mac
#compatibility is an issue, also special thanks to Kabiigon for testing
#this widget until I got it right since I don't have a mac
class navbutton(tk.Label):
	def __init__(self,frame,command_name=None,image_object= None,text_string=None,background=dark_color):
		self.command = command_name

		tk.Label.__init__(self,frame,
			background=background,
			foreground= w,
			borderwidth= 0,
			activebackground=light_color,
			image=image_object,
			text = text_string,
			font = navbuttonfont,
			)
		self.bind('<Button-1>', self.on_click)

	#Use callback when our makeshift "button" clicked
	def on_click(self, event=None):
		if self.command:
			self.command()

	#Function to update the button's set command
	def setcommand(self,command):
		self.command = command

	#Function to set the button's image
	def setimage(self,image):
		self.configure(image=image)

	#Function to set the button's text
	def settext(self,text):
		self.configure(text=text)



#compound widgets for different pages
#Used to navigate list pages
class navbox(ThemedFrame):
	def __init__(self,frame,
		
		primary_button_command,
		etc_button_command,
		left_context_command,
		right_context_command,
		etc_button_image,
		etc_button_text = "",
		primary_button_text = "INSTALL",
		left_context_text = "PREV",
		right_context_text = "NEXT",
		):
		ThemedFrame.__init__(self,frame, background=light_color, frame_borderwidth=0)

		#big button
		self.primary_button = navbutton(self, text_string = primary_button_text, command_name = primary_button_command)
		self.primary_button.place(relx=0.0, rely=0, x=+navbuttonspacing, height=navbuttonheight, width=(navboxwidth - navbuttonheight) - 3.5 * navbuttonspacing)

		#etc button
		self.etc_button = navbutton(self, text_string = etc_button_text, image_object=etc_button_image, command_name=etc_button_command)
		self.etc_button.place(relx=0, rely=0, x=navboxwidth - (navbuttonheight + 1.5 * navbuttonspacing), height=navbuttonheight, width=navbuttonheight)

		#previous in context
		self.left_context_button = navbutton(self, text_string = left_context_text, command_name = left_context_command)
		self.left_context_button.place(relx=0.0, rely=0, x=+navbuttonspacing, y=navbuttonheight + navbuttonspacing,  height=navbuttonheight, width = ((navboxwidth)*0.5) - 1.5 * navbuttonspacing)

		#next in context
		self.right_context_button = navbutton(self, text_string=right_context_text, command_name=right_context_command)
		self.right_context_button.place(relx=0, rely=0, y=navbuttonheight + navbuttonspacing, height=navbuttonheight, x=((navboxwidth + navbuttonspacing) *0.5), width = ((navboxwidth)*0.5) - 2 * navbuttonspacing)


class titledlistbox(ThemedFrame):
	def __init__(self,frame,title):
		ThemedFrame.__init__(self,frame)
		self.label_frame = ThemedFrame(self)
		self.label_frame.place(relx=0.0, rely=0.0, height=columtitlesheight, relwidth=1)
		self.listbox_label = ThemedLabel(self.label_frame, title, label_font = columnlabelfont, background = dark_color, foreground = columnlabelcolor, anchor="w")
		self.listbox_label.place(relx=0, x=+columnoffset, rely=0, height=columtitlesheight-separatorwidth/2, relwidth=1, width = -columnoffset)
		self.listbox_separator = Separator(self) 
		self.listbox_separator.place(y=columtitlesheight-separatorwidth/2,relwidth=1,height=separatorwidth/2)
		self.listbox_frame = ThemedFrame(self)
		self.listbox_frame.place(relx=0, x=+2*columnoffset,rely=0, y=+columtitlesheight, relheight=1,height=-columtitlesheight, relwidth=1,width=-2*columnoffset)
		self.listbox = ThemedListbox(self.listbox_frame)
		self.listbox.place(relheight=1,relwidth=1)

	def activate(self,sel):
		self.listbox.activate(sel)

	def bind(self,event,callback):
		self.listbox.bind(event,callback)

	def configure(self, **args):
		self.listbox.configure(args)

	def itemconfig(self,index,**args):
		self.listbox.itemconfig(index,args)

	def insert(self, index, item):
		self.listbox.insert(index, item)

	def curselection(self):
		return self.listbox.curselection()

	def get(self, arg):
		return self.listbox.get(arg)

	def selection_clear(self,index,end):
		self.listbox.selection_clear(index,end)

	def selection_set(self,index):
		self.listbox.selection_set(index)

	def see(self, index):
		self.listbox.see(index)

	def yview(self,event,delta,units):
		self.listbox.yview(event,delta,units)

	def delete(self, index,end):
		self.listbox.delete(index,end)

	def size(self):
		return self.listbox.size()

	def disable(self):
		self.listbox.configure(state=DISABLED)

	def enable(self):
		self.listbox.configure(state=NORMAL)

	def index(self, i):
		self.listbox.index(i)

	def nearest(self, i):
		self.listbox.index(i)


class themedtable(ThemedFrame):
	def __init__(self,frame,columns,columnwidth = 150, popup_callback = None):
		self.columnwidth = columnwidth
		self.listboxes = {}
		self.popupsSet = False
		self.popup_on_exit_callback = popup_callback
		ThemedFrame.__init__(self,frame)

		numcolumns = len(columns)
		curcolumn = 0
		curx = 0
		for column in reversed(columns):
			title = column[0]
			listbox = titledlistbox(self, title)
			
			#if we are on last column, make it fill the rest of the available space
			if curcolumn == numcolumns-1:
				self.listbox = listbox
				self.listbox.place(relx=0,relwidth=1,width=-curx,relheight=1)
				# self.listbox.bind("<Button-3>", self.popup)

				self.popup_menu = tk.Menu(self, tearoff=0)
				self.popup_menu.config(
					activebackground = dark_color,
					activeforeground = w,
					foreground = w,
					background = light_color,
					borderwidth = separatorwidth,
					font = smalltext,
					)
				self.popup_menu.bind("<Leave>", self.leave)
				self.popup_menu.bind("<ButtonPress>", self.leave)
				tooltip(self.popup_menu, "ADD TO 'conf/blacklist.txt'")

			#Normal column 
			else:
				cwidth = self.columnwidth
				if not column[1] == None:
					cwidth = column[1]

				listbox.place(relx=1,x=-((curx+cwidth)-(separatorwidth/2)),relheight=1,width=(cwidth-separatorwidth/2))
				lbseparator = Separator(self)
				lbseparator.place(relx=1,x=-(curx+cwidth),relheight=1,width=separatorwidth/2)
				curx += cwidth

			self.listboxes[title] = listbox
			curcolumn += 1

	#Table
	def clear(self):
		self.enable()
		for lb in self.listboxes:
			self.listboxes[lb].delete(0,END)

	def enable(self):
		for lb in self.listboxes:
			self.listboxes[lb].configure(state = NORMAL)

	def disable(self):
		for lb in self.listboxes:
			self.listboxes[lb].configure(state = DISABLED)

	#Popup
	def leave(self, event=None):
		self.hide()

	def hide(self):
		self.popup_menu.grab_release()

	def popup(self, event):
		if self.popupsSet:
			try:
				self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
			finally:
				self.popup_menu.grab_release()
				if self.popup_on_exit_callback:
					self.popup_on_exit_callback()

	def addpopupcommands(self, commandDict):
		for label, command in commandDict:
			self.popup_menu.add_command(label=label,
				command=command)
		self.popupsSet = True



#Tooltip
class ToolTipBase:
	def __init__(self, button):
		self.button = button
		self.tipwindow = None
		self.id = None
		self.x = self.y = 0
		self._id1 = self.button.bind("<Enter>", self.enter)
		self._id2 = self.button.bind("<Leave>", self.leave)
		self._id3 = self.button.bind("<ButtonPress>", self.leave)

	def enter(self, event=None):
		self.schedule()

	def leave(self, event=None):
		self.unschedule()
		self.hidetip()

	def schedule(self):
		self.unschedule()
		self.id = self.button.after(10, self.showtip)

	def unschedule(self):
		id = self.id
		self.id = None
		if id:
			self.button.after_cancel(id)

	def showtip(self):
		if self.tipwindow:
			return
		# The tip window must be completely outside the button;
		# otherwise when the mouse enters the tip window we get
		# a leave event and it disappears, and then we get an enter
		# event and it reappears, ad naseum.
		x = self.button.winfo_rootx() + 20
		y = self.button.winfo_rooty() + self.button.winfo_height() + 1
		self.tipwindow = tw = tk.Toplevel(self.button)
		tw.wm_overrideredirect(1)
		tw.wm_geometry("+%d+%d" % (x, y))
		self.showcontents()

	def showcontents(self, text=""):
		label = tk.Label(self.tipwindow, text=text, justify=LEFT,
					  background=dark_color, 
					  relief=SOLID, 
					  borderwidth=2,
					  foreground=lgray,
					  font=mediumboldtext
					  )
		label.pack()

	def hidetip(self):
		tw = self.tipwindow
		self.tipwindow = None
		if tw:
			tw.destroy()



class tooltip(ToolTipBase):
	def __init__(self, button, text):
		ToolTipBase.__init__(self, button)
		self.text = text

	def showcontents(self):
		ToolTipBase.showcontents(self, self.text)





#User Entry Boxes:
class Placeholder_State(object):
	 __slots__ = 'normal_color', 'normal_font', 'placeholder_text', 'placeholder_color', 'placeholder_font', 'contains_placeholder'

def add_placeholder_to(entry, placeholder, color="grey", font=None):
	normal_color = entry.cget("fg")
	normal_font = entry.cget("font")

	if font is None:
		font = normal_font

	state = Placeholder_State()
	state.normal_color=normal_color
	state.normal_font=normal_font
	state.placeholder_color=color
	state.placeholder_font=font
	state.placeholder_text = placeholder
	state.contains_placeholder=True

	def on_focusin(event, entry=entry, state=state):
		if state.contains_placeholder:
			entry.delete(0, "end")
			entry.config(fg = state.normal_color, font=state.normal_font)
		
			state.contains_placeholder = False

	def on_focusout(event, entry=entry, state=state):
		if entry.get() == '':
			entry.insert(0, state.placeholder_text)
			entry.config(fg = state.placeholder_color, font=state.placeholder_font)
			
			state.contains_placeholder = True

	entry.insert(0, placeholder)
	entry.config(fg = color, font=font)

	entry.bind('<FocusIn>', on_focusin, add="+")
	entry.bind('<FocusOut>', on_focusout, add="+")
	
	entry.placeholder_state = state

	return state

class entrybox(tk.Frame):
	def __init__(self, master, 
		entry_width=30, 
		entry_font=smalltext, 
		entry_background=dark_color, 
		entry_foreground=search_font_color, 
		placeholder=None,
		placeholder_font=smalltext, 
		placeholder_color=place_holder_color, 
		spacing=10, 
		command=None,
		command_on_keystroke = False, 
		justification="left"
	):

		tk.Frame.__init__(self, master, borderwidth=0, highlightthickness=0,background=entry_background,)

		self._command = None
		
		self.entry = tk.Entry(self, 
			width=entry_width, 
			background=entry_background, 
			disabledbackground=entry_background,
			foreground = entry_foreground,
			disabledforeground=w,
			highlightcolor=dark_color, 
			highlightthickness=0, 
			borderwidth=0,
			justify=justification
			)
		self.entry.place(x=0,y=0,relwidth=1,relheight=1)

		if entry_font:
			self.entry.configure(font=entry_font)

		if placeholder:
			add_placeholder_to(self.entry, placeholder, color=placeholder_color, font=smalltext)

		if command:
			self._command = command

			if command_on_keystroke:
				self.entry.bind("<KeyRelease>", self._on_execute_command)

		self.entry.bind("<Escape>", lambda event: self.entry.nametowidget(".").focus())

		self.focus()
		self.on_focusout()

		self.last = None



	def get(self):
		entry = self.entry
		if hasattr(entry, "placeholder_state"):
			if entry.placeholder_state.contains_placeholder:
				return ""
		return entry.get().strip().strip("/")

	def cget(self, kw):
		entry = self.entry
		return entry.cget(kw)

	def set(self, text):
		if not text == None and not text == "":
			self.last = self.get()
			self.on_focusin()
			self.entry.insert(0, text)
			self.on_focusout()
		else:
			self.focus()


	def on_focusin(self):
		entry = self.entry
		state = entry.placeholder_state
		
		if state.contains_placeholder:
			entry.config(fg = state.normal_color, font=state.normal_font)
			state.contains_placeholder = False

		entry.delete(0, "end")

	def on_focusout(self):
		entry = self.entry
		state = entry.placeholder_state

		if entry.get() == '':
			entry.insert(0, state.placeholder_text)
			entry.config(fg = state.placeholder_color, font=state.placeholder_font)
			
			state.contains_placeholder = True

		if state.contains_placeholder:
			entry.configure(disabledforeground = state.placeholder_color, font = state.placeholder_font)
		else:
			entry.configure(disabledforeground = state.normal_color, font = state.normal_font)

	def clear(self):
		self.entry.delete(0, END)
		self.focus()
		
	def focus(self):
		self.entry.nametowidget(".").focus()

	def disable(self):
		self.entry.configure(state=DISABLED)

	def enable(self):
		self.entry.configure(state=NORMAL)

	def _on_execute_command(self, event):
		text = self.get()
		if self._command:
			self._command(text)


#Widgets with scroll bars that appear when needed and supporting code
#Automatic scrollbars on certain text boxes
class AutoScroll(object):
	def __init__(self, master):
		try:
			vsb = tk.Scrollbar(master, orient='vertical', command=self.yview)
		except:
			pass
		hsb = tk.Scrollbar(master, orient='horizontal', command=self.xview)

		try:
			self.configure(yscrollcommand=self._autoscroll(vsb))
		except:
			pass
		self.configure(xscrollcommand=self._autoscroll(hsb))

		self.grid(column=0, row=0, sticky='nsew')
		try:
			vsb.grid(column=1, row=0, sticky='ns')
		except:
			pass
		hsb.grid(column=0, row=1, sticky='ew')

		master.grid_columnconfigure(0, weight=1)
		master.grid_rowconfigure(0, weight=1)

		methods = tk.Pack.__dict__.keys() | tk.Grid.__dict__.keys() \
			| tk.Place.__dict__.keys()

		for meth in methods:
			if meth[0] != '_' and meth not in ('config', 'configure'):
				setattr(self, meth, getattr(master, meth))

	@staticmethod
	def _autoscroll(sbar):
		'''Hide and show scrollbar as needed.'''
		def wrapped(first, last):
			first, last = float(first), float(last)
			if first <= 0 and last >= 1:
				sbar.grid_remove()
			else:
				sbar.grid()
			sbar.set(first, last)
		return wrapped

	def __str__(self):
		return str(self.master)

def _create_container(func):
	'''Creates a tk Frame with a given master, and use this new frame to
	place the scrollbars and the widget.'''
	def wrapped(cls, master, **kw):
		container = tk.Frame(master)
		container.bind('<Enter>', lambda e: _bound_to_mousewheel(e, container))
		container.bind('<Leave>', lambda e: _unbound_to_mousewheel(e, container))
		return func(cls, container, **kw)
	return wrapped

class ScrolledText(AutoScroll, tk.Text):
	'''A standard Tkinter Text widget with scrollbars that will
	automatically show/hide as needed.'''
	@_create_container
	def __init__(self, master, **kw):
		tk.Text.__init__(self, master, **kw)
		AutoScroll.__init__(self, master)

class ScrolledListBox(AutoScroll, ThemedListbox):
	@_create_container
	def __init__(self, master, **kw):
		ThemedListbox.__init__(self, master, **kw,)
		AutoScroll.__init__(self, master)

def _bound_to_mousewheel(event, widget):
	child = widget.winfo_children()[0]
	if platform.system() == 'Windows' or platform.system() == 'Darwin':
		child.bind_all('<MouseWheel>', lambda e: _on_mousewheel(e, child))
		child.bind_all('<Shift-MouseWheel>', lambda e: _on_shiftmouse(e, child))
	else:
		child.bind_all('<Button-4>', lambda e: _on_mousewheel(e, child))
		child.bind_all('<Button-5>', lambda e: _on_mousewheel(e, child))
		child.bind_all('<Shift-Button-4>', lambda e: _on_shiftmouse(e, child))
		child.bind_all('<Shift-Button-5>', lambda e: _on_shiftmouse(e, child))

def _unbound_to_mousewheel(event, widget):
	if platform.system() == 'Windows' or platform.system() == 'Darwin':
		widget.unbind_all('<MouseWheel>')
		widget.unbind_all('<Shift-MouseWheel>')
	else:
		widget.unbind_all('<Button-4>')
		widget.unbind_all('<Button-5>')
		widget.unbind_all('<Shift-Button-4>')
		widget.unbind_all('<Shift-Button-5>')

def _on_mousewheel(event, widget):
	if platform.system() == 'Windows':
		widget.yview("scroll",-1*int(event.delta/120),'units')
	elif platform.system() == 'Darwin':
		widget.yview("scroll", -event.delta,"units")
	else:
		if event.num == 4:
			widget.yview("scroll",-1, 'units')
		elif event.num == 5:
			widget.yview("scroll",1, 'units')


def _on_shiftmouse(event, widget):
	if platform.system() == 'Windows':
		widget.xview_scroll(-1*int(event.delta/120), 'units')
	elif platform.system() == 'Darwin':
		widget.xview_scroll(-1*int(event.delta), 'units')
	else:
		if event.num == 4:
			widget.xview_scroll(-1, 'units')
		elif event.num == 5:
			widget.xview_scroll(1, 'units')

def getplatform():
	return platform.system()

class progBar(ThemedFrame):
	def __init__(self, frame):
		ThemedFrame.__init__(self,frame,background=dark_color)

		self.progress = ThemedFrame(self, background=light_color)
		self.geo = None
		self.placed = False
		self.setValue(None)

	def setValue(self, val):
		if val and not val == 0:
			if not self.placed:
				self.show()
			self.progress.place(x=separatorwidth, y=separatorwidth, relheight=1, height=-(2*separatorwidth),relwidth=(val/100),width=-2*separatorwidth)
		else:
			if self.placed:
				self.hide()

	def show(self):
		self.place(self.geo)
		self.placed = True

	def hide(self):
		self.place_forget()
		self.placed = False

	def Place(self, **geo):
		self.place(**geo)
		self.placed = True
		self.geo = geo




class ButtonRow(ThemedFrame):
	def __init__(self, frame, **kw):
		ThemedFrame.__init__(self,frame,**kw)
		self.placed = False
		self.geo = None

	#Call this with a list of image objects, tooltips, and associated callbacks to initialize the path box and add buttons
	def setbuttons(self,buttonlist, set_pathbox = False, pathbox_callback = None, pathbox_callback_on_keystroke = False, pathbox_placeholder = "Scan", frame_height = searchboxheight, sep_width = separatorwidth, background=dark_color, font=mediumboldtext):
	    iconspacer = frame_height - sep_width #<- uncomment for slight offset

	    #Generate a button and link a tooltip for each button in the list
	    for button in buttonlist:
	        if not button == buttonlist[0]:
	            iconspacer += frame_height-2*sep_width
	        buttonobj = navbutton(self,image_object=button["image"],command_name=button["callback"],background=background)
	        buttonobj.place(relx= 1, rely=.5, x=-iconspacer, y = -((frame_height)/2) + sep_width,width = frame_height-2*sep_width, height=frame_height-2*sep_width)
	        button_ttp = tooltip(buttonobj,button["tooltip"])
	        iconspacer += sep_width

	    if set_pathbox:
	        #add search box with remaining space
	        iconspacer += sep_width
	        self.sb = entrybox(self, command=pathbox_callback, command_on_keystroke = pathbox_callback_on_keystroke, placeholder=pathbox_placeholder, entry_font=font)
	        self.sb.place(relx=0,rely=.5, x=+sep_width, relwidth=1, width=-(iconspacer), height=frame_height-2*sep_width, y=-((frame_height)/2) + sep_width)

	#One of these is called to assign it a place on the parent frame
	def Place(self, **geo):
		self.place(**geo)
		self.placed = True
		self.geo = geo

	def Put(self, **geo):
		self.geo = geo

	#These are called after to show or hide the row of buttons + entry box
	def show(self):
		self.place(self.geo)
		self.placed = True

	def hide(self):
		self.place_forget()
		self.placed = False
