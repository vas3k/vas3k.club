<template>
    <div class="post-toc" v-if="headlines.length > 0">
        <ul v-if="isOpen" class="post-toc-opened-list" @mouseleave.prevent="closeToc">
            <li :class="{
                    'post-toc-item': true,
                    'post-toc-item-level-1': headline.level === 1,
                    'post-toc-item-level-2': headline.level === 2,
                    'post-toc-item-level-3': headline.level === 3,
                }" v-for="headline in headlines">
                <a href="#" @click.prevent="onHeadlineClick(headline)">{{ headline.text }}</a>
            </li>
        </ul>
        <ul v-else class="post-toc-collapsed-list" @mouseover.prevent="openToc" @click.prevent="openToc">
            <li v-for="headline in headlines"
                :class="{
                    'post-toc-collapsed-item': true,
                    'post-toc-collapsed-level-1': headline.level === 1,
                    'post-toc-collapsed-level-2': headline.level === 2,
                    'post-toc-collapsed-level-3': headline.level === 3,
                }"
            >
            </li>
        </ul>
    </div>
</template>

<script>
export default {
    name: "PostToC",
    data() {
        return {
            headlines: [],
            isOpen: false
        };
    },
    methods: {
        onHeadlineClick(headline) {
            headline.element.scrollIntoView({ behavior: "smooth", block: "center" });
        },
        openToc() {
            this.isOpen = true;
        },
        closeToc() {
            this.isOpen = false;
        }
    },
    beforeMount() {
        this.headlines = Array.from(document.querySelectorAll("article.post .text-body h1, article.post .text-body h2, article.post .text-body h3"))
            .filter(headline => !headline.classList.contains("post-title"))
            .map(createHeadlineDescription);
    }
};

function createHeadlineDescription(headline, index, headlines) {
    const tagLevel = parseInt(headline.tagName[headline.tagName.length - 1], 10);
    const prevHeadlineLevel = index > 0 ? headlines[index - 1].level : 0;

    return ({
        text: headline.innerText,
        element: headline,
        level: tagLevel - prevHeadlineLevel > 1 ? prevHeadlineLevel + 1 : tagLevel
    });
}
</script>
