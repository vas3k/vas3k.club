<template>
    <div class="post-toc" v-if="headlines.length > 0">
        <ul>
            <li v-for="headline in headlines">
                <a href="#" @click.prevent="onHeadlineClick(headline)">{{ headline.innerText }}</a>
            </li>
        </ul>
    </div>
</template>

<script>
export default {
    name: "PostToC",
    data() {
        return {
            headlines: []
        };
    },
    methods: {
        onHeadlineClick(headline) {
            headline.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    },
    beforeMount() {
        this.headlines = Array.from(document.querySelectorAll("article.post .text-body h1, article.post .text-body h2, article.post .text-body h3"))
            .filter(headline => !headline.classList.contains("post-title"));
    }
};
</script>
