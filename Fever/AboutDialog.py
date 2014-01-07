# AboutDialog.py
# -*- Mode: Python; indent-tabs-mode: nil; tab-width: 4; coding: utf-8 -*-
#
# Copyright © 2013-2014 Gwendal Le Bihan
# 
# This file is part of Fever.
# 
# Fever is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Fever is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Fever.  If not, see <http://www.gnu.org/licenses/>.

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
