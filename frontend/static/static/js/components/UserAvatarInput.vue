<template>
    <label class="user-avatar-input" :for="inputId">
        <div class="avatar profile-user-avatar" :style="avatarStyle" />
    </label>
</template>
<script>
const FILE_READER_STATE = {
    EMPTY: 0,
    LOADING: 1,
    DONE: 2,
};

export default {
    name: "UserAvatarInput",
    props: {
        // To allow "click-to-activate" on avatar
        inputId: {
            type: String,
            required: true,
        },
        // For preview
        currentAvatar: {
            type: String,
            required: false,
        },
    },
    data() {
        return {
            inputElement: null,
            imageData: null,
            fileReader: null,
            error: null,
        };
    },
    methods: {
        subscribeToInput(ele) {
            ele.addEventListener("change", (e) => {
                let file = e.target.files[0];
                if (file) {
                    this.handleFile(file);
                } else {
                    this.imageData = null;
                    this.fileReader = null;
                    this.error = null;
                }
            });
        },
        async handleFile(file) {
            if (this.fileReader) {
                this.fileReader.abort();
                // reset state
                this.imageData = null;
                this.error = null;
                this.progress = 0;
            }
            let fileReader = new FileReader();
            fileReader.readAsDataURL(file);

            fileReader.addEventListener("loadend", (ev) => {
                this.imageData = fileReader.result;
            });
            fileReader.addEventListener("error", (ev) => {
                this.error = fileReader.error;
            });
        },
        init() {
            // Find related input in DOM
            this.inputElement = document.querySelector("#" + this.inputId);

            // Assign listeners
            if (this.inputElement) {
                this.subscribeToInput(this.inputElement);
            }
        },
    },
    computed: {
        avatarStyle() {
            if (!this.imageData && !this.currentAvatar) {
                return null;
            }
            return `background-image: url(${this.imageData || this.currentAvatar})`;
        },
    },
    mounted() {
        // Vue recreates elements, so using mounted hook instead of 'created'.
        this.init();
    },
};
</script>
<style scoped>
.user-avatar-input {
    display: inline-block;
}
</style>
