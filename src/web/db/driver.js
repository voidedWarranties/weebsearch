const mongoose = require("mongoose");

const uri = "mongodb://localhost:27017/weebsearch";
mongoose.connect(uri, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
    useFindAndModify: true
});

const db = mongoose.connection;

db.once("open", () => {
    console.log(`MongoDB connected to ${uri}`);
});

module.exports = db;
