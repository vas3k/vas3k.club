<template>
    <div class="input-select">
        <input type="hidden" :value="formValue" :name="id" />
        <v-select
            :taggable="allowCreateNew"
            :multiple="allowMultiple"

            label="title"
            placeholder=""

            v-model="selectValue"

            :options="options"
            :selectable="canSelect"

            @input="onSelectValueChange"
            @search="onSearch"
        >
            <template #no-options="{ search, searching, loading }">
                <template v-if="!searching || search.length < 3">
                    Начните набирать текст для поиска...
                </template>
                <template v-else>
                    Ничего не найдено
                </template>
            </template>

            <template #option="{ title, isExist }">
                <span>
                    <template v-if="!isExist">{{ labelPrefixInput }}</template>
                    {{ title }}
                </span>
                <br>
                <template v-if="!isExist">
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
                    @blur="onInputBlur"
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
        validationRegExp: {
            type: String,
            required: false,
            default: null,
        },
        searchUrl: {
            type: String,
            required: true,
        },
        labelValidInput: String,
        labelInvalidInput: String,
        labelPrefixInput: String,
    },
    mounted() {
        if (this.$props.initialValue) {
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
            options: [],
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
            return option.isExist || this.isValidInput;
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

        onInputBlur(event) {
            // clear old search results
            this.options = [];
        },

        onSearch(search, loading) {
            if (search.length >= 3) {
                loading(true);
                this.search(loading, search, this);
                return;
            }

            this.options = [];
        },

        search: debounce(((loading, search, vm) => {
            fetch(`${vm.$props.searchUrl}${search}`)
                .then(response => response.json())
                .then(json => {
                    if (!json.tags) {
                        return;
                    }
                    vm.options = json.tags
                        .map(tag => ({
                            title: tag.name,
                            isExist: true,
                        }))
                    ;
                })
                .finally(() => {
                    loading(false);
                });

        }), 500),

        // value changed at item in dropdown
        onSelectValueChange(option) {
            if (!option) {
                this.formValue = null;
                return;
            }

            this.formValue = option.title || option;
        }
    },
};
</script>
