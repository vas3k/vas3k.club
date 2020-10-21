<template>
    <a :href="url" class="comment-edit-button comment-button-hidden">
        <i class="fas fa-thumbtack"></i>
    </a>
</template>

<script>
export default {
    name: "PinAction",
    props: {
        url: {
            type: String,
            required: true,
        },
    },
};
</script>
