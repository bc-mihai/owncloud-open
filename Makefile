install: /usr/bin/xclip /usr/share/nautilus-python
	cp -p owncloud-copy-link.desktop owncloud-open.desktop /usr/share/applications
	cp -p owncloud-copy-link.desktop owncloud-copy-link-kde.desktop /usr/share/applications/kde4
	install -t /usr/local/bin owncloud_transform.py owncloud_copy_link owncloud_open
	install -t /usr/share/nautilus-python/extensions/ filemanager-integration/nautilus_copy_link.py
	update-desktop-database

/usr/share/nautilus-python:
	if which apt-get; then apt-get install python-nautilus; else echo "please install python-nautilus!"; fi

/usr/bin/xclip:
	if which apt-get; then apt-get install xclip; else echo "please install xclip!"; fi

uninstall:
	rm -f /usr/share/applications/owncloud-copy-link.desktop /usr/share/applications/owncloud-open.desktop /usr/share/applications/kde4/owncloud-copy-link-kde.desktop
	rm -f /usr/local/bin/owncloud_transform.py /usr/local/bin/owncloud_copy_link /usr/local/bin/owncloud_open
	rm -f /usr/share/nautilus-python/extensions/nautilus_copy_link.py
	update-desktop-database
