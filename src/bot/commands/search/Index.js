const { Command } = require("karasu");
const config = require("../../config.json");
const { randomString, downloadImage, sendAndWait } = require("../../../js_common/utils");

module.exports = class IndexCommand extends Command {
    constructor(bot) {
        super(bot, "index", {
            category: "search"
        });
    }

    run(msg, args) {
        if (!config.curators.includes(msg.author.id)) return "No permissions";

        const attachments = msg.attachments;

        const url = attachments.length ? attachments[0].url : args[0];

        if (!url) return "No image specified";

        const id = randomString();

        downloadImage(url, `library/${id}`).then(async filePath => {
            if (!filePath) return;

            const output = await sendAndWait(id, this.bot.sock, `process$${id}$${filePath}`);
            if (!output) {
                return msg.channel.createMessage("Timed out");
            }
            await msg.channel.createMessage(`Created ${output[1]}`);

            await sendAndWait(id, this.bot.sock, `index$${id}$${filePath}`);
        });
    }
}