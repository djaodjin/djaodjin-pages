/* global $ angular Dropzone:true */


var app = angular.module("UploaderApp",[]);
var url = null;

app.config(function($interpolateProvider,$locationProvider,$httpProvider) {
   $interpolateProvider.startSymbol("[%");
   $interpolateProvider.endSymbol("%]");
   // $httpProvider.defaults.xsrfCookieName = "csrftoken";
   // $httpProvider.defaults.xsrfHeaderName = "X-CSRFToken";
});

app.directive("dropzone", function (csrf) {
    return function (scope, element, attrs) {
        var config, dropzone;

        config = scope[attrs.dropzone];

        // create a Dropzone for the element with the given options
        dropzone = new Dropzone(element[0], config.options);

        // bind the given event handlers
        dropzone.on("sending", function (file, xhr, formData) {
            formData.append("csrfmiddlewaretoken", csrf.csrf_token);
        });

        dropzone.on("drop", function (event) {
            var ans = confirm("Are you sure?");
            if (!ans){
                dropzone.emit("error");
            }
        });

        dropzone.on("error", function (file, response) {
            console.log(response.info);
        });

        dropzone.on("success", function (file, response) {
            console.log(response);
            scope.$apply(function(){
                var updatedPackage = $.grep(scope.uploadedPackagelist, function(el){
                    return el.id === response.id;
                })[0];
                if (updatedPackage){
                   var idx = scope.uploadedPackagelist.indexOf(updatedPackage);
                   scope.uploadedPackagelist[idx].updated_at = response.updated_at;
                }else{
                   scope.uploadedPackagelist.push(response);
                }
            });
      });
   };
});

app.controller("UploaderCtrl", function($scope, UploadedTemplateFactory, urls, csrf, $timeout){
   // $scope.uploadedPackagelist = [];
   $scope.dropzoneConfig = {
       "options": { // passed into the Dropzone constructor
         "url": urls.upload_template,
         "addRemoveLinks": true
       }};

   $scope.init = function(){

      UploadedTemplateFactory.getUploadedPackages(urls.get_uploaded_templates).success(function(data){
        console.log(data)
         $scope.uploadedPackagelist = data;
      });
   };

   $scope.init();
   // $scope.uploadedPackagelist[0].updated_at = "nullqsdfqsd";

   $scope.TogglePublication = function(idx){
      var template = $scope.uploadedPackagelist[idx];
      var data = {};
      if (template.is_active){
         data = {"is_active": false};
      }else{
         data = {"is_active": true};
      }
      UploadedTemplateFactory.UpdatePackage(urls.get_uploaded_templates, template.id, data).success(function(response){
         $scope.uploadedPackagelist[idx] = response;
      });
   };

});

app.factory("UploadedTemplateFactory", function($http){
    "use strict";
    var factory = {};

    factory.getUploadedPackages = function(url) {
        return $http.get(url);
    };

    factory.UpdatePackage = function(url, id, data){
        return $http.patch(url + id + "/", data);
    };

    return factory;
});
