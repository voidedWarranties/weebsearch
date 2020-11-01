const crypto = require("crypto");
const FileType = require("file-type");
const axios = require("axios");
const fs = require("fs");
const glob = require("glob");
const zmq = require("zeromq");
const { EventEmitter } = require("events");

module.exports.randomString = () => {
    return Math.abs(crypto.randomBytes(5).readInt32LE()).toString(36);
}

module.exports.downloadImage = (url, filePath) => {
    return axios({
        method: "get",
        url,
        responseType: "arraybuffer"
    }).then(async res => {
        const { ext } = await FileType.fromBuffer(res.data);
        const fileLoc = `${filePath}.${ext}`;

        if (glob.sync(`${filePath}.*`).length) return null;

        fs.writeFileSync(fileLoc, res.data);

        return fileLoc;
    });
}

module.exports.imageB64 = url => {
    return axios({
        method: "get",
        url,
        responseType: "arraybuffer"
    }).then(async res => {
        const { mime } = await FileType.fromBuffer(res.data);
        if (!mime.startsWith("image/")) return null;

        return res.data.toString("base64");
    });
}

module.exports.sendAndWait = (id, sock, msg) => {
    return new Promise(async resolve => {
        await sock.send(msg);

        const handler = async res => {
            const begin = `>>${id}$`;
            if (res.startsWith(begin)) {
                const output = res.toString().slice(begin.length).split("$");
                sock.emitter.off("message", handler);
                resolve(output);
            }
        }

        setTimeout(() => {
            sock.emitter.off("message", handler);
            resolve(null);
        }, 15000);

        sock.emitter.on("message", handler);
    });
}

module.exports.IpcSocket = class IpcSocket {
    constructor() {
        this.socket = new zmq.Dealer({
            reconnectInterval: 1000
        });

        this.socket.connect("tcp://127.0.0.1:6969");

        this.emitter = new EventEmitter();

        this.loop();
    }

    async loop() {
        for await (const [msg] of this.socket) {
            this.emitter.emit("message", msg.toString());
        }
    }

    send(msg) {
        return this.socket.send(msg);
    }
}