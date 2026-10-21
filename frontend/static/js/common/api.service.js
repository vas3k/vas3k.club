const ClubApi = {
    async request(href, params, callback) {
        let data;

        try {
            const response = await fetch(href, {
                credentials: "include",
                ...params,
                headers: { Accept: "application/json", ...params.headers },
            });
            data = await response.json();

            if (!response.ok) {
                const error = data.error || {};
                throw new Error(error.message || error.title || `HTTP error! status: ${response.status}`);
            }
        } catch (error) {
            if (!callback) {
                throw error;
            }

            return callback({ error: error.message });
        }

        return callback ? callback(data) : data;
    },

    post(href, callback) {
        return this.request(href, { method: "POST" }, callback);
    },

    postForm(href, data, callback) {
        return this.request(href, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8" },
            body: new URLSearchParams(data).toString(),
        }, callback);
    },

    delete(href, callback) {
        return this.request(href, { method: "DELETE" }, callback);
    },

    get(href, callback) {
        return this.request(href, { method: "GET" }, callback);
    },
};

export default ClubApi;
