const ClubApi = {
    ajaxify(href, { method = 'POST' }, callback) {
        const params = {
            method,
            credentials: "include",
        };

        fetch( `${href}?is_ajax=true`, params)
            .then((response) => response.json())
            .then((data) => callback(data));
    },
};

export default ClubApi;
