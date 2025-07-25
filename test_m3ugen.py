"""
Unit tests for the m3ugen playlist generator.
"""

import os
import unittest
from unittest import mock
import logging
import m3ugen


class TestPlaylistWriter(unittest.TestCase):
    """
    Create a test class for the playlistwriter class.
    """

    def setUp(self):
        """
        Mock the setup method to create a logger and config.
        """
        self.logger = mock.Mock()
        self.file_extensions = [".flac", ".mp3"]
        self.config = mock.MagicMock()
        self.writer = m3ugen.PlaylistWriter(
            self.config, self.logger, self.file_extensions
        )

    def test_run_varied_filenames_and_folders(self):
        """
        Test against different file and folder names.
        """
        self.config.sections.return_value = ["Playlist1"]
        section_dict = {
            "musicSource": "src",
            "playListFolder": "dest",
            "foldersToInclude": "normal_folder\nBad Name Folder\nodd_@_folder\n\n",
        }
        self.config.__getitem__.side_effect = lambda x: (
            section_dict if x == "Playlist1" else None
        )

        # Simulate files in each folder
        all_files = [
            "src/normal_folder/song1.flac",
            "src/normal_folder/track two.mp3",
            "src/normal_folder/.hiddenfile.flac",
            "src/normal_folder/weird&name.flac",
            "src/Bad Name Folder/track@.mp3",
            "src/Bad Name Folder/README.txt",  # not a music file
            "src/odd_@_folder/audiofile.wav",  # different extension
            "src/odd_@_folder/song3.flac",
            "src/odd_@_folder/dir/",  # should not be treated as file
            "src/Bad Name Folder/ADMO - Zero Wave LP - 02 Against All Odds.flac",
        ]

        def isfile_side_effect(path):
            # Only treat listed files as files, not folders or directories
            return path in all_files and not path.endswith("/")

        def isdir_side_effect(path):
            return path in [
                "src/normal_folder",
                "src/Bad Name Folder",
                "src/odd_@_folder",
            ]

        # Simulate globbing per folder and extension (as your code would)
        def glob_side_effect(pattern, recursive):
            # E.g., pattern could be 'src/normal_folder/**/*.flac' or similar
            base_folder = pattern.split("/**/")[0]
            ext = pattern.split("*")[-1]
            if recursive:
                return [
                    f
                    for f in all_files
                    if f.startswith(base_folder) and f.endswith(ext)
                ]
            return [
                f for f in all_files if f.startswith(base_folder) and f.endswith(ext)
            ]

        with mock.patch("os.path.isfile", side_effect=isfile_side_effect), mock.patch(
            "os.path.isdir", side_effect=isdir_side_effect
        ), mock.patch("glob.glob", side_effect=glob_side_effect), mock.patch(
            "os.path.relpath", side_effect=lambda p, d: f"rel/{os.path.basename(p)}"
        ), mock.patch(
            "io.open", mock.mock_open()
        ) as mfile:
            self.writer.write_all_playlists()
            handle = mfile()
            # Confirm the playlist header was written
            handle.write.assert_any_call("#EXTM3U\n")
            # Confirm correct files (by extension) were added
            handle.write.assert_any_call("rel/song1.flac\n")
            handle.write.assert_any_call("rel/track two.mp3\n")
            handle.write.assert_any_call("rel/.hiddenfile.flac\n")
            handle.write.assert_any_call("rel/weird&name.flac\n")
            handle.write.assert_any_call("rel/track@.mp3\n")
            handle.write.assert_any_call("rel/song3.flac\n")
            handle.write.assert_any_call(
                "rel/ADMO - Zero Wave LP - 02 Against All Odds.flac\n"
            )
            # Should NOT include .txt, .wav, directories
            for not_expected in ["README.txt", "audiofile.wav", "dir"]:
                call = mock.call(f"rel/{not_expected}\n")
                assert call not in handle.write.call_args_list

    @mock.patch("io.open")
    def test_add_file_to_playlist_writes_and_logs(self, _mock_open):
        """
        Make sure writing a file to the playlist works.
        """
        with mock.patch("os.path.relpath", return_value="rel/file.flac"):
            playlist = mock.Mock()
            self.writer.add_file_to_playlist(playlist, "/abs/file.flac", "/dest")
            playlist.write.assert_called_with("rel/file.flac\n")
            self.logger.info.assert_any_call("Added file to playlist: rel/file.flac")

    @mock.patch("os.path.isfile")
    def test_process_folder_file(self, mock_isfile):
        """
        Test that a full file path is handled.
        """
        mock_isfile.side_effect = lambda p: bool(p.endswith("file.flac"))
        playlist = mock.Mock()
        with mock.patch.object(self.writer, "add_file_to_playlist") as mock_add_file:
            self.writer.process_folder(playlist, "/src", "file.flac", "/dest")
            mock_add_file.assert_called_once()

    @mock.patch("os.path.isdir")
    @mock.patch("os.path.isfile")
    @mock.patch("glob.glob")
    def test_process_folder_directory(self, mock_glob, mock_isfile, mock_isdir):
        """
        Test that a directory is handled.
        """
        mock_isdir.side_effect = lambda p: bool(p.endswith("folder1"))
        mock_isfile.side_effect = lambda p: p.endswith(".flac")
        mock_glob.return_value = [
            "/src/folder1/track1.flac",
            "/src/folder1/track2.flac",
        ]
        playlist = mock.Mock()
        with mock.patch.object(self.writer, "add_file_to_playlist") as mock_add_file:
            self.writer.process_folder(playlist, "/src", "folder1", "/dest")
            self.assertEqual(mock_add_file.call_count, 4)

    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch("os.path.isfile", return_value=False)
    def test_process_folder_neither(self, _mock_isfile, _mock_isdir):
        """
        Test that a non-file, non-directory is handled.
        """
        playlist = mock.Mock()
        self.writer.process_folder(playlist, "/src", "notfound", "/dest")
        self.logger.warning.assert_any_call(
            "/src/notfound is not a file or directory, skipping"
        )

    @mock.patch("io.open", new_callable=mock.mock_open)
    def test_process_section_missing_values(self, mock_open):
        """
        Test that missing values in a section is handled.
        """
        config = {
            "Section1": {
                "musicSource": "",
                "playListFolder": "",
                "foldersToInclude": "",
            }
        }
        writer = m3ugen.PlaylistWriter(config, self.logger, self.file_extensions)
        writer.process_section("Section1")
        self.logger.warning.assert_any_call(
            "Section 'Section1' missing required values. Skipping"
        )
        mock_open.assert_not_called()

    @mock.patch("io.open", new_callable=mock.mock_open)
    @mock.patch("os.path.isdir", return_value=True)
    @mock.patch("os.path.isfile")
    @mock.patch("glob.glob", return_value=["/music/folder1/track.flac"])
    def test_process_section_success(
        self, _mock_glob, mock_isfile, _mock_isdir, mock_open
    ):
        """
        Test a successful expected config section.
        """

        # Mock isfile so that only the globbed file is seen as a file
        def isfile_side_effect(path):
            if path == "/music/folder1/track.flac":
                return True
            return False

        mock_isfile.side_effect = isfile_side_effect
        config = {
            "Rock": {
                "musicSource": "/music",
                "playListFolder": "/playlists",
                "foldersToInclude": "folder1\n",
            }
        }
        writer = m3ugen.PlaylistWriter(config, self.logger, self.file_extensions)
        with mock.patch.object(writer, "add_file_to_playlist") as mock_add_file:
            writer.process_section("Rock")
            mock_open.assert_called_with("/playlists/rock.m3u", "w", encoding="utf8")
            mock_add_file.assert_called_with(
                mock.ANY, "/music/folder1/track.flac", "/playlists"
            )

    @mock.patch("io.open", side_effect=FileNotFoundError)
    def test_process_section_file_not_found(self, _mock_open):
        """
        Test that a missing folder is handled.
        """
        config = {
            "Section1": {
                "musicSource": "/src",
                "playListFolder": "/dest",
                "foldersToInclude": "folder1",
            }
        }
        writer = m3ugen.PlaylistWriter(config, self.logger, self.file_extensions)
        writer.process_section("Section1")
        self.logger.error.assert_any_call(
            "Playlist destination folder not found: /dest. Exception: "
        )

    def test_write_all_playlists_calls_process_section(self):
        """
        Test that calling write_all_playlists calls process_section.
        """
        self.config.sections.return_value = ["S1", "S2"]
        with mock.patch.object(self.writer, "process_section") as mock_proc:
            self.writer.write_all_playlists()
            self.assertEqual(mock_proc.call_count, 2)


