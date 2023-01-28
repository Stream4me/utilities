# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# XBMC Library Tools
# ------------------------------------------------------------

import sys

PY3 = False
if sys.version_info[0] >= 3: PY3 = True; unicode = str; unichr = chr; long = int

import os
import xbmc, json
from dependencies import filetools, config, logger, platformtools, scrapertools
from xml.dom import minidom


def search_library_path():
    sql = 'SELECT strPath FROM path WHERE strPath LIKE "special://%/plugin.video.kod/library/" AND idParentPath ISNULL'
    nun_records, records = execute_sql_kodi(sql)
    if nun_records >= 1:
        logger.debug(records[0][0])
        return records[0][0]
    return None



def set_content(content_type, silent=False, custom=False):
    """
    Procedure to auto-configure the kodi video library with the default values
    @type content_type: str ('movie' o 'tvshow')
    @param content_type: content type to configure, series or movies
    """
    logger.debug()
    continuar = True
    msg_text = ""
    videolibrarypath = config.get_setting("videolibrarypath")

    scraper = []
    values = []
    # from core.support import dbg;dbg()
    rpc = '{ "jsonrpc": "2.0", "method": "Addons.GetAddons","params":{"type":"xbmc.metadata.scraper.' + content_type + 's", "properties":["name"]}, "id": "1"}'
    response = json.loads(xbmc.executeJSONRPC(rpc))['result']['addons']
    for r in response:
        scraper.append(r['name'])
        values.append(r['addonid'])
    if not custom:
        if content_type == 'movie':
            if PY3:        
                seleccion = values.index('metadata.themoviedb.org.python')
            else:
                seleccion = values.index('metadata.themoviedb.org')
        else:
            if PY3:
                seleccion = values.index('metadata.tvshows.themoviedb.org.python')
            else:
                seleccion = values.index('metadata.tvshows.themoviedb.org')

    # Configure scraper
    if seleccion != -1:
        xbmc.executebuiltin('Addon.OpenSettings({})'.format(values[seleccion]), True)
    else:
        continuar = False



    idPath = 0
    idParentPath = 0
    if continuar:
        continuar = False

        # We look for the idPath
        sql = 'SELECT MAX(idPath) FROM path'
        nun_records, records = execute_sql_kodi(sql)
        if nun_records == 1:
            idPath = records[0][0] + 1

        sql_videolibrarypath = videolibrarypath
        if sql_videolibrarypath.startswith("special://"):
            sql_videolibrarypath = sql_videolibrarypath.replace('/profile/', '/%/').replace('/home/userdata/', '/%/')
            sep = '/'
        elif scrapertools.find_single_match(sql_videolibrarypath, r'(^\w+:\/\/)'):
            sep = '/'
        else:
            sep = os.sep

        if not sql_videolibrarypath.endswith(sep):
            sql_videolibrarypath += sep

        # We are looking for the idParentPath
        sql = 'SELECT idPath, strPath FROM path where strPath LIKE "%s"' % sql_videolibrarypath
        nun_records, records = execute_sql_kodi(sql)
        if nun_records == 1:
            idParentPath = records[0][0]
            videolibrarypath = records[0][1][:-1]
            continuar = True
        else:
            # There is no videolibrarypath in the DB: we insert it
            sql_videolibrarypath = videolibrarypath
            if not sql_videolibrarypath.endswith(sep):
                sql_videolibrarypath += sep

            sql = 'INSERT INTO path (idPath, strPath,  scanRecursive, useFolderNames, noUpdate, exclude) VALUES ' \
                  '(%s, "%s", 0, 0, 0, 0)' % (idPath, sql_videolibrarypath)
            nun_records, records = execute_sql_kodi(sql)
            if nun_records == 1:
                continuar = True
                idParentPath = idPath
                idPath += 1
            else:
                msg_text = config.get_localized_string(70101)

    if continuar:
        continuar = False

        # We set strContent, strScraper, scanRecursive and strSettings
        if content_type == 'movie':
            strContent = 'movies'
            scanRecursive = 2147483647
            strScraper = values[seleccion]
            path_settings = xbmc.translatePath("special://profile/addon_data/{}/settings.xml".format(strScraper))
            if not os.path.exists(path_settings):
                logger.debug("%s: %s" % (content_type, path_settings + " doesn't exist"))
                return continuar
            settings_data = filetools.read(path_settings)
            strSettings = ' '.join(settings_data.split()).replace("> <", "><")
            strSettings = strSettings.replace("\"","\'")
            strActualizar = "Do you want to set this Scraper in Spanish as the default option for movies?"
            if not videolibrarypath.endswith(sep):
                videolibrarypath += sep
            strPath = videolibrarypath + config.get_setting("folder_movies") + sep
        else:
            strContent = 'tvshows'
            scanRecursive = 0
            strScraper = values[seleccion]
            path_settings = xbmc.translatePath("special://profile/addon_data/{}/settings.xml".format(strScraper))
            if not os.path.exists(path_settings):
                logger.debug("%s: %s" % (content_type, path_settings + " doesn't exist"))
                return continuar
            settings_data = filetools.read(path_settings)
            strSettings = ' '.join(settings_data.split()).replace("> <", "><")
            strSettings = strSettings.replace("\"","\'")
            strActualizar = "Do you want to configure this Scraper in Spanish as a default option for series?"
            if not videolibrarypath.endswith(sep):
                videolibrarypath += sep
            strPath = videolibrarypath + config.get_setting("folder_tvshows") + sep

        logger.debug("%s: %s" % (content_type, strPath))
        # We check if strPath already exists in the DB to avoid duplicates
        sql = 'SELECT idPath FROM path where strPath="%s"' % strPath
        nun_records, records = execute_sql_kodi(sql)
        sql = ""
        if nun_records == 0:
            # Insertamos el scraper
            sql = 'INSERT INTO path (idPath, strPath, strContent, strScraper, scanRecursive, useFolderNames, ' \
                  'strSettings, noUpdate, exclude, idParentPath) VALUES (%s, "%s", "%s", "%s", %s, 0, ' \
                  '"%s", 0, 0, %s)' % (
                      idPath, strPath, strContent, strScraper, scanRecursive, strSettings, idParentPath)
        else:
            if not silent:
                # Preguntar si queremos configurar themoviedb.org como opcion por defecto
                actualizar = platformtools.dialog_yesno(config.get_localized_string(70098), strActualizar)
            else:
                actualizar = True

            if actualizar:
                # Actualizamos el scraper
                idPath = records[0][0]
                sql = 'UPDATE path SET strContent="%s", strScraper="%s", scanRecursive=%s, strSettings="%s" ' \
                      'WHERE idPath=%s' % (strContent, strScraper, scanRecursive, strSettings, idPath)

        if sql:
            nun_records, records = execute_sql_kodi(sql)
            if nun_records == 1:
                continuar = True

        if not continuar:
            msg_text = config.get_localized_string(60055)

    if not continuar:
        heading = config.get_localized_string(70102) % content_type
    elif content_type == 'tvshow' and not xbmc.getCondVisibility(
            'System.HasAddon(metadata.tvshows.themoviedb.org)'):
        heading = config.get_localized_string(70103) % content_type
        msg_text = config.get_localized_string(60058)
    else:
        heading = config.get_localized_string(70103) % content_type
        msg_text = config.get_localized_string(70104)

    logger.debug("%s: %s" % (heading, msg_text))
    return continuar


