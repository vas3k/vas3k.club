<template>
    <div class="window window-expertise">
        <div class="window-close-button" @click="closeWindow"><i class="fas fa-times"></i></div>
        <div class="window-title">Я могу в...</div>
        <form :action="submitFormAction" method="post">
            <div class="edit-expertise">
                <div class="edit-expertise-select">
                    <select name="expertise" id="id_expertise" @change="onSelectionChange">
                        <optgroup v-for="group in expertiseList" :label="group[0]">
                            <option v-for="option in group[1]" :value="option[0]">{{ option[1] }}</option>
                        </optgroup>
                        <option value="custom">[добавить своё]</option>
                    </select>
                </div>
                <div id="edit-expertise-custom" class="edit-expertise-custom" v-show="isCustom">
                    <input type="text" name="expertise_custom" maxlength="32" />
                </div>
                <div class="edit-expertise-value">
                    Насколько хорошо: <input type="range" name="value" step="1" min="0" max="100" required="required" />
                </div>
            </div>
            <button type="submit" class="button window-button">Добавить</button>
        </form>
    </div>
</template>

<script>
export default {
    name: "UserExpertiseWindow",
    props: {
        submitFormAction: {
            type: String,
            required: true,
        },
        expertiseList: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            isCustom: false,
        };
    },
    methods: {
        closeWindow(event) {
            this.$emit("close-window");
        },
        onSelectionChange(event) {
            this.isCustom = event.target.value === "custom";
        },
    },
};
</script>
