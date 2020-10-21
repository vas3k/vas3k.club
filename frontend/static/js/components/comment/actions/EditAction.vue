<template>
    <a :href="url" class="comment-edit-button comment-button-hidden">
        <i class="fas fa-edit"></i>
    </a>
</template>

<script>
export default {
    name: "EditAction",
    props: {
        url: {
            type: String,
            required: true,
        },
    },
};
</script>
