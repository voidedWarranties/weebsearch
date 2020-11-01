// https://github.com/journey-ad/Moe-counter/blob/master/utils/themify.js

const sizeOf = require("image-size");
const path = require("path");
const fs = require("fs");
const FileType = require("file-type");

module.exports = class Counter {
    async init() {
        this.images = [];
        const assetsDir = path.join(__dirname, "../../assets");
        const photos = fs.readdirSync(assetsDir);

        for (const photo of photos) {
            const photoData = fs.readFileSync(path.join(assetsDir, photo));

            const { mime } = await FileType.fromBuffer(photoData);

            const { width, height } = sizeOf(photoData);

            this.images.push({
                url: `data:${mime};base64,${photoData.toString("base64")}`,
                width, height
            });
        }
    }

    getSVG(num) {
        const imgs = [];
    
        var totalWidth = 0;
        var height = 0;
        
        for (let i = 0; i < num.length; i++) {
            const char = num.charAt(i);
            const img = this.images[parseInt(char)];
        
            imgs.push(`<image x="${totalWidth}" href="${img.url}" width="${img.width}" height="${img.height}" />`);
        
            totalWidth += img.width;
            height = Math.max(height, img.height);
        }
        
        return `<svg width="${totalWidth}" height="${height}" xmlns="http://www.w3.org/2000/svg"><g>${imgs.join("")}</g></svg>`;
    }
}