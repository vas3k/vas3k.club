<template>
    <div class="input-select">
        <input type="hidden" :value="formValue" :name="id" />
        <v-select
            taggable

            label="title"
            placeholder=""

            v-model="selectValue"

            :options="tags"
            :selectable="canSelect"

            @input="onSelectValueChange"
            @search="onSearch"
        >
            <template #no-options="{ search, searching, loading }">
              Начните набирать текст для поиска...
            </template>

            <template #option="{ title, isExist }">
                <span>{{ title }}</span>
                <br>
                <template v-if="!isExist">
                    <span class="TODO_HINT">
                        <template v-if="!isValidInput">
                            Каждый тег обязан начинаться с emoji, потом идёт пробел и название.
                        </template>
                        <template v-else>
                            Вы добавите этот тег первым!
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

<!--

    v-bind: === : →→→
    v-on:   === @ ←←←
    v-model === bind + on ←→←→←→

-->

<script>

import { debounce } from "../common/utils";

const EMOJI_REGEXP = /^(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff]) .+$/;

export default {
    props: {
        id: String,
        initialValue: String
    },
    mounted() {
        console.log(this.selectValue);
        console.log(this.initialValue);

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
            tags: [],
        };
    },
    methods: {
        canSelect(option) {
            return option.isExist || this.isValidInput;
        },

        onInputChange(event) {
            if (EMOJI_REGEXP.test(event.target.value)) {
                this.isValidInput = true;
                return;
            }

            this.isValidInput = false;
        },

        onInputBlur(event) {
            // clear old search results
            this.tags = [];
        },

        onSearch(search, loading) {
            if (search.length >= 3) {
                loading(true);
                this.search(loading, search, this);
                return;
            }

            this.tags = [];
        },

        search: debounce(((loading, search, vm) => {
            fetch(`/search/tags.json?prefix=${search}`)
                .then(response => response.json())
                .then(json => {
                    if (!json.tags) {
                        return;
                    }
                    vm.tags = json.tags.map(tag => ({
                        title: tag.name,
                        isExist: true,
                    }));
                })
                .finally(() => {
                    loading(false);
                });

        }), 500),

        // value changed at item in dropdown
        onSelectValueChange(tag) {
            console.log('Value changed: ', tag);

            if (!tag) {
                this.formValue = null;
                return;
            }

            this.formValue = tag.title;
        }
    },
};
</script>
