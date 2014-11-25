install:
	cp -p owncloud-copy-link.desktop owncloud-open.desktop /usr/share/applications
	install -t /usr/local/bin owncloud_transform.py owncloud_copy_link owncloud_open
	update-desktop-database

uninstall:
	rm -f /usr/share/applications/owncloud-copy-link.desktop /usr/share/applications/owncloud-open.desktop
	rm -f /usr/local/bin/owncloud_transform.py /usr/local/bin/owncloud_copy_link /usr/local/bin/owncloud_open
	update-desktop-database
