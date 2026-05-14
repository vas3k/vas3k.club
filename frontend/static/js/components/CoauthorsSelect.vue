<template>
    <div class="input-select">
        <input type="hidden" :name="id" :value="formValue" />
        <v-select
            multiple
            label="full_name"
            :filterable="false"
            v-model="selectedUsers"
            :options="mergedOptions"
            :get-option-key="(opt) => opt.slug"
            :selectable="isSelectable"
            :close-on-select="false"
            placeholder=""
            @search="onSearch"
        >
            <template #no-options="{ search, loading }">
                <template v-if="!search || search.length < 3">
                    Минимум 3 символа для поиска…
                </template>
                <template v-else-if="loading">
                    Загрузка…
                </template>
                <template v-else>
                    Ничего не найдено
                </template>
            </template>

            <template #option="option">
                <div class="coauthors-select-row">
                    <img
                        class="coauthors-select-avatar"
                        :src="avatarUrl(option)"
                        :alt="''"
                        loading="lazy"
                        width="22"
                        height="22"
                    />
                    <span class="coauthors-select-name">{{ option.full_name }}</span>
                </div>
            </template>

            <template #selected-option="option">
                <div class="coauthors-select-row">
                    <img
                        class="coauthors-select-avatar"
                        :src="avatarUrl(option)"
                        :alt="''"
                        loading="lazy"
                        width="22"
                        height="22"
                    />
                    <span class="coauthors-select-name">{{ option.full_name }}</span>
                </div>
            </template>

            <template #search="{ attributes, events }">
                <input class="vs__search" v-bind="attributes" v-on="events" />
            </template>
        </v-select>
    </div>
</template>

<script>
import { debounce } from "../common/utils";

const DEFAULT_AVATAR = "https://i.vas3k.club/v.png";
const MAX_COAUTHORS = 10;
const MIN_PREFIX = 3;
const MAX_PREFIX = 15;

export default {
    name: "CoauthorsSelect",
    props: {
        id: {
            type: String,
            required: true,
        },
        searchUrl: {
            type: String,
            required: true,
        },
        initialUsers: {
            type: Array,
            default() {
                return [];
            },
        },
        initialSlugs: {
            type: String,
            default: "",
        },
        excludeSlug: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            selectedUsers: [],
            searchResults: [],
        };
    },
    computed: {
        mergedOptions() {
            const selected = [...this.selectedUsers];
            const slugs = new Set(selected.map((u) => u.slug));
            const fromSearch = this.searchResults.filter((u) => !slugs.has(u.slug));
            return [...selected, ...fromSearch];
        },
        formValue() {
            return this.selectedUsers.map((u) => u.slug).join(",");
        },
    },
    created() {
        this.debouncedFetch = debounce((loading, prefix) => {
            fetch(`${this.searchUrl}${encodeURIComponent(prefix)}`)
                .then((res) => res.json())
                .then((data) => {
                    if (!data.users) {
                        return;
                    }

                    this.searchResults = data.users
                        .filter((u) => !this.excludeSlug || u.slug !== this.excludeSlug)
                        .map((u) => ({
                            slug: u.slug,
                            full_name: u.full_name,
                            avatar: u.avatar || DEFAULT_AVATAR,
                        }));
                })
                .finally(() => {
                    loading(false);
                });
        }, 500);
    },
    mounted() {
        const slugsRaw = (this.initialSlugs && String(this.initialSlugs).trim()) || "";
        if (slugsRaw) {
            this.selectedUsers = slugsRaw
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean)
                .map((slug) => ({
                    slug,
                    full_name: slug,
                    avatar: DEFAULT_AVATAR,
                }));
            return;
        }

        if (this.initialUsers && this.initialUsers.length) {
            this.selectedUsers = this.initialUsers.map((u) => ({
                slug: u.slug,
                full_name: u.full_name,
                avatar: u.avatar || DEFAULT_AVATAR,
            }));
        }
    },
    methods: {
        avatarUrl(option) {
            if (!option) {
                return DEFAULT_AVATAR;
            }

            return option.avatar || DEFAULT_AVATAR;
        },

        isSelectable(option) {
            if (!option || !option.slug) {
                return false;
            }

            if (this.excludeSlug && option.slug === this.excludeSlug) {
                return false;
            }

            const already = this.selectedUsers.some((u) => u.slug === option.slug);
            if (already) {
                return true;
            }

            return this.selectedUsers.length < MAX_COAUTHORS;
        },

        onSearch(search, loading) {
            this.searchResults = [];

            if (!search || search.length < MIN_PREFIX) {
                loading(false);
                return;
            }

            const prefix = search.slice(0, MAX_PREFIX);
            loading(true);
            this.debouncedFetch(loading, prefix);
        },
    },
};
</script>

<style scoped>
.coauthors-select-row {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-width: 0;
    max-width: 100%;
}

.coauthors-select-avatar {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
}

.coauthors-select-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
    max-width: 14rem;
}
</style>
