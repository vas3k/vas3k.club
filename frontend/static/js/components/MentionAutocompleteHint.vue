<template>
    <div class="mention-autocomplete-hint" v-show="users.length > 0">
        <div
            v-for="(user, index) in users"
            v-bind:class="{ 'mention-autocomplete-hint__option--suggested': index === 0 }"
            v-on:click="onClick(user)"
            class="mention-autocomplete-hint__option"
        >
           {{ user.slug }}<span class="mention-autocomplete-hint__option-fullName">{{ user.fullName }}</span>
        </div>
    </div>
</template>

<style>
    .mention-autocomplete-hint {
        min-width: 100px;
        box-shadow: 0 4px 8px -2px rgb(9 30 66 / 25%), 0 0 0 1px rgb(9 30 66 / 8%);
        border-radius: 3px;
    }

    .mention-autocomplete-hint__option {
        font-weight: 400;
        padding: 0 5px;
    }

    .mention-autocomplete-hint__option span {
        font-weight: 200;
        color: #737373;
        padding-left: 10px;
    }

    .mention-autocomplete-hint__option:hover {
        cursor: pointer;
        background: #4C98D5;
        color: #FFF;
    }

    .mention-autocomplete-hint__option:hover span {
        color: #FFF;
    }

    .mention-autocomplete-hint__option--suggested {
        background: #4C98D5;
        color: #FFF;
    }

    .mention-autocomplete-hint__option--suggested span {
        color: #FFF;
    }
</style>

<script>
export default {
    data: function () {
        return {
            users: [],
            onClick: () => {}
        }
    }
};
</script>