def execute_sql_kodi(sql):
    """
    Run sql query against kodi database
    @param sql: Valid sql query
    @type sql: str
    @return: Number of records modified or returned by the query
    @rtype nun_records: int
    @return: list with the query result
    @rtype records: list of tuples
    """
    logger.info()
    file_db = ""
    nun_records = 0
    records = None

    # We look for the archive of the video database according to the version of kodi
    video_db = config.get_platform(True)['video_db']
    if video_db:
        file_db = filetools.join(xbmc.translatePath("special://userdata/Database"), video_db)

    # alternative method to locate the database
    if not file_db or not filetools.exists(file_db):
        file_db = ""
        for f in filetools.listdir(xbmc.translatePath("special://userdata/Database")):
            path_f = filetools.join(xbmc.translatePath("special://userdata/Database"), f)

            if filetools.isfile(path_f) and f.lower().startswith('myvideos') and f.lower().endswith('.db'):
                file_db = path_f
                break

    if file_db:
        logger.info("DB file: %s" % file_db)
        conn = None
        try:
            import sqlite3
            conn = sqlite3.connect(file_db)
            cursor = conn.cursor()

            logger.info("Running sql: %s" % sql)
            cursor.execute(sql)
            conn.commit()

            records = cursor.fetchall()
            if sql.lower().startswith("select"):
                nun_records = len(records)
                if nun_records == 1 and records[0][0] is None:
                    nun_records = 0
                    records = []
            else:
                nun_records = conn.total_changes

            conn.close()
            logger.info("Query executed. Records: %s" % nun_records)

        except:
            logger.error("Error executing sql query")
            if conn:
                conn.close()

    else:
        logger.info("Database not found")

    return nun_records, records


