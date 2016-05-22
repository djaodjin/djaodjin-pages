/* global $ ace document:true */

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
            self.$element.on("djtemplates.loadresources", function(event) {
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
