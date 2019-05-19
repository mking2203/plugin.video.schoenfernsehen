#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime

import urllib
import urlparse
import re
import requests

import buggalo
import json

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs

import inputstreamhelper
from random import randint

PROTOCOL = 'mpd'
DRM = 'com.widevine.alpha'

def play(tv):

    is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
    if is_helper.check_inputstream():

        url = 'https://www.schoener-fernsehen.com/ajax/get_live.php'
        resp = requests.post(url)

        if (resp.status_code == 200):
            obj = json.loads(resp.text)

            root = obj['channelname']

            for item in root:
                channel = root[item]['station']

                if channel == tv:
                    mpd = root[item]['mdp']
                    sec = root[item]['sec']

                    title = root[item]['title']
                    member = root[item]['membership_status']
                    desc = root[item]['description']
                    start = root[item]['starttime']
                    stop = root[item]['nextstarttime']
                    lower = root[item]['lowerstation']

                    ref = 'https://h5p2p.peer-stream.com/s0/index-video.html?mpd=//'
                    ref = ref + mpd
                    ref = ref + '&sec=' + sec

                    url = 'https://' + mpd + '?cp=' + str(randint(20000,50000))
                    url = url + '|Origin=' + urllib.quote_plus('https://h5p2p.peer-stream.com')
                    url = url + '&Referer=' + urllib.quote_plus(ref)

                    if member == 'free':
                        thumb = 'https://static.onlinetvrecorder.com/images/easy/stationlogos/white/' + lower.replace(' ','%20') + '.gif'
                    else:
                        thumb = 'https://static.onlinetvrecorder.com/images/easy/stationlogos/black/' + lower.replace(' ','%20') + '.gif'

                    playitem = xbmcgui.ListItem(path=url, thumbnailImage=thumb)
                    txt =  urllib.unquote(title) + ' ' + start + '-' + stop + '\n' + urllib.unquote(desc)
                    playitem.setInfo('video', { 'plot': txt })
                    playitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
                    playitem.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
                    playitem.setProperty('inputstream.adaptive.manifest_update_parameter', 'full')
                    xbmc.Player().play(item=url, listitem=playitem)

def showChannels(userState, chanList):

    is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
    if is_helper.check_inputstream():

        url = 'https://www.schoener-fernsehen.com/ajax/get_live.php'
        resp = requests.post(url)

        if (resp.status_code == 200):
            obj = json.loads(resp.text)

            root = obj['channelname']

            if not USE_ALL:

                f= file(chanList,'r')
                lines = f.readlines()
                f.close()

                for line in lines:
                    for item in root:
                        member = root[item]['membership_status']
                        channel = root[item]['station']

                        if (member == 'free') | (userState == 'plus'):
                            if line.replace('\n','') == channel:
                                 addItem(root[item])
            else:
                for item in root:
                    member = root[item]['membership_status']
                    if (member == 'free') | (userState == 'plus'):
                        addItem(root[item])


        if USE_ALL:
            xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)

        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def addItem(item1):

    member = item1['membership_status']
    title = item1['title']
    nxt = item1['nexttitle']
    channel = item1['station']

    lower = item1['lowerstation']
    desc = item1['description']

    start = item1['starttime']
    stop = item1['nextstarttime']
    perc = item1['passed_relative']

    strInfo = start + ' - ' + stop + ' (' + str(perc) + "%)"
    if(nxt != ''):
        strInfo = strInfo + "\nDanach: " + nxt

    desc = urllib.unquote(desc)

    if(len(desc) > 150):
        desc = desc[:147] + '...'

    desc = desc + '\n' + strInfo
    url = '{0}?tv={1}'.format(PATH, channel)

    if member == 'free':
        thumb = 'https://static.onlinetvrecorder.com/images/easy/stationlogos/white/' + lower.replace(' ','%20') + '.gif'
    else:
        thumb = 'https://static.onlinetvrecorder.com/images/easy/stationlogos/black/' + lower.replace(' ','%20') + '.gif'

    list_item = xbmcgui.ListItem(label=channel + ': ' + title, thumbnailImage=thumb)
    list_item.setInfo('video', { 'plot': desc })
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, False)

