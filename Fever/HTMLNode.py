#! /usr/bin/python
# -*- coding=utf-8 -*-

class HTMLNode(object):
    def __init__(self, xml_node):
        self._xml_node = xml_node
    
    def find(self, elname = None, maxdepth = -1, **params):
        res = []
        if elname == None or self._xml_node.name == elname:
            add = True
            for i in params:
                if self._xml_node.prop(i) != params[i]:
                    add = False
                    break
            if add:
                res.append(self)
        if maxdepth!=0:
            child = self._xml_node.children
            while child:
                res += HTMLNode(child).find(elname, maxdepth - 1, **params)
                child = child.next
        return res
    
    def _get_next(self):
        if self._xml_node.next:
            return HTMLNode(self._xml_node.next)
        else:
            return None
    next = property(_get_next)
    
    def getContent(self):
        return self._xml_node.getContent()
    
    def prop(self, *args):
        return self._xml_node.prop(*args)
    
    def _get_children(self):
        children = self._xml_node.children
        if children:
            return HTMLNode(children)
        else:
            return children
    children = property(_get_children)
    
    def replaceNode(self, newNode):
        self._xml_node.replaceNode(newNode)
    
    def __str__(self):
        return str(self._xml_node)
