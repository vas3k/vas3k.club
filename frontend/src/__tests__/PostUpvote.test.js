import { act } from "react";
import { render } from "../../test/render";
import PostUpvote from "../islands/PostUpvote";
import ClubApi from "../lib/api.service";

vi.mock("../lib/api.service", () => ({ __esModule: true, default: { post: vi.fn(), delete: vi.fn() } }));

describe("PostUpvote", () => {
    let view;
    afterEach(() => { view?.unmount(); vi.resetAllMocks(); });

    it("renders the initial count", () => {
        view = render(PostUpvote, { initialUpvotes: 42 });
        expect(view.container.textContent).toBe("42");
    });
    it("creates and retracts a vote using the server count", async () => {
        ClubApi.post.mockResolvedValue({ post: { upvotes: 6 }, is_voted: true, upvoted_timestamp: Date.now() });
        ClubApi.delete.mockResolvedValue({ post: { upvotes: 4 }, is_voted: false });
        view = render(PostUpvote, { initialUpvotes: 5, voteUrl: "/post/test/votes.json", hoursToRetractVote: 1 });
        await act(async () => view.container.querySelector("a").click());
        expect(ClubApi.post).toHaveBeenCalledWith("/post/test/votes.json");
        expect(view.container.textContent).toBe("6");
        expect(view.container.firstChild.className).toContain("upvote-voted");
        await act(async () => view.container.querySelector("a").click());
        expect(ClubApi.delete).toHaveBeenCalledWith("/post/test/votes.json");
        expect(view.container.textContent).toBe("4");
        expect(view.container.firstChild.className).not.toContain("upvote-voted");
    });
    it("does not retract an expired vote", async () => {
        view = render(PostUpvote, { initialIsVoted: true, initialUpvoteTimestamp: Date.now() - 7200000, hoursToRetractVote: 1 });
        await act(async () => view.container.querySelector("a").click());
        expect(ClubApi.delete).not.toHaveBeenCalled();
        expect(ClubApi.post).not.toHaveBeenCalled();
    });
    it("does not submit a disabled vote", async () => {
        view = render(PostUpvote, { isDisabled: true });
        await act(async () => view.container.querySelector("a").click());
        expect(ClubApi.post).not.toHaveBeenCalled();
        expect(view.container.firstChild.className).toContain("upvote-disabled");
    });
    it("renders and updates the checkbox variant", async () => {
        ClubApi.post.mockResolvedValue({ post: { upvotes: 43 }, is_voted: true });
        view = render(PostUpvote, { initialUpvotes: 42, variant: "checkbox", caption: "Мне тоже интересно!" });
        expect(view.container.textContent).toContain("Мне тоже интересно!");
        expect(view.container.textContent).not.toContain("42");
        expect(view.container.querySelector(".far.fa-square")).not.toBeNull();
        await act(async () => view.container.querySelector("a").click());
        expect(view.container.querySelector(".fas.fa-check-square")).not.toBeNull();
    });
    it("renders a disabled checkbox as checked without a caption", () => {
        view = render(PostUpvote, { variant: "checkbox", caption: "Мне тоже интересно!", isDisabled: true });
        expect(view.container.querySelector(".fas.fa-check-square")).not.toBeNull();
        expect(view.container.querySelector(".upvote-checkbox-caption")).toBeNull();
    });
});
