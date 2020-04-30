const path = require("path");
const BundleTracker = require("webpack-bundle-tracker");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
    mode: "development",
    context: __dirname,
    entry: {
        scripts: [
            path.join(__dirname, "static/js/main.js"),
        ],
        styles: [
            path.join(__dirname, "static/css/normalize.css"),
            path.join(__dirname, "static/css/fontawesome.min.css"),
            path.join(__dirname, "static/css/theme.css"),
            path.join(__dirname, "static/css/base.css"),
            path.join(__dirname, "static/css/layout.css"),
            path.join(__dirname, "static/css/components.css"),
            path.join(__dirname, "static/css/posts.css"),
        ]
    },
    output: {
        path: path.join(__dirname, "static/dist"),
        filename: "[name]-[hash].js"
    },
    resolve: {
        extensions: [".js", ".jsx", ".json", ".css"]
    },
    plugins: [
        require('autoprefixer'),
        new BundleTracker({filename: "webpack-stats.json"}),
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
                    "css-loader",
                    {
                        loader: 'postcss-loader',
                        options: {
                            ident: 'postcss',
                            plugins: [
                                require('autoprefixer')(),
                            ]
                        }
                    },
                ],
            },
            {
                test: /.(ttf|otf|eot|svg|woff(2)?)(\?[a-z0-9]+)?$/,
                use: [{
                    loader: "file-loader",
                    options: {
                        name: "[name].[ext]",
                        outputPath: "fonts/",    // where the fonts will go
                        publicPath: "fonts/"       // override the default path
                    }
                }]
            }
        ]
    },
    devtool: "source-map",
};
