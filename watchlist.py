#! /usr/bin/env python3

import json, time, glob, os, re, requests, sys
from pprint import pprint
import config

list_id = config.list_id
trakt_user = config.trakt_user
local_path = config.local_path
trakt_clientid = config.trakt_clientid
trakt_secret = config.trakt_secret
apiurl = 'https://api.trakt.tv'
cwd = os.path.abspath(os.path.dirname(__file__))
cache = os.path.join(cwd, '.local.db')

localdb = {}
if os.path.exists(cache):
        with open(cache, 'r') as fp:
                localdb = json.load(fp)

def db_set(k, v):
    localdb[k] = v
    with open(cache, 'w') as fpo:
        json.dump(localdb, fpo, indent=2, sort_keys=True)


def get_oauth_headers():
        access_token = localdb.get('access_token')
        access_token_expires = float(localdb.get('access_token_expires', 0))
        refresh_token = localdb.get('refresh_token')

        print("localdb: ",localdb)
        print("access_token: ",access_token)
        print("refresh_token: ",refresh_token)
        print("access_token_expires: ",access_token_expires)
        print("time.time: ",time.time())

        headers = {
                'Content-type': 'application/json',
                'trakt-api-key': trakt_clientid,
                'trakt-api-version': '2',
        }

        if access_token_expires > time.time() and access_token:
                headers['Authorization'] = 'Bearer %s' % access_token
        else:
                # REFRESH EXISTING TOKEN
                if refresh_token:
                        r = requests.post(
                                        '{0}/oauth/token'.format(apiurl),
                                        headers=headers,
                                        json={
                                                'refresh_token': refresh_token,
                                                'client_id': trakt_clientid,
                                                'client_secret': trakt_secret,
                                                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                                                'grant_type': 'refresh_token',
                                        }
                                )
                        res = r.json()
                        db_set('access_token', r['access_token'])
                        db_set('refresh_token', r['refresh_token'])
                        db_set('access_token_expires', time.time() + r['expires_in'] - (14 * 24 * 3600))
                        print("New access token acquired!")
                else:
                        print("No refresh token, manual action needed...")
                        r = requests.post(
                                        '{0}/oauth/device/code'.format(apiurl),
                                        json={
                                                'client_id': trakt_clientid,
                                        }
                                )

                        data = r.json()
                        start_time = time.time()

                        print('Go to {verification_url} and enter code {user_code}'.format(
                                verification_url = data['verification_url'],
                                user_code = data['user_code'],
                                )
                        )

                        interval = data['interval']

                        while 1:
                                if start_time + data['expires_in'] < time.time():
                                        print('Too late, you need to start from beginning :(')
                                        sys.exit(1)

                                time.sleep(interval)
                                req = requests.post(
                                        '{0}/oauth/device/token'.format(apiurl),
                                        json={
                                                'client_id': trakt_clientid,
                                                'client_secret': trakt_secret,
                                                'code': data['device_code'],
                                        }
                                )

                                if req.status_code == 200:
                                        res = req.json()
                                        print('New tokens acquired!')
                                        db_set('access_token', res['access_token'])
                                        db_set('refresh_token', res['refresh_token'])
                                        db_set('access_token_expires', time.time() + res['expires_in'] - (14 * 24 * 3600))
                                        break
                                elif req.status_code == 400:
                                        print('Pending - waiting for the user to authorize your app')
                                elif req.status_code == 404:
                                        print('Not Found - invalid device_code')
                                        return
                                elif req.status_code == 409:
                                        print('Already Used - user already approved this code')
                                        return
                                elif req.status_code == 410:
                                        print('Expired - the tokens have expired, restart the process')
                                        return
                                elif req.status_code == 418:
                                        print('Denied - user explicitly denied this code')
                                        return
                                elif req.status_code == 429:
                                        print('Slow Down - your app is polling too quickly')
                                        time.sleep(interval)
                        headers['Authorization'] = 'Bearer %s' % res['access_token']

        return headers

def get_oauth_request(path, *args, **kwargs):
    headers = get_oauth_headers()
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))
    req = requests.get(
        '{0}/{1}'.format(apiurl, path), headers=headers, **kwargs
    )
    assert req.ok, (req, req.content)
    return req.json()


def post_oauth_request(path, data, *args, **kwargs):
    req = requests.post(
        '{0}/{1}'.format(apiurl, path),
        json=data, headers=get_oauth_headers(), **kwargs
    )
    assert req.ok, (req, req.content)
    return req

def put_oauth_request(path, data, *args, **kwargs):
    req = requests.put(
        '{0}/{1}'.format(apiurl, path),
        json=data, headers=get_oauth_headers(), **kwargs
    )
    assert req.ok, (req, req.content)
    return req

def get_list_id(name):
    key = 'list-id:{0}'.format(name)
    if key in localdb:
        return localdb[key]
    req = get_oauth_request('users/me/lists')
    existing_lists = [x['name'] for x in req]
    if name not in existing_lists:
        post_oauth_request('users/me/lists', data={
            'name': name,
        })
        time.sleep(0.5)
        req = get_oauth_request('users/me/lists')
    res = [x for x in req if x['name'] == name]
    if not res:
        raise Exception('Could not find the list "{0}" :('.format(name))
    list_id = res[0]['ids']['trakt']
    db_set(key, list_id)
    return list_id


def get_trakt_ids(list_id):
        list_url = 'users/{0}/lists/{1}/items'.format(trakt_user,list_id)

        req = get_oauth_request(list_url)
        trakt_movies = []
        local_movies = get_local_movies()

        for movie in req:
                mtitle = movie["movie"]["title"]
                myear = str(movie["movie"]["year"])
                if mtitle in local_movies and myear == local_movies[mtitle]:
                        print("Matched movie {0} ({1}) in list '{2}' with local file".format(
                                        mtitle, myear, list_id)
                        )
                        imdb = movie["movie"]["ids"]["imdb"]
                        trakt_movies.append(imdb)
        return trakt_movies

def get_local_movies():
        ext = [".mkv", ".mp4", ".avi"]

        local_files = [os.path.split(os.path.dirname(e))[-1] for e in glob.glob(local_path + '/**)/*')
                                        if e.endswith(tuple(ext))]

        local_movies = {}

        for lm in local_files:
                #print("lm: ",lm)
                m = re.search('^([A-Za-z0-9,!é½· \.\'&:\-()]+)(?=\([0-9]+\))', lm)
                y = re.search('\(([0-9]+?)\)', lm)
                if m:
                        movie = m.group(0).rstrip()
                if y:
                        year = y.group(1)
                if m and y:
                        local_movies[movie] = year

        return local_movies

def main():
        trakt_list = get_trakt_ids(list_id)
        post_data = [] # should contain ids for movies to be removed

        for film in trakt_list:
                post_data.append({'ids': {'imdb': '{0}'.format(film)}})

        #print("post_data: ",post_data)

        list_rm_url = 'users/{0}/lists/{1}/items/remove'.format(trakt_user,list_id)

        print("Checking for movies to add to collection...")
        pprint(post_oauth_request('sync/collection', data={'movies': post_data}).json())
        print("Checking for movies to remove from list...")
        pprint(post_oauth_request(list_rm_url, data={'movies': post_data}).json())

if __name__ == '__main__':
        main()
