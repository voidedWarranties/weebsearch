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

            this.bot.sock.search(id, b64, 0, true).then(output => {
                if (!output.success) {
                    return msg.channel.createMessage("No results");
                }

                const jsonOutput = output.data;

                const plt = output.plot;

                msg.channel.createMessage(`**performance**:\n${jsonOutput.performance}`, {
                    file: Buffer.from(plt, "base64"),
                    name: "out.png"
                });
            }).catch(() => {
                return msg.channel.createMessage("Timed out");
            });
        });
    }
}
