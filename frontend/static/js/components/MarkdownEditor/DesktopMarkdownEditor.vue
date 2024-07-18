<template>
    <div class="comment-markdown-editor">
        <textarea
            required
            name="text"
            maxlength="20000"
            placeholder="Напишите ответ..."
            class="markdown-editor-invisible"
            ref="textarea"
        >
        </textarea>
        <div
            class="mention-autocomplete-hint"
            v-show="users.length > 0"
            :style="{
                top: autocomplete ? autocomplete.top + 'px' : 0,
                left: autocomplete ? autocomplete.left + 'px' : 0,
            }"
        >
            <div
                v-for="(user, index) in users.slice(0, 5)"
                :class="{ 'mention-autocomplete-hint__option--suggested': index === selectedUserIndex }"
                @click="insertSuggestion(user)"
                class="mention-autocomplete-hint__option"
            >
                {{ user.slug }}<span class="mention-autocomplete-hint__option-full_name">{{ user.full_name }}</span>
            </div>
        </div>
    </div>
</template>

<script>
import { throttle } from "../../common/utils";
import {
    createMarkdownEditor,
    handleFormSubmissionShortcuts,
    imageUploadOptions
} from "../../common/markdown-editor";

export default {
    props: {
        value: {
            type: String
        },
        focused: {
            type: Boolean
        }
    },
    mounted() {
        const fileInputEl = this.$el.closest("form").querySelector("input[type=file][name=attach-image]")
        if (fileInputEl) {
            fileInputEl.accept = imageUploadOptions.allowedTypes.join()
        }

        this.editor = createMarkdownEditor(this.$refs["textarea"], {
            toolbar: false,
        });

        this.editor.element.form.addEventListener("keydown", handleFormSubmissionShortcuts);
        inlineAttachment.editors.codemirror4.attach(this.editor.codemirror, { ...imageUploadOptions, fileInputEl });

        this.editor.codemirror.on("change", this.handleAutocompleteHintTrigger);
        this.editor.codemirror.on("change", this.handleSuggest);
        this.editor.codemirror.on("blur", this.emitCustomBlur);

        this.populateCacheWithCommentAuthors();

        this.editor.value(this.value);
        this.focusIfNeeded(this.focused);
    },
    watch: {
        users: function (val) {
            if (val.length > 0) {
                this.selectedUserIndex = 0;
                document.addEventListener("keydown", this.handleKeydown, true);
            } else {
                document.removeEventListener("keydown", this.handleKeydown, true);
            }
        },
        focused: function (value) {
            this.focusIfNeeded(value);
        },
        value: function (value) {
            this.editor.value(value);
            this.focusIfNeeded(true);
        }
    },
    data() {
        return {
            selectedUserIndex: null,
            editor: null,
            users: [],
            autocomplete: null,
            autocompleteCache: {
                samples: {},
                users: {},
            },
        };
    },
    methods: {
        handleKeydown(event) {
            if (
                event.code !== "ArrowDown" &&
                event.code !== "ArrowUp" &&
                event.code !== "Tab" &&
                event.code !== "Enter"
            ) {
                return;
            }

            event.preventDefault();

            if (event.code === "Enter" || event.code === "Tab") {
                this.insertSuggestion(this.users[this.selectedUserIndex]);
            } else if (event.code === "ArrowDown" && this.selectedUserIndex + 1 < this.users.length) {
                this.selectedUserIndex += 1;
            } else if (event.code === "ArrowUp" && this.selectedUserIndex - 1 >= 0) {
                this.selectedUserIndex -= 1;
            }
        },
        triggersAutocomplete(cm, event) {
            const eventText = event.text.join("");
            if (eventText !== "@") {
                return false;
            }

            const prevSymbol = cm.getRange(
                {
                    line: event.from.line,
                    ch: event.from.ch - 1,
                },
                event.from
            );

            return prevSymbol.trim() === "";
        },
        insertSuggestion(user) {
            if (!this.autocomplete) {
                return;
            }

            const { line, ch } = this.autocomplete;
            const cursor = this.editor.codemirror.getCursor();

            this.resetAutocomplete();

            this.editor.codemirror.replaceRange(
                `${user.slug} `,
                {
                    line,
                    ch: ch + 1,
                },
                {
                    line: cursor.line,
                    ch: cursor.ch,
                }
            );
        },
        populateCacheWithCommentAuthors: function () {
            document.querySelectorAll(".comment-header-author-name").forEach((linkEl) => {
                const slug = linkEl.dataset.authorSlug;
                const full_name = linkEl.innerText;

                if (!slug || !full_name) {
                    return;
                }

                this.autocompleteCache.users[slug] = {
                    slug,
                    full_name,
                };
            });
        },
        fetchAutocompleteSuggestions: throttle(function (sample) {
            fetch(`/search/users.json?prefix=${sample}`)
                .then((res) => {
                    if (!res.url.includes(`prefix=${sample}`)) {
                        return { users: [] };
                    }

                    return res.json();
                })
                .then((data) => {
                    if (!this.autocomplete) {
                        return;
                    }

                    this.users = data.users;

                    this.autocompleteCache.samples[sample] = this.users;

                    this.users.forEach((user) => {
                        this.autocompleteCache.users[user.slug] = user;
                    });
                });
        }, 600),
        handleAutocompleteHintTrigger(cm, event) {
            if (this.autocomplete) {
                const eventText = event.text.join("");
                const eventRemoved = event.removed.join("");
                if ([" ", "@"].includes(eventText) || eventRemoved.includes("@")) {
                    this.resetAutocomplete();
                }

                return;
            }

            if (event.origin === "+input" && this.triggersAutocomplete(cm, event)) {
                const cursorCoords = this.editor.codemirror.cursorCoords(false, "local");

                this.autocomplete = {
                    ...event.from,
                    top: cursorCoords.top + 36, // first line offset
                    left: Math.floor(cursorCoords.left),
                };
            }
        },
        handleSuggest(cm, event) {
            if (!this.autocomplete) {
                return;
            }

            const value = this.editor.value();

            const line = value.split("\n")[this.autocomplete.line];

            const cursor = this.editor.codemirror.getCursor();
            const sample = line.substring(this.autocomplete.ch, cursor.ch).substring(1);

            // For short samples lookup users directly
            if (sample.length < 3) {
                const cacheKeys = Object.keys(this.autocompleteCache.users).filter((k) => k.includes(sample));
                if (cacheKeys) {
                    this.users = cacheKeys.map((k) => this.autocompleteCache.users[k]);
                }

                return;
            }

            // For longer samples lookup a whole cached sample
            const cachedSample = this.autocompleteCache.samples[sample];
            if (cachedSample) {
                this.users = cachedSample;

                return;
            }

            this.fetchAutocompleteSuggestions(sample);
        },
        resetAutocomplete() {
            this.autocomplete = null;
            this.users = [];
            this.editor.codemirror.focus();
        },
        focusIfNeeded: function(shouldFocus) {
            this.$nextTick(() => {
                if (shouldFocus) {
                    this.editor.codemirror.focus();
                    this.editor.codemirror.execCommand("goDocEnd");
                }
            });
        },
        emitCustomBlur: function (editor) {
            this.$emit("blur", editor.getValue());
        }
    },
};
</script>

<style>
.comment-markdown-editor .CodeMirror {
    resize: none;
}

.comment-markdown-editor .EasyMDEContainer .CodeMirror {
    border-radius: 0;
    box-shadow: none;
    border: none;
}

</style>
