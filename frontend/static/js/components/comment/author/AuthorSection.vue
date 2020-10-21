<template>
    <div class="user user-small">
        <span class="user-avatar">
            <a :href="profileUrl">
                <span class="avatar" :style="{ backgroundImage: `url(${avatarUrl})` }"></span>
            </a>
        </span>
        <span class="user-info">
            <a :href="profileUrl">
                <span class="user-name">{{ displayName }}</span>
                <span class="user-position" v-if="description">, {{ description }}</span>
                <author-hat v-if="hat" :hat="hat"></author-hat>
            </a>
        </span>
        <span class="user-footer">
            <slot name="footer"></slot>
        </span>
    </div>
</template>

<script>
import AuthorHat from "./AuthorHat.vue";

export default {
    name: "AuthorSection",
    components: { AuthorHat },
    props: {
        avatarUrl: {
            type: String,
            required: true,
        },
        profileUrl: {
            type: String,
            required: true,
        },
        displayName: {
            type: String,
            required: true,
        },
        description: String,
        hat: Object,
    },
};
</script>
