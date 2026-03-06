import { shallowMount } from "@vue/test-utils";
import PostUpvote from "../components/PostUpvote.vue";

jest.mock("../common/api.service", () => ({
    __esModule: true,
    default: {
        post: jest.fn(),
    },
}));

import ClubApi from "../common/api.service";

describe("PostUpvote.vue", () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    function mountUpvote(props = {}) {
        return shallowMount(PostUpvote, {
            propsData: {
                upvoteUrl: "/upvote",
                retractVoteUrl: "/retract",
                initialUpvotes: 5,
                ...props,
            },
        });
    }

    it("renders initial upvote count", () => {
        const wrapper = mountUpvote({ initialUpvotes: 42 });
        expect(wrapper.text()).toContain("42");
    });

    it("calls upvoteUrl and updates state on upvote", () => {
        ClubApi.post.mockImplementation((url, cb) => cb({ post: { upvotes: 6 }, upvoted_timestamp: 1000000 }));
        const wrapper = mountUpvote({ initialUpvotes: 5 });

        wrapper.vm.toggle();

        expect(ClubApi.post).toHaveBeenCalledWith("/upvote", expect.any(Function));
        expect(wrapper.vm.upvotes).toBe(6);
        expect(wrapper.vm.isVoted).toBe(true);
        expect(wrapper.vm.upvotedTimestamp).toBe(1000000);
    });

    it("retracts vote within hoursToRetractVote", () => {
        ClubApi.post.mockImplementation((url, cb) => cb({ post: { upvotes: 4 }, success: true }));
        const wrapper = mountUpvote({
            initialUpvotes: 5,
            initialIsVoted: true,
            initialUpvoteTimestamp: String(Date.now()), // just voted
            hoursToRetractVote: 1,
        });

        wrapper.vm.toggle();

        expect(ClubApi.post).toHaveBeenCalledWith("/retract", expect.any(Function));
        expect(wrapper.vm.upvotes).toBe(4);
        expect(wrapper.vm.isVoted).toBe(false);
    });

    it("does not retract vote beyond hoursToRetractVote", () => {
        const twoHoursAgo = Date.now() - 2 * 60 * 60 * 1000;
        const wrapper = mountUpvote({
            initialUpvotes: 5,
            initialIsVoted: true,
            initialUpvoteTimestamp: String(twoHoursAgo),
            hoursToRetractVote: 1,
        });

        wrapper.vm.toggle();

        expect(ClubApi.post).not.toHaveBeenCalled();
    });

    it("getHoursSinceVote returns correct value", () => {
        const oneHourAgo = Date.now() - 60 * 60 * 1000;
        const wrapper = mountUpvote({
            initialUpvoteTimestamp: String(oneHourAgo),
        });

        const hours = wrapper.vm.getHoursSinceVote();
        expect(hours).toBeGreaterThanOrEqual(0.99);
        expect(hours).toBeLessThanOrEqual(1.01);
    });

    it("getHoursSinceVote returns false without timestamp", () => {
        const wrapper = mountUpvote();
        expect(wrapper.vm.getHoursSinceVote()).toBe(false);
    });

    it("applies upvote-voted class when voted and not disabled", async () => {
        const wrapper = mountUpvote({ initialIsVoted: true });
        await wrapper.vm.$nextTick();

        expect(wrapper.classes()).toContain("upvote-voted");
        expect(wrapper.classes()).not.toContain("upvote-disabled");
    });

    it("applies upvote-disabled class when disabled", async () => {
        const wrapper = mountUpvote({ isDisabled: true });
        await wrapper.vm.$nextTick();

        expect(wrapper.classes()).toContain("upvote-disabled");
    });
});
