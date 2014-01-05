#! /usr/bin/python
# -*- coding=utf-8 -*-

import gtk
import informations

class AboutDialog(gtk.AboutDialog):
    def __init__(self, window):
        gtk.AboutDialog.__init__(self)
        self.set_transient_for(window)
        
        self.set_name(informations.UNIX_APPNAME)
        self.set_program_name(informations.APPNAME)
        self.set_version(informations.VERSION)
        self.set_copyright(informations.COPYRIGHT_NOTICE)
        self.set_comments(informations.APP_DESCRIPTION)
        self.set_license(informations.LICENSE)
        self.set_authors(["%s <%s>" % (a["name"], a["email"]) for a in informations.AUTHORS])
    
    def run(self):
        self.show_all()
        gtk.AboutDialog.run(self)
        self.hide()