def getUserState():

    userState = 'free'

    # user data
    login = xbmcplugin.getSetting(HANDLE, 'email')
    pw = xbmcplugin.getSetting(HANDLE, 'pass')

    if(len(login) != 0):

        loginURL = 'https://www.schoener-fernsehen.com/ajax/login.php'

        params = dict()
        params["email"] = login
        params["password"] = pw

        r = requests.post(loginURL, data=params)
        result = r.text

        obj = json.loads(result)
        state = obj['success']
        if(state):
            userState = obj['membership']
            xbmc.log('SF: userstate ' + userState)
        else:
            userState = 'error'
            xbmc.log('SF: login failed')

    return userState

def saveFile(filePath, userState):

    try:
        f = file(filePath,'w')
        f.write(userState)
        f.close()
    except Exception as e:
        pass

def deleteFile(filePath):

    try:
        if os.path.isfile(filePath):
            os.unlink(filePath)
    except Exception as e:
        pass

def checkFile(filePath, userState):

    date = datetime.datetime.now() - datetime.timedelta(hours = 24)
    ts = time.mktime(date.timetuple())

    # invalid login
    if(userState == 'error'):
        if(os.path.exists(filePath)):
            deleteFile(filePath)

    if(os.path.exists(filePath)):
        fileDate = os.path.getmtime(filePath)
        if(ts>fileDate):
            deleteFile(filePath)
            return False
        else:
            f= file(filePath,'r')
            txt = f.read()
            f.close()

            if(txt == userState):
                return True
            else:
                deleteFile(filePath)
                return False

    return False

def createDefault(chanList):

    if(True):

        try:
            f = file(chanList,'w')
            f.write('ARD\n')
            f.write('ZDF\n')
            f.write('NDR\n')
            f.write('VOX\n')
            f.write('SAT 1\n')
            f.write('KABEL 1\n')
            f.write('PRO SIEBEN\n')
            f.write('RTL2\n')
            f.write('KABEL1DOKU\n')
            f.write('DMAX\n')
            f.write('TLC\n')
            f.write('N24\n')
            f.write('EUROSPORT\n')
            f.write('SPORT1\n')
            f.close()

        except Exception as e:
            pass

if __name__ == '__main__':

    ADDON = xbmcaddon.Addon()
    ADDON_NAME = ADDON.getAddonInfo('name')
    PATH = sys.argv[0]
    HANDLE = int(sys.argv[1])
    PARAMS = urlparse.parse_qs(sys.argv[2][1:])

    profilePath = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode("utf-8")
    if not xbmcvfs.exists(profilePath): xbmcvfs.mkdirs(profilePath)
    filePath = os.path.join(profilePath, "user.txt")

    chanList = os.path.join(profilePath, "channel.txt")
    createDefault(chanList)

    USE_ALL = xbmcplugin.getSetting(HANDLE, 'view')  == "true"

    # check version adaptive
    info = xbmcaddon.Addon(id='inputstream.adaptive').getAddonInfo('version')
    if (info == '2.3.17'):
        xbmcgui.Dialog().notification(ADDON_NAME, 'Falsche Version inputstream.adaptive\nbenötigt wird Version 2.3.18', time=5000)

    if PARAMS.has_key('tv'):
        play(PARAMS['tv'][0])
    else:
        userState = getUserState()

        check = checkFile(filePath, userState)
        if(not check):
            if(userState == 'free'):
                # keine Daten ?
                xbmcgui.Dialog().notification(ADDON_NAME, 'Sie benutzen SF im FREE Modus.\nBitte melden Sie sich an.', time=5000)
            elif(userState == 'error'):
                # falsche Daten ?
                xbmcgui.Dialog().notification(ADDON_NAME, 'Der LOGIN war nicht erfolgreich.\nBitte überprüfen Sie die Daten.', time=5000)
            elif(userState == 'member'):
                # wir sind angemeldet
                xbmcgui.Dialog().notification(ADDON_NAME, 'Sie haben keinen PLUS Status\nAktivieren Sie bitte PLUS.', time=5000)
            elif(userState == 'plus'):
                # wir sind plus mitglied
                pass
            else:
                xbmcgui.Dialog().notification(ADDON_NAME, 'StateState= ' + userState, time=5000)
            saveFile(filePath, userState)

        showChannels(userState, chanList)




