self.on("click", function (node, data) {
    // transform to owncloud+*:// URL that will be handled by the URL handler.
    window.location.href = "owncloud+"+node.href;
});
