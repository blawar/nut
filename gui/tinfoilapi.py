import json, sys, os, shutil

import urllib.request 
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

BASEAPIURL = "https://tinfoil.io/Api/Title/{}"
CACHEFOLDER = "cache"
IMAGENAME  = "thumbnail.png"
APIFILENAME = "title.json"

class getError(Exception):
    pass

class loadError(Exception):
    pass

def getTitleFile(id):
    path = os.path.join(os.path.join(sys.path[0], CACHEFOLDER), id)
    file = os.path.join(path, APIFILENAME)
    return file

def getTitle(id = None):
    file = getTitleFile(id)
    
    if os.path.isfile(file):
        title_dict = loadJson(file)
        return title_dict

    file = getJson(id)

    if os.path.isfile(file):
        title_dict = loadJson(file)
        return title_dict

    return {}

def getTitleImage(title_dict):
    path = os.path.join(os.path.join(sys.path[0], CACHEFOLDER), title_dict['id'])
    image_file = os.path.join(path, IMAGENAME)

    if os.path.isfile(image_file):
        return(image_file)

    if title_dict:
        if not "icon_url" in title_dict:
            return None
        icon_url = title_dict["icon_url"]
        if not icon_url:
            return None
        downloaded_file = None
        try:
            downloaded_file, headers = urllib.request.urlretrieve(icon_url)
            shutil.move(downloaded_file, image_file)
            print('downloading image %s' % icon_url)
            return image_file
        except Exception as e: 
            print("Exception getting json %s, %s -> %s" % (e, str(downloaded_file), str(image_file)))
            raise

    raise getError()

def getTitleValue(id, key):
    title_dict = getTitle(id)

    if title_dict:
        try:
            return title_dict[key]
        except Exception as e:
            print("Error getting title value for key {} for id {}".format(key,id))
    
    raise getError()

def getJson(id):
    apiURL = BASEAPIURL.format(id)
    file = getTitleFile(id)
    path = os.path.dirname(file)

    if not os.path.isdir(path):
        try:
            os.mkdir(path)
        except:
            if os.path.isdir(path):
                pass
            else:
                print("Failed to init cache dir for {}".format(id))

    try:
        downloaded_file, headers = urllib.request.urlretrieve(apiURL, file)
        return downloaded_file
    except Exception as e: 
        print("Exception getting json {}".format(e))
    
    return '{}'

def loadJson(file):
    try:
        if os.path.isfile(file):
            with open(file, encoding="utf8") as file_object:
                file_dict = json.load(file_object)
                return file_dict
    except Exception as e:
        print("Exception loading json %s - file %s" % (e, file))
    
    return {}


def get_title_jsons(idlist):
    raise IOError("do not call this")
    import threading

    threadlist = []
    for id in idlist:
        threadlist.append(threading.Thread(target = getTitle, args = (str(id),)))

    for thread in threadlist:
        thread.start()

    for thread in threadlist:
        thread.join()



def test(id):
    getTitleImage(id)
    print(getTitleValue(id, "description"))

if __name__ == "__main__":
    #"Test with airheart tales of broken wings"
    test("01003DD00BFEE000")