<template>
    <div>
        <div class="user-expertise-row-bar" @click="showInput = true">
            <div class="user-expertise-row-bar-inner" :style="style"></div>
        </div>
        <div>

            <div v-if="showInput" class="window window-expertise">
                <form :action="submitFormAction" method="post">
                    <div class="window-close-button" @click="closeWindow"><i class="fas fa-times"></i></div>
                    <div id="expertise" v-show="false">
                        <input type="text" name="expertise" v-model="expertise" maxlength="32" />
                    </div>
                    <div id="edit-expertise-custom" class="edit-expertise-custom" v-show="false">
                        <input type="text" name="expertise_custom" v-model="expertise" maxlength="32" />
                    </div>
                    <div class="window-title">Я могу в {{ name }}</div>
                    <div class="edit-expertise">
                        <div class="edit-expertise-value">
                            Насколько хорошо:
                            <input
                                v-model="inputValue"
                                type="range"
                                name="value"
                                step="1"
                                min="0"
                                max="100"
                                required="required"
                            />
                        </div>
                    </div>
                    <button type="submit" class="button window-button">Сохранить</button>
                </form>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "EditUserExpertiseWindow",
    props: {
        value: {
            type: Number,
            required: true,
        },
        expertise: {
            type: String,
            required: true,
        },
        name: {
            type: String,
            required: true,
        },
        submitFormAction: {
            type: String,
            required: true,
        },
    },
    computed: {
        style() {
            return `width: ${this.value}%`;
        },
    },
    data() {
        return {
            showInput: false,
            inputValue: this.value,
        };
    },
    methods: {
        closeWindow(event) {
            this.showInput = false;
        },
    },
};
</script>
