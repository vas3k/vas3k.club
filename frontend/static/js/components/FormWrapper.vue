<template>
    <form :action="action" :method="method" @submit="submitAction" enctype="multipart/form-data">
        <slot></slot>
    </form>
</template>

<script>
export default {
    name: "FormWrapper",
    props: {
        action: String,
        method: String,
    },
    data() {
        return {
            isDisabled: false
        }
    },
    methods: {
        submitAction(ev) {
            if (this.isDisabled) {
                return ev.preventDefault();
            }
            this.isDisabled = true;
        }
    }
};
</script>
