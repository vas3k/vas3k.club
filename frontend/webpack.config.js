const path = require("path");
const BundleTracker = require("webpack-bundle-tracker");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
    context: __dirname,
    entry: path.join(__dirname, "static/js/main.js"),
    output: {
        path: path.join(__dirname, "static/dist"),
        filename: "[name]-[hash].js",
        libraryTarget: "var",
        library: "Club",
    },
    plugins: [
        new BundleTracker(),
        new MiniCssExtractPlugin({
            filename: "[name]-[hash].css",
            chunkFilename: "[id].css",
            ignoreOrder: false, // Enable to remove warnings about conflicting order
        }),
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
            }
        ]
    },
    devtool: "source-map",
};
