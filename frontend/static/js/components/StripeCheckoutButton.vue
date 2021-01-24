<template>
    <button @click="pay">
        <slot></slot>
    </button>
</template>

<script>
import { loadStripe } from "@stripe/stripe-js";

export default {
    name: "StripeCheckoutButton",
    props: {
        publicKey: {
            type: String,
            required: true,
        },
        sessionId: {
            type: String,
            required: true,
        },
    },
    async created() {
        this.stripe = await loadStripe(this.publicKey);
    },
    methods: {
        pay() {
            this.stripe
                .redirectToCheckout({
                    sessionId: this.sessionId,
                })
                .then(function (result) {
                    alert(result.error.message);
                });
        },
    },
};
</script>
