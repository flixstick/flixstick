import CommonFunctions
import binascii
import os
import sys
import requests
import time
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

common  = CommonFunctions
addonid = "plugin.program.flixstick"
Addon   = xbmcaddon.Addon(addonid)
home    = xbmc.translatePath('special://home')
profile = Addon.getAddonInfo('profile')
dialog  = xbmcgui.Dialog()
dp      = xbmcgui.DialogProgress()
urlSize = ""
pbUrl   = None

tvdict = {
    "BBC iplayer" : "ActivateWindow(10025,\"plugin://plugin.video.iplayerwww\",return)",
    "Crackle" : "ActivateWindow(10025,\"plugin://plugin.video.crackle/?id=shows&mode=99\",return)",
    "ITV" : "ActivateWindow(10025,\"plugin://plugin.video.itv/?mode=1&name=Shows&url=http://www.itv.com/hub/shows\",return)",
}

moviedict = {
    "BBC iplayer" : "ActivateWindow(10025,\"plugin://plugin.video.iplayerwww/?mode=126&url=films\",return)",
    "Crackle" : "ActivateWindow(10025,\"plugin://plugin.video.crackle/?id=movies&mode=99\",return)",
}

tvlist = tvdict.keys()
movielist = moviedict.keys()

# keyword = "Ygj3bKpK"
# keyword = "66EHj0kz"

def checkTar (source):
    import tarfile
    return tarfile.is_tarfile(source)

def checkZip (source):
    import zipfile
    if zipfile.is_zipfile(source):
        zipCheck = zipfile.ZipFile(source)
        if zipCheck.testzip() == None: return True
    return False

def cleanHTML(text):
    clean = common.replaceHTMLCodes(text)
    clean = common.stripTags(clean)
    return clean.encode('utf-8')

def compress(src,dst,useZip=True,parent=False, exclude_dirs=['temp'], exclude_files=['kodi.log','kodi.old.log']):
    directory = os.path.dirname(dst)
    if not os.path.exists(directory):
        try:
            xbmcvfs.mkdirs(directory)
        except Exception as e:
            xbmc.log(repr(e),2)
            return
    if useZip:
        import zipfile
        zip = zipfile.ZipFile(dst, 'w', compression=zipfile.ZIP_DEFLATED)
    else:
        import tarfile
        zip = tarfile.open(dst, mode='w')
    try:
        if os.path.exists(src):
            rootLen = len(os.path.dirname(os.path.abspath(src)))
            for base, dirs, files in os.walk(src):
                dirs[:]  = [d for d in dirs if d not in exclude_dirs]
                files[:] = [f for f in files if f not in exclude_files and not 'crashlog' in f and not 'stacktrace' in f]
                archive_root = os.path.abspath(base)[rootLen:]

                for f in files:
                    fullpath = os.path.join(base, f)
                    if parent:
                        archive_name = os.path.join(archive_root, f)
                        if useZip:
                            zip.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)
                        else:
                            zip.add(fullpath, archive_name)
                    else:
                        newpath = fullpath.split(src)[1]
                        if useZip:
                            zip.write(fullpath, newpath, zipfile.ZIP_DEFLATED)
                        else:
                            zip.add(fullpath, newpath)
            zip.close()
            return True
    except Exception as e:
        xbmc.log(repr(e),2)
        zip.close()
        return False

def createKw():
    import shutil
    backupFolder = xbmc.translatePath("special://home")
    librePath = "/storage/.kodi"
    backup = os.path.join(backupFolder,"backup")
    if os.path.exists(librePath): backup="/storage/backup/"
    packages = os.path.join(backupFolder,"addons","packages")
    if os.path.exists(packages):
        shutil.rmtree(packages)
    backupSize = folderSize(backupFolder)
    space = freeSpace(backupFolder)
    choice = 1
    if backupSize > space:
        choice = dialog.yesno(getString(32027),getString(32028))
        if choice:
            shutil.rmtree(backup)
    if choice:
        if not os.path.exists(backup):
            xbmcvfs.mkdirs(backup)
        backupName = timestamp()+".tar"
        backupPath = os.path.join(backup,backupName)
        result = compress(backupFolder,backupPath,False,False,['temp','backup'],['kodi.log','kodi.old.log'])
        if result: dialog.ok(getString(32029),getString(32030)%(backupName,backup))
        else: dialog.ok(getString(32031),getString(32032))

