<template>
  <div
    :id="`clicker-${clickerId}`"
    :class="{
      clicker: true,
      'clicker-is-clicked': active,
    }"
    @click.prevent="toggle"
  >
    <div v-if="loading" class="clicker-checkbox">⌛</div>
    <div v-else class="clicker-checkbox"></div>

    <div class="clicker-text">
      {{ text }}
    </div>

    <div class="clicker-counter" v-if="count != 0">{{ count }}</div>

    <div class="clicker-users" v-if="clicks.length > 0">
      <a
        v-for="(c, i) in clicks"
        :key="i"
        :href="`/user/${c.user.slug}/`"
        target="_blank"
        class="clicker-avatar"
        :title="c.user.full_name"
        :style="{ backgroundImage: `url(${c.user.avatar || 'https://i.vas3k.club/v.png'})` }"
        @click.stop="$event.stopPropagation()"
      ></a>
    </div>
  </div>
</template>

<script>
import ClubApi from "../common/api.service";

export default {
  name: "Clicker",
  props: {
    clickerId: { type: [String, Number], required: true },
    text: { type: String, required: true },
  },
  data() {
    return {
      clicks: [],
      count: 0,
      active: false,
      loading: true,
    };
  },
  mounted() {
    this.load();
  },
  methods: {
    url() {
      return `/clickers/${encodeURIComponent(this.clickerId)}.json`;
    },

    load() {
      this.loading = true;
      return ClubApi.get(this.url(), (data) => {
        this.loading = false;
        this.clicks = data.clicks || [];
        this.count = data.count || 0;
        this.active = !!data.is_clicked;
      });
    },

    toggle() {
      if (this.loading) return;
      this.loading = true;

      const method = this.active ? "delete" : "post";
      return ClubApi[method](this.url(), (data) => {
        this.loading = false;

        if (data.error) {
          this.$emit("error", data.error);
          return;
        }

        this.clicks = data.clicks || [];
        this.count = data.count || 0;
        this.active = !!data.is_clicked;
      });
    },
  },
};
</script>
