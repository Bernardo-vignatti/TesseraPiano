import QtQuick
import QtQuick.Controls

ToolTip {
    id: tip
    delay: 650
    padding: 10
    font.family: Theme.font; font.pixelSize: 11
    contentItem: Text { text: tip.text; color: Theme.text; font: tip.font; wrapMode: Text.WordWrap }
    background: Surface { radius: 8 }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.fast } }
}
