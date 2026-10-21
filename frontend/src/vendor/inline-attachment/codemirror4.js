/*jslint newcap: true */
/*global inlineAttachment: false */
/**
 * CodeMirror version for inlineAttachment
 *
 * Call inlineAttachment.attach(editor) to attach to a codemirror instance
 */
(function () {
    "use strict";

    var codeMirrorEditor = function (instance) {
        if (!instance.getWrapperElement) {
            throw "Invalid CodeMirror object given";
        }

        this.codeMirror = instance;
    };

    codeMirrorEditor.prototype.getValue = function () {
        return this.codeMirror.getValue();
    };

    codeMirrorEditor.prototype.insertValue = function (val) {
        this.codeMirror.replaceSelection(val);
    };

    codeMirrorEditor.prototype.setValue = function (val) {
        var cursor = this.codeMirror.getCursor();
        this.codeMirror.setValue(val);
        this.codeMirror.setCursor(cursor);
    };

    const codeMirrorEditor4 = {};

    codeMirrorEditor4.attach = function (codeMirror, options) {
        options = options || {};

        var editor = new codeMirrorEditor(codeMirror),
            inlineattach = new inlineAttachment(options, editor),
            el = codeMirror.getWrapperElement();

        const fileInput = options.fileInputEl || el.closest("form").querySelector("input[type=file]");
        const paste = (event) => inlineattach.onPaste(event);
        const drop = (data, event) => {
            if (inlineattach.onDrop(event)) {
                event.stopPropagation();
                event.preventDefault();
            }
        };
        const upload = (event) => {
            event.stopPropagation();
            event.preventDefault();
            inlineattach.onFileInputUpload(event);
            event.target.value = "";
        };
        el.addEventListener("paste", paste);
        codeMirror.on("drop", drop);
        fileInput?.addEventListener("change", upload);

        return () => {
            el.removeEventListener("paste", paste);
            codeMirror.off("drop", drop);
            fileInput?.removeEventListener("change", upload);
        };
    };

    inlineAttachment.editors.codemirror4 = codeMirrorEditor4;
})();