def download(url,dest,dp=None):
    import urllib
    try:
        if dp:
            startTime=time.time()
            urllib.urlretrieve(url, dest, lambda nb, bs, fs: downloadProgress(nb, bs, fs, dp, startTime))
        else: urllib.urlretrieve(url, dest)
    except Exception as e:
        xbmc.log(e,2)
        return False
    return True

def downloadCheck(url,dstFile,update=False):
    urlSize = linkDate(url)
    if urlSize != Addon.getSetting("cache"):
        if update:
            if not dialog.yesno(getString(32013),getString(32014),yeslabel=getString(32015),nolabel=getString(32016)):
                return False
        dp.create(getString(32009),getString(32010))
        return download(url,dstFile,dp)
    return False

def downloadProgress(numblocks, blocksize, filesize, dp, start_time):
    percent = min(numblocks * blocksize * 100 / filesize, 100) 
    currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
    kbps_speed = numblocks * blocksize / (time.time() - start_time) 
    if kbps_speed > 0: eta = (filesize - numblocks * blocksize) / kbps_speed 
    else: eta = 0 
    kbps_speed = kbps_speed / 1024 
    total = float(filesize) / (1024 * 1024) 
    mbs = getString(32004) % (currently_downloaded, total) 
    e = getString(32005) % kbps_speed 
    e += "[CR]"+getString(32006) % divmod(eta, 60) 
    dp.update(percent, mbs, e)
    if dp.iscanceled(): dp.close()

def extract(source,dest,dp=None):
    import zipfile
    nFiles = 0
    count = 0
    try:
        if dp:
            zin = zipfile.ZipFile(source,  'r')
            nFiles   = float(len(zin.infolist()))
            contents = zin.infolist()
            for item in contents:
                count += 1
                update = count / nFiles * 100
                dp.update(int(update))
                zin.extract(item, dest)
            zin.close()
            dp.close()
        else: zin.extractall(dest)
    except Exception as e:
        xbmc.log(e,2)
        return False
    return True

def folderSize(dirname):
    finalSize = 0
    for dirpath, dirnames, filenames in os.walk(dirname):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            finalSize += os.path.getsize(fp)
    return finalSize

def freeSpace(dirname):
    dirname = os.path.dirname(dirname)
    if xbmc.getCondVisibility('system.platform.windows'):
        import ctypes
        freeBytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dirname), None, None, ctypes.pointer(freeBytes))
        finalSize = freeBytes.value
    else:
        st = os.statvfs(dirname)
        finalsize = st.f_bavail * st.f_frsize
        return finalsize

def getString(code,system=False):
    if system: return xbmc.getLocalizedString(code)
    return Addon.getLocalizedString(code)

def getUrl(contents):
    for line in contents.split():
        if 'http' in line: return line.strip()
    return None

def installZip(pbUrl,update=False,reinstall=False):
    content = pastebin(pbUrl)
    if not content: dialog.ok(getString(32007),getString(32008))
    else:
        url = getUrl(content)
        content = content.replace(url,"")
        runInstall = True
        if not update and not reinstall:
            viewNotes(content)
            runInstall = dialog.yesno(getString(32018),getString(32024)%pbUrl.replace(getString(32001),""))
        if runInstall:
            if downloadCheck(url,dl,update):
                dp.close()
                xbmc.log('download check success, checking if valid zip',2)
                if checkZip(dl):
                    xbmc.log("ALL GOOD, EXTRACTING",2)
                    dp.create(getString(32009),getString(32012))
                    if extract(dl,home,dp):
                        Addon.setSetting("cache",urlSize)
                        Addon.setSetting("kw",keyword)
                        Addon.setSetting("notes",binascii.hexlify(content))
                        xbmcvfs.delete(dl)
                        dialog.ok(getString(32009),getString(32012))
                elif checkTar(dl):
                    xbmcvfs.rename(dl,'/storage/.restore/%s.tar' % timestamp())
                    xbmc.executebuiltin('Reboot')
                else:
                    xbmc.log("NOT VALID FILE",2)
            else:
                xbmc.log("NOTHING NEW",2)

