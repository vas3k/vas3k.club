/*jslint newcap: true */
/*global inlineAttachment: false */
/**
 * CodeMirror version for inlineAttachment
 *
 * Call inlineAttachment.attach(editor) to attach to a codemirror instance
 */
(function () {
    "use strict";

    const codeMirrorEditor = function (instance) {
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

    /**
     * Attach InlineAttachment to CodeMirror
     *
     * @param {CodeMirror} codeMirror
     */
    codeMirrorEditor.attach = function (codeMirror, options) {
        options = options || {};

        var editor = new codeMirrorEditor(codeMirror),
            inlineattach = new inlineAttachment(options, editor),
            el = codeMirror.getWrapperElement();

        el.addEventListener(
            "paste",
            function (e) {
                inlineattach.onPaste(e);
            },
            false
        );

        codeMirror.setOption("onDragEvent", function (data, e) {
            if (e.type === "drop") {
                e.stopPropagation();
                e.preventDefault();
                return inlineattach.onDrop(e);
            }
        });
    };

    const codeMirrorEditor4 = function(instance) {
        codeMirrorEditor.call(this, instance);
    };

    codeMirrorEditor4.attach = function (codeMirror, options, fileInputEl) {
        options = options || {};

        const editor = new codeMirrorEditor(codeMirror);
        const inlineAttach = new inlineAttachment(options, editor);
        const el = codeMirror.getWrapperElement();

        el.addEventListener(
            "paste",
            function (e) {
                inlineAttach.onPaste(e);
            },
            false
        );

        codeMirror.on("drop", function (data, e) {
            if (inlineAttach.onDrop(e)) {
                e.stopPropagation();
                e.preventDefault();
                return true;
            } else {
                return false;
            }
        });

        fileInputEl && fileInputEl.addEventListener("change", (e) => inlineAttach.onFileInputChange(e));
    };

    inlineAttachment.editors.codemirror4 = codeMirrorEditor4;
})();
