

Vue.component('editables-list', {
    mixins: [
        itemListMixin
    ],
    data: function() {
        return {
            url: this.$urls.api_content,
            params: {
                o: '-created_at'
            },
            newItem: {title: ""},
            nbItemsPerRow: 2,
        }
    },
    methods: {
        create: function() {
            var vm = this;
            vm.reqPost(vm.url,{title: vm.newItem.title},
            function success(resp, textStatus, jqXHR) {
                var location = jqXHR.getResponseHeader('Location');
                if( location ) {
                    window.location = location;
                }
            });
            return false;
        },
    },
    computed: {
        nbRows: function() {
            var vm = this;
            const nbFullRows = Math.floor(
                vm.items.results.length / vm.nbItemsPerRow);
            return vm.items.results.length % vm.nbItemsPerRow == 0 ?
                nbFullRows : nbFullRows + 1;
        },
    },
    mounted: function(){
        this.get();
    }
});


Vue.component('editables-detail', {
    mixins: [
        itemMixin
    ],
    data: function() {
        return {
            item: this.$element ? this.$element : {},
            url: this.$urls.api_content,
            tags: [],
            isFollowing: false,
            nbFollowers: 0,
            isUpVote: 0,
            nbUpVotes: 0,
            comments: {count: 0, results: []},
            message: "",
            newItem: {title: ""},
        }
    },
    methods: {
        // functions available to editors
        create: function() {
            var vm = this;
            vm.reqPost(vm.url,{title: vm.newItem.title},
            function success(resp, textStatus, jqXHR) {
                var location = jqXHR.getResponseHeader('Location');
                if( location ) {
                    window.location = location;
                }
            });
            return false;
        },
        // functions available to readers
        submitFollow: function() {
            var vm = this;
            vm.reqPost(vm.isFollowing ? this.$urls.api_unfollow
                       : this.$urls.api_follow,
                function success(resp) {
                    vm.isFollowing = !vm.isFollowing;
                    vm.nbFollowers += vm.isFollowing ? 1 : -1;
            });
            return false;
        },
        submitVote: function() {
            var vm = this;
            vm.reqPost(vm.isUpVote ? this.$urls.api_downvote
                       : this.$urls.api_upvote,
                function success(resp) {
                    vm.isUpVote = !vm.isUpVote;
                    vm.nbUpVotes += vm.isUpVote ? 1 : -1;
            });
            return false;
        },
        submitComment: function() {
            var vm = this;
            vm.reqPost(this.$urls.api_comments, {
                text: vm.message},
            function success(resp) {
                vm.message = "";
                vm.comments.results.push(resp);
                vm.comments.count += 1;
            });
            return 0;
        },
    },
    mounted: function() {
        var vm = this;
        if( vm.item && vm.item.text ) {
            vm.itemLoaded = true;
        } else {
            vm.get(function success(resp) {
                vm.isFollowing = resp.data.is_following;
                vm.nbFollowers = resp.data.nb_followers;
                vm.isUpVote = resp.data.is_upvote;
                vm.nbUpVotes = resp.data.nb_upvotes;
                if( resp.data.extra && resp.data.extra.tags ) {
                    vm.tags = resp.data.extra.tags;
                }
            });
        }
        vm.reqGet(this.$urls.api_comments,
        function success(resp) {
            vm.comments = resp;
        }, function error() {
            // We might be looking at the page anonymously and the comments
            // will only load for authenticated users.
        });
    }
});


/** used to add uploaded assets
 */
