# m3ugen

* ![Build Status](https://github.com/snw35/m3ugen/actions/workflows/update.yml/badge.svg)
* [Dockerhub: snw35/m3ugen](https://hub.docker.com/r/snw35/m3ugen)

Genre playlist generator for large music collections.

Generates one or more music playlist (.m3u) files according to a given configuration file. Provided as a script or container, it can be set to run on a schedule, and is designed to keep a set of playlists updated and maintained as new music is added to your collection.

## Why?

This is designed to maintain *genre* playlists, as well as ones containing individual albums or tracks. Say you have a large collection of music all in the same folder, with some fast-paced metal music and some relaxing ambient music, like this:

* All Music
    * Ambient Artist
        * Ambient Album
    * Metal Artist
        * Metal Album
        * Metal Album

You probably don't want a fast metal album or track to play straight after a relaxing ambient one. So you need two playlists - one for all the metal artists, and one for all the ambient. You can create two config sections in a config file (described below) and this playlist generator will do that.

Now, say you buy some more metal albums. You want the metal playlist to just update seamlessly with the new albums, right? Set this script to run on a schedule and it will do that the next time it runs.

## Configuration File

The config file contains one or more sections that each specify a playlist. Each section will create its own independent playlist file based on the values provided. You can use this to create several different playlists from the same large tree of music files, for example.

An example config file is included which shows two sections and explains the fields required.

Each section looks like:

```
[PLAYLISTNAME]
musicSource = "/full/path/to/music"
playListFolder = "/full/path/to/playlist/destination"
foldersToInclude = "Artist1"
    "Artist2"
    "Artist3"
    ...
```

Each value is:

 * musicSource = The top-level folder of your music collection. This is where the script begins when it looks for the folders you specify in 'foldersToInclude'.
 * playListFolder = Where you want the playlist files to be created. Each config section will create a separate playlist file here.
 * foldersToInclude = Subdirectories underneath 'musicSource' where the script should look for music. These can be artist folders, album folders, etc. They can also point directly to individual tracks.

## Recursive Search and Relative Pathing

The script will search recursively under the given folder names and include any files found with `.flac` or `.mp3` by default. You can specify custom extensions to search for using `-e`. It will then generate a relative path to each file based on the location of the playlist file itself, and write that into the file.

The playlist files will be completely replaced on each run to ensure they are correct and up to date.

## Standalone Use

To use standalone, run the script with a configuration file provided as the only argument:

`python ./m3ugen.py ./playlists.conf`

The script will create playlist files at the locations given in the config file, and a will log its actions to `m3ugen.log` in the same directory.

To see all available options, run:

`python ./m3ugen.py --help`

## Container Use

The container can be run standalone:

`docker run -d --volume -e CONFIG_FILE=/path/to/config snw35/m3ugen:latest`

Or via compose:

```
  m3ugen:
    container_name: m3ugen
    image: snw35/m3ugen:latest
    restart: always
    volumes:
      - /path/to/music:/data
    environment:
      - CONFIG_FILE=/data/playlists.conf
```

## Contributing

Unit tests are inside `test_m3ugen.py` and cover a range of situations, including badly named files, missing files, etc. They will likely need updated if any core functionality is changed, and should provide some warning if bugs are introduced.

This repo has git pre-commit hooks that can be set up by running:

```
pip install pre-commit
pip install -r requirements-dev.txt
pre-commit install
```

The configured linters and checkers will now run on every commit.

The script can be run with debug logging by adding `-l DEBUG` as an argument.
