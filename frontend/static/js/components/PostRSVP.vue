<template>
    <span>
        <label class="button event-rsvp-button">
            <span v-if="isActive" class="event-rsvp-button-icon"><i class="fas fa-check-square"></i></span>
            <span v-else class="event-rsvp-button-icon"><i class="far fa-square"></i></span>

            <span v-if="isActive" class="event-rsvp-button-text">Я в деле!</span>
            <span v-else class="event-rsvp-button-text">Я приду</span>

            <input type="checkbox" v-model="isActive" @change.prevent="toggle" style="display: none;" />
        </label>
    </span>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
    name: "PostRSVP",
    props: {
        isActiveByDefault: {
            type: Boolean,
            default() {
                return false;
            },
        },
        url: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            isActive: this.isActiveByDefault,
            isLoading: false,
        };
    },
    methods: {
        toggle() {
            this.isLoading = true;
            return ClubApi.ajaxify(this.url, (data) => {
                this.isLoading = false;

                if (data.status === "created") {
                    this.isActive = true;
                }

                if (data.status === "deleted") {
                    this.isActive = false;
                }
            });
        },
    },
};
</script>
