var editing_note_local_id = null;
var editing_note_notebook_local_id = null;
var notes_notebook_filter = null;
var notebooks_list_open_nodes = new Array();
var notes_tag_filter = null;
var availableTags = new Array();

function _(string){
    return string;
}

function clear_all(){
}

function edit_note(local_id){
    editing_note_local_id = null;
    editing_note_notebook_local_id = null;
    tinymce.get("tinymcecontainer").setContent("");
    jQuery("#note_title").val("")
    
    alert("edit_note:" + local_id);
}

function set_editing_note(note_data){
    jQuery("#note_title").val(jQuery("<div/>").html(note_data.title).text());
    tinymce.get("tinymcecontainer").setContent(note_data.contents);
    
    editing_note_local_id = note_data.local_id;
    editing_note_notebook_local_id = note_data.notebook_local_id;
    jQuery("#note_notebook_selector").val(note_data.notebook_local_id);
    
    jQuery("#note_tags_list").find("span.tag").remove();
    for (var i in note_data.tags_list){
        push_note_tag(note_data.tags_list[i]);
    }
    
    jQuery("#noteeditor_wrapper").toggle(true);
    jQuery("#noteslist > a.edited").removeClass("edited");
    jQuery("#noteslist > a[href='#note_" + editing_note_local_id + "']").addClass("edited");
    
    update_editor_height();
}

function update_notes_list(notes_list){
    var link;
    
    jQuery("#noteslist").html("");
    for (var i in notes_list){
        link = jQuery("<a notebook_local_id='" + notes_list[i].notebook_local_id + "' href='#note_" + notes_list[i].local_id + "'><span class='title'>" + notes_list[i].title + "</span><span class='summary'>" + notes_list[i].summary + "</span></a>");
        link.click(function(event){
            edit_note(jQuery(this).attr("href").substring(6));
            event.preventDefault();
        });
        link.appendTo("#noteslist");
    }
    
    if (editing_note_local_id){
        jQuery("#noteslist > a[href='#note_" + editing_note_local_id + "']").addClass("edited");
    }
}

function update_note_notebook(notebook_local_id){
    if (editing_note_local_id){
        alert("set_note_notebook:" + editing_note_local_id + ":" + notebook_local_id);
        editing_note_notebook_local_id = notebook_local_id;
        jQuery("#noteslist > a[href='#note_" + editing_note_local_id + "']").attr("notebook_local_id", notebook_local_id);
        update_notes_filter();
    }
}

function update_tags_list(tags_list){
    jQuery("#tagslist").tree("loadData", tags_list);
    availableTags = new Array();
    for (var i in tags_list){
        availableTags.push(tags_list[i].label);
    }
}

function update_notebooks_list(notebooks_list){
    var node;
    jQuery("#notebookslist").tree("loadData", notebooks_list);
    if (notes_notebook_filter){
        node = jQuery("#notebookslist").tree("getNodeById", notes_notebook_filter.id);
        jQuery("#notebookslist").tree('selectNode', node);
    }
    for (var i in notebooks_list_open_nodes){
        node = jQuery("#notebookslist").tree("getNodeById", notebooks_list_open_nodes[i]);
        if (node){
            jQuery("#notebookslist").tree('openNode', node);
        }
    }
}

function update_note_notebook_selector(notebooks_list){
    jQuery("#note_notebook_selector").html("");
    for (var i in notebooks_list){
        jQuery("<option value='" + notebooks_list[i].local_id + "'>" + notebooks_list[i].label + "</option>").appendTo("#note_notebook_selector");
    }
    jQuery("#note_notebook_selector").val(editing_note_notebook_local_id);
}

function update_editor_height(){
    jQuery("#tinymcecontainer_ifr").css("height", (jQuery("#noteeditor_inside_wrapper").height() - jQuery("#tinymcecontainer_ifr").offset().top) + "px");
}

function update_noteslist_height(){
    jQuery("#noteslist").css("height", (jQuery("#noteslist_wrapper").height() - jQuery("#noteslist").offset().top) + "px");
}

function update_notes_filter(){
    if (notes_notebook_filter === null){
        jQuery("#searchbox_notebook_filter").toggle(false);
        jQuery("#searchbox_tag_filter").toggle(false);
        resize_search_input();
    }else{
        jQuery("#searchbox_notebook_filter").find("span.value").html(notes_notebook_filter.name);
        resize_search_input();
        jQuery("#searchbox_notebook_filter").toggle(true);
    }
    
    alert("refresh_notes_search_results:" + (notes_notebook_filter ? (notes_notebook_filter.is_stack ? "stack_" : "") + notes_notebook_filter.id : "") + ":" + (notes_tag_filter ? notes_tag_filter.id : "") + ":" + jQuery("#searchinput").val());
}

function resize_search_input(){
    var width = jQuery("#searchbox").width() - 8;
    if (notes_notebook_filter != null){
        console.log("notes_notebook_filter != null");
        width -= jQuery("#searchbox_notebook_filter").outerWidth() + 3;
    }
    if (notes_tag_filter != null){
        width -= jQuery("#searchbox_tag_filter").outerWidth() + 3;
    }
    jQuery("#searchinput").css("width", width + "px");
}

