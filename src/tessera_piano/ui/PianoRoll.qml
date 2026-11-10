import QtQuick

Rectangle {
    id: roll
    property var notes: []
    property real duration: 1
    property real position: 0
    property int lowPitch: 21
    property int highPitch: 108
    signal seek(real seconds)
    color: Theme.side
    radius: 14
    clip: true
    border.color: Theme.line
    onNotesChanged: canvas.requestPaint()
    onDurationChanged: canvas.requestPaint()
    onLowPitchChanged: canvas.requestPaint()
    onHighPitchChanged: canvas.requestPaint()
    Connections { target: Theme; function onLightChanged() { canvas.requestPaint() } }
    Canvas {
        id: canvas
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            let c = getContext("2d"); c.reset()
            const pad = 24, usable = height - 65
            c.fillStyle = Theme.muted; c.font = "9px 'Segoe UI'"
            c.fillText("PARTITURA", 20, 21)
            for (let i = 0; i < 9; i++) {
                c.strokeStyle = Theme.line; c.globalAlpha = 0.45
                const x = pad + i * (width - pad * 2) / 8
                c.beginPath(); c.moveTo(x, 36)
                c.lineTo(x, height - 25); c.stroke()
                const t = roll.duration * i / 8
                c.globalAlpha = 1; c.fillStyle = Theme.faint
                c.fillText(Math.floor(t / 60) + ":" + ("0" + Math.floor(t % 60)).slice(-2), x - 10, height - 9)
            }
            c.globalAlpha = 1
            const stride = Math.max(1, Math.ceil(roll.notes.length / 16000))
            for (let i = 0; i < roll.notes.length; i += stride) {
                const n = roll.notes[i]
                const x = pad + n.start / Math.max(.001, roll.duration) * (width - pad * 2)
                const y = 38 + (roll.highPitch - n.pitch) / (roll.highPitch - roll.lowPitch) * usable
                c.fillStyle = n.pitch >= 60 ? Theme.accentFill : (Theme.light ? "#8b9d96" : "#81a49b")
                c.globalAlpha = .8
                c.fillRect(x, y, Math.max(2, n.duration / Math.max(.001, roll.duration) * (width - pad * 2)), 3)
            }
        }
    }
    Rectangle {
        x: 24 + Math.min(1, roll.position / Math.max(.001, roll.duration)) * (parent.width - 48)
        y: 34; width: 1; height: parent.height - 59
        color: Theme.text
        Behavior on x { NumberAnimation { duration: Theme.reduced ? 0 : 40 } }
        Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: -2; width: 5; height: 5; radius: 3; color: Theme.text }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => roll.seek(Math.max(0, Math.min(1,(mouse.x - 24) / (width - 48))) * roll.duration)
    }
}
