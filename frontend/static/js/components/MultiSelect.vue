<template>
    <div class="input-select">
        <input type="hidden" :value="formValue" :name="id" />
        <v-select
            :taggable="allowCreateNew"
            :multiple="allowMultiple"

            label="title"
            placeholder=""

            v-model="selectValue"

            :options="lastSearchOptions"
            :selectable="canSelect"

            @input="onSelectValueChange"
            @search="onSearch"
            @option:selected="clearSearchResults"
            @option:created="clearSearchResults"
        >
            <template #no-options="{ search, searching, loading }">
                <template v-if="!searching || search.length < 3">
                    Начните набирать текст для поиска...
                </template>
                <template v-else>
                    Ничего не найдено
                </template>
            </template>

            <template #option="{ title, isExist, description, img }">
                <span>
                    <template v-if="!isExist">{{ labelPrefixInput }}</template>
                    <img v-if="img" :src="img"></img>
                    <span>{{ title }}</span>
                    <span class="vs__dropdown-option-description-text" v-if="!!description">{{ description }}</span>
                </span>
                <br>
                <template v-if="!isExist || !isValidInput">
                    <span class="vs__dropdown-option-secondary-text">
                        <template v-if="!isValidInput">
                            {{ labelInvalidInput }}
                        </template>
                        <template v-else>
                            {{ labelValidInput }}
                        </template>
                    </span>
                </template>
            </template>


            <template #search="{attributes, events}">
                <input
                    class="vs__search"
                    @input="onInputChange"
                    v-bind="attributes"
                    v-on="events"
                />
            </template>
        </v-select>
    </div>
</template>

<script>
import { debounce } from "../common/utils";


export default {
    props: {
        id: {
            type: String,
            required: true,
        },
        initialValue: {
            type: String,
            required: false,
        },
        allowCreateNew: {
            type: Boolean,
            required: false,
            default: false,
        },
        allowMultiple: {
            type: Boolean,
            required: false,
            default: false,
        },
        maxCount: {
            type: Number,
            required: false,
            default: 10,
        },
        validationRegExp: {
            type: String,
            required: false,
            default: null,
        },
        searchUrl: {
            type: String,
            required: true,
        },
        apiFieldArray: {
            type: String,
            required: true,
        },
        apiFieldItemTitle: {
            type: String,
            required: true,
        },
        apiFieldItemImg: {
            type: String,
            required: false,
        },
        apiFieldItemDescription: {
            type: String,
            required: false,
        },
        labelValidInput: {
            type: String,
            required: false,
        },
        labelInvalidInput: {
            type: String,
            required: false,
        },
        labelPrefixInput: {
            type: String,
            required: false,
        },
    },
    mounted() {
        if (this.initialValue) {
            if (this.allowMultiple) {
                // TODO: handle initial data for multiple values case - it's WIP solution?
                const values = this.initialValue.split(',');

                this.selectValue = values.map(value => ({
                   title: value,
                   isExist: true,
                }));
                this.formValue = values;
                return;
            }

            this.selectValue = {
                title: this.initialValue,
                isExist: true,
            }
            this.formValue = this.initialValue;
        }
    },
    data() {
        return {
            isValidInput: false,
            selectValue: null,
            formValue: null,
            lastSearchOptions: [],
        };
    },
    computed: {
        validationRe() {
            if (!this.validationRegExp) {
                return null;
            }

            return new RegExp(this.validationRegExp);
        }
    },
    methods: {
        canSelect(option) {
            // Limits
            if (this.allowMultiple && this.selectValue && this.selectValue.length >= this.maxCount) {
                this.isValidInput = false;
                return false;
            }

            // Skip check for existing items OR look at regexp result
            return option.isExist || this.isValidInput;
        },

        clearSearchResults() {
            this.lastSearchOptions = [];
        },

        onInputChange(event) {
            if (!this.validationRe) {
                this.isValidInput = true;
                return;
            }

            if (this.validationRe.test(event.target.value)) {
                this.isValidInput = true;
                return;
            }

            this.isValidInput = false;
        },

        onSearch(search, loading) {
            if (search.length >= 3) {
                loading(true);
                this.search(loading, search, this);
                return;
            }

            this.lastSearchOptions = [];
        },

        search: debounce(((loading, search, vm) => {
            fetch(`${vm.searchUrl}${search}`)
                .then(response => response.json())
                .then(json => {
                    if (!json[vm.apiFieldArray]) {
                        return;
                    }

                    vm.lastSearchOptions = json[vm.apiFieldArray].map(item => ({
                        title: item[vm.apiFieldItemTitle],
                        description: vm.apiFieldItemDescription ? item[vm.apiFieldItemDescription] : null,
                        img: vm.apiFieldItemImg ? item[vm.apiFieldItemImg] : null,
                        isExist: true,
                    }));
                })
                .finally(() => {
                    loading(false);
                });

        }), 500),

        onSelectValueChange(options) {
            if (!options) {
                this.formValue = null;
                return;
            }

            // TODO: need to test it properly
            if (Array.isArray(options)) {
                this.formValue = options.map(item => item.title || item);
                return;
            }

            this.formValue = options.title || options;
        }
    },
};
</script>
