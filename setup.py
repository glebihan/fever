#! /usr/bin/env python
# -*- Mode: Python; indent-tabs-mode: nil; tab-width: 4; coding: utf-8 -*-
#
# Copyright © 2013 Gwendal Le Bihan
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

from distutils.core import setup
import sys, os
from Fever.informations import *

def list_packages():
    res = ['Fever']
    for dirpath, dirnames, filenames in os.walk('Fever'):
        if ".svn" in dirpath:
            continue
        for dirname in dirnames:
            if os.path.exists(os.path.join(dirpath, dirname, '__init__.py')):
                res.append(os.path.join(dirpath, dirname).replace("/", "."))
    return res
      
def list_share_files():
    res = []
    for dirpath, dirnames, filenames in os.walk('share'):
        dirfileslist = []
        if ".svn" in dirpath:
            continue
        for i in filenames:
            if not i.endswith("~") and not i.endswith(".bak") and os.path.isfile(os.path.join(dirpath, i)):
                dirfileslist.append(os.path.join(dirpath, i))
        if dirfileslist:
            res.append((dirpath, dirfileslist))
    return res

packages = list_packages()
package_dir = {}
for i in packages:
    package_dir[i] = i.replace(".", "/")

# build tinymce
os.chdir("tinymce")
os.system("npm install")
os.system("jake")
os.chdir("..")
os.system("cp -R tinymce/js/tinymce share/fever")

# package evernote API
os.system("cp -R evernote/lib/evernote evernote/lib/thrift Fever")

setup(
    name = UNIX_APPNAME,
    version = VERSION,
    author = AUTHORS[0]["name"],
    author_email = AUTHORS[0]["email"],
    maintainer = AUTHORS[0]["name"],
    maintainer_email = AUTHORS[0]["email"],
    description = APP_DESCRIPTION,
    scripts = ["fever"],
    packages = packages,
    package_dir = package_dir,
    data_files = list_share_files()
)
