var editing_note_local_id = null;

function clear_all(){
}

function edit_note(local_id){
    editing_note_local_id = null;
    tinymce.get("tinymcecontainer").setContent("");
    jQuery("#note_title").val("")
    
    alert("edit_note:" + local_id);
}

function set_editing_note(note_data){
    jQuery("#note_title").val(jQuery("<div/>").html(note_data.title).text());
    tinymce.get("tinymcecontainer").setContent(note_data.contents);
    
    editing_note_local_id = note_data.local_id;
}

function update_notes_list(notes_list){
    var link;
    
    jQuery("#noteslist").html("");
    for (var i in notes_list){
        link = jQuery("<a href='#note_" + notes_list[i].local_id + "'>" + notes_list[i].title + "</a>");
        link.click(function(event){
            edit_note(jQuery(this).attr("href").substring(6));
            event.preventDefault();
        });
        link.appendTo("#noteslist");
    }
}

function update_tags_list(tags_list){
    jQuery("#tagslist").tree("loadData", tags_list);
}

function update_notebooks_list(notebooks_list){
    jQuery("#notebookslist").tree("loadData", notebooks_list);
}

function update_editor_height(){
    jQuery("#tinymcecontainer_ifr").css("height", (jQuery("#noteeditor_inside_wrapper").height() - jQuery("#tinymcecontainer_ifr").offset().top) + "px");
}

function update_noteslist_height(){
    jQuery("#noteslist").css("height", (jQuery("#noteslist_wrapper").height() - jQuery("#noteslist").offset().top) + "px");
}


jQuery(document).ready(function(){
    jQuery("#notebookslist").tree({
        data: []
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
    
    jQuery(window).resize(function(event){
        update_editor_height();
        update_noteslist_height();
    });
});
