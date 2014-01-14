jQuery.widget("custom.searchbox", {
 
    options: {
    },
 
    _create: function(){
        this._search_filters_animation_running = false;
        this._search_filters_next_state = null;
        
        this._search_filters_bubbles_wrapper = jQuery("<span class='search_filters_bubbles_wrapper'></span>");
        this._search_filters_bubbles_wrapper.appendTo(this.element);
        
        this._input = jQuery("<input/>");
        this._input.appendTo(this.element);
        
        this._search_filters_box = jQuery("<div class='search_filters_box'></div>");
        this._search_filters_box.appendTo(this.element);
        
        this._build_search_filters_contains_box();
        this._build_search_filters_source_box();
        this._build_search_filters_created_box();
        this._build_search_filters_modified_box();
        
        this._search_filters_box.accordion({
            collapsible: true,
            active: false
        });
        
        this.element.bind("focusin", this._on_focusin.bind(this));
        this.element.bind("focusout", this._on_focusout.bind(this));
    },
    
    _on_focusin: function(){
        this._toggle_search_filters(true);
    },
    
    _on_focusout: function(){
        this._toggle_search_filters(false);
    },
    
    _toggle_search_filters: function(visible){
        this._search_filters_next_state = (visible ? "visible" : "hidden");
        setTimeout(this._apply_search_filters_state.bind(this), 100);
    },
    
    _apply_search_filters_state: function(){
        if (this._search_filters_animation_running){
            setTimeout(this._apply_search_filters_state.bind(this), 100);
            return;
        }
        if ((this._search_filters_next_state == "visible" && !this._search_filters_box.is(":visible")) || (this._search_filters_next_state == "hidden" && this._search_filters_box.is(":visible"))){
            this._search_filters_animation_running = true;
            this._search_filters_box.slideToggle({
                done: function(){
                    this._search_filters_animation_running = false;
                }.bind(this)
            });
        }
    },
    
    _build_search_filters_contains_box: function(){
        var container = jQuery("<div></div>");
        var items = [
            {key: "images", label: _("Images")},
            {key: "audio", label: _("Audio")},
            {key: "video", label: _("Video")},
            {key: "pdf", label: _("PDF")},
            {key: "encrypted_text", label: _("Encrypted text")},
            {key: "ink", label: _("Ink")},
            {key: "attachments", label: _("Attachments")}
        ];
        
        var filter_span, filter_input, filter_label;
        for (var i in items){
            filter_span = jQuery("<span></span>");
            filter_input = jQuery("<input type='checkbox' id='filter_contains_" + items[i].key + "'/>");
            filter_input.appendTo(filter_span);
            filter_label = jQuery("<label for='filter_contains_" + items[i].key + "'>" + items[i].label + "</label>");
            filter_label.appendTo(filter_span);
            filter_span.appendTo(container);
        }
        
        jQuery("<h3>" + _("Contains") + "</h3>").appendTo(this._search_filters_box);
        container.appendTo(this._search_filters_box);
    },
    
    _build_search_filters_source_box: function(){
        var container = jQuery("<div></div>");
        
        jQuery("<h3>" + _("Source") + "</h3>").appendTo(this._search_filters_box);
        container.appendTo(this._search_filters_box);
    },
    
    _build_search_filters_created_box: function(){
        var container = jQuery("<div></div>");
        
        jQuery("<label for='filter_created_after'>" + _("Since : ") + "</label>").appendTo(container);
        jQuery("<input class='date_input' id='filter_created_after' />").appendTo(container);
        jQuery("<br/>").appendTo(container);
        jQuery("<label for='filter_created_before'>" + _("Before : ") + "</label>").appendTo(container);
        jQuery("<input class='date_input' id='filter_created_before' />").appendTo(container);
        
        jQuery("<h3>" + _("Created") + "</h3>").appendTo(this._search_filters_box);
        container.appendTo(this._search_filters_box);
    },
    
    _build_search_filters_modified_box: function(){
        var container = jQuery("<div></div>");
        
        jQuery("<label for='filter_modified_after'>" + _("Since : ") + "</label>").appendTo(container);
        jQuery("<input class='date_input' id='filter_modified_after' />").appendTo(container);
        jQuery("<br/>").appendTo(container);
        jQuery("<label for='filter_modified_before'>" + _("Before : ") + "</label>").appendTo(container);
        jQuery("<input class='date_input' id='filter_modified_before' />").appendTo(container);
        
        jQuery("<h3>" + _("Modified") + "</h3>").appendTo(this._search_filters_box);
        container.appendTo(this._search_filters_box);
    }
});
