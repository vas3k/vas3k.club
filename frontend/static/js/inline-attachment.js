/**
 * Default configuration options
 *
 * @type {Object}
 **/
export const DEFAULT_SETTINGS = {
    /**
     * URL where the file will be sent
     */
    uploadUrl: "upload_attachment.php",

    /**
     * Which method will be used to send the file to the upload URL
     */
    uploadMethod: "POST",

    /**
     * Name in which the file will be placed
     */
    uploadFieldName: "file",

    /**
     * Extension which will be used when a file extension could not
     * be detected
     */
    defaultExtension: "png",

    /**
     * JSON field which refers to the uploaded file URL
     */
    jsonFieldName: "filename",

    /**
     * Allowed MIME types
     */
    allowedTypes: [
        "image/jpeg", "image/png", "image/jpg", "image/gif", "image/webp", "image/avif",
        "video/mp4", "video/webm", "video/quicktime",
    ],

    /**
     * Text which will be inserted when dropping or pasting a file.
     * Acts as a placeholder which will be replaced when the file is done with uploading
     */
    progressText: "![Uploading file...]()",

    /**
     * When a file has successfully been uploaded the progressText
     * will be replaced by the urlText, the {filename} tag will be replaced
     * by the filename that has been returned by the server
     */
    urlText: "![file]({filename})",
    filenameTag: "{filename}",

    /**
     * Text which will be used when uploading has failed
     */
    errorText: "Error uploading file",

    /**
     * Extra parameters which will be send when uploading a file
     */
    extraParams: {},

    /**
     * Extra headers which will be send when uploading a file
     */
    extraHeaders: {},

    /**
     * Before the file is send
     */
    beforeFileUpload: function () {
        return true;
    },

    /**
     * Triggers when a file is dropped or pasted
     */
    onFileReceived: function () {},

    /**
     * Custom upload handler
     *
     * @return {Boolean} when false is returned it will prevent default upload behavior
     */
    onFileUploadResponse: function () {
        return true;
    },

    /**
     * Custom error handler. Runs after removing the placeholder text and before the alert().
     * Return false from this function to prevent the alert dialog.
     *
     * @return {Boolean} when false is returned it will prevent default error behavior
     */
    onFileUploadError: function () {
        return true;
    },

    /**
     * When a file has successfully been uploaded
     */
    onFileUploaded: function () {},
};

/**
 * Initializes settings object
 * @param {Object} settings Custom settings
 * @returns {{settings}} Initialized settings
 */
export function initSettings(settings) {
    return {...DEFAULT_SETTINGS, ...settings}
}

/**
 * Uploads the blob
 *
 * @param  {Blob} file blob data received from event.dataTransfer object
 * @param {Object} settings for inline attachment
 * @param {(XMLHttpRequest) => {}} onSuccess upload handler
 * @param {(XMLHttpRequest) => {}} onFailure upload handler
 * @return {XMLHttpRequest} request object which sends the file
 */
export function uploadFile(file, settings, onSuccess = () => {}, onFailure = () => {}) {
    let formData = new FormData(),
        xhr = new XMLHttpRequest(),
        extension = settings.defaultExtension;

    if (typeof settings.setupFormData === "function") {
        settings.setupFormData(formData, file);
    }

    // Attach the file. If coming from clipboard, add a default filename (only works in Chrome for now)
    // http://stackoverflow.com/questions/6664967/how-to-give-a-blob-uploaded-as-formdata-a-file-name
    if (file.name) {
        const fileNameMatches = file.name.match(/\.(.+)$/);
        if (fileNameMatches) {
            extension = fileNameMatches[1];
        }
    }

    let remoteFilename = "image-" + Date.now() + "." + extension;
    if (typeof settings.remoteFilename === "function") {
        remoteFilename = settings.remoteFilename(file);
    }

    formData.append(settings.uploadFieldName, file, remoteFilename);

    // Append the extra parameters to the formdata
    if (typeof settings.extraParams === "object") {
        for (let key in settings.extraParams) {
            if (settings.extraParams.hasOwnProperty(key)) {
                formData.append(key, settings.extraParams[key]);
            }
        }
    }

    xhr.open("POST", settings.uploadUrl);

    // Add any available extra headers
    if (typeof settings.extraHeaders === "object") {
        for (let header in settings.extraHeaders) {
            if (settings.extraHeaders.hasOwnProperty(header)) {
                xhr.setRequestHeader(header, settings.extraHeaders[header]);
            }
        }
    }

    xhr.onload = function () {
        // If HTTP status is OK or Created
        if (xhr.status === 200 || xhr.status === 201) {
            onSuccess(xhr);
        } else {
            onFailure(xhr);
        }
    };

    xhr.onerror = function () {
        onFailure(xhr);
    };

    if (settings.beforeFileUpload(xhr) !== false) {
        xhr.send(formData);
    }
    return xhr;
}

    /**
     * Returns if the given file is allowed to handle
     *
     * @param {Blob} file
     * @param {Object} settings
     */
export function isFileAllowed(file, settings) {
    if (file.kind === "string") {
        return false;
    }
    if (settings.allowedTypes.indexOf("*") === 0) {
        return true;
    } else {
        return settings.allowedTypes.indexOf(file.type) >= 0;
    }
};


/*jslint newcap: true */
/*global XMLHttpRequest: false, FormData: false */
/*
 * Inline Text Attachment
 *
 * Author: Roy van Kaathoven
 * Contact: ik@royvankaathoven.nl
 */
