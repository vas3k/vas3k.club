import { shallowMount } from "@vue/test-utils";
import Toggle from "../components/Toggle.vue";

jest.mock("../common/api.service", () => ({
    __esModule: true,
    default: {
        post: jest.fn(),
    },
}));

import ClubApi from "../common/api.service";

describe("Toggle.vue", () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    function mountToggle(props = {}) {
        return shallowMount(Toggle, {
            propsData: {
                url: "/toggle-url",
                ...props,
            },
            slots: { default: "Toggle me" },
        });
    }

    it("isActive is false by default", () => {
        const wrapper = mountToggle();
        expect(wrapper.vm.isActive).toBe(false);
    });

    it("isActive is true when isActiveByDefault is true", () => {
        const wrapper = mountToggle({ isActiveByDefault: true });
        expect(wrapper.vm.isActive).toBe(true);
    });

    it("sets isActive to true when API returns status 'created'", async () => {
        ClubApi.post.mockImplementation((url, cb) => cb({ status: "created" }));
        const wrapper = mountToggle();

        await wrapper.vm.toggle();

        expect(ClubApi.post).toHaveBeenCalledWith("/toggle-url", expect.any(Function));
        expect(wrapper.vm.isActive).toBe(true);
        expect(wrapper.vm.isLoading).toBe(false);
    });

    it("sets isActive to false when API returns status 'deleted'", async () => {
        ClubApi.post.mockImplementation((url, cb) => cb({ status: "deleted" }));
        const wrapper = mountToggle({ isActiveByDefault: true });

        await wrapper.vm.toggle();

        expect(wrapper.vm.isActive).toBe(false);
        expect(wrapper.vm.isLoading).toBe(false);
    });

    it("sets isLoading to true during toggle", () => {
        ClubApi.post.mockImplementation(() => {
            // don't call callback — simulate pending request
        });
        const wrapper = mountToggle();

        wrapper.vm.toggle();

        expect(wrapper.vm.isLoading).toBe(true);
    });

    it("applies is-active class when active", async () => {
        ClubApi.post.mockImplementation((url, cb) => cb({ status: "created" }));
        const wrapper = mountToggle();

        await wrapper.vm.toggle();
        await wrapper.vm.$nextTick();

        expect(wrapper.classes()).toContain("is-active");
    });
});
