# -*- coding: utf-8 -*-
import io

import xbmc, os, shutil
from dependencies import platformtools, logger, filetools
from dependencies import xbmc_videolibrary, config
from threading import Thread
import urllib

branch = 'stable'
user = 'kodiondemand'
repo = 'addon'
addonDir = os.path.dirname(os.path.abspath(__file__)) + '/'
maxPage = 5  # le api restituiscono 30 commit per volta, quindi se si è rimasti troppo indietro c'è bisogno di andare avanti con le pagine
trackingFile = "last_commit.txt"


def updateFromZip(message='Installazione in corso...'):
    dp = platformtools.dialog_progress_bg('Kodi on Demand', message)
    dp.update(0)

    remotefilename = 'https://github.com/' + user + "/" + repo + "/archive/" + branch + ".zip"
    localfilename = (xbmc.translatePath("special://home/addons/") + "plugin.video.kod.update.zip").encode('utf-8')
    destpathname = xbmc.translatePath("special://home/addons/")

    logger.info("remotefilename=%s" % remotefilename)
    logger.info("localfilename=%s" % localfilename)

    # pulizia preliminare
    remove(localfilename)
    removeTree(destpathname + "addon-" + branch)

    try:
        urllib.urlretrieve(remotefilename, localfilename,
                           lambda nb, bs, fs, url=remotefilename: _pbhook(nb, bs, fs, url, dp))
    except Exception as e:
        platformtools.dialog_ok('Kodi on Demand', 'Non riesco a scaricare il file d\'installazione da github, questo è probabilmente dovuto ad una mancanza di connessione (o qualcosa impedisce di raggiungere github).\n'
                                                  'Controlla bene e quando hai risolto riapri KoD.')
        logger.info('Non sono riuscito a scaricare il file zip')
        logger.info(e)
        dp.close()
        return False

    # Lo descomprime
    logger.info("decompressione...")
    logger.info("destpathname=%s" % destpathname)

    try:
        hash = fixZipGetHash(localfilename)
        import zipfile
        with zipfile.ZipFile(io.FileIO(localfilename), "r") as zip_ref:
            zip_ref.extractall(destpathname)
    except Exception as e:
        logger.info('Non sono riuscito ad estrarre il file zip')
        logger.info(e)
        dp.close()
        return False

    dp.update(95)

    # puliamo tutto
    removeTree(addonDir)
    xbmc.sleep(1000)

    rename(destpathname + "addon-" + branch, addonDir)

    logger.info("Cancellando il file zip...")
    remove(localfilename)

    dp.update(100)
    dp.close()
    xbmc.executebuiltin("UpdateLocalAddons")

    return hash


def remove(file):
    if os.path.isfile(file):
        try:
            os.remove(file)
        except:
            logger.info('File ' + file + ' NON eliminato')


def onerror(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise

def removeTree(dir):
    if os.path.isdir(dir):
        try:
            shutil.rmtree(dir, ignore_errors=False, onerror=onerror)
        except Exception as e:
            logger.info('Cartella ' + dir + ' NON eliminata')
            logger.error(e)


def rename(dir1, dir2):
    try:
        filetools.rename(dir1, dir2)
    except:
        logger.info('cartella ' + dir1 + ' NON rinominata')

def fixZipGetHash(zipFile):
    f = io.FileIO(zipFile, 'r+b')
    data = f.read()
    pos = data.find(b'\x50\x4b\x05\x06')  # End of central directory signature
    hash = ''
    if pos > 0:
        f.seek(pos + 20)  # +20: see secion V.I in 'ZIP format' link above.
        hash = f.read()[2:]
        f.seek(pos + 20)
        f.truncate()
        f.write(
            b'\x00\x00')  # Zip file comment length: 0 byte length; tell zip applications to stop reading.
        f.seek(0)

    f.close()

    return str(hash)


def _pbhook(numblocks, blocksize, filesize, url, dp):
    try:
        percent = min((numblocks*blocksize*90)/filesize, 100)
        dp.update(percent)
    except:
        percent = 90
        dp.update(percent)


def download():
    hash = updateFromZip()
    # se ha scaricato lo zip si trova di sicuro all'ultimo commit
    localCommitFile = open(addonDir + trackingFile, 'w')
    localCommitFile.write(hash)
    localCommitFile.close()


def run():
    t = Thread(target=download)
    t.start()

    xbmc_videolibrary.ask_set_content(1, config.get_setting('videolibrary_kodi_force'))
    config.set_setting('show_once', True)

    t.join()


if __name__ == "__main__":
    run()
