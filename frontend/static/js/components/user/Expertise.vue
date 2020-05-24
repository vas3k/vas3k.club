<template>
    <div>
        <div class="profile-header">Экспертиза</div>
        <div class="block profile-expertise">
            <div v-if="userExpertises" class="profile-expertise-rows" id="expertises">
                <div
                    v-for="expertise in filterUserExpertises"
                    :key="expertise.expertise"
                    :id="'expertise-' + expertise.expertise"
                    class="user-expertise-row"
                >
                    <div class="user-expertise-row-name">
                        {{ expertise.name }}
                        <a
                            v-if="isUser"
                            class="user-expertise-delete"
                            @click.prevent="deleteExpertise(expertise.expertise)"
                            >[x]</a
                        >
                    </div>
                    <div v-if="isUser" class="user-expertise-row-bar" @click="openEditModal(expertise)">
                        <div class="user-expertise-row-bar-inner" :style="{ width: expertise.value + '%' }"></div>
                    </div>
                </div>
            </div>
            <span v-if="isUser" class="button profile-expertise-add-button" @click="openModal()"
                >Укажи, во что можешь</span
            >
        </div>

        <div v-if="showModal">
            <div class="window window-expertise">
                <div class="window-close-button" @click="closeModal()"><i class="fas fa-times"></i></div>
                <div class="window-title">Я могу в...</div>
                <form :action="submitFormAction" method="post">
                    <div class="edit-expertise">
                        <div class="edit-expertise-select">
                            <select v-if="editModalMode" name="expertise" id="id_expertise" @change="onSelectionChange">
                                <option v-if="isCustom" value="custom"> {{ expertise.name }}</option>
                                <option v-else :value="expertise.expertise"> {{ expertise.name }}</option>
                            </select>
                            <input
                                v-if="editModalMode"
                                v-show="false"
                                type="text"
                                name="expertise_custom"
                                :value="expertise.expertise"
                            />
                            <select v-else name="expertise" id="id_expertise" @change="onSelectionChange">
                                <optgroup v-for="group in globalExpertises" :label="group[0]">
                                    <option v-for="option in group[1]" :value="option[0]">{{ option[1] }}</option>
                                </optgroup>
                                <option value="custom">[добавить своё]</option>
                            </select>
                        </div>
                        <div
                            v-if="!editModalMode"
                            id="edit-expertise-custom"
                            class="edit-expertise-custom"
                            v-show="isCustom"
                        >
                            <input type="text" name="expertise_custom" maxlength="32" />
                        </div>
                        <div class="edit-expertise-value">
                            Насколько хорошо:
                            <input
                                :value="editModalMode ? expertise.value : 50"
                                type="range"
                                name="value"
                                step="1"
                                min="0"
                                max="100"
                                required="required"
                            />
                        </div>
                    </div>
                    <button type="submit" class="button window-button">
                        {{ editModalMode ? "Сохранить" : "Добавить" }}
                    </button>
                </form>
            </div>
        </div>
    </div>
</template>

<script>
import ClubApi from "../../common/api.service";

export default {
    name: "Expertise",
    props: {
        userExpertises: {
            type: Array,
            required: true,
        },
        globalExpertises: {
            type: Array,
            required: true,
        },
        isUser: {
            type: Boolean,
            required: true,
        },
        submitFormAction: {
            type: String,
            required: true,
        },
    },
    computed: {
        filterUserExpertises() {
            return this.userExpertises.map((expertise) => expertise.fields);
        },
    },
    data() {
        return {
            showModal: false,
            isCustom: false,
            editModalMode: false,
            expertise: false,
            globalExpertisesSet: new Set(),
        };
    },
    created() {
        for (const group of this.globalExpertises) {
            for (const expertiseMap of group[1]) {
                const expertiseName = expertiseMap[0];
                this.globalExpertisesSet.add(expertiseName);
            }
        }
    },
    methods: {
        clearState() {
            this.isCustom = false;
            this.expertise = false;
            this.editModalMode = false;
            this.showModal = false;
        },
        closeModal(event) {
            this.clearState();
        },
        openModal(edit) {
            this.showModal = true;
        },
        openEditModal(expertise) {
            this.showModal = true;
            this.editModalMode = true;
            this.expertise = expertise;
            this.isCustom = this.isCustomExpertise(expertise.expertise);
        },
        deleteExpertise(expertise) {
            return ClubApi.ajaxify(`/profile/expertise/${expertise}/delete/`, (data) => {
                if (data.status === "deleted") {
                    document.getElementById("expertise-" + data.expertise.expertise).outerHTML = "";
                }
            });
        },
        onSelectionChange(event) {
            this.isCustom = event.target.value === "custom";
        },
        isCustomExpertise(expertise) {
            return !this.globalExpertisesSet.has(expertise);
        },
    },
};
</script>
