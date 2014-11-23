#!/usr/bin/env python
import argparse
import ConfigParser
import os
import urllib
import subprocess
import logging

"""
ownCloud URL format:
owncloud+http://<owncloud URL>/<path>
owncloud+https://<owncloud URL>/<path>

e.g. owncloud+https://owncloud.example.com/developers/example.txt
"""


class OwnCloudConfig(object):
    def __init__(self, filename=None):
        """
        Read an ownCloud configuration from the given filename.
        :param filename: The filename, or None to use the default file.
        """
        # TODO windows, mac (probably has different directories)

        self.filename = filename

        if self.filename is None:
            self.filename = os.path.join(os.path.expanduser("~"), ".local", "share", "data", "ownCloud", "owncloud.cfg")

        log.debug("opening config file %s" % self.filename)

        self.folders_dir = os.path.join(os.path.dirname(self.filename), "folders")

        log.debug("got folders dir %s" % self.folders_dir)

        self.config = ConfigParser.ConfigParser()
        self.config.read(self.filename)

        self.dir_url_map = {} # alias: (dir, url) tuples

        self._get_dir_url_map()

    def _get_dir_url_map(self):
        """
        Obtain all url - directory mappings from the config files.
        """

        for dir_alias, category_params in \
                [(section, dict(self.config.items(section))) for section in self.config.sections()]:
            log.debug("scanning section %s: %s" % (dir_alias, str(category_params)))
            if "url" not in category_params: continue

            alias_config = ConfigParser.ConfigParser()
            alias_config.read(os.path.join(self.folders_dir, dir_alias))

            self.dir_url_map[dir_alias] = (alias_config.get(dir_alias, "localPath"), category_params["url"])
            log.debug("map: %s %s" % (dir_alias, self.dir_url_map[dir_alias]))

        return self.dir_url_map


    def get_filename(self, url):
        """
        Get the filename for the given owncloud*:// URL as a string, or None if no match is found.
        """
        for base_path, base_url in self.dir_url_map.itervalues():
            # check if URL matches
            log.debug("matching %s with %s" % (url, "owncloud+"+base_url))
            if not url.startswith("owncloud+"+base_url): continue

            # translate path, split into array
            rel_path = url[len("owncloud+"+base_url):].strip("/")
            rel_path = [urllib.unquote_plus(s) for s in rel_path.split("/")]
            log.debug("relative path: %s" % rel_path)

            return os.path.join(base_path, *rel_path)

        return None

    def get_url(self, filename):
        """
        Get an URL for the given filename (or file:// URL), or None if the file is not within one of
        the owncloud directories.
        """
        if filename.startswith("file://"):
            filename = urllib.url2pathname(filename[len("file://"):])
            log.debug("transforming file URL to path: %s" % filename)

        log.debug("file %s: absolute path %s" % (filename, os.path.abspath(filename)))

        filename = os.path.abspath(filename)

        if os.path.isdir(filename):
            filename += os.path.sep
            log.debug("adding dir separator to dir: %s" % filename)

        for base_path, base_url in self.dir_url_map.itervalues():
            # check if path matches
            if not base_path.endswith(os.path.sep):
                base_path += os.path.sep

            log.debug("comparing with basepath; now %s" % base_path)

            if not filename.startswith(base_path): continue

            # translate url
            rel_path = os.path.relpath(filename, base_path)

            if rel_path == ".": rel_path = ""

            log.debug("relative path to %s: %s" % (base_path, rel_path))

            rel_path = [urllib.quote(s) for s in rel_path.split(os.path.sep)]

            if not base_url.endswith("/"):
                base_url += "/"

            log.debug("base url is %s" % base_url)

            return "owncloud+"+base_url+("/".join(rel_path))

        return None

class URLHandler(object):
    # TODO windows, mac

    @staticmethod
    def register(desktop_path=None):
        """
        Register this script as a (persistent) URL handler for owncloud*:// URLs in the user's session.
        This will overwrite any previously created URL handler configuration file.
        :param desktop_path: The path to which to write the config file, or None to use the default.
        """
        if desktop_path is None:
            desktop_path = URLHandler._get_default_path()

        log.info("writing to %s" % desktop_path)

        f = open(desktop_path, "w")
        f.write(URLHandler.CONFIG_FILE_CONTENTS)
        f.close()

        log.info("done, calling update-desktop-database")

        subprocess.call(["update-desktop-database", os.path.dirname(desktop_path)])


    @staticmethod
    def unregister(desktop_path=None):
        """
        Unregister this script as a (persistent) URL handler for owncloud*:// URLs in the user's session.
        :param desktop_path: The path from which to delete the config file, or None to use the default.
        """
        if desktop_path is None:
            desktop_path = URLHandler._get_default_path()

        log.info("removing %s" % desktop_path)

        if os.path.exists(desktop_path):
            os.unlink(desktop_path)

        log.info("done, calling update-desktop-database")

        subprocess.call(["update-desktop-database", os.path.dirname(desktop_path)])

    @staticmethod
    def _get_default_path():
        return os.path.join(os.path.expanduser("~"), ".local", "share", "applications", "owncloud-url.desktop")

    CONFIG_FILE_CONTENTS = """
[Desktop Entry]
Type=Application
Exec="""+os.path.abspath(__file__)+""" -v --url %u --run xdg-open
Name=ownCloud URL handler
NoDisplay=true
MimeType=x-scheme-handler/owncloud+http;x-scheme-handler/owncloud+https;x-scheme-handler/owncloud;
"""

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--register-url-handler", action="store_true", \
                   help="Register this script as the URL handler for owncloud*:// URLs")
    p.add_argument("--unregister-url-handler", action="store_true", \
                   help="Unregister this script as the URL handler for owncloud*:// URLs")

    p.add_argument("--url", help="Output the filesystem path for the given owncloud*:// URL")
    p.add_argument("--path", help="Output the owncloud*:// URL for the given path")

    p.add_argument("--run", help="Run the command with the resulting URL / path as the first parameter")

    p.add_argument("-c", "--config", \
                   help="Use the specified ownCloud config file. If no file is specified, use the default.")

    p.add_argument("-v", "--verbose", action="store_true", help="Output debug messages")

    try:
        import argcomplete
        argcomplete.autocomplete(p)
    except: pass

    opts = p.parse_args()

    def print_or_run(obj):
        if opts.run:
            log.debug("running: %s %s" % (opts.run, obj))
            subprocess.call([opts.run, obj])
        else:
            print obj

    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(logging.DEBUG if opts.verbose else logging.INFO)

    log.debug(opts)

    if opts.url is not None or opts.path is not None:
        oc = OwnCloudConfig(opts.config)

        if opts.url is not None:
            print_or_run(oc.get_filename(opts.url))

        if opts.path is not None:
            print_or_run(oc.get_url(opts.path))

    if opts.unregister_url_handler:
        URLHandler.unregister()

    if opts.register_url_handler:
        URLHandler.register()
else:
    log = logging.getLogger(__name__)