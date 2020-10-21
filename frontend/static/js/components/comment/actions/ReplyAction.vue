<template>
    <span class="comment-reply-button" v-on:click="$emit('reply', commentId, username, true)">
        <i class="fas fa-reply"></i>&nbsp;ответить
    </span>
</template>

<script>
export default {
    name: "ReplyAction",
    props: {
        commentId: {
            type: String,
            required: true,
        },
        username: {
            type: String,
            required: true,
        },
    },
};
</script>
