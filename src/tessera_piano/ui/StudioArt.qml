import QtQuick

Canvas {
    id: art
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Connections { target: Theme; function onLightChanged() { art.requestPaint() } }
    onPaint: {
        const c = getContext("2d")
        c.reset()
        const light = c.createRadialGradient(width - 90, 18, 0, width - 90, 18, 230)
        light.addColorStop(0, Theme.light ? "rgba(176,133,69,.23)" : "rgba(221,173,104,.23)")
        light.addColorStop(1, "rgba(221,173,104,0)")
        c.fillStyle = light; c.fillRect(0, 0, width, height)
        c.save(); c.translate(width - 320, 35); c.rotate(-.26)
        c.beginPath(); c.moveTo(30, 105); c.lineTo(36, 9)
        c.bezierCurveTo(110, -17, 128, -42, 210, -9)
        c.bezierCurveTo(258, 11, 251, 62, 318, 89)
        c.lineTo(318, 113); c.closePath()
        const lid = c.createLinearGradient(60, -25, 260, 130)
        lid.addColorStop(0, "#5a6260"); lid.addColorStop(.07, "#3b4444")
        lid.addColorStop(.65, "#1c2427"); lid.addColorStop(1, "#13191c")
        c.shadowColor = "rgba(17,22,24,.27)"; c.shadowBlur = 20; c.shadowOffsetY = 12
        c.fillStyle = lid; c.fill(); c.shadowBlur = 0; c.shadowOffsetY = 0
        c.strokeStyle = "#8f8266"; c.lineWidth = 1; c.stroke()
        c.save(); c.clip()
        for (let i = 0; i < 29; i++) {
            c.beginPath(); c.moveTo(68 + i * 7.4, -25); c.lineTo(46 + i * 8.3, 92)
            c.strokeStyle = i % 3 ? "rgba(201,172,123,.13)" : "rgba(224,190,131,.28)"
            c.lineWidth = .7; c.stroke()
        }
        c.restore()
        c.fillStyle = "#10171a"; c.fillRect(32, 88, 286, 79)
        const ivory = c.createLinearGradient(0, 93, 0, 160)
        ivory.addColorStop(0, "#a7b0ae"); ivory.addColorStop(.24, "#e3e1d4")
        ivory.addColorStop(.89, "#d0cbbd"); ivory.addColorStop(1, "#8a918c")
        for (let k = 0; k < 23; k++) {
            const x = 37 + k * 12
            c.fillStyle = ivory; c.fillRect(x, 93, 11, 67)
            c.fillStyle = "#8e9995"; c.fillRect(x, 159, 11, 3)
            if ([0, 1, 3, 4, 5].includes(k % 7)) {
                c.fillStyle = "#10171b"; c.fillRect(x + 7, 92, 8, 42)
                c.fillStyle = "#303b3f"; c.fillRect(x + 8, 94, 6, 3)
            }
        }
        c.restore()
    }
}
