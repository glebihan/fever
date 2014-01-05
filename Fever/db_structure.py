#! /usr/bin/python
# -*- coding=utf-8 -*-

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
