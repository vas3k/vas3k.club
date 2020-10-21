<template>
    <a :href="url" class="comment-edit-button comment-button-hidden" @click="confirm('Удаляем?')">
        <i class="fas fa-trash"></i>
    </a>
</template>

<script>
export default {
    name: "DeleteAction",
    props: {
        url: {
            type: String,
            required: true,
        },
    },
};
</script>
