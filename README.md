## Description

This is a (non-standard) ownCloud URL handler implementation. It contains three scripts and two .desktop files:

* `owncloud_transform.py` can be used to transform paths to local files (or "file://" URLs) into (non-standardized) "owncloud+http(s)://" URLs containing the remote host and WebDAV file path. As a fallback, both URLs without the WebDAV path prefix and without the "owncloud+" prefix (the latter being equivalent to "normal ownCloud WebDAV links") are supported (but not generated). Note that this script uses your local ownCloud desktop sync configuration files to do the mapping.

* `owncloud_open` will transform the URL passed to it into a local path using `owncloud_transform.py` and open it using the default action (`xdg-open`). If no URL is passed, the script will try to use `xclip` to get a URL from the clipboard.

* `owncloud_copy_link` will transform the path passed via its first parameter to an "owncloud+http(s)://" URL, copy it to the clipboard and show a notification. If no first parameter is passed, the script will try to use `xclip` to get a path from the clipboard.

* `owncloud-open.desktop`: After installing this, XDG-compliant applications will start recognizing "owncloud+http(s)://" URLs. A shortcut to `owncloud_open` is added to the "Accessories" menu; it can be used to open an ownCloud URL from the clipboard, as a drag-drop target for URLs (as a launcher or desktop shortcut) or as an "Open as" launcher.

* `owncloud-copy-link.desktop`: This is a shortcut file for `owncloud_copy_link`. An entry is added to the "Accessories" menu and can be used as a drag-drop target by e.g. creating a launcher or desktop shortcut for it or as an "Open as" launcher. **TODO** ideally this would show up as a right-click action in your file manager..

### File manager / browser integration

* **Firefox**: The Firefox `.xpi` extension adds an "Open ownCloud URL" entry to the context ("right click") menu. It will attempt to trigger the ownCloud URL handler (i.e. open the file or directory locally).

* **Nautilus**: The Nautilus extension adds a "Copy ownCloud Link" entry to the context ("right click") menu, which runs `owncloud_copy_link` with the selected file as a parameter. The extension requires Nautilus-Python support (may be called called `nautilus-python` or `python-nautilus`).

* **Dolphin**: The Dolphin extension adds a "Copy ownCloud Link" entry to the "Actions" context ("right click") menu, which runs `owncloud_copy_link` with the selected file as a parameter. TODO: Probably depends on package *python-kde4*.

## Installation

This will install the utilities in `/usr/local/bin`, the .desktop files in `/usr/share/applications`, `/usr/share/applications/kde4` and the Nautilus extension in `/usr/share/nautilus-python/extensions`.

```
sudo make install 
```

To install the .xpi, just open it in Firefox.
  
## State

Currently tested (a little) on Ubuntu 14.04 with XFCE and Ubuntu 12.04 with KDE. Should work on Linux in general. Some issues may still arise (perhaps with custom ownCloud client configurations), in which case please report them. Mac / Windows support is still missing.

## License

Simplified BSD. See LICENSE.txt.
