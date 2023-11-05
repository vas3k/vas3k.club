<template>
    <div class="input-select">
        <input type="hidden" v-model="currentValue.code" :name="id" />
        <v-select
            :options="options"
            :value="currentValue"
            @input="onChange"
            placeholder="Комната не выбрана"
        >
            <template #no-options="{ search, searching, loading }">
                <template>
                    Ничего не найдено
                </template>
            </template>
        </v-select>
    </div>
</template>

<script>

export default {
    name: "SimpleSelect",
    props: {
        id: {
            type: String,
            required: true,
        },
        initialValue: {
            type: String,
            required: false,
        },
        options: {
            type: Array,
            required: true,
        }
    },
    data() {
        return {
            currentValue: this.options.find(x => x.code === this.initialValue) || [],
        };
    },
    methods: {
        onChange(newValue) {
            this.currentValue = newValue || [];
        }
    }
};
</script>
