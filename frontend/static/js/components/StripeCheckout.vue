<template>
    <button @click="pay">Плоти</button>
</template>

<script>
import {loadStripe} from "@stripe/stripe-js";

export default {
    name: "StripeCheckout",
    props: {
        sessionId: {
            type: String,
            required: true,
        },
    },
    async created() {
        this.stripe = await loadStripe("pk_test_51H5W9dKgJMaF2rHt3v6m1ap2UQHAyrymYG5ALmPtXdQBc2eQz7JXFYcHvsVrseqEMcWNA8Gy7WRM6sVsMcR2GEay00wi5EAYw0");
    },
    methods: {
        pay() {
            this.stripe.redirectToCheckout({
                sessionId: this.sessionId,
            }).then(function (result) {
                alert(result.error.message);
            });
        },
    },
};
</script>