Vue.component('explainer', {
    mixins: [
        httpRequestMixin
    ],
    data: function() {
        return {
            upload_start_url: this.$urls.api_asset_upload_start,
            upload_complete_url: this.$urls.api_asset_upload_complete,
            editMode: true,
            uploadInProgress: false,
            text: "",
            awsConfig: {
                mediaPrefix: "",
                acl: null,
            }
        }
    },
    props: [
        'disabled',
        'callbackArg',
        'collectedByPicture',
        'collectedByPrintableName',
        'collectedAtTime',
        'initText'
    ],
    methods: {
        // upload files
        _uploaderror: function(files, status, xhr) {
            this.showErrorMessages("error uploading file");
        },
        _uploadprogress: function(file, progress, bytesSent) {
            var progressBar = this.$el.querySelector(
                ".upload-progress .progress-bar");
            var progressWidth = (
                file.upload.bytesSent * 100 / file.upload.total);
            if( progressWidth < 10 ) progressWidth = 10;
            progressBar.style.width = progressWidth.toString() + '%';
        },
        _uploadfinished: function(files, resp, evt) {
            var vm = this;
            vm.uploadInProgress = false;
            var dataCompleteUrl = vm.upload_complete_url;
            if( dataCompleteUrl && dataCompleteUrl != vm.upload_start_url ) {
                vm.reqPost(dataCompleteUrl, resp, function(resp) {
                    vm.text += resp.location;
                })
            } else {
                vm.text += resp.location;
            }
        },
        isTagged: function(tag) {
            var vm = this;
            return vm.callbackArg.extra &&
                vm.callbackArg.extra.tags &&
                vm.callbackArg.extra.tags.includes(tag);
        },
        startUpload: function(xhr, uploadUrl, formData) {
            xhr.open("POST", uploadUrl, true);
            var headers = {
                "Accept": "application/json",
                "Cache-Control": "no-cache",
                "X-Requested-With": "XMLHttpRequest"
            };
            for (headerName in headers) {
                headerValue = headers[headerName];
                if (headerValue) {
                    xhr.setRequestHeader(headerName, headerValue);
                }
            }
            return xhr.send(formData);
        },
        uploadFiles: function(files) {
            var vm = this;

            var progressBar = vm.$el.querySelector(
                ".upload-progress .progress-bar");
            if( progressBar ) {
                progressBar.style.width = "10%";
            }
            vm.uploadInProgress = true;

            var xhr = new XMLHttpRequest();
            var formData = new FormData();

            if( !vm.upload_start_url ) {
                console.warn("[explainer] uploading assets will not work because 'url' is undefined.");
                return;
            }
            xhr.withCredentials = false;

            for( var idx = 0; idx < files.length; ++idx ) {
                files[idx].xhr = xhr;
            }
            var file = files[0];

            handleError = (function(_this) {
                return function() {
                    for( var jdx = 0; jdx < files.length; ++jdx ) {
                        var file = files[jdx];
                        _this._uploaderror(files, xhr.status, xhr);
                    }
                };
            })(this);
            updateProgress = (function(_this) {
                return function(evt) {
                    var progress = 0;
                    var allFilesFinished = false;
                    if( evt != null ) {
                        progress = 100 * evt.loaded / evt.total;
                        for( var jdx = 0; jdx < files.length; ++jdx ) {
                            var file = files[jdx];
                            file.upload = {
                                progress: progress,
                                total: evt.total,
                                bytesSent: evt.loaded
                            };
                        }
                    } else {
                        allFilesFinished = true;
                        progress = 100;
                        for( var jdx = 0; jdx < files.length; ++jdx ) {
                            var file = files[jdx];
                            if( !(file.upload.progress === 100 &&
                               file.upload.bytesSent === file.upload.total) ) {
                                allFilesFinished = false;
                            }
                            file.upload.progress = progress;
                            file.upload.bytesSent = file.upload.total;
                        }
                        if( allFilesFinished ) {
                            return;
                        }
                    }
                    for( var jdx = 0; jdx < files.length; ++jdx ) {
                        var file = files[jdx];
                        _this._uploadprogress(
                            file, progress, file.upload.bytesSent);
                    }
                };
            })(this);

            xhr.onload = (function(_this) {
                return function(evt) {
                   if( xhr.readyState !== 4 ) {
                        return;
                    }
                    var resp = xhr.responseText;
                    if( resp ) {
                        if( xhr.getResponseHeader("content-type") &&
                            ~xhr.getResponseHeader("content-type").indexOf(
                                "application/json") ) {
                            try {
                                resp = JSON.parse(resp);
                            } catch (_error) {
                                e = _error;
                                resp = "Invalid JSON response from server.";
                            }
                        }
                    } else {
                        resp = {location: xhr.responseURL + vm.awsConfig.mediaPrefix + file.name};
                    }
                    updateProgress();
                    if( !(200 <= xhr.status && xhr.status < 300) ) {
                        return handleError();
                    } else {
                        return _this._uploadfinished(files, resp, evt);
                    }
                };
            })(this);
            xhr.onerror = (function(_this) {
                return function() {
                    return handleError();
                };
            })(this);
            if( xhr.upload != null ) {
                xhr.upload.onprogress = updateProgress;
            } else {
                xhr.onprogress = updateProgress;
            }

            var uploadUrl = vm.upload_start_url;
            if( vm.upload_start_url.indexOf("/api/auth/") >= 0 ) {
                this.reqGet(vm.upload_start_url +
                    (vm.awsConfig.acl === "public-read" ? "?public=1" : ""),
                    function(data) {
                        var parser = document.createElement('a');
                        parser.href = data.location;
                        uploadUrl = parser.host + "/";
                        if( parser.protocol ) {
                            uploadUrl = parser.protocol + "//" + uploadUrl;
                        }
                        vm.awsConfig.mediaPrefix = parser.pathname;
                        if( vm.awsConfig.mediaPrefix === 'undefined'
                            || vm.awsConfig.mediaPrefix === null ) {
                            vm.awsConfig.mediaPrefix = "";
                        }
                        if( vm.awsConfig.mediaPrefix !== ""
                            && vm.awsConfig.mediaPrefix.match(/^\//)){
                            vm.awsConfig.mediaPrefix = vm.awsConfig.mediaPrefix.substring(1);
                        }
                        if( vm.awsConfig.mediaPrefix !== ""
                            && !vm.awsConfig.mediaPrefix.match(/\/$/)){
                            vm.awsConfig.mediaPrefix += "/";
                        }

                        formData.append(
                            "key", vm.awsConfig.mediaPrefix + file.name);
                        formData.append("policy", data.policy);
                        formData.append("x-amz-algorithm", "AWS4-HMAC-SHA256");
                        formData.append(
                            "x-amz-credential", data.x_amz_credential);
                        formData.append("x-amz-date", data.x_amz_date);
                        formData.append(
                            "x-amz-security-token", data.security_token);
                        formData.append(
                            "x-amz-signature", data.signature);
                        if( vm.awsConfig.acl ) {
                            formData.append("acl", vm.awsConfig.acl);
                        } else {
                            formData.append("acl", "private");
                        }
                        if( data.x_amz_server_side_encryption ) {
                            formData.append("x-amz-server-side-encryption",
                                            data.x_amz_server_side_encryption);
                        } else if( !vm.awsConfig.acl
                                   || vm.awsConfig.acl !== "public-read" ) {
                            formData.append("x-amz-server-side-encryption",
                                            "AES256");
                        }
                        var ext = file.name.slice(
                            file.name.lastIndexOf('.')).toLowerCase();
                        if( ext === ".jpg" ) {
                            formData.append("Content-Type", "image/jpeg");
                        } else if( ext === ".png" ) {
                            formData.append("Content-Type", "image/png");
                        } else if( ext === ".gif" ) {
                            formData.append("Content-Type", "image/gif");
                        } else if( ext === ".mp4" ) {
                            formData.append("Content-Type", "video/mp4");
                        } else {
                            formData.append(
                                "Content-Type", "binary/octet-stream");
                        }
                        formData.append("file", file);
                        // submitRequest
                        return vm.startUpload(xhr, uploadUrl, formData);
                    },
                    function(resp) {
                        vm.showErrorMessages(resp);
                    });
            } else {
                formData.append(
                    "csrfmiddlewaretoken", vm._getCSRFToken());
                formData.append("file", file);
                // submitRequest
                return vm.startUpload(xhr, uploadUrl, formData);
            }
        },
        processFile: function(file) {
            file.processing = true;
            file.status = Dropzone.UPLOADING;
            return this.uploadFiles([file]);
        },
        addFile: function(file) {
            file.upload = {
                progress: 0,
                total: file.size,
                bytesSent: 0
            };
            // assumes the file is accepted.
            return setTimeout(((function(_this) {
                return function() {
                    return _this.processFile(file);
                };
            })(this)), 0);
        },
        _addFilesFromItems: function(items) {
            for( var idx = 0; idx < items.length; ++idx ) {
                var item = items[idx];
                if( item.webkitGetAsEntry != null ) {
                    var entry = item.webkitGetAsEntry();
                    if( entry.isFile ) {
                        this.addFile(item.getAsFile());
                    }
                } else if( item.getAsFile != null ) {
                    if( (item.kind == null) || item.kind === "file" ) {
                        this.addFile(item.getAsFile());
                    }
                }
            }
        },
        _handleFiles: function(files) {
            for( var idx = 0; idx < files.length; ++idx ) {
                var file = files[idx];
                this.addFile(file);
            }
        },
        dropFile: function(evt) {
            var files, items;
            if( !evt.dataTransfer ) {
                return;
            }
            files = evt.dataTransfer.files;
            if( files.length ) {
                items = evt.dataTransfer.items;
                if( items && items.length && (
                    items[0].webkitGetAsEntry != null) ) {
                    this._addFilesFromItems(items);
                } else {
                    this._handleFiles(files);
                }
            }
        },
        uploadFile: function(evt) {
            var files = evt.target.files;
            if( files.length ) {
                this._handleFiles(files);
            }
        },
        // edit mode
        humanizeDate: function (at_time) {
            var dateTime = moment(at_time);
            return dateTime.format('MMMM Do YYYY');
        },
        humanizeTimeDelta: function (at_time, ends_at) {
            var cutOff = ends_at ? moment(ends_at) : moment();
            var dateTime = moment(at_time);
            var relative = "";
            if( dateTime <= cutOff ) {
                var timeAgoTemplate = "%(timedelta)s ago";
                relative = timeAgoTemplate.replace("%(timedelta)s",
                    moment.duration(cutOff.diff(dateTime)).humanize());
            } else {
                var timeLeftTemplate = "%(timedelta)s ago";
                relative = timeLeftTemplate.replace("%(timedelta)s",
                    moment.duration(dateTime.diff(cutOff)).humanize());
            }
            return relative;
        },
        toggleEditMode: function() {
            this.editMode = true;
        },
        saveText: function() {
            var vm = this;
            if( vm.text ) {
                vm.editMode = false;
            }
            vm.$emit('update-text', vm.text, vm.callbackArg);
        },
        fitToText: function() {
            var textarea = this.$el.querySelector('textarea');
            var updatedHeight = parseInt(textarea.style.height);
            if( isNaN(updatedHeight) ) {
                updatedHeight = textarea.scrollHeight;
            } else {
                updatedHeight = Math.max(updatedHeight, textarea.scrollHeight);
            }
            textarea.style.height = updatedHeight + 'px';
        },
        openLink: function(event) {
            var vm = this;
            var href = event.target.getAttribute('href');
            var pathname = event.target.pathname;
            if( href ) {
                if( href.startsWith(vm.upload_complete_url) ||
                    pathname.startsWith(vm.upload_complete_url) ) {
                    // handles both cases, `upload_complete_url` is a fully
                    // qualified URL or just a path.
                    vm.reqGet(pathname,
                    function(resp) {
                        window.open(resp.location, '_blank');
                    });
                } else {
                    window.open(href, '_blank');
                }
            }
        }
    },
    computed: {
        // display with active links
        textAsHtml: function() {
            var vm = this;
            if( !vm.text ) {
                return "";
            }
            var activeLinks = vm.text.replace(
                /(https?:\/\/\S+)/gi,
                '<a href="$1" target="_blank">external link</a>');
            if( vm.upload_complete_url ) {
                var reg = new RegExp(
                    '<a href="(' + vm.upload_complete_url +
                    '\/\\S+)" target="_blank">(external link)<\/a>', 'gi');
                activeLinks = activeLinks.replace(reg,
                    '<a href="$1">uploaded document</a>');
            }
            return activeLinks;
        }
    },
    mounted: function() {
        var vm = this;
        if( vm.collectedAtTime || vm.disabled ) {
            vm.editMode = false;
        }
        this.text = this.initText;
    },
});

Vue.component('viewing-timer', {
    mixins: [httpRequestMixin],
    props: {
        initialDuration: Number,
        rank: Number,
        sequence: String,
        user: String,
        pingInterval: {
            type: Number,
            default: 10
        }
    },
    data() {
        return {
            duration: this.initialDuration,
            timerInterval: null,
            updateInterval: null,
            pingUrl: this.$urls.api_enumerated_progress_user_detail,
        };
    },
    methods: {
        toggleTimers() {
            if (document.hidden) {
                clearInterval(this.timerInterval);
                clearInterval(this.updateInterval);
                this.timerInterval = this.updateInterval = null;
            } else {
                this.startTimers();
            }
        },
        startTimers() {
            this.timerInterval = this.timerInterval || setInterval(this.sendPing, this.pingInterval * 1000);
            this.updateInterval = this.updateInterval || setInterval(() => this.duration++, 1000);
        },
        sendPing() {
            this.reqPost(this.pingUrl, {}, resp => {},
                error => console.error(`Error sending ping: ${error.statusText}`));
        },
        clearTimers() {
            clearInterval(this.timerInterval);
            clearInterval(this.updateInterval);
        }
    },
    mounted() {
        this.toggleTimers();
        document.addEventListener('visibilitychange', this.toggleTimers);
        window.addEventListener('beforeunload', this.clearTimers);
    },
    beforeDestroy() {
        this.clearTimers();
        document.removeEventListener('visibilitychange', this.toggleTimers);
        window.removeEventListener('beforeunload', this.clearTimers);
    },
});



Vue.component('sequence-items', {
        mixins: [
        itemListMixin],
    data() {
        return {
            url: this.$urls.api_enumerated_progress_user_list
        };
    },
    mounted() {
        this.get();
    }
});


Vue.component('start-progress', {
    mixins: [httpRequestMixin],
    props: ['sequenceSlug', 'userUsername', 'elementRank'],
    data() {
        return {
            progressExists: false,
            progressUrl: this.$urls.api_enumerated_progress_list_create
        };
    },
    methods: {
        startProgress() {
            var postData = {
                sequence_slug: this.sequenceSlug,
                username: this.userUsername,
                rank: this.elementRank
            };
            this.reqPost(this.progressUrl, postData);
        }
    },
});

Vue.filter('formatDuration', function (value) {
    if (typeof value === 'string' && value.match(/^\d{2}:\d{2}:\d{2}(\.\d+)?$/)) {
        return value.split('.')[0];
    }

    let numericValue = (typeof value === 'string' && !isNaN(value)) ? parseFloat(value) : value;

    if (numericValue > 0 && !isNaN(numericValue)) {
        let hours = Math.floor(numericValue / 3600).toString().padStart(2, '0');
        let minutes = Math.floor((numericValue % 3600) / 60).toString().padStart(2, '0');
        let seconds = Math.floor(numericValue % 60).toString().padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    return value || '00:00:00';
});
