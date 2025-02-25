# -*- coding: utf-8 -*-
from dependencies import platformtools
import downloader_service, os, xbmc
# functions that on kodi 19 moved to xbmcvfs
try:
    import xbmcvfs
    xbmc.translatePath = xbmcvfs.translatePath
    xbmc.validatePath = xbmcvfs.validatePath
    xbmc.makeLegalFilename = xbmcvfs.makeLegalFilename
except:
    pass

if os.path.isfile(xbmc.translatePath("special://home/addons/") + "plugin.video.s4me.update.zip"):
    dial = None
    while os.path.isfile(xbmc.translatePath("special://home/addons/") + "plugin.video.s4me.update.zip"):
        if not dial:
            dial = platformtools.dialog_progress('Stream4Me', 'Attendi che il processo di installazione finisca.')
        xbmc.sleep(500)
        if dial.iscanceled():
            dial.close()
            exit(0)
    dial.close()
    xbmc.executebuiltin("RunAddon(plugin.video.s4me)")
else:
    downloader_service.run()
