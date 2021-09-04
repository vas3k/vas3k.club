<template>
    <div class="mention-suggest" id="asdbg" v-show="isActive">
        {{ users }}
    </div>
</template>

<script>
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
    methods: {},
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
            const editor = e.detail[0];
            const { line: cursorLine, ch: cursorPosition } = editor.getCursor();
            const currentLine = editor.getLine(cursorLine);

            const {word: currentWord, wordPosition: currentWordPosition} = extractWordByCursorPosition(currentLine, cursorPosition);

            console.log("ASDBG handle", currentWord, editor.getCursor(), e);

            if (!currentWord || currentWord[0] !== "@") {
                this.isActive = false;
                return;
            }

            editor.addWidget({line: cursorLine, ch: currentWordPosition}, document.getElementById("asdbg"));
            this.isActive = true;
            this.users = [currentWord];
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
