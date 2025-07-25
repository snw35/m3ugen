#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates relative pathed m3u files according to
a given configuration file.
"""
import argparse
import configparser
import glob
import io
import logging
import os
import sys
import unicodedata


class PlaylistWriter:
    """
    Creates a play list writer class, with a configuraiton,
    a logger, and a chosen file extension to search for.
    """

    def __init__(self, config, logger, file_extensions):
        self.config = config
        self.logger = logger
        self.file_extensions = file_extensions

    def filter_folders(self, folders_raw):
        """
        Split provided folders/files by newline and sanitise.
        Strips quotes, whitespace, and leading slashes.
        """
        return [
            line.strip('"').lstrip("/\\")
            for line in folders_raw.splitlines()
            if line.strip()
        ]

    def add_file_to_playlist(self, playlist, file_path, dest):
        """
        Write the given file to the playlist file.
        """
        rel_path = os.path.relpath(file_path, dest)
        playlist.write(f"{rel_path}\n")
        self.logger.info(f"Added file to playlist: {rel_path}")

    def process_folder(self, playlist, source, folder, dest):
        """
        Process the given line from the folders section in the config.
        If a file, just write it directly to the playlist.
        If a folder, search it recursively for the given extension
        and write all files found to the playlist.
        """
        full_path = os.path.join(source, folder)
        full_path = norm_path(full_path)
        if os.path.isfile(full_path):
            self.add_file_to_playlist(playlist, full_path, dest)
            return
        if os.path.isdir(full_path):
            self.logger.info(f"Searching for files inside {full_path}")
            for ext in self.file_extensions:
                pattern = os.path.join(full_path, f"**/*{ext}")
                for fname in sorted(glob.glob(pattern, recursive=True)):
                    fname = norm_path(fname)
                    if os.path.isfile(fname):
                        self.add_file_to_playlist(playlist, fname, dest)
            return
        self.logger.warning(f"{full_path} is not a file or directory, skipping")

    def process_section(self, section):
        """
        Read the given config file section and parse all values.
        """
        sec = self.config[section]
        name = section.lower()
        source = sec.get("musicSource", "").strip('"')
        dest = sec.get("playListFolder", "").strip('"')
        folders = self.filter_folders(sec.get("foldersToInclude", ""))
        self.logger.debug(f"Reading section {section}")
        if not source or not dest or not folders:
            self.logger.warning(
                f"Section '{section}' missing required values. Skipping"
            )
            return
        playlist_path = os.path.join(dest, f"{name}.m3u")
        try:
            with io.open(playlist_path, "w", encoding="utf8") as playlist:
                self.logger.debug(f"Opened playlist file {playlist_path}")
                playlist.write("#EXTM3U\n")
                for folder in folders:
                    self.process_folder(playlist, source, folder, dest)
                self.logger.info("Finished writing playlist file")
        except FileNotFoundError as e:
            self.logger.error(
                f"Playlist destination folder not found: {dest}. Exception: {e}"
            )
        except PermissionError as e:
            self.logger.error(
                f"Permission denied writing playlist file at: \
                {playlist_path}. Exception: {e}"
            )
        except OSError as e:
            self.logger.error(
                f"OS error encountered writing playlist file at: \
                {playlist_path}. Exception: {e}"
            )
        except UnicodeEncodeError as e:
            self.logger.error(
                f"Encoding error when writing playlist file at: \
                {playlist_path}. Exception: {e}"
            )

    def write_all_playlists(self):
        """
        Run for all discovered sections in
        the configuration. Each will produce
        a separate playlist file.
        """
        for section in self.config.sections():
            self.logger.debug(f"Processing section {section}")
            self.process_section(section)


def setup_logger(log_file: str = "m3ugen.log", level=logging.INFO, print_log=False):
    """
    Create central logger that outputs to stdout
    and a log file in the working directory.
    """
    logging.basicConfig(
        filename=log_file, level=level, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    if print_log:
        stdout_handler = logging.StreamHandler(sys.stdout)
        logging.getLogger("m3ugen").addHandler(stdout_handler)
    return logging.getLogger("m3ugen")


def norm_path(path):
    """
    Normalise paths to NFC encoding (typical for Linux and Windows)
    """
    return unicodedata.normalize("NFC", path)


def parse_arguments():
    """
    Read script arguments and provide help.
    """
    parser = argparse.ArgumentParser(
        description="Generate m3u playlists from the given config file."
    )
    parser.add_argument(
        "config_file",
        nargs="?",
        help="Path to configuration file (or set CONFIG_FILE env variable)",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "-e",
        "--ext",
        nargs="+",
        dest="file_extensions",
        default=[".flac", ".mp3"],
        help="File extensions to include (default: '.flac' '.mp3')",
    )
    parser.add_argument(
        "-p",
        "--print-log",
        dest="print_log",
        action="store_true",
        help="Print log to stdout as well as logfile",
    )
    return parser.parse_args()


def load_config(config_file_name: str) -> configparser.ConfigParser:
    """
    Attempt to load and parse the configuration file.
    """
    config = configparser.ConfigParser()

    if not os.path.isfile(config_file_name):
        raise FileNotFoundError(f"Config file '{config_file_name}' does not exist.")
    with io.open(os.path.abspath(config_file_name), "r", encoding="utf8") as f:
        config.read_file(f)
    return config


def main():
    """
    Main function, parses CLI args, sets log level, sets up logger, reads config
    then writes playlist files.
    """
    args = parse_arguments()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = setup_logger(level=log_level, print_log=args.print_log)
    if args.print_log:
        logger.info("Printing log to stdout")

    config_file = args.config_file or os.environ.get("CONFIG_FILE")
    if not config_file:
        logger.error(
            "No config file specified. Set CONFIG_FILE env or pass as argument"
        )
        sys.exit(1)
    try:
        config = load_config(config_file)
    except FileNotFoundError as e:
        logger.error("Config file not found: %s", str(e))
        sys.exit(1)
    except PermissionError as e:
        logger.error("Permission denied opening config file: %s", str(e))
        sys.exit(1)
    except (configparser.Error, UnicodeDecodeError) as e:
        logger.error("Failed to parse config file: %s", str(e))
        sys.exit(1)

    writer = PlaylistWriter(config, logger, args.file_extensions)
    writer.write_all_playlists()
    logger.info("Finished writing all playlists")


if __name__ == "__main__":
    main()
