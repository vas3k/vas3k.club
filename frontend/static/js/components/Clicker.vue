<template>
  <div
    :id="`clicker-${clickerId}`"
    :class="{ 'clicker': true, 'clicker-is-clicked': active }"
    @click.prevent="toggle"
  >
    <div class="clicker-checkbox"></div>
    <div v-if="loading">⌛</div>

    <div class="clicker-text">
      {{ text }}
    </div>

    <div class="clicker-users" v-if="!loading">
      <div
        v-for="(c, i) in clicks"
        :key="i"
        class="clicker-avatar"
        :title="c.user.name"
        :style="{ backgroundImage: `url(${c.user.avatar})` }"
      ></div>
    </div>

    <div class="clicker-counter">
      <span v-if="loading">(0)</span>
      <span v-else>({{ count }})</span>
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
      return `/clickers/${this.clickerId}.json`;
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

      return ClubApi.post(this.url(), () => {
        // After toggle — reload full state
        this.load();
      });
    },
  },
};
</script>
