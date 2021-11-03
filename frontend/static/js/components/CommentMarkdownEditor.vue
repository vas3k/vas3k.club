<template>
    <div>
        <slot></slot>
        <div class="mention-autocomplete-hint" v-show="users.length > 0" ref="mention-autocomplete-hint">
            <div
                v-for="(user, index) in users"
                :class="{ 'mention-autocomplete-hint__option--suggested': index === selectedUserIndex }"
                @click="insertSuggestion(user)"
                class="mention-autocomplete-hint__option"
            >
                {{ user.slug }}<span class="mention-autocomplete-hint__option-fullName">{{ user.fullName }}</span>
            </div>
        </div>
    </div>
</template>

<script>
import {
    createMarkdownEditor,
    isMobile,
    throttle,
    handleFormSubmissionShortcuts,
    imageUploadOptions,
} from "../common/utils.js";

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
    },
    watch: {
        users: function (val, oldVal) {
            if (val.length > 0) {
                this.selectedUserIndex = 0;
                document.addEventListener("keydown", this.handleKeydown, true);
            } else {
                document.removeEventListener("keydown", this.handleKeydown);
            }
        },
    },
    data() {
        return {
            selectedUserIndex: null,
            users: [],
            autocompleteCache: {},
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

            const cursor = this.editor.codemirror.getCursor();

            this.editor.codemirror.replaceRange(
                `${user.slug} `,
                {
                    line: this.autocomplete.line,
                    ch: this.autocomplete.ch + 1,
                },
                {
                    line: cursor.line,
                    ch: cursor.ch,
                }
            );

            this.resetAutocomplete();
        },
        fetchAutocompleteSuggestions: throttle(function (sample) {
            fetch(`/users/suggest/?is_ajax=true&sample=${sample}`)
                .then((res) => {
                    if (!res.url.includes(`sample=${sample}`)) {
                        return { suggested_users: [] };
                    }

                    return res.json();
                })
                .then((data) => {
                    if (!this.autocomplete) {
                        return;
                    }

                    this.users = data.suggested_users;
                    this.autocompleteCache[sample] = this.users;
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
                this.autocomplete = event.from;

                this.editor.codemirror.addWidget(
                    {
                        ...this.autocomplete,
                        ch: this.autocomplete.ch + 1,
                    },
                    this.$refs["mention-autocomplete-hint"]
                );
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

            console.log("sample", sample, this.autocompleteCache);

            if (sample.length < 3 || this.autocompleteCache[sample]) {
                // TODO: Populate autocompleteCache with post users
                this.users = this.autocompleteCache[sample] || [];

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
