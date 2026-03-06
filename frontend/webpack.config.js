const path = require("path");
const webpack = require("webpack");
const BundleTracker = require("webpack-bundle-tracker");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { CleanWebpackPlugin } = require("clean-webpack-plugin");
const { VueLoaderPlugin } = require("vue-loader");

const { NODE_ENV: mode = "production" } = process.env;

module.exports = {
    mode,
    context: __dirname,
    entry: path.join(__dirname, "static/js/main.js"),
    output: {
        path: path.join(__dirname, "static/dist"),
        publicPath: "/static/dist/",
        filename: mode === "production" ? "[name]-[fullhash].js" : "[name].js",
        libraryTarget: "var",
        library: "Club",
    },
    plugins: [
        new BundleTracker({
            path: __dirname,
            filename: "webpack-stats.json",
        }),
        new MiniCssExtractPlugin({
            filename: mode === "production" ? "[name]-[fullhash].css" : "[name].css",
            chunkFilename: "[id].css",
            ignoreOrder: false, // Enable to remove warnings about conflicting order
        }),
        new CleanWebpackPlugin(),
        new VueLoaderPlugin(),
        new webpack.DefinePlugin({
            __VUE_OPTIONS_API__: true,
            __VUE_PROD_DEVTOOLS__: false,
            __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
        }),
    ],
    module: {
        rules: [
            {
                test: /\.css$/,
                exclude: /node_modules/,
                use: [
                    MiniCssExtractPlugin.loader,
                    { loader: "css-loader", options: { importLoaders: 1 } },
                    "postcss-loader",
                ],
            },
            {
                test: /\.(ttf|otf|eot|svg|woff2?)(\?.*)?$/,
                type: "asset/resource",
                generator: {
                    filename: "fonts/[name][ext]",
                },
            },
            {
                test: /\.vue$/,
                loader: "vue-loader",
            },
        ],
    },
    devtool: "source-map",
    resolve: {
        alias: {
            vue: "vue/dist/vue.esm-bundler.js",
        },
    },
};
