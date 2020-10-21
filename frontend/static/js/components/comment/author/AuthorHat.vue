<template>
    <span class="hat" :style="{ backgroundColor: hat.color }">
        <span v-if="hat.icon" class="hat-icon" :style="{ backgroundImage: `url(${hat.icon})` }"></span>
        <span class="hat-title">{{ hat.title }}</span>
    </span>
</template>

<script>
export default {
    name: "AuthorHat",
    props: {
        hat: {
            type: Object,
            required: true,
        },
    },
};
</script>
