<template>
    <div class="comment-markdown-editor">
        <slot></slot>
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
import { isMobile, throttle } from "../common/utils";
import { createMarkdownEditor, handleFormSubmissionShortcuts, imageUploadOptions } from "../common/markdown-editor";

export default {
    mounted() {
        if (isMobile()) {
            return;
        }

        const $markdownElementDiv = this.$el.children[0];
        this.editor = createMarkdownEditor($markdownElementDiv, {
            toolbar: false,
        });

        this.editor.element.form.addEventListener("keydown", handleFormSubmissionShortcuts);
        inlineAttachment.editors.codemirror4.attach(this.editor.codemirror, imageUploadOptions);

        this.editor.codemirror.on("change", this.handleAutocompleteHintTrigger);
        this.editor.codemirror.on("change", this.handleSuggest);

        this.populateCacheWithCommentAuthors();
    },
    watch: {
        users: function (val, oldVal) {
            if (val.length > 0) {
                this.selectedUserIndex = 0;
                document.addEventListener("keydown", this.handleKeydown, true);
            } else {
                document.removeEventListener("keydown", this.handleKeydown, true);
            }
        },
    },
    data() {
        return {
            selectedUserIndex: null,
            postSlug: null,
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
    },
};
</script>
