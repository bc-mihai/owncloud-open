from gi.repository import Nautilus, GObject
import subprocess

class ColumnExtension(GObject.GObject, Nautilus.MenuProvider):
    def copy_link(self, menu, files):
        if len(files) == 0: return
        # TODO use the python API to get the URL, some Gnome API to write to the clipboard..
        subprocess.call(["owncloud_copy_link", files[0].get_uri()])

    def get_file_items(self, window, files):
        copy_link_item = Nautilus.MenuItem(name='OwnCloudOpen::CopyLink', label='Copy ownCloud Link')
        copy_link_item.connect("activate", self.copy_link, files)
        return copy_link_item,

    def get_background_items(self, window, file):
        return None