def check_sources(new_movies_path='', new_tvshows_path=''):
    def format_path(path):
        if path.startswith("special://") or '://' in path: sep = '/'
        else: sep = os.sep
        if not path.endswith(sep): path += sep
        return path

    logger.info()

    new_movies_path = format_path(new_movies_path)
    new_tvshows_path = format_path(new_tvshows_path)

    SOURCES_PATH = xbmc.translatePath("special://userdata/sources.xml")
    if filetools.isfile(SOURCES_PATH):
        xmldoc = minidom.parse(SOURCES_PATH)

        video_node = xmldoc.childNodes[0].getElementsByTagName("video")[0]
        paths_node = video_node.getElementsByTagName("path")
        list_path = [p.firstChild.data for p in paths_node]

        return new_movies_path in list_path, new_tvshows_path in list_path
    else:
        xmldoc = minidom.Document()
        source_nodes = xmldoc.createElement("sources")

        for type in ['programs', 'video', 'music', 'picture', 'files']:
            nodo_type = xmldoc.createElement(type)
            element_default = xmldoc.createElement("default")
            element_default.setAttribute("pathversion", "1")
            nodo_type.appendChild(element_default)
            source_nodes.appendChild(nodo_type)
        xmldoc.appendChild(source_nodes)

        return False, False


def update_sources(new='', old=''):
    logger.info()
    if new == old: return

    SOURCES_PATH = xbmc.translatePath("special://userdata/sources.xml")
    if filetools.isfile(SOURCES_PATH):
        xmldoc = minidom.parse(SOURCES_PATH)
    else:
        xmldoc = minidom.Document()
        source_nodes = xmldoc.createElement("sources")

        for type in ['programs', 'video', 'music', 'picture', 'files']:
            nodo_type = xmldoc.createElement(type)
            element_default = xmldoc.createElement("default")
            element_default.setAttribute("pathversion", "1")
            nodo_type.appendChild(element_default)
            source_nodes.appendChild(nodo_type)
        xmldoc.appendChild(source_nodes)

    # collect nodes
    # nodes = xmldoc.getElementsByTagName("video")
    video_node = xmldoc.childNodes[0].getElementsByTagName("video")[0]
    paths_node = video_node.getElementsByTagName("path")

    if old:
        # delete old path
        for node in paths_node:
            if node.firstChild.data == old:
                parent = node.parentNode
                remove = parent.parentNode
                remove.removeChild(parent)

        # write changes
        if sys.version_info[0] >= 3: #PY3
            filetools.write(SOURCES_PATH, '\n'.join([x for x in xmldoc.toprettyxml().splitlines() if x.strip()]))
        else:
            filetools.write(SOURCES_PATH, '\n'.join([x for x in xmldoc.toprettyxml().splitlines() if x.strip()]), vfs=False)
        logger.info("The path %s has been removed from sources.xml" % old)

    if new:
        # create new path
        list_path = [p.firstChild.data for p in paths_node]
        if new in list_path:
            logger.info("The path %s already exists in sources.xml" % new)
            return
        logger.info("The path %s does not exist in sources.xml" % new)

        # if the path does not exist we create one
        source_node = xmldoc.createElement("source")

        # <name> Node
        name_node = xmldoc.createElement("name")
        sep = os.sep
        if new.startswith("special://") or scrapertools.find_single_match(new, r'(^\w+:\/\/)'):
            sep = "/"
        name = new
        if new.endswith(sep):
            name = new[:-1]
        name_node.appendChild(xmldoc.createTextNode(name.rsplit(sep)[-1]))
        source_node.appendChild(name_node)

        # <path> Node
        path_node = xmldoc.createElement("path")
        path_node.setAttribute("pathversion", "1")
        path_node.appendChild(xmldoc.createTextNode(new))
        source_node.appendChild(path_node)

        # <allowsharing> Node
        allowsharing_node = xmldoc.createElement("allowsharing")
        allowsharing_node.appendChild(xmldoc.createTextNode('true'))
        source_node.appendChild(allowsharing_node)

        # Añadimos <source>  a <video>
        video_node.appendChild(source_node)

        # write changes
        if sys.version_info[0] >= 3: #PY3
            filetools.write(SOURCES_PATH, '\n'.join([x for x in xmldoc.toprettyxml().splitlines() if x.strip()]))
        else:
            filetools.write(SOURCES_PATH, '\n'.join([x for x in xmldoc.toprettyxml().splitlines() if x.strip()]), vfs=False)
        logger.info("The path %s has been added to sources.xml" % new)