(function (document, window) {
    "use strict";

    var inlineAttachment = function (options, instance) {
        this.settings = initSettings(options);
        this.editor = instance;
        this.lastValue = null;
    };

    /**
     * Will holds the available editors
     *
     * @type {Object}
     */
    inlineAttachment.editors = {};

    /**
     * Utility functions
     */
    inlineAttachment.util = {
        /**
         * Append a line of text at the bottom, ensuring there aren't unnecessary newlines
         *
         * @param {String} appended Current content
         * @param {String} previous Value which should be appended after the current content
         */
        appendInItsOwnLine: function (previous, appended) {
            return (previous + "\n\n[[D]]" + appended).replace(/(\n{2,})\[\[D\]\]/, "\n\n").replace(/^(\n*)/, "");
        },

        /**
         * Inserts the given value at the current cursor position of the textarea element
         *
         * @param  {HtmlElement} el
         * @param  {String} value Text which will be inserted at the cursor position
         */
        insertTextAtCursor: function (el, text) {
            var scrollPos = el.scrollTop,
                strPos = 0,
                browser = false,
                range;

            if (el.selectionStart || el.selectionStart === "0") {
                browser = "ff";
            } else if (document.selection) {
                browser = "ie";
            }

            if (browser === "ie") {
                el.focus();
                range = document.selection.createRange();
                range.moveStart("character", -el.value.length);
                strPos = range.text.length;
            } else if (browser === "ff") {
                strPos = el.selectionStart;
            }

            var front = el.value.substring(0, strPos);
            var back = el.value.substring(strPos, el.value.length);
            el.value = front + text + back;
            strPos = strPos + text.length;
            if (browser === "ie") {
                el.focus();
                range = document.selection.createRange();
                range.moveStart("character", -el.value.length);
                range.moveStart("character", strPos);
                range.moveEnd("character", 0);
                range.select();
            } else if (browser === "ff") {
                el.selectionStart = strPos;
                el.selectionEnd = strPos;
                el.focus();
            }
            el.scrollTop = scrollPos;
        },
    };

    /**
     * Handles upload response
     *
     * @param  {XMLHttpRequest} xhr
     * @return {Void}
     */
    inlineAttachment.prototype.onFileUploadResponse = function (xhr) {
        if (this.settings.onFileUploadResponse.call(this, xhr) !== false) {
            var result = JSON.parse(xhr.responseText),
                filename = result[this.settings.jsonFieldName];

            if (result && filename) {
                var newValue;
                if (typeof this.settings.urlText === "function") {
                    newValue = this.settings.urlText.call(this, filename, result);
                } else {
                    newValue = this.settings.urlText.replace(this.settings.filenameTag, filename);
                }
                var text = this.editor.getValue().replace(this.lastValue, newValue);
                this.editor.setValue(text);
                this.settings.onFileUploaded.call(this, filename);
            }
        }
    };

    /**
     * Called when a file has failed to upload
     *
     * @param  {XMLHttpRequest} xhr
     * @return {Void}
     */
    inlineAttachment.prototype.onFileUploadError = function (xhr) {
        if (this.settings.onFileUploadError.call(this, xhr) !== false) {
            var text = this.editor.getValue().replace(this.lastValue, this.settings.errorText);
            this.editor.setValue(text);
        }
    };

    /**
     * Called when a file has been inserted, either by drop or paste
     *
     * @param  {File} file
     * @return {Void}
     */
    inlineAttachment.prototype.onFileInserted = function (file) {
        if (this.settings.onFileReceived.call(this, file) !== false) {
            this.lastValue = this.settings.progressText;
            this.editor.insertValue(this.lastValue);
        }
    };

    /**
     * Called when a paste event occured
     * @param  {Event} e
     * @return {Boolean} if the event was handled
     */
    inlineAttachment.prototype.onPaste = function (e) {
        var result = false,
            clipboardData = e.clipboardData,
            items;

        if (typeof clipboardData === "object") {
            items = clipboardData.items || clipboardData.files || [];

            for (var i = 0; i < items.length; i++) {
                var item = items[i];
                if (isFileAllowed(item, this.settings)) {
                    result = true;
                    this.onFileInserted(item.getAsFile());
                    uploadFile(item.getAsFile(), this.settings, this.onFileUploadResponse.bind(this), this.onFileUploadError.bind(this));
                }
            }
        }

        if (result) {
            e.preventDefault();
        }

        return result;
    };

    /**
     * Called when a drop event occures
     * @param  {DragEvent} e
     * @return {Boolean} if the event was handled
     */
    inlineAttachment.prototype.onDrop = function (e) {
        var result = false;
        for (var i = 0; i < e.dataTransfer.files.length; i++) {
            var file = e.dataTransfer.files[i];
            if (isFileAllowed(file, this.settings)) {
                result = true;
                this.onFileInserted(file);
                uploadFile(file, this.settings, this.onFileUploadResponse.bind(this), this.onFileUploadError.bind(this));
            }
        }

        return result;
    };

    /**
     * Called when user selects a file
     * @param  {Event} e
     * @return {Boolean} whether or not the event was handled
     */
    inlineAttachment.prototype.onFileInputUpload = function (e) {
        let result = false;
        for (const file of e.target.files) {
            if (isFileAllowed(file, this.settings)) {
                result = true;
                this.onFileInserted(file);
                uploadFile(
                    file,
                    this.settings,
                    (xhr) => {
                        this.onFileUploadResponse.call(this, xhr);
                        this.editor.codeMirror.focus();
                    },
                    (xhr) => {
                        this.onFileUploadError.call(this, xhr);
                        this.editor.codeMirror.focus();
                    }
                );
            }
        }

        return result;
    };

    window.inlineAttachment = inlineAttachment;
})(document, window);
