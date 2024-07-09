<template>
    <div class="comment-markdown-editor">
        <textarea
            required
            name="text"
            maxlength="20000"
            placeholder="Напишите ответ..."
            v-bind:value="value"
            v-on:blur="handleBlur"
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
        handleBlur: function (event) {
            this.$emit("blur", this.$refs["textarea"].value)
        },
        focusTextareaIfNeeded: function(shouldFocus) {
            this.$nextTick(() => {
                shouldFocus && this.$refs["textarea"].focus();
            })
        }
    }
}
</script>
