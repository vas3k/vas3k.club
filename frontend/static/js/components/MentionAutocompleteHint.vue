<template>
    <div>
        <div v-for="user in users">
            {{ user }}
        </div>
    </div>
</template>

<script>

export default {
    data: function () {
        return {
            users: []
        }
    }
};
</script>
