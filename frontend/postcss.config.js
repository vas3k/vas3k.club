const cssnano = require("cssnano");
const postcssImport = require("postcss-import");
const postcssNormalize = require("postcss-normalize");
const postcssPresetEnv = require("postcss-preset-env");

const { NODE_ENV: mode = 'production' } = process.env;

module.exports = {
    minimize: mode === 'production',
    plugins: [
        // more: https://github.com/csstools/postcss-normalize#postcss-import-usage
        postcssImport(postcssNormalize().postcssImport()),
        postcssPresetEnv(),
        cssnano()
    ],
};
