/* global $ ace document:true */

function initCodeEditors(api_sources, iframe) {
    "use strict";

    var templates = (typeof templateNames !== "undefined" ) ?
        templateNames : [];
    if( typeof iframe !== "undefined" ) {
        templates = iframe.contentWindow.templateNames || [];
    }
    if( templates.length > 0 ) {
        for( var idx = 0; idx < templates.length; ++idx ) {
            $("#code-editor [role='tablist']").append("<li" + (idx === 0 ? " class=\"active\"" : "") + "><a href=\"#tab-" + idx + "\" data-toggle=\"tab\">" + templates[idx].name + "</a></li>");
            $("#code-editor .tab-content").append("<div id=\"tab-" + idx + "\" class=\"tab-pane" + (idx === 0 ? " active" : "") + " role=\"tabpanel\" style=\"width:100%;height:100%;\"><div class=\"content\" data-content=\"" + templates[idx].name + "\" style=\"width:100%;min-height:100%;\"></div></div>");
        }
    } else {
        $("#code-editor .tab-content").append("<div>No editable templates</div>");
    }
    $("#code-editor .content").djtemplates({
        api_source_code: api_sources,
        iframe_view: iframe
    });
}

(function ($) {
    "use strict";

    /** Template editor
        <div id="#_editor_"></div>
     */
    function TemplateEditor(el, options){
        this.element = el;
        this.$element = $(el);
        this.options = options;
        this.activeFile = "";
        this.init();
    }

    TemplateEditor.prototype = {
        init: function () {
            var self = this;
            self.$element.on("pages.loadresources", function(event) {
                self.loadSource();
            });

            // load ace and extensions
            self.editor = ace.edit(self.element);
            self.editor.setTheme("ace/theme/monokai");
            self.editor.setOption({
                enableEmmet: true,
                enableBasicAutocompletion: true,
                enableSnippets: true,
                enableLiveAutocompletion: false
            });
        },

        loadSource: function(){
            var self = this;
            var path = self.$element.attr("data-content");
            $.ajax({
                url: self.options.api_source_code + path,
                method: "GET",
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(resp){
                    self.editor.setValue(resp.text);
                    var modelist = ace.require("ace/ext/modelist");
                    var mode = modelist.getModeForPath(resp.path).mode;
                    self.editor.getSession().setMode(mode);
                    self.editor.focus();
                    self.editor.gotoLine(0);
                    self.editor.on("change", $.debounce( 250, function() {
                        self.saveSource();
                    }));
                },
                error: function(resp) {
                    showErrorMessages(resp);
                }
            });
        },

        saveSource: function(){
            var self = this;
            var path = self.$element.attr("data-content");
            $.ajax({
                url: self.options.api_source_code + path,
                method: "PUT",
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                data: JSON.stringify({
                    path: path, text: self.editor.getValue()}),
                beforeSend: function(xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", getMetaCSRFToken());
                },
                success: function(){
                    // reload content
                    if ( self.options.iframe_view ){
                        self.options.iframe_view.src = self.options.iframe_view.src;
                    }
                },
                error: function(resp) {
                    showErrorMessages(resp);
                }
            });
        }

    };

    $.fn.djtemplates = function(options) {
        var opts = $.extend( {}, $.fn.djtemplates.defaults, options );
        return this.each(function() {
            if (!$.data($(this), "djtemplates")) {
                $.data($(this), "djtemplates", new TemplateEditor(this, opts));
            }
        });
    };

    $.fn.djtemplates.defaults = {
        api_source_code: "/api/source"
    };

})(jQuery);
