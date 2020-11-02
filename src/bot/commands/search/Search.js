const { Command } = require("karasu");
const { randomString, imageB64 } = require("../../../js_common/utils");

module.exports = class SearchCommand extends Command {
    constructor(bot) {
        super(bot, "search", {
            category: "search"
        });
    }

    run(msg, args) {
        const attachments = msg.attachments;

        const url = attachments.length ? attachments[0].url : args[0];

        if (!url) return "No image specified";

        const id = randomString();

        imageB64(url).then(async b64 => {
            if (!b64) return;

            const output = await this.bot.sock.sendAndWait(id, `search$${id}$${b64}`);

            if (!output) {
                return msg.channel.createMessage("Timed out");
            }

            if (output[1] == "failed") {
                return msg.channel.createMessage("No results");
            }

            const jsonOutput = JSON.parse(output[1]);

            const plt = output[2];

            await msg.channel.createMessage(`**performance**:\n${jsonOutput.performance}`, {
                file: Buffer.from(plt, "base64"),
                name: "out.png"
            });
        });
    }
}