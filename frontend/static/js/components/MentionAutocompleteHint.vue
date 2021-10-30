<template>
    <div>
        <div v-for="user in users">
            {{ user }}
        </div>
    </div>
</template>

<script>

export default {
    name: "MentionAutocompleteHint",
    data: function () {
        return {
            users: []
        }
    },
    mounted() {
        console.log('mounted');
    }
};
</script>
