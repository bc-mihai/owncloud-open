#!/usr/bin/env python
import argparse
import ConfigParser
import urlparse
from collections import defaultdict
import os
import urllib
import subprocess
import logging

"""
Supported ownCloud URL formats:
[owncloud+]http[s]://<owncloud URL>/[remote.php/webdav/]<path>
[owncloud+]http[s]://<owncloud URL>/[index.php]/apps/files/?dir=<encoded path>
[owncloud+]http[s]://<owncloud URL>/[index.php]/apps/files/ajax/download.php?dir=<encoded path>&files=<encoded basename>

e.g. owncloud+https://owncloud.example.com/remote.php/webdav/developers/example.txt
"""


class OwnCloudAccount(object):
    def __init__(self):
        self.base_url = None
        self.paths = defaultdict(OwnCloudPath)

    def set_base_url(self, base_url):
        self.base_url = base_url.rstrip("/")


class OwnCloudPath(object):
    def __init__(self):
        self.local_path = None
        self.target_path = None

    def set_local_path(self, local_path):
        # note: local_path: no trailing path separator
        self.local_path = local_path.rstrip(os.path.sep)

    def set_target_path(self, target_path):
        # note: target_path: leading slash, no trailing slash
        self.target_path = target_path.rstrip("/")

        if not self.target_path.startswith("/"):
            self.target_path = "/" + self.target_path


