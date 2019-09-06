#format.py

##Base colors:
#background color
light_color = "#1f1f1f"
#Color for most user-interactable items
dark_color = "#121212"
#White
w = "#ffffff"
#Black
b = "#000000"
#lgray (used for author / project title / description
lgray = "#acadaf"



##Text Styles
#Normal Text
smallertext = ("Trebuchet MS",8)
smalltext = ("Trebuchet MS",10)
mediumtext = ("Trebuchet MS",12)
largetext = ("Trebuchet MS",14,)
#Bold
smallerboldtext = ("Trebuchet MS",8,"bold")
smallboldtext = ("Trebuchet MS",10,"bold")
mediumboldtext = ("Trebuchet MS",12,"bold")
largeboldtext = ("Trebuchet MS",14,"bold")
giantboldtext = ("Trebuchet MS",16,"bold")



##Dimensions
#width infoframe takes up
infoframewidth = 200
#Height of searchbox
searchboxheight=45
#consistant separator width
separatorwidth = 4
#Height of the frames holding the listbox column titles
columtitlesheight= 25 
#Offset of listbox contents
columnoffset = 5
#Height of the stats box
stats_box_height = 75
#Nav button box dimensions
navboxheight = 87.5
navboxwidth = infoframewidth
navbuttonheight = 40
navbuttonfont = mediumboldtext
navbuttonspacing = separatorwidth
etcbuttonwidth = navbuttonheight


##Widget colors
#Info column 
info_author_color= lgray
info_author_font = smallboldtext
info_softwarename_color = w
info_softwarename_font = mediumboldtext
info_description_color = w
info_description_font = smalltext
#Listbox selection highlight color 
listboxselectionbackground =  "#c4c4c4"
#Listbox selection text color
listboxselectionforeground = b
#Listbox column label color
columnlabelcolor = w
#Listbox column label font
columnlabelfont = mediumboldtext
#Text in listbox
listbox_font  = mediumtext
#Color of primary listbox font
listbox_font_color = w
#Color of the text in listboxes other then the primary file list
dark_listbox_font_color = "#777777"

#Font when typing in search box (Path box)
search_font = mediumtext
search_font_color = w

#font for placeholder in search box (path box)
place_holder_font = mediumboldtext
place_holder_color = "#777777"