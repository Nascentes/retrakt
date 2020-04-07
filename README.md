# Description

The purpose of this project is to automatically update a Trakt Watchlist and Collection based on downloaded movies.
The primary actions that this script will take are:

1. Check local movies folder to compile list of downloaded movies
2. Check Trakt Watchlist (defined in config.py) to build list of movies on the list
3. Add downloaded movies to your Trakt collection
4. Remove downloaded movies from your Trakt watchlist

The script executes via a cron schedule

# Use case

My use case for this is that I use Radarr to import movies to be grabbed based on my Trakt watchlist. I use an option that will remove items from Radarr that no longer exist in my Trakt watchlist. I wanted to automate the curation of my list based on media downloaded. So, now I only need add movies to my Trakt list -> Radarr does its thing -> retrakt removes from my Trakt list -> Radarr removes from its library.

# Configuration

Edit config.py with your unique values.

Edit retrakt_cron to update the schedule, if desired.

Build docker container (`git clone https://github.com/Nascentes/retrakt.git && cd retrakt && docker build -t retrakt .`)

Run docker container, eg: ```docker run -dit --name=retrakt --env="PUID=1040" --env="PGID=100" --volume="/volume1/Movies:/movies:ro" --volume="/etc/localtime:/etc/localtime:ro" --restart=unless-stopped retrakt:latest && docker logs -f retrakt```

Notice the logs follow at the end? This is NECESSARY. The Trakt API (annoyingly) _requires_ manual intervention to get an initial access_token. The logs will tell you what to do, but it boils down to copying a unique key the API gives you and authorizing the device via the Trakt website. It's obnoxious, but you only need to do it once, or if your container crashes/restarts (has yet to happen to me). The script will automatically renew your token for you.

NOTE: I use this on my Synology NAS. PUID & PGID will be unique to the user you want your docker container to run as. (aka, someone with permissions to read your movies directory)

# Notes

Huge thank you to the work of @linaspurinis in his [trakt.plex.scripts](https://github.com/linaspurinis/trakt.plex.scripts) repository. His work was heavily borrowed from to make this a reality.

This is very much a work-in-progress as far as compatibility for others and I'm not actively working on it. It works for ME, but that doesn't mean a whole lot for others. If you happen to run across this project and give it a go, feel free to file issues as you encounter them and I'll be happy to help where I can.
