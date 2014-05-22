#!/usr/bin/python2

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import httplib2
import os
import sys
import isodate

from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Developers Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "google-auth.json"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

# This OAuth 2.0 access scope allows for read-only access to the authenticated
# user's account, but not other types of account access.
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
    message=MISSING_CLIENT_SECRETS_MESSAGE,
    scope=YOUTUBE_READ_WRITE_SCOPE)

storage = Storage("%s-oauth2.json" % sys.argv[0])
credentials = storage.get()

if credentials is None or credentials.invalid:
    flags = argparser.parse_args()
    credentials = run_flow(flow, storage, flags)

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))

videos = []

channels_response = youtube.channels().list(
    mine = True,
    part = "contentDetails"
).execute()

for channel in channels_response["items"]:
    watchlater_list_id = channel["contentDetails"]["relatedPlaylists"]["watchLater"]

    print "Parsing the WatchLater playlist ({0})...".format(watchlater_list_id)

    playlistitems_list_request = youtube.playlistItems().list(
        playlistId = watchlater_list_id,
        part = "snippet",
        maxResults = 50
    )

    while playlistitems_list_request:
        playlistitems_list_response = playlistitems_list_request.execute()

        for playlist_item in playlistitems_list_response["items"]:
            new_video = playlist_item["snippet"]
            
            videos_response = youtube.videos().list(
                id = new_video["resourceId"]["videoId"],
                part = "contentDetails"
            ).execute()

            new_video['duration'] = isodate.parse_duration(videos_response['items'][0]['contentDetails']['duration'])
        
            for video in videos:
                if video['duration'] > new_video['duration']:
                    videos.insert(videos.index(video), new_video)
                
                    snippet = {
                        'position': videos.index(new_video),
                        'resourceId': new_video['resourceId'],
                        'playlistId': watchlater_list_id
                    }

                    playlistitems_list_request = youtube.playlistItems().update(
                        part = "snippet",
                        body = { 
                            'id': playlist_item['id'],
                            'snippet': snippet
                        }
                    ).execute()

                    break
            else:
                videos.append(new_video)

        playlistitems_list_request = youtube.playlistItems().list_next(
            playlistitems_list_request, playlistitems_list_response)

    for video in videos:
        print "{0} - {1}".format(video['duration'], video['title'])
