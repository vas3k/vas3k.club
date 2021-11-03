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

<style>
.mention-autocomplete-hint {
    min-width: 100px;
    box-shadow: 0 4px 8px -2px rgb(9 30 66 / 25%), 0 0 0 1px rgb(9 30 66 / 8%);
    border-radius: 3px;
}

.mention-autocomplete-hint__option {
    font-weight: 400;
    padding: 0 5px;
}

.mention-autocomplete-hint__option span {
    font-weight: 200;
    color: #737373;
    padding-left: 10px;
}

.mention-autocomplete-hint__option:hover {
    cursor: pointer;
    background: #4c98d5;
    color: #fff;
}

.mention-autocomplete-hint__option:hover span {
    color: #fff;
}

.mention-autocomplete-hint__option--suggested {
    background: #4c98d5;
    color: #fff;
}

.mention-autocomplete-hint__option--suggested span {
    color: #fff;
}
</style>

<script>
import { createMarkdownEditor, isMobile, throttle } from "../common/utils.js";

export default {
    mounted() {
        if (isMobile()) {
            return;
        }

        const $markdownElementDiv = this.$el.children[0];
        const $hintElementDiv = this.$refs["mention-autocomplete-hint"];

        this.editor = createMarkdownEditor($markdownElementDiv, {
            toolbar: false,
        });

        this.editor.codemirror.on("change", (cm, event) => {
            if (!this.autocomplete && event.origin === "+input" && this.triggersAutocomplete(cm, event)) {
                this.autocomplete = event.from;

                this.editor.codemirror.addWidget(
                    {
                        ...this.autocomplete,
                        ch: this.autocomplete.ch + 1,
                    },
                    $hintElementDiv
                );
            }

            if (!this.autocomplete) {
                return;
            }

            let sample = cm.getRange(this.autocomplete, event.from) + event.text.join("");
            if (sample[0] !== "@") {
                this.users = [];
                this.autocomplete = null;

                return;
            }

            this.fetchAutocompleteSuggestions(sample.substr(1));
        });
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

            this.editor.codemirror.replaceRange(
                `${user.slug} `,
                {
                    line: this.autocomplete.line,
                    ch: this.autocomplete.ch + 1,
                },
                {
                    line: this.autocomplete.line,
                    ch: this.autocomplete.ch + user.slug.length + 1,
                }
            );

            this.editor.codemirror.focus();

            this.users = [];
            this.autocomplete = null;
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
                    console.log("data", data);
                    if (!this.autocomplete) {
                        return;
                    }

                    this.users = data.suggested_users;
                });
        }, 600),
    },
};
</script>
