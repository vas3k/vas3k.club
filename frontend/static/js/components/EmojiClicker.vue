<template>
    <div class="emoji-clicker" @click="handleClick">
        {{ emojis[currentEmojiIndex] }}
    </div>
</template>

<script>
const EMOJIS = ["✈️", "🏖️", "🏔️", "🏝️"];

export default {
    name: "EmojiClicker",
    data() {
        return {
            emojis: EMOJIS,
            currentEmojiIndex: 0
        };
    },
    methods: {
        triggerAnimation(event) {
            setTimeout(() => {
                event.target.classList.remove("bounce-enter-active");
            }, 500);
            event.target.classList.add("bounce-enter-active");
        },
        handleClick(event) {
            if (this.currentEmojiIndex < this.emojis.length - 1) {
                this.triggerAnimation(event);
                this.currentEmojiIndex++;
            } else {
                this.triggerAnimation(event);
                this.currentEmojiIndex = 0; // Reset to initial state
            }
        }
    }
};
</script>
