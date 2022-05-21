<template>
    <div class="people-map-user-content">
        <b><a :href="url" target="_blank">{{full_name}}</a></b>
        <p>{{position}}  —  {{company}}</p>
    </div>
</template>

<script>
import Vue from 'vue';

export default Vue.extend({
    name: 'GeoPopup',
    props: {
        full_name: String,
        url: String,
        position: String,
        company: String,
    }
})
</script>