def update(folder_content=config.get_setting("folder_tvshows"), folder=""):
    """
    Actualiza la libreria dependiendo del tipo de contenido y la ruta que se le pase.

    @type folder_content: str
    @param folder_content: tipo de contenido para actualizar, series o peliculas
    @type folder: str
    @param folder: nombre de la carpeta a escanear.
    """
    logger.info(folder)

    payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.Scan",
        "id": 1
    }

    if folder:
        folder = str(folder)
        videolibrarypath = config.get_videolibrary_config_path()

        if folder.endswith('/') or folder.endswith('\\'):
            folder = folder[:-1]

        update_path = None

        if videolibrarypath.startswith("special:"):
            if videolibrarypath.endswith('/'):
                videolibrarypath = videolibrarypath[:-1]
            update_path = videolibrarypath + "/" + folder_content + "/" + folder + "/"
        else:
            #update_path = filetools.join(videolibrarypath, folder_content, folder) + "/"   # Problemas de encode en "folder"
            update_path = filetools.join(videolibrarypath, folder_content, ' ').rstrip()

        if not scrapertools.find_single_match(update_path, '(^\w+:\/\/)'):
            payload["params"] = {"directory": update_path}

    """while xbmc.getCondVisibility('Library.IsScanningVideo()'):
        xbmc.sleep(500)

    data = get_data(payload)

    xbmc.executebuiltin('XBMC.ReloadSkin()')"""


def ask_set_content(silent=False):
    logger.debug()
    logger.debug("videolibrary_kodi %s" % config.get_setting("videolibrary_kodi"))
    def do_config(custom=False):
        if set_content("movie", True, custom) and set_content("tvshow", True, custom):
            platformtools.dialog_ok(config.get_localized_string(80026), config.get_localized_string(70104))
            config.set_setting("videolibrary_kodi", True)
            update()
        else:
            platformtools.dialog_ok(config.get_localized_string(80026), config.get_localized_string(80024))
            config.set_setting("videolibrary_kodi", False)

    # configuration during installation
    if not silent:
        # ask to configure Kodi video library
        if platformtools.dialog_yesno(config.get_localized_string(20000), config.get_localized_string(80015)):
            # ask for custom or default settings
            if not platformtools.dialog_yesno(config.get_localized_string(80026), config.get_localized_string(80016), config.get_localized_string(80017), config.get_localized_string(80018)):
                # input path and folders
                path = platformtools.dialog_browse(3, config.get_localized_string(80019), config.get_setting("videolibrarypath"))
                movies_folder = platformtools.dialog_input(config.get_setting("folder_movies"), config.get_localized_string(80020))
                tvshows_folder = platformtools.dialog_input(config.get_setting("folder_tvshows"), config.get_localized_string(80021))

                if path != "" and movies_folder != "" and tvshows_folder != "":
                    movies_path, tvshows_path = check_sources(filetools.join(path, movies_folder), filetools.join(path, tvshows_folder))
                    # configure later
                    if movies_path or tvshows_path:
                        platformtools.dialog_ok(config.get_localized_string(80026), config.get_localized_string(80029))
                    # set path and folders
                    else:
                        update_sources(path, config.get_setting("videolibrarypath"))
                        config.set_setting("videolibrarypath", path)
                        config.set_setting("folder_movies", movies_folder)
                        config.set_setting("folder_tvshows", tvshows_folder)
                        config.verify_directories_created()
                        do_config(False)
                # default path and folders
                else:
                    platformtools.dialog_ok(config.get_localized_string(80026), config.get_localized_string(80030))
                    do_config(False)
            # default settings
            else:
                platformtools.dialog_ok(config.get_localized_string(80026), config.get_localized_string(80027))
                do_config(False)
        # configure later
        else:
            platformtools.dialog_ok(config.get_localized_string(20000), config.get_localized_string(80022))
    # configuration from the settings menu
    else:
        platformtools.dialog_ok(config.get_localized_string(80026), config.get_localized_string(80023))
        do_config(True)