function push_note_tag(tag){
    var tag_node = jQuery("<span class='tag'></span>");
    tag_node.html(tag);
    var remove_link = jQuery("<a href='#'><img src='icons/12x12/delete.png'/></a>");
    tag_node.append(remove_link);
    tag_node.insertBefore("#note_tags_selector");
    remove_link.click(function(event){
        alert("remove_note_tag:" + editing_note_local_id + ":" + jQuery(this).parent().text());
        jQuery(this).parent().remove();
    });
}

jQuery(document).ready(function(){
    jQuery("#notebookslist").tree({
        data: [],
        dragAndDrop: true,
        autoOpen: 0,
        onCanMove: function(node){
            return (!node.is_stack);
        },
        onCanMoveTo: function(moved_node, target_node, position){
            if (target_node.is_stack || target_node.id == -1){
                return (position == 'inside');
            }
            else {
                return false;
            }
        }
    });
    jQuery("#notebookslist").bind('tree.select', function(event){
        if (event.node && event.node.id == -1){
            notes_notebook_filter = null;
            notes_tags_filter = null;
        }else{
            notes_notebook_filter = event.node;
        }
        update_notes_filter();
    });
    jQuery("#notebookslist").bind('tree.move', function(event){
        if (event.move_info.target_node.id == -1){
            alert("update_notebook_stack:" + event.move_info.moved_node.id + ":");
        }else{
            alert("update_notebook_stack:" + event.move_info.moved_node.id + ":" + event.move_info.target_node.id);
        }
    });
    jQuery("#notebookslist").bind('tree.open', function(event){
        notebooks_list_open_nodes.push(event.node.id);
    });
    jQuery("#notebookslist").bind('tree.close', function(event){
        var i = notebooks_list_open_nodes.indexOf(event.node.id);
        while (i != -1){
            notebooks_list_open_nodes.splice(i, 1);
            i = notebooks_list_open_nodes.indexOf(event.node.id);
        }
    });
    jQuery("#tagslist").tree({
        data: []
    });
    jQuery("#leftbar").resizable({
        handles: "e",
        resize: function(event, ui){
            jQuery("#noteslist_wrapper").css("left", jQuery("#leftbar").outerWidth());
            jQuery("#noteeditor_wrapper").css("left", jQuery("#leftbar").outerWidth() + jQuery("#noteslist_wrapper").outerWidth());
        }
    });
    jQuery("#noteslist_wrapper").resizable({
        handles: "e",
        resize: function(event, ui){
            jQuery("#noteeditor_wrapper").css("left", jQuery("#leftbar").outerWidth() + jQuery("#noteslist_wrapper").outerWidth());
            jQuery("#searchinput").css("width", (jQuery("#noteslist_wrapper").width() - 32) + "px");
        }
    });
    
    tinymce.init({
        selector: "#tinymcecontainer",
        setup: function(editor){
            editor.on('change', function(e){
                alert('set_note_contents:' + editing_note_local_id + ':' + editor.getContent());
            });
            editor.on('init', function(e){
                setTimeout(function(){
                    update_editor_height();
                    update_noteslist_height();
                }, 100);
            });
        },
        menubar: false,
        statusbar: false,
        toolbar: "bold italic underline strikethrough | alignleft aligncenter alignright alignjustify | formatselect fontselect fontsizeselect | cut copy paste | bullist numlist | outdent indent | blockquote | undo redo | removeformat subscript superscript"
    });
    
    jQuery("#note_title").change(function(event){
        alert("set_note_title:" + editing_note_local_id + ":" + jQuery("#note_title").val());
    });
 
    jQuery("#note_tags_selector")
        // don't navigate away from the field on tab when selecting an item
        .bind("keydown", function(event){
            if (event.keyCode === jQuery.ui.keyCode.TAB && jQuery(this).data("ui-autocomplete").menu.active){
                event.preventDefault();
            }
        })
        .bind("keypress", function(event){
            if (event.keyCode === jQuery.ui.keyCode.ENTER){
                var tag = jQuery(this).val();
                if (tag){
                    var selected_tags = new Array();
                    jQuery("#note_tags_list").find("span.tag").each(function(index){
                        selected_tags.push(jQuery(this).html());
                    });
                    if (selected_tags.indexOf(tag) == -1){
                        push_note_tag(tag);
                        jQuery(this).val("");
                        alert("add_note_tag:" + editing_note_local_id + ":" + tag);
                    }
                }
            }
        })
        .autocomplete({
            minLength: 1,
            source: function(request, response){
                var selected_tags = new Array();
                jQuery("#note_tags_list").find("span.tag").each(function(index){
                    selected_tags.push(jQuery(this).html());
                });
                var matches = jQuery.ui.autocomplete.filter(availableTags, request.term);
                var res = new Array();
                for (var i in matches){
                    if (selected_tags.indexOf(matches[i]) == -1){
                        res.push(matches[i]);
                    }
                }
                response(res);
            },
            focus: function(){
                // prevent value inserted on focus
                return false;
            },
            select: function(event, ui){
                push_note_tag(ui.item.value);
                jQuery(this).val("");
                alert("add_note_tag:" + editing_note_local_id + ":" + ui.item.value);
                return false;
            }
        });
    
    jQuery(window).resize(function(event){
        update_editor_height();
        update_noteslist_height();
    });
    
    resize_search_input();
});
