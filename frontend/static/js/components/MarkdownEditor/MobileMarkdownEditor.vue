<template>
    <div class="comment-markdown-editor">
        <textarea
            required
            name="text"
            maxlength="20000"
            placeholder="Напишите ответ..."
            v-bind:value="value"
            v-on:input="$emit('input', $event.target.value)"
            v-on:blur="$emit('blur', $event)"
            ref="textarea"
        >
        </textarea>
    </div>
</template>

<script>
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
            this.focusTextareaIfNeeded(this.focused)
    },
    watch: {
        focused: function (value) {
            this.focusTextareaIfNeeded(value)
        }
    },
    methods: {
        focusTextareaIfNeeded: function(shouldFocus) {
            this.$nextTick(() => {
                shouldFocus && this.$refs["textarea"].focus();
            })
        }
    }
}
</script>
