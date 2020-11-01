const { Client } = require("karasu");
const config = require("./config.json");
const path = require("path");
const { IpcSocket } = require("../js_common/utils");

const bot = new Client(config.token, {
    maxShards: "auto"
}, {
    owner: config.owner,
    defaultCommands: true,
    development: config.development,
    categories: [
        {
            id: "search",
            title: "Search",
            description: "Search or manipulate image library"
        }
    ],
    prefix: ","
});

bot.commandRegistry.registerDirectory(path.join(__dirname, "commands"));

bot.on("ready", () => {
    console.log("Logged in");
});

bot.sock = new IpcSocket();

bot.connect();