<template>
    <span :class="{ bad: counter < minLength, good: counter >= minLength }">
        <slot></slot>
        <span v-if="counter < minLength" key="poop">💩</span>
        <span v-if="counter >= minLength && counter < minLength + 100" key="ok">🙂</span>
        <span v-if="counter >= minLength + 100 && counter < minLength + 300" key="cool">😎</span>
        <span v-if="counter >= minLength + 300 && counter < minLength + 500" key="awesome">🚀</span>
        <span v-if="counter >= minLength + 500" key="star">💎🚀👍</span>
        {{ counter !== null ? counter : "-" }}
        <span v-if="counter < minLength">&nbsp;&#47;&nbsp;{{ minLength }}</span>
    </span>
</template>

<script>
import { throttle } from "../common/utils.js";

export default {
    name: "InputLengthCounter",
    props: {
        minLength: {
            type: Number,
            default: 0,
        },
        delay: {
            type: Number,
            default: 300,
        },
        element: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            counter: null,
            $target: null,
        };
    },
    mounted() {
        this.$target = document.querySelector(this.element);
        if (!this.$target) {
            return console.warn(`${this.element} is not found.`);
        }

        if (!(this.$target instanceof HTMLTextAreaElement) && !(this.$target instanceof HTMLInputElement)) {
            return console.warn(`${this.element} is not an input element.`);
        }

        this.counter = this.$target.value.length;

        this.throttledCounterHandler = throttle((e) => {
            this.counter = e.target.value.length;
        }, this.delay);

        this.$target.addEventListener("keyup", this.throttledCounterHandler);
    },
    beforeDestroy() {
        if (this.$target) {
            this.$target.removeEventListener("keyup", this.throttledCounterHandler);
        }
    },
};

</script>
