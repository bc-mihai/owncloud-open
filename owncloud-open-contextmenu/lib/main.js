var self = require("sdk/self");
var cm = require("sdk/context-menu");

var item = cm.Item({
    label: "Open ownCloud URL",
    image: self.data.url("owncloud.png"),
    context: cm.SelectorContext("a[href]"),
    contentScriptFile: self.data.url("contextmenu.js")
});