class TestHelperFunctions(unittest.TestCase):
    """
    Test class for helper functions outside of play list writer
    """

    @mock.patch("logging.basicConfig")
    @mock.patch("logging.getLogger")
    def test_setup_logger_default(self, mock_get_logger, mock_basic_config):
        """
        Test logger setup.
        """
        logger = mock.Mock()
        mock_get_logger.return_value = logger
        result = m3ugen.setup_logger()
        mock_basic_config.assert_called_once_with(
            filename="m3ugen.log",
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        mock_get_logger.assert_called_once_with("m3ugen")
        self.assertIs(result, logger)

    @mock.patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments_defaults(self, mock_parse_args):
        """
        Test argument handling.
        """
        # Simulate argparse returning specific args
        namespace = mock.Mock()
        namespace.config_file = "config.ini"
        namespace.log_level = "DEBUG"
        namespace.file_extensions = ".mp3"
        mock_parse_args.return_value = namespace

        result = m3ugen.parse_arguments()
        self.assertEqual(result.config_file, "config.ini")
        self.assertEqual(result.log_level, "DEBUG")
        self.assertEqual(result.file_extensions, ".mp3")
        mock_parse_args.assert_called_once()

    @mock.patch("os.path.isfile")
    @mock.patch(
        "io.open", new_callable=mock.mock_open, read_data="[Section]\nfoo=bar\n"
    )
    def test_load_config_success(self, mock_open, mock_isfile):
        """
        Test loading an existing configuration file.
        """
        mock_isfile.return_value = True
        config = m3ugen.load_config("myconfig.cfg")
        self.assertIn("Section", config.sections())
        mock_isfile.assert_called_with("myconfig.cfg")
        mock_open.assert_called_once()

    @mock.patch("os.path.isfile", return_value=False)
    def test_load_config_file_not_found(self, mock_isfile):
        """
        Test loading a non-existant configuration file
        """
        with self.assertRaises(FileNotFoundError):
            m3ugen.load_config("doesnotexist.cfg")
        mock_isfile.assert_called_with("doesnotexist.cfg")


if __name__ == "__main__":
    unittest.main()
