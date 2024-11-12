<template>
    <div class="comment-markdown-editor">
        <textarea
            required
            name="text"
            maxlength="20000"
            placeholder="Напишите ответ..."
            ref="textarea"
            :value="value"
            @input="growTextareaIfNeeded"
            @blur="emitCustomBlur"
        >
        </textarea>
    </div>
</template>

<script>
import { imageUploadOptions } from "../../common/markdown-editor";
import { initSettings, isFileAllowed, uploadFile } from "../../inline-attachment";

export default {
    props: {
        value: {
            type: String
        },
        focused: {
            type: Boolean
        }
    },
    mounted: function() {
        this.attachImageListener();
        this.focusTextareaIfNeeded(this.focused);
        this.growTextareaIfNeeded();

    },
    watch: {
        focused: function (value) {
            this.focusTextareaIfNeeded(value);
        }
    },
    methods: {
        emitCustomBlur: function () {
            this.$emit("blur", this.$refs["textarea"].value);
        },
        focusTextareaIfNeeded: function(shouldFocus) {
            this.$nextTick(() => {
                shouldFocus && this.$refs["textarea"].focus();
            });
        },
        growTextareaIfNeeded: function() {
            this.$refs["textarea"].style.height = 'auto';
            this.$refs["textarea"].style.height = this.$refs["textarea"].scrollHeight + 'px';
        },
        attachImageListener: function() {
            // we reach outside the current component to get the filepicker. It is not a good practice,
            // but we cannot move the text ownership to form because the editor is used in many different contexts
            const fileInput = this.$el.closest("form").querySelector("input[type=file][name=attach-image]");
            if (!fileInput) return;

            const settings = initSettings(imageUploadOptions);
            const textarea = this.$refs["textarea"]

            fileInput.accept = settings.allowedTypes.join();
            fileInput.addEventListener("change", (e) => {
                e.stopPropagation();
                e.preventDefault();

                for (const file of e.target.files) {
                    if (!isFileAllowed(file, settings)) continue

                    textarea.value = appendText(textarea.value, settings.progressText);
                    uploadFile(
                        file,
                        settings,
                        (xhr) => {
                            const result = JSON.parse(xhr.responseText);
                            const filename = result[settings.jsonFieldName];

                            if (filename) {
                                const urlMarkdown = settings.urlText.replace(settings.filenameTag, filename);
                                textarea.value = replaceProgressTextOrAppend(textarea.value, settings.progressText, urlMarkdown);
                                this.focusTextareaIfNeeded(true);
                            }
                        },
                        () => {
                            textarea.value = replaceProgressTextOrAppend(textarea.value, settings.progressText, settings.errorText);
                            this.focusTextareaIfNeeded(true);
                        }
                    );
                }
            })
        }
    }
}

function appendText(target, text) {
    return target.length > 0 ? `${target} ${text}` : text
}

function replaceProgressTextOrAppend(target, progressText, replacement) {
    if (target.includes(progressText)) {
        return target.replace(progressText, replacement);
    } else {
        return appendText(target, replacement)
    }
}
</script>

<style scoped>
.comment-markdown-editor {
    line-height: 0;
}

textarea {
    resize: none;
    box-shadow: none;
    border-radius: 0;

    &:focus {
        box-shadow: none;
    }
}

</style>
