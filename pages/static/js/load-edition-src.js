function AddScript(url, onload){
    var doc = window.document;

    var script   = doc.createElement("script");
    doc.body.appendChild(script);
    script.type  = "text/javascript";
    script.src   = url;
    script.onload = onload;

    // remove from the dom
    // doc.body.removeChild(doc.body.lastChild);
};

function loadNext(){
    if ( window.edition_sources.length > 0 ){
        var src = window.edition_sources.shift();
        console.log('loading ' + src);
        AddScript(src, loadNext);
    }
}
loadNext();
