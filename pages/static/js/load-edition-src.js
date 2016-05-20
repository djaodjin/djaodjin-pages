function AddScript(url, onload){
    var doc = window.document;

    var script   = doc.createElement("script");
    doc.body.appendChild(script);
    script.type  = "text/javascript";
    script.src   = url;
    script.onload = onload;
};

function loadNext(){
    if ( window.edition_sources.length > 0 ){
        var src = window.edition_sources.shift();
        AddScript(src, loadNext);
    }
}
loadNext();
