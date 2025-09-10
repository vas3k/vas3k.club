<template>
    <div class="post-toc" v-if="headlines.length > 0">
        <transition name="expand" mode="out-in">
            <ul v-if="isOpen" class="post-toc-opened-list" @mouseleave.prevent="closeToc" key="opened">
                <li v-for="(headline, index) in headlines"
                    :class="{
                    'post-toc-item': true,
                    'post-toc-item-level-1': headline.level === 1,
                    'post-toc-item-level-2': headline.level === 2,
                    'post-toc-item-level-3': headline.level === 3,
                    'post-toc-item-active': index === currentHeadingIndex
                }">
                    <a :href="`#${headline.element.id}`" @click="onHeadlineClick">{{ headline.text }}</a>
                </li>
                <li class="post-toc-item-level-1 post-toc-item-comments">
                    <a href="#comments" @click="onHeadlineClick">Комментарии
                        {{ commentsCount > 0 ? `(${commentsCount})` : "" }}</a>
                </li>
            </ul>
            <ul v-else class="post-toc-collapsed-list" @mouseover.prevent="openToc" @click.prevent="openToc"
                key="closed">
                <li v-for="(headline, index) in headlines"
                    :class="{
                    'post-toc-collapsed-item': true,
                    'post-toc-collapsed-level-1': headline.level === 1,
                    'post-toc-collapsed-level-2': headline.level === 2,
                    'post-toc-collapsed-level-3': headline.level === 3,
                    'post-toc-collapsed-active': index === currentHeadingIndex
                }"
                >
                </li>
            </ul>
        </transition>
    </div>
</template>

<script>
export default {
    name: "PostToC",
    props: {
        commentsCount: {
            type: String
        }
    },
    data() {
        return {
            headlines: [],
            isOpen: false,
            currentHeadingIndex: undefined,
            prevScrollPosition: undefined
        };
    },
    methods: {
        onHeadlineClick() {
            document.documentElement.style.scrollBehavior = "smooth";
            document.addEventListener("scrollend", () => {
                document.documentElement.style.scrollBehavior = "auto";
            }, { once: true });
        },
        openToc() {
            this.isOpen = true;
        },
        closeToc() {
            this.isOpen = false;
        }
    },
    mounted() {
        this.currentHeadingIndex = calcActivePosition(this.headlines);
        this.prevScrollPosition = window.scrollY;
    },
    beforeMount() {
        this.headlines = Array.from(document.querySelectorAll("article.post .text-body h1, article.post .text-body h2, article.post .text-body h3"))
            .filter(headline => !headline.classList.contains("post-title"))
            .map(createHeadlineDescription);

        const headlineObserver = new IntersectionObserver((entries) => {
            const lastIntersecting = entries.findLast(entry => entry.isIntersecting === true);
            const scrollDirection = this.prevScrollPosition - window.scrollY > 0 ? "up" : "down";
            this.prevScrollPosition = window.scrollY;

            if (lastIntersecting) {
                this.currentHeadingIndex = this.headlines.findIndex(headline => headline.element === lastIntersecting.target);
            } else if (scrollDirection === "up" && entries.length === 1 && !entries[0].isIntersecting) {
                // when we scroll up past the current headline and there is no headline visible, switch to the previous headline
                this.currentHeadingIndex = calcActivePosition(this.headlines);
            }
        }, { threshold: 1 });

        for (const headline of this.headlines) {
            headlineObserver.observe(headline.element);
        }

        // highlight nothing when a post is out of the screen
        const postTextObserver = new IntersectionObserver(([entry]) => {
            if (!entry.isIntersecting) {
                this.currentHeadingIndex = undefined;
            }
        });
        postTextObserver.observe(document.querySelector("section.post-text"));
    }
};

function createHeadlineDescription(headline) {
    const tagLevel = getTagLevel(headline);

    return ({
        text: headline.innerText,
        element: headline,
        level: tagLevel
    });
}

function calcActivePosition(headlines) {
    const viewportHeight = window.innerHeight;
    return headlines.reduce((closestFromTopIndex, headline, index) => {
            const headlinePosition = headline.element.getBoundingClientRect();
            const isAboveViewport = headlinePosition.y <= 0;
            const isWithinViewport = !isAboveViewport && headlinePosition.bottom < viewportHeight;
            return isAboveViewport || isWithinViewport ? index : closestFromTopIndex;
        },
        undefined);
}

function getTagLevel(headlineElement) {
    return parseInt(headlineElement.tagName.slice(-1), 10);
}
</script>

<style>
@media (prefers-reduced-motion: no-preference) {
    .expand-enter-active {
        transition: all .2s ease;
        pointer-events: none;
    }

    .expand-leave-active {
        transition: all .1s ease-out;
        pointer-events: none;
    }

    .expand-enter {
        transform: translateX(50px);
        opacity: 0;
    }

    .expand-leave {
        transform: translateX(50px);
        opacity: 0;
    }


    .expand-leave-to {
        transform: translateX(50px);
        opacity: 0;
    }
}
</style>