class OwnCloudConfig(object):

    URL_TYPE_WEBCLIENT = 0
    URL_TYPE_WEBDAV = 1

    def __init__(self, filename=None):
        """
        Read an ownCloud configuration from the given filename.
        :param filename: The filename, or None to use the default file.
        """
        # TODO windows, mac (different directories)

        self.filename = filename

        if self.filename is None:
            self.filename = os.path.join(os.path.expanduser("~"), ".local", "share", "data", "ownCloud", "owncloud.cfg")

        log.debug("opening config file %s" % self.filename)

        self.config = ConfigParser.ConfigParser()
        self.config.read(self.filename)

        self.accounts = defaultdict(OwnCloudAccount)
        self._get_accounts()

    def _get_accounts(self):
        """
        Obtain all url - directory mappings from the config files.

        ownCloud config file format has changed. In 2.1, everything is in the Accounts section:

        <num>\url
        <num>\Folders\<id>\localPath
        <num>\Folders\<id>\targetPath

        with num being a number (starting with 0) and <id> a folder identifier string..
        """

        if not self.config.has_section("Accounts"):
            return

        for key, val in self.config.items("Accounts"):
            key_path = key.lower().split("\\")
            if len(key_path) < 2 or not key_path[0].isdigit():
                continue # skip unknown option

            account_id = int(key_path[0])

            logging.debug("Parsing %s: %s", key, val)

            if len(key_path) == 2 and key_path[1] == "url":
                self.accounts[account_id].set_base_url(val)

            elif len(key_path) == 4 and key_path[1] == "folders" and key_path[3] == "localpath":
                self.accounts[account_id].paths[key_path[2]].set_local_path(val)

            elif len(key_path) == 4 and key_path[1] == "folders" and key_path[3] == "targetpath":
                self.accounts[account_id].paths[key_path[2]].set_target_path(val)

        invalid_account_ids = []
        for account_id, account in self.accounts.iteritems():
            if account.base_url is None:
                invalid_account_ids.append(account_id)
                log.debug("deleting account with invalid URL: %d", account_id)
                continue

            invalid_path_ids = []
            for path_id, path in account.paths.iteritems():
                if path.local_path is None or path.target_path is None:
                    invalid_path_ids.append(path_id)
                    log.debug("deleting path with invalid values: %s (%s -> %s)", path_id, path.local_path,
                                  path.target_path)
            for i in invalid_path_ids:
                del account.paths[i]

        for i in invalid_account_ids:
            del self.accounts[i]

        if log.isEnabledFor(logging.DEBUG):
            for account_id, account in self.accounts.iteritems():
                logging.debug("Account %d: %s", account_id, account.base_url)
                for path_id, path in account.paths.iteritems():
                    logging.debug(" Path %s: %s -> %s", path_id, path.local_path, path.target_path)


    def get_filename_or_url(self, url_or_path, url_type=URL_TYPE_WEBCLIENT):
        """
        Get the filename for the given owncloud+*:// URL, or the URL for the given path / file URL otherwise.
        Also parse http:// and https:// URLs AS IF they were owncloud+*:// URLs.
        """
        if any(url_or_path.startswith(prefix) for prefix in ["owncloud+", "http:", "https:"]):
            return self.get_filename(url_or_path)
        else:
            return self.get_url(url_or_path, url_type)

    def get_filename(self, url):
        """
        Get the filename for the given owncloud*:// URL as a string, or None if no match is found.
        Also parse http:// and https:// URLs AS IF they were owncloud+*:// URLs.
        """
        
        # strip "owncloud+" from links
        if url.startswith("owncloud+"):
            url = url[len("owncloud+"):]

        for account in self.accounts.itervalues():
            if url != account.base_url and not url.startswith(account.base_url+"/"):
                continue

            # found match
            log.debug("found matching URL %s", account.base_url)

            # remove URL
            url_path = url[len(account.base_url):]

            # remove prefixes
            is_actual_path = False

            if url_path == "/index.php" or url_path.startswith("/index.php/"):
                url_path = url_path[len("/index.php"):]

            if url_path == "/remote.php/webdav" or url_path.startswith("/remote.php/webdav/"):
                url_path = url_path[len("/remote.php/webdav"):]
                is_actual_path = True
                logging.debug("found webdav path")

            url_path = url_path.lstrip("/")

            if not is_actual_path:
                # parse apps/files/?dir= and apps/files/ajax/download.php?dir= if present
                if url_path.startswith("apps/files?") or url_path.startswith("apps/files/?"):
                    log.debug("parsing file app path to dir: %s", url_path)
                    url_params = urlparse.parse_qs(url_path.split("?", 1)[1])
                    log.debug(url_params)
                    if "dir" not in url_params:
                        log.error("required dir parameter not found in URL")
                        return None # error
                    else:
                        url_path = url_params["dir"][0]
                elif url_path.startswith("apps/files/ajax/download.php?"):
                    log.debug("parsing file app path to file: %s", url_path)
                    url_params = urlparse.parse_qs(url_path.split("?", 1)[1])
                    log.debug(url_params)
                    if "dir" not in url_params or "files" not in url_params:
                        log.error("required parameters not found in URL")
                        return None # error
                    else:
                        url_path = url_params["dir"][0].rstrip("/") + "/" + url_params["files"][0]
                else:
                    log.debug("unknown URL path fragment: %s", url_path)
            else:
                # assume full path. unquote URL
                url_path = urllib.unquote_plus(url_path)

            # find matching path prefix. make sure leading slash is there (in order to match it with the target path)
            if not url_path.startswith("/"):
                url_path = "/" + url_path

            for account_path in account.paths.itervalues():
                log.debug("matching %s with %s -> %s", url_path, account_path.local_path, account_path.target_path)
                if url_path == account_path.target_path or url_path.startswith(account_path.target_path+"/"):

                    return os.path.join(account_path.local_path,
                                        *(url_path[len(account_path.target_path):].strip("/").split("/")))

            log.debug("path not matched: %s", url_path)

        return None

    def get_url(self, filename, url_type=URL_TYPE_WEBCLIENT):
        """
        Get an URL for the given filename (or file:// URL), or None if the file is not within one of
        the owncloud directories.

        :param filename The file or directory name, or file:// URL
        :param url_type One of the URL_TYPE_* constants; returns different URL types.
        """
        if filename.startswith("file://"):
            filename = urllib.url2pathname(filename[len("file://"):])
            log.debug("transforming file URL to path: %s" % filename)

        log.debug("file %s: absolute path %s" % (filename, os.path.abspath(filename)))

        filename = os.path.abspath(filename)

        if os.path.isdir(filename):
            filename += os.path.sep
            log.debug("adding dir separator to dir: %s" % filename)

        for account in self.accounts.itervalues():
            for path in account.paths.itervalues():
                local_path = path.local_path + os.path.sep
                log.debug("comparing with basepath; now %s" % local_path)
                if not filename.startswith(local_path): continue

                rel_path = os.path.relpath(filename, local_path)
                if rel_path == ".": rel_path = ""

                file_path_elems = path.target_path.split("/") + rel_path.split("/")

                # translate url
                log.debug("relative path to %s: %s" % (path, rel_path))

                if url_type == OwnCloudConfig.URL_TYPE_WEBCLIENT:
                    base_url = account.base_url
                    if not base_url.endswith("/index.php"):
                        base_url += "/index.php"  # ugh!

                    if os.path.isdir(filename) or len(file_path_elems) < 1:
                        return base_url + "/apps/files/?dir=" + \
                               urllib.quote_plus("/".join(file_path_elems))
                    else:
                        return base_url + "/apps/files/ajax/download.php?dir=" + \
                               urllib.quote_plus("/".join(file_path_elems[:-1])) + \
                               "&files=" + urllib.quote_plus(file_path_elems[-1])
                elif url_type == OwnCloudConfig.URL_TYPE_WEBDAV:
                    return account.base_url + "/remote.php/webdav/" + \
                            "/".join(urllib.quote(s) for s in file_path_elems)

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
Exec="""+os.path.abspath(__file__)+""" --run xdg-open %u
Name=ownCloud URL handler
NoDisplay=true
MimeType=x-scheme-handler/owncloud+http;x-scheme-handler/owncloud+https;x-scheme-handler/owncloud;
X-KDE-Protocols=owncloud+http;owncloud+https;owncloud
"""

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--register-url-handler", action="store_true", \
                   help="Register this script as the URL handler for owncloud*:// URLs")
    p.add_argument("--unregister-url-handler", action="store_true", \
                   help="Unregister this script as the URL handler for owncloud*:// URLs")

    p.add_argument("url_or_path", nargs="?",\
                   help="Transform either the given owncloud*:// URL into a path or the other way around")

    p.add_argument("--output-webdav", action="store_true", help="Output the WebDAV URL")

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

    if opts.url_or_path is not None:
        oc = OwnCloudConfig(opts.config)
        print_or_run(oc.get_filename_or_url(opts.url_or_path, OwnCloudConfig.URL_TYPE_WEBDAV if opts.output_webdav
            else OwnCloudConfig.URL_TYPE_WEBCLIENT))

    if opts.unregister_url_handler:
        URLHandler.unregister()

    if opts.register_url_handler:
        URLHandler.register()
else:
    log = logging.getLogger(__name__)
