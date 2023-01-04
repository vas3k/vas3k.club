const path = require("path");
const BundleTracker = require("webpack-bundle-tracker");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { CleanWebpackPlugin } = require("clean-webpack-plugin");
const { VueLoaderPlugin } = require("vue-loader");

const { NODE_ENV: mode = 'production' } = process.env;

module.exports = {
    mode,
    context: __dirname,
    entry: path.join(__dirname, "static/js/main.js"),
    output: {
        path: path.join(__dirname, "static/dist"),
        publicPath: "/static/dist/",
        filename: mode === "production" ? "[name]-[hash].js": "[name].js",
        libraryTarget: "var",
        library: "Club",
    },
    plugins: [
        new BundleTracker({
            path: __dirname,
            filename: "webpack-stats.json",
        }),
        new MiniCssExtractPlugin({
            filename: mode === "production" ? "[name]-[hash].css": "[name].css",
            chunkFilename: "[id].css",
            ignoreOrder: false, // Enable to remove warnings about conflicting order
        }),
        new CleanWebpackPlugin(),
        new VueLoaderPlugin(),
    ],
    module: {
        rules: [
            {
                test: /\.css$/,
                exclude: /node_modules/,
                use: [
                    MiniCssExtractPlugin.loader,
                    { loader: 'css-loader', options: { importLoaders: 1 } },
                    "postcss-loader",
                ],
            },
            {
                test: /.(ttf|otf|eot|svg|woff(2)?)(\?[a-z0-9]+)?$/,
                use: [{
                    loader: "file-loader",
                    options: {
                        name: "[name].[ext]",
                        outputPath: "fonts/",    // where the fonts will go
                        publicPath: "fonts/"     // override the default path
                    }
                }]
            },
            {
                test: /\.vue$/,
                loader: "vue-loader"
            }
        ]
    },
    devtool: "source-map",
    resolve: {
        alias: {
            vue: mode === "production" ? "vue/dist/vue.min.js" : "vue/dist/vue.js",
            "vue-mapbox-ho": "vue-mapbox-ho/dist/vue-mapbox.min.js",
        }
    }
};
