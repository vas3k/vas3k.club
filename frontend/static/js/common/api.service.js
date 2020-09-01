const ClubApi = {
    ajaxify(href, callback) {
        const params = {
            method: "POST",
            credentials: "include",
        };

        fetch(href + "?is_ajax=true", params)
            .then((response) => response.json())
            .then((data) => callback(data));
    },

    /**
     * @param {string} markdownPlaintext
     * @param {Function} callback
     */
    markdownPreview(markdownPlaintext, callback) {
        fetch("/markdown/preview/?is_ajax=true", {
            method:  "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            // escapes all characters except A-Z a-z 0-9 - _ . ! ~ * ' ( )
            body: `markdownPlaintext=${encodeURIComponent(markdownPlaintext)}`
        }).
            then(this.handleErrors).
            then((response) => response.json()).
            then(({ markdown }) => callback(markdown)).
            catch(() => callback('Дико извиняемся, но произошла ошибка 🤷‍♂️'))
    },

    handleErrors(response) {
        if (!response.ok) throw Error(response.statusText);
        return response;
    }
};

export default ClubApi;
