const { NODE_ENV: mode = 'production' } = process.env;

module.exports = {
    plugins: {
        "postcss-import": {},
        "postcss-preset-env": {},
        "cssnano": mode === 'production' ? {} : false
    }
};
