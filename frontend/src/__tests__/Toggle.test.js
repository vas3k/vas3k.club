import { act } from "react";
import { render } from "../../test/render";
import Toggle from "../components/Toggle";
import ClubApi from "../lib/api.service";

vi.mock("../lib/api.service", () => ({ __esModule: true, default: { post: vi.fn(), delete: vi.fn() } }));

describe("Toggle", () => {
    let view;
    afterEach(() => { view?.unmount(); vi.resetAllMocks(); });

    it.each([false, true])("renders the initial active state %s", (active) => {
        view = render(Toggle, { url: "/resource.json", isActiveByDefault: active });
        expect(view.container.querySelector("input").checked).toBe(active);
    });

    it("creates and removes the resource with the corresponding HTTP method", async () => {
        ClubApi.post.mockResolvedValue({ status: "created" });
        ClubApi.delete.mockResolvedValue({ status: "deleted" });
        view = render(Toggle, { url: "/resource.json", label: "Toggle" });
        await act(async () => view.container.querySelector("label").click());
        expect(ClubApi.post).toHaveBeenCalledWith("/resource.json");
        expect(view.container.querySelector("input").checked).toBe(true);
        expect(view.container.firstChild.className).toContain("is-active");
        await act(async () => view.container.querySelector("input").click());
        expect(ClubApi.delete).toHaveBeenCalledWith("/resource.json");
        expect(view.container.querySelector("input").checked).toBe(false);
    });

    it("prevents repeated requests while saving", async () => {
        let finish;
        ClubApi.post.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
        view = render(Toggle, { url: "/resource.json" });
        act(() => view.container.querySelector("input").click());
        expect(view.container.querySelector("input").disabled).toBe(true);
        act(() => view.container.querySelector("input").click());
        expect(ClubApi.post).toHaveBeenCalledTimes(1);
        await act(async () => finish({ status: "created" }));
        expect(view.container.querySelector("input").disabled).toBe(false);
    });

    it("inverts resource state for muted rooms", async () => {
        ClubApi.post.mockResolvedValue({ status: "created" });
        ClubApi.delete.mockResolvedValue({ status: "deleted" });
        view = render(Toggle, { url: "/resource.json", isInverted: true, isActiveByDefault: true });
        await act(async () => view.container.querySelector("input").click());
        expect(ClubApi.post).toHaveBeenCalledTimes(1);
        expect(view.container.querySelector("input").checked).toBe(false);
        await act(async () => view.container.querySelector("input").click());
        expect(ClubApi.delete).toHaveBeenCalledTimes(1);
        expect(view.container.querySelector("input").checked).toBe(true);
    });
});
