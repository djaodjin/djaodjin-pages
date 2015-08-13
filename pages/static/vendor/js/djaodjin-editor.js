/* jshint multistr: true */

(function ($) {
    "use strict";
    var mardownToolHtml = "";
    var preventclick = false;

    $("body").on("mousedown", "#tool_markdown", function(event){
        event.preventDefault();
        var $target = $(event.target);
        if ($target.attr("id") === "title_h3"){
            $("#input_editor").selection("insert", {text: "###", mode: "before"}).selection("insert", {text: "", mode: "after"});
        }else if($target.attr("id") === "title_h4"){
            $("#input_editor").selection("insert", {text: "####", mode: "before"}).selection("insert", {text: "", mode: "after"});
        }else if($target.attr("id") === "bold"){
            $("#input_editor").selection("insert", {text: "**", mode: "before"}).selection("insert", {text: "**", mode: "after"});
        }else if($target.attr("id") === "list_ul"){
            $("#input_editor").selection("insert", {text: "* ", mode: "before"}).selection("insert", {text: "", mode: "after"});
        }else if($target.attr("id") === "link"){
            var text = $("#input_editor").selection();
            if (text.indexOf("http://") >= 0){
                $("#input_editor").selection("insert", {text: "[" + text + "](", mode: "before"}).selection("insert", {text: ")", mode: "after"});
            }else{
                $("#input_editor").selection("insert", {text: "[http://" + text + "](http://", mode: "before"}).selection("insert", {text: ")", mode: "after"});
            }
        }else if($target.attr("id") === "italic"){
            $("#input_editor").selection("insert", {text: "*", mode: "before"}).selection("insert", {text: "*", mode: "after"});
        }
    });

    function Editor(element, options){
        var _this = this;
        _this.el = element;
        _this.$el = $(element);
        _this.options = options;
        _this.init();
        return _this;
    }

    Editor.prototype = {
        init: function(){
            var self = this;
            self.getProperties();
            self.$el.on("click", function(){
                self.toggleInput();
            });

            if (self.options.prevent_change_editor_selectors !== ""){
                $(document).on("mousedown", self.options.prevent_change_editor_selectors, function(event){
                    event.stopPropagation();
                    preventclick = true;
                });
            }

        },

        getId: function() {
            var self = this;
            var slug = self.$el.attr(self.options.unique_identifier);
            if( !slug ) {
                slug = self.$el.parents(
                    "[" + self.options.unique_identifier + "]").attr(
                        self.options.unique_identifier);
            }
            if( !slug ) {
                slug = "undefined";
            }
            return slug;
        },

        getOriginText: function(){
            var self = this;
            self.originText = $.trim(self.$el.text());
            return self.originText;
        },

        getElementProperties: function(){
            var self = this;
            return self.$el;
        },

        getProperties: function(){
            var self = this;
            self.classElement = self.$el.attr("class");
            var element = self.getElementProperties();
            self.cssVar = {
                "font-size": element.css("font-size"),
                "line-height": element.css("line-height"),
                "height": parseInt(element.css("height").split("px")) + (parseInt(element.css("line-height").split("px")) - parseInt(element.css("font-size").split("px"))) + "px",
                "margin-top": element.css("margin-top"),
                "font-family": element.css("font-family"),
                "font-weight": element.css("font-weight"),
                "text-align": element.css("text-align"),
                "padding-top": -(parseInt(element.css("line-height").split("px")) - parseInt(element.css("font-size").split("px"))) + "px",
                "color": element.css("color"),
                "width": element.css("width")
            };
        },

        inputEditable: "<div class=\"input-group\" id=\"editable_section\"><textarea class=\"form-control editor\" id=\"input_editor\" spellcheck=\"false\"></textarea></div>",

        toogleStartOptional: function(){
            return true;
        },

        toogleEndOptional: function(){
            return true;
        },

        toggleInput: function(){
            var self = this;
            if (!$("#input_editor").length){

            self.toogleStartOptional();
            var originText = self.getOriginText();
            self.$el.replaceWith(self.inputEditable);
            if (self.options.enableMarkdownMedia){
                console.log(jQuery.ui)
                $("textarea").droppable({
                    drop: function(event, ui){
                        var droppable = $(this);
                        var draggable = ui.draggable;
                        droppable.focus();
                        droppable.selection("insert", {
                            text: "![Alt text](" + draggable.attr("src") + ")",
                            mode: "before"
                        });
                        $(ui.helper).remove();
                        $("#input_editor").trigger("autosize.resize");
                    }
                });
            }
            $("#input_editor").focus();
            $("#input_editor").val(originText);
            $("#input_editor").css(self.cssVar);
            $("#input_editor").autosize({append:""});
            $("#input_editor").on("blur", function(event){
                if (!preventclick){
                    self.saveEdition(event);
                }else{
                    $("#input_editor").focus();
                    preventclick = false;
                }
            });

            $("#input_editor").on("keyup", function(){
                self.checkInput();
            });
            }else{
                return false;
            }
        },

        getSavedText: function(){
            return $("#input_editor").val();
        },

        getDisplayedText: function(){
            var self = this;
            return self.getSavedText();
        },

        checkInput: function(){
            var self = this;
            if (self.getDisplayedText() === ""){
                $("#input_editor").focus().attr("placeholder", self.options.empty_input);
                return false;
            }else{
                return true;
            }
        },

        saveEdition: function(){
            var self = this;
            var savedText = self.getSavedText();

            var displayedText = self.getDisplayedText();

            if (!self.checkInput()){
                return false;
            }

            var data = {};
            var method = "PUT";
            if (self.$el.attr("data-key")){
                data[self.$el.attr("data-key")] = $.trim(savedText);
                method = "PATCH";
            } else {
                data = {
                    slug: self.getId(),
                    text: $.trim(savedText),
                    old_text: self.originText,
                    tag: self.$el.prop("tagName")
                };
            }
            self.$el.html(displayedText);
            self.toogleEndOptional();
            $("#editable_section").replaceWith(self.$el);
            if (!self.options.base_url){
                if ($(".error-label").length > 0){
                    $(".error-label").remove();
                }
                $("body").append("<div class=\"error-label\">No base_url option provided. Please update your script to use save edition.</div>");
                return false;
            }else{
                $.ajax({
                    method: method,
                    async: false,
                    url: self.options.base_url + self.getId() + "/",
                    data: data,
                    success: function(response) {
                        self.options.onSuccess(self, response);
                    },
                    error: self.options.onError
                });
            }
            self.init();
        }
    };

    function CurrencyEditor(element, options){
        var _this = this;
        _this.el = element;
        _this.$el = $(element);
        _this.options = options;
        _this.init();
        return _this;
    }

    CurrencyEditor.prototype = $.extend({}, Editor.prototype, {
        getSavedText: function(){
            var enteredValue =  $("#input_editor").val();
            var amount = parseInt(parseFloat(enteredValue.replace(/[^0-9\.]+/g, "")) * 100);
            return amount;
        },

        getDisplayedText: function(){
            var self = this;
            var defaultCurrency = "$";
            if (self.$el.data("currency")){
                defaultCurrency = self.$el.data("currency");
            }

            var amount = self.getSavedText();
            var text = defaultCurrency + String((amount / 100).toFixed(2));

            return text;
        }
    });

    function MarkdownEditor(element, options){
        var _this = this;
        _this.el = element;
        _this.$el = $(element);
        _this.options = options;
        _this.init();
        return _this;
    }

    MarkdownEditor.prototype = $.extend({}, Editor.prototype, {
        toogleStartOptional: function(){
            var self = this;
            mardownToolHtml = "<div id=\"tool_markdown\" class=\"" + self.options.container_tool_class + "\">\
                    <button type=\"button\" class=\"" + self.options.btn_tool_class + "\" id=\"title_h3\">H3</button>\
                    <button type=\"button\" class=\"" + self.options.btn_tool_class + "\" id=\"title_h4\">H4</button>\
                    <button type=\"button\" class=\"" + self.options.btn_tool_class + "\" id=\"bold\"><strong>B</strong></button>\
                    <button type=\"button\" class=\"" + self.options.btn_tool_class + "\" id=\"italic\"><em>I</em></button>\
                    <button type=\"button\" class=\"" + self.options.btn_tool_class + "\" id=\"list_ul\">List</button>\
                    <button type=\"button\" class=\"" + self.options.btn_tool_class + "\" id=\"link\">Link</button></div>";
            $("body").prepend(mardownToolHtml);
            $("#tool_markdown").css({
                "top": (self.$el.offset().top - 45) + "px",
                "left": self.$el.offset().left + "px"
            });
        },

        toogleEndOptional: function(){
            $("#tool_markdown").remove();
        },

        getElementProperties: function(){
            var self = this;
            if (self.$el.prop("tagName") === "DIV"){
                if (self.$el.children("p").length > 0){
                    return self.$el.children("p");
                }else{
                    return $("p");
                }
            }else{
                return self.$el;
            }
        },

        getOriginText: function(){
            var self = this;
            self.originText = "";
            if (self.options.base_url){
                $.ajax({
                    method: "GET",
                    async: false,
                    url: self.options.base_url + self.getId() + "/",
                    success: function(data){
                        if (self.$el.attr("data-key")){
                            self.originText = data[self.$el.attr("data-key")];
                        }else{
                            self.originText = data.text;
                        }
                    },
                    error: function(){
                        self.originText = $.trim(self.$el.text());
                    }
                });
            }
            return self.originText;
        },

        getDisplayedText: function(){
            var self = this;
            var convert = new Markdown.getSanitizingConverter().makeHtml;
            return convert(self.getSavedText()).replace("<img ", "<img style=\"max-width:100%\" ");
        }
    });

    $.fn.editor = function(options, custom){
        var opts = $.extend( {}, $.fn.editor.defaults, options );
        return this.each(function() {
            if (!$.data($(this), "editor")) {
                if ($(this).hasClass("edit-markdown")){
                    $.data($(this), "editor", new MarkdownEditor($(this), opts));
                }else if ($(this).hasClass("edit-currency")){
                    $.data($(this), "editor", new CurrencyEditor($(this), opts));
                }else{
                    $.data($(this), "editor", new Editor($(this), opts));
                }
            }
        });
    };

    $.fn.editor.defaults = {
        base_url: null, // Url to send request to server
        enable_markdown: true,
        enable_upload : false,
        img_upload_url:'',
        empty_input:'Please enter text...',
        prevent_change_editor_selectors: '',
        unique_identifier: 'id',
        container_tool_class:'',
        btn_tool_class: '',
        enableMarkdownMedia: true,
        onSuccess: function(){
            return true;
        },
        onError: function(){
            return true;
        }
    };

}( jQuery ));
