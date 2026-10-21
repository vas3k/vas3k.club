const ClubApi = {
    async request(href, params = {}) {
        const response = await fetch(href, {
            credentials: "include",
            ...params,
            headers: { Accept: "application/json", ...params.headers },
        });
        const data = await response.json();
        if (!response.ok) {
            const error = data.error || {};
            throw new Error(error.message || error.title || `HTTP error! status: ${response.status}`);
        }
        return data;
    },

    post(href) {
        return this.request(href, { method: "POST" });
    },

    postForm(href, data) {
        return this.request(href, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8" },
            body: new URLSearchParams(data).toString(),
        });
    },

    delete(href) {
        return this.request(href, { method: "DELETE" });
    },

    get(href) {
        return this.request(href);
    },
};

export default ClubApi;
