<template>
    <a class="user-expertise-delete" @click.prevent="deleteExpertise">[x]</a>
</template>

<script>
import ClubApi from "../../common/api.service";

export default {
    name: "DeleteUserExpertiseWindow",
    props: {
        expertise: {
            type: String,
            required: true,
        },
        url: {
            type: String,
            required: true,
        },
    },
    methods: {
        deleteExpertise(event) {
            return ClubApi.ajaxify(this.url, (data) => {
                if (data.status === "deleted") {
                    document.getElementById("expertise-" + data.expertise.expertise).outerHTML = "";
                }
            });  
        },
    },
};
</script>
