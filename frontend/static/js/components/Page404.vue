<template>
    <div class="block not-found" ref="block">
        <div class="not-found-inner">
            <div class="not-found-header">
                🥲 404
            </div>
            <div class="not-found-description">
                Ссылка никогда не существовала и/или была удалена.
            </div>
        </div>
        <a class="upvote" @click="addItem">
            {{ this.items.length }}
        </a>
    </div>


</template>

<script>
import { randomIntFromInterval } from "../common/utils";


function genBlock(handler) {
    const block = document.createElement('div');
    block.className = 'not-found-bg-block';
    block.addEventListener('transitionend', handler);
    return block;
}

function getMoveCoord(start, max, extra) {
    if (start > max / 2) {
        return randomIntFromInterval(-start - extra, extra);
    }

    return randomIntFromInterval(extra, max - start + extra);
}

function updateBlock(block, maxX, maxY) {
    const startX = randomIntFromInterval(0, maxX);
    const startY = randomIntFromInterval(0, maxY);

    // Reset animation
    block.style.animation = 'none';
    block.style.opacity = 0;
    block.style.transitionDelay = `0s`;
    block.style.transitionDuration = `0s`;
    block.style.transform = 'translate(0%, 0%)';
    block.offsetHeight; // trigger reflow to reset animation

    const moveX = getMoveCoord(startX, maxX, maxX * 0.2);
    const moveY = getMoveCoord(startY, maxY, maxY * 0.2);
    const distanceMod = Math.sqrt(Math.pow(moveX, 2) + Math.pow(moveY, 2)) / 100;
    const duration = Math.max(2, distanceMod * 2.75);
    const degree = distanceMod * randomIntFromInterval(100, 250) * (randomIntFromInterval(0, 1) ? 1 : -1);

    // Setup new styles
    block.innerHTML = EMOJI_LIST[randomIntFromInterval(0, EMOJI_LIST.length - 1)];
    block.style.fontSize = `${randomIntFromInterval(100, 350)}%`;
    block.style.top = `${startY}px`;
    block.style.left = `${startX}px`;
    block.style.transitionDelay = '0s';
    block.style.transitionDuration = `${duration}s`;
    block.style.transform = `translate(${moveX}px, ${moveY}px) rotate(${degree}deg)`;
    block.style.animation = `not-found-bg-block-opacity ${duration}s ease-in-out`;
    block.style.animationDelay = '0s';
}

const EMOJI_LIST = [
    '🎰', '🐸', '🌚', '🤔', '😱', '😳', '🤯', '🥳', '👻', '🤡', '👀', '🕶', '🌈', '🍎', '🍏',
    '🚗', '💣', '✖️', '🔥', '⚡️', '🍿', '🍺', '🎲', '🍹', '🥴',
];
const ITEMS_START = 3;
const ITEMS_MAX = 15;
const ADD_ITEM_EVERY = 8;

export default {
    data() {
        return {
            fieldWidth: 0,
            fieldHeight: 0,
            items: [],
            timer: null,
            eventsCounter: 0,
        };
    },
    mounted() {
        this.fieldWidth = this.$refs.block.clientWidth;
        this.fieldHeight = this.$refs.block.clientHeight;

        console.log(this);

        for (let i = 0; i < ITEMS_START; i++) {
            this.addItem();
        }
    },
    beforeDestroy() {
        this.items.forEach(item => {
            item.removeEventListener('transitionend', this.handler);
        });

        if (this.timer) {
            clearTimeout(this.timer);
        }
    },
    methods: {
        handler(event) {
            if (event.propertyName !== 'transform') {
                return;
            }

            if (this.eventsCounter % ADD_ITEM_EVERY === 0 && this.items.length <= ITEMS_MAX) {
                this.addItem();
            }

            this.eventsCounter++;
            this.updateAnimation(event.target);
        },

        addItem() {
            const block = genBlock(this.handler);
            this.items.push(block);
            this.$refs.block.appendChild(block);
            this.updateAnimation(block);
        },

        updateAnimation(element) {
            this.timer = setTimeout(() => {
                updateBlock(element, this.fieldWidth, this.fieldHeight);
            }, 0);
        },

    },
};
</script>
