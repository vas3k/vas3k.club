<template>
    <div class="mention-suggest" id="asdbg" v-show="isActive">
        <div v-for="user in users" v-on:click="insertSuggestion(user)">
            @{{ user }}
        </div>
    </div>
</template>

<script>
import ClubApi from "../common/api.service";
import { findCodeMirrorEditorByTextarea } from "../common/utils";

export default {
    name: "MentionSuggest",
    props: {
        element: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            isActive: false,
            users: [],
        };
    },
    methods: {
        insertSuggestion: function (suggestion) {
            const editor = findCodeMirrorEditorByTextarea(this.$target);
            const { line: currentLineIdx, ch: cursorPosition } = editor.getCursor();
            const currentLineValue = editor.getLine(currentLineIdx);

            const {word: currentWord, wordPosition: currentWordPosition} =
                extractWordByCursorPosition(currentLineValue, cursorPosition);

            // console.log({line: currentLineIdx, ch: currentWordPosition});
            // console.log({line: currentLineIdx, ch: currentWordPosition + currentWord.length});
            // console.log(editor);
            editor.replaceRange(
                "@" + suggestion,
                {line: currentLineIdx, ch: currentWordPosition},  // from
                {line: currentLineIdx, ch: currentWordPosition + currentWord.length},  // to
            );
            editor.focus();
        },
        // getAttachedEditor: function () {
        //     return this.$target.nextElementSibling.CodeMirror ||
        //            this.$target.nextElementSibling.querySelector(".CodeMirror").CodeMirror;
        // },
    },
    created() {
        console.log("ASDBG created");
    },
    mounted() {
        this.$target = document.querySelector(this.element);
        if (!this.$target) {
            return console.warn(`${this.element} is not found.`);
        }

        if (!(this.$target instanceof HTMLTextAreaElement) && !(this.$target instanceof HTMLInputElement)) {
            return console.warn(`${this.element} is not an input element.`);
        }

        this.throttledCursorActivityHandler = throttle((e) => {
            const editor = findCodeMirrorEditorByTextarea(this.$target);
            const { line: currentLineIdx, ch: cursorPosition } = editor.getCursor();
            const currentLineValue = editor.getLine(currentLineIdx);

            const { word: currentWord, wordPosition: currentWordPosition } =
                extractWordByCursorPosition(currentLineValue, cursorPosition);

            if (!currentWord || currentWord[0] !== "@") {
                this.isActive = false;
                return;
            }

            editor.addWidget({line: currentLineIdx, ch: currentWordPosition}, document.getElementById("asdbg"));
            this.isActive = true;

            if (currentWord.length <= 1) {
                return;
            }

            fetch(`/users/suggest/?is_ajax=true&sample=${currentWord.substr(1)}`)
                .then(res => res.json())
                .then((data) => this.users = data.suggested_users);
        }, 300);


        this.$target.addEventListener("cursorActivity", this.throttledCursorActivityHandler);
        console.log("ASDBG mounted", this.$target);
    },
};

function extractWordByCursorPosition(str, cursorPosition) {
    const words = str.split(" ");
    if (words.length === 0) {
        return {word: "", wordPosition: 0};
    }

    let currentPosition = 0;
    for (let i = 0; i < words.length; i++) {
        if (currentPosition + words[i].length >= cursorPosition) {
            return {word: words[i], wordPosition: currentPosition};
        }

        currentPosition += words[i].length + 1;  // + space character
    }

    const lastWord = words[words.length - 1];
    return {word: lastWord, wordPosition: str.length - lastWord.length};
}

function throttle(fn, wait) {
    let inThrottle, lastFn, lastTime;
    return function () {
        const context = this,
            args = arguments;
        if (!inThrottle) {
            fn.apply(context, args);
            lastTime = Date.now();
            inThrottle = true;
        } else {
            clearTimeout(lastFn);
            lastFn = setTimeout(function () {
                if (Date.now() - lastTime >= wait) {
                    fn.apply(context, args);
                    lastTime = Date.now();
                }
            }, Math.max(wait - (Date.now() - lastTime), 0));
        }
    };
}
</script>
