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
    radius: 9
    clip: true
    border.color: Theme.line
    onNotesChanged: canvas.requestPaint()
    onDurationChanged: canvas.requestPaint()
    onLowPitchChanged: canvas.requestPaint()
    Connections { target: Theme; function onLightChanged() { canvas.requestPaint() } }
    Canvas {
        id: canvas
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            let c = getContext("2d"); c.reset()
            const pad = 20, usable = height - 42
            for (let i = 0; i < 9; i++) {
                c.strokeStyle = Theme.line; c.globalAlpha = 0.45
                c.beginPath(); c.moveTo(pad + i * (width - pad * 2) / 8, 15)
                c.lineTo(pad + i * (width - pad * 2) / 8, height - 20); c.stroke()
            }
            c.globalAlpha = 1
            const stride = Math.max(1, Math.ceil(roll.notes.length / 16000))
            for (let i = 0; i < roll.notes.length; i += stride) {
                const n = roll.notes[i]
                const x = pad + n.start / Math.max(.001, roll.duration) * (width - pad * 2)
                const y = 17 + (roll.highPitch - n.pitch) / (roll.highPitch - roll.lowPitch) * usable
                c.fillStyle = n.pitch >= 60 ? Theme.accentFill : (Theme.light ? "#8b9d96" : "#81a49b")
                c.globalAlpha = .8
                c.fillRect(x, y, Math.max(2, n.duration / Math.max(.001, roll.duration) * (width - pad * 2)), 3)
            }
        }
    }
    Rectangle {
        x: 20 + Math.min(1, roll.position / Math.max(.001, roll.duration)) * (parent.width - 40)
        y: 13; width: 1; height: parent.height - 30
        color: Theme.text
        Behavior on x { NumberAnimation { duration: Theme.reduced ? 0 : 40 } }
        Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: -2; width: 5; height: 5; radius: 3; color: Theme.text }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => roll.seek(Math.max(0, Math.min(1,(mouse.x - 20) / (width - 40))) * roll.duration)
    }
}
