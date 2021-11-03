<template>
    <div class="mention-autocomplete-hint" v-show="users.length > 0">
        <div
            v-for="(user, index) in users"
            :class="{ 'mention-autocomplete-hint__option--suggested': index === selectedUserIndex }"
            @click="onAutocomplete(user)"
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
    background: #4c98d5;
    color: #fff;
}

.mention-autocomplete-hint__option:hover span {
    color: #fff;
}

.mention-autocomplete-hint__option--suggested {
    background: #4c98d5;
    color: #fff;
}

.mention-autocomplete-hint__option--suggested span {
    color: #fff;
}
</style>

<script>
export default {
    watch: {
        users: function (val, oldVal) {
            if (val.length > 0) {
                this.selectedUserIndex = 0;
                document.addEventListener("keydown", this.handleKeydown, true);
            } else {
                document.removeEventListener("keydown", this.handleKeydown);
            }
        },
    },
    data() {
        return {
            selectedUserIndex: null,
            users: [],
            onAutocomplete: () => {},
        };
    },
    methods: {
        handleKeydown(event) {
            if (
                event.code !== "ArrowDown" &&
                event.code !== "ArrowUp" &&
                event.code !== "Tab" &&
                event.code !== "Enter"
            ) {
                return;
            }

            event.preventDefault();

            if (event.code === "Enter" || event.code === "Tab") {
                this.onAutocomplete(this.users[this.selectedUserIndex]);
            } else if (event.code === "ArrowDown" && this.selectedUserIndex + 1 < this.users.length) {
                this.selectedUserIndex += 1;
            } else if (event.code === "ArrowUp" && this.selectedUserIndex - 1 >= 0) {
                this.selectedUserIndex -= 1;
            }
        },
    },
};
</script>
