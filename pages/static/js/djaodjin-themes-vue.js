Vue.component('theme-update', {
    mixins: [
        httpRequestMixin
    ],
    data: function() {
        return {
            url: (this.$urls.rules && this.$urls.rules.api_detail) ?
                this.$urls.rules.api_detail : null,
            showEditTools: false
        }
    },
    methods: {
        get: function() {
            var vm = this;
            vm.reqGet(vm.url, function(res){
                vm.showEditTools = res.show_edit_tools;
            });
        },
        reset: function() {
            var vm = this;
            vm.reqDelete(this.$urls.pages.api_themes,
            function(resp) {
                if( resp.detail ) {
                    showMessages([resp.detail], "success");
                }
            });
        },
        save: function(){
            var vm = this;
            vm.reqPut(vm.url, {
                    show_edit_tools: vm.showEditTools,
                },
                function(){
                    location.reload();
                }
            );
        },
    },
    mounted: function(){
        var vm = this;
        if( vm.url ) {
            vm.get();
        }
    },
});
