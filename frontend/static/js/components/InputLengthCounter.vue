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
        };
    },
    mounted() {
        this._target = document.querySelector(this.element);
        if (!this._target) {
            return console.warn(`${this.element} is not found.`);
        }

        if (this._target.tagName !== "TEXTAREA" && this._target.tagName !== "INPUT") {
            return console.warn(`${this.element} is not an input element.`);
        }

        this.counter = this._target.value.length;

        this._throttledHandler = throttle((e) => {
            this.counter = e.target.value.length;
        }, this.delay);

        this._target.addEventListener("keyup", this._throttledHandler);
    },
    beforeUnmount() {
        if (this._target) {
            this._target.removeEventListener("keyup", this._throttledHandler);
        }
    },
};
</script>