def kwOptions():
    notes = Addon.getSetting("notes")
    size = Addon.getSetting("cache")
    choices = [getString(32021),getString(32022)]
    choice = dialog.select("[COLOR dodgerblue]%s[/COLOR]"%currentKw,choices)
    if choice != -1:
        if choices[choice] == getString(32021): viewNotes(binascii.unhexlify(notes))
        if choices[choice] == getString(32022):
            if dialog.yesno(getString(32022),getString(32020)):
                wipeSettings()
                installZip(getString(32001)+currentKw,reinstall=True)
                if Addon.getSetting("kw") == "":
                    Addon.setSetting("kw",currentKw)
                    Addon.setSetting("cache",size)
                    Addon.setSetting("notes",notes)

def linkDate(url):
    global urlSize
    counter = 0
    while urlSize == "":
        counter += 1
        try:
            r = requests.head(url)
            urlSize = r.headers['Content-Length']
            if counter == 5: break
        except: pass
    return urlSize

def openUrl(url='',post_type='get',payload={},timeout=None,headers={'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'}):
    import requests
    try:
        if post_type == 'post': r = requests.post(url, payload, headers=headers, timeout=timeout)
        else: r = requests.get(url, payload, headers=headers, timeout=timeout)
    except:
        xbmc.log('### CODE: %s   |   REASON: %s' % (r.status_code, r.reason),2)
        return False
    if r.status_code >= 200 and r.status_code < 400: return r.text.encode('utf-8')
    return False

def pastebin(url):
    raw = openUrl(url)
    if raw:
        ret = common.parseDOM(raw, "ol")
        return cleanHTML(ret[0])
    return False

def timestamp():
    now = time.time()
    localtime = time.localtime(now)
    return time.strftime('%Y%m%d%H%M%S', localtime)

def viewNotes(notes):
    windowActive = False
    counter = 0
    xbmc.executebuiltin("ActivateWindow(10147)")
    controller = xbmcgui.Window(10147)
    while not windowActive and counter < 20:
        xbmc.sleep(100)
        windowActive = xbmc.getCondVisibility('Window.IsActive(10147)')
        counter += 1
    controller.getControl(1).setLabel(getString(32023))
    controller.getControl(5).setText(notes)
    while windowActive:
        windowActive = xbmc.getCondVisibility('Window.IsActive(10147)')
        xbmc.sleep(250)

def wipeSettings():
    Addon.setSetting("cache","")
    Addon.setSetting("kw","")
    Addon.setSetting("notes","")

""" MAIN """
if __name__ == '__main__':
    xbmc.log("SYS: %s"%repr(sys.argv),2)
    currentKw = Addon.getSetting("kw")
    dl = xbmc.translatePath(os.path.join(profile,getString(32003)))
    if not os.path.exists(dl): xbmcvfs.mkdir(profile)
    
    if len(sys.argv)>0 and sys.argv[len(sys.argv)-1] == 'update':
        if not xbmc.Player().isPlaying():
            keyword = currentKw
            installZip(getString(32001)+currentKw,True)

    elif len(sys.argv)>0 and sys.argv[len(sys.argv)-1] == 'tv':
        choice = dialog.select('TV SHOWS',tvlist)
        if choice != -1:
            try: xbmc.executebuiltin(tvdict[tvlist[choice]])
            except Exception as e: xbmc.log(e,2)

    elif len(sys.argv)>0 and sys.argv[len(sys.argv)-1] == 'movie':
        choice = dialog.select('MOVIES',movielist)
        if choice != -1:
            try: xbmc.executebuiltin(moviedict[movielist[choice]])
            except Exception as e: xbmc.log(e,2)
    else:
        xbmc.executebuiltin("ActivateWindow(HOME)")
        choices = [getString(32017)%Addon.getSetting("kw"),getString(32018),getString(32019)]
        if currentKw == "":
            choices.pop(0)
            wipeSettings()
        choice = dialog.select(getString(32009),choices)
        if choice != -1:
            if choices[choice] == getString(32018):
                keyword = dialog.input(getString(32002), type=xbmcgui.INPUT_ALPHANUM)
                pbUrl = getString(32001)+keyword
                if keyword == currentKw: wipeSettings()
                if keyword: installZip(pbUrl)
            elif choices[choice] == getString(32019): createKw()
            else:
                keyword = currentKw
                kwOptions()
        xbmc.executebuiltin("ActivateWindow(HOME)")