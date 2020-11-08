const mongoose = require("mongoose");
const crypto = require("crypto");

const iterations = 10000;
const keyLength = 512;
const digest = "sha256";

const userSchema = new mongoose.Schema({
    username: String,
    password: String,
    salt: String
});

userSchema.pre("save", function(next) {
    const salt = crypto.randomBytes(128).toString("base64");
    const key = crypto.pbkdf2Sync(this.password, salt, iterations, keyLength, digest);

    this.password = key;
    this.salt = salt;
    next();
});

userSchema.methods.verifyPassword = function(password) {
    const key = crypto.pbkdf2Sync(password, this.salt, iterations, keyLength, digest);

    return this.password == key;
}

module.exports = mongoose.model("User", userSchema);
