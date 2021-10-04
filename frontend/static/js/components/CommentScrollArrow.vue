<template>
    <span
        class="comment-scroll-arrow"
        :class="{
            'arrow-up': arrowDirection === 'Up'
        }"
        @click.prevent="onArrowClickHandler"
    >
    </span>
</template>

<script>
import { throttle } from "../common/utils.js";

export default {
    name: "CommentScrollArrow",
    data() {
        return {
            arrowDirection: "Down",
            scrollThrottleDelay: 150,
            commentMargin: 20,
        };
    },
    methods: {
        getBodyTop() {
            return document.body.getBoundingClientRect().top;
        },
        scrollTo(elementId, callback) {
            document.location.hash = `#${elementId}`;

            // TODO: callback call after document.location scroll end
            if (callback) {
                callback();
            }
        },
        scrollExtreme(direction) {
            document.location.hash = '';

            if (direction === "Down") {
                this.arrowDirection = "Up";

                document.location.hash = '#post-comments-form';
            } else {
                this.arrowDirection = "Down";

                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            }
        },
        scrollToComment(direction) {
            let comments = document.querySelectorAll(".comment-is-new");

            const bodyTop = this.getBodyTop();

            if (comments.length < 1) {
                // take only the first comment
                const commentBlock = document.getElementById("comments");
                comments = commentBlock ? [commentBlock] : [];
            }

            if (comments.length < 1) {
                // Then post without comments
                return this.scrollExtreme(direction);
            }

            const position = window.scrollY + this.commentMargin;

            // Убираем комментарии ниже или выше направления поиска
            const filteredComments = [...comments].filter((el) => {
                const elBCR = el.getBoundingClientRect();
                const eltop = elBCR.top - bodyTop;
                return (direction === "Down") ?
                    eltop - elBCR.height / 2 > position
                    : eltop + elBCR.height / 2 < position;
            });
            if (filteredComments.length < 1) {
                return this.scrollExtreme(direction);
            }

            // Находим ближайший к середине экрана комментарий
            const nearest = [...filteredComments].reduce((a, b) => {
                const atop = a.getBoundingClientRect().top - bodyTop;
                const btop = b.getBoundingClientRect().top - bodyTop;
                return Math.abs(btop - position) < Math.abs(atop - position) ? b : a;
            });

            const highlightComment = () => {
                nearest.classList.add("comment-scroll-selected");
                window.setTimeout(() => { nearest.classList.remove("comment-scroll-selected"); }, 500);
            };

            this.scrollTo(nearest.id, highlightComment);
        },
        onArrowClickHandler() {
            if (this.arrowDirection == "Up") {
                this.scrollExtreme(this.arrowDirection);
            } else {
                this.scrollToComment(this.arrowDirection);
            }
        },
        initOnPageScroll() {
            this.onPageScrollHandler = throttle(() => {
                const scrollPosition = Math.max(
                    window.pageYOffset,
                    document.documentElement.scrollTop,
                    document.body.scrollTop
                );
                const bottomOfWindow = scrollPosition + window.innerHeight === document.documentElement.offsetHeight;
                const topOfWindow = scrollPosition === 0;

                if (bottomOfWindow) {
                    this.arrowDirection = "Up";
                }

                if (topOfWindow) {
                    this.arrowDirection = "Down";
                }
            }, this.scrollThrottleDelay);

            window.addEventListener("scroll", this.onPageScrollHandler);
        },
        initOnKeyUp() {
             this.keyUpHandler = (e) => {
                // ctrl-up/down для всех, а в macos - ⇧⌃↑/↓
                if (!e.ctrlKey || ["ArrowDown", "ArrowUp", "Down", "Up"].indexOf(e.key) < 0) {
                    return;
                }

                e.preventDefault();
                const direction = e.key.replace(/^Arrow/, "");

                this.arrowDirection = direction;

                this.scrollToComment(direction);
            };

            document.addEventListener("keyup", this.keyUpHandler);
        },
        init() {
            this.initOnKeyUp();
            this.initOnPageScroll();
        }
    },
    mounted() {
        this.init();
    },
    beforeDestroy() {
        document.removeEventListener("keyup", this.keyUpHandler);
        window.removeEventListener("scroll", this.onPageScrollHandler);
    },
};
</script>
