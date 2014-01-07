# db_structure.py
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

DB_STRUCTURE = {
    "global_data": [
        {"field_name": "key", "type": "TEXT", "no_upload": True, "no_download": True},
        {"field_name": "value", "type": "TEXT", "no_upload": True, "no_download": True}
    ],
    
    "tags": [
        {"field_name": "local_id", "type": "INTEGER PRIMARY KEY", "no_upload": True, "no_download": True},
        {"field_name": "guid", "type": "TEXT", "no_upload": True, "no_download": False},
        {"field_name": "name", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "parent_local_id", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True},
        {"field_name": "parentGuid", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "updateSequenceNum", "type": "NUMERIC", "no_upload": True, "no_download": False},
        {"field_name": "dirty", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True},
        {"field_name": "deleted", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True}
    ],
    
    "notebooks": [
        {"field_name": "local_id", "type": "INTEGER PRIMARY KEY", "no_upload": True, "no_download": True},
        {"field_name": "guid", "type": "TEXT", "no_upload": True, "no_download": False},
        {"field_name": "name", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "updateSequenceNum", "type": "NUMERIC", "no_upload": True, "no_download": False},
        {"field_name": "defaultNotebook", "type": "NUMERIC DEFAULT 0", "no_upload": False, "no_download": False},
        {"field_name": "stack", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "dirty", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True},
        {"field_name": "deleted", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True}
    ],
    
    "resources": [
        {"field_name": "local_id", "type": "INTEGER PRIMARY KEY", "no_upload": True, "no_download": True},
        {"field_name": "guid", "type": "TEXT", "no_upload": True, "no_download": False},
        {"field_name": "noteGuid", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "data", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "bodyHash", "type": "TEXT", "no_upload": True, "no_download": False},
        {"field_name": "mime", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "width", "type": "NUMERIC", "no_upload": False, "no_download": False},
        {"field_name": "height", "type": "NUMERIC", "no_upload": False, "no_download": False},
        {"field_name": "updateSequenceNum", "type": "NUMERIC", "no_upload": True, "no_download": False},
        {"field_name": "dirty", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True},
        {"field_name": "deleted", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True}
    ],
    
    "notes": [
        {"field_name": "local_id", "type": "INTEGER PRIMARY KEY", "no_upload": True, "no_download": True},
        {"field_name": "guid", "type": "TEXT", "no_upload": True, "no_download": False},
        {"field_name": "title", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "content", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "contentHash", "type": "TEXT", "no_upload": True, "no_download": False},
        {"field_name": "contentLength", "type": "NUMERIC", "no_upload": True, "no_download": False},
        {"field_name": "active", "type": "NUMERIC DEFAULT 1", "no_upload": False, "no_download": False},
        {"field_name": "updateSequenceNum", "type": "NUMERIC", "no_upload": True, "no_download": False},
        {"field_name": "notebook_local_id", "type": "NUMERIC", "no_upload": True, "no_download": False},
        {"field_name": "notebookGuid", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "tagGuids", "type": "TEXT", "no_upload": False, "no_download": False},
        {"field_name": "dirty", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True},
        {"field_name": "deleted", "type": "NUMERIC DEFAULT 0", "no_upload": True, "no_download": True}
    ]
}
