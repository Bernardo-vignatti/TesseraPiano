import QtQuick

Item {
    id: piano
    property bool extended: true
    property var activeNotes: []
    property int low: extended ? 21 : 36
    property int high: extended ? 108 : 96
    property var whites: {
        let result = []
        for (let p = low; p <= high; p++) if ([0,2,4,5,7,9,11].indexOf(p % 12) >= 0) result.push(p)
        return result
    }
    property var blacks: {
        let result = []
        for (let p = low; p <= high; p++) if ([1,3,6,8,10].indexOf(p % 12) >= 0) result.push(p)
        return result
    }
    readonly property real unit: width / whites.length
    Repeater {
        model: piano.whites
        Rectangle {
            required property int index
            required property var modelData
            x: index * piano.unit + 1
            width: piano.unit - 2
            height: piano.height
            radius: 3
            color: piano.activeNotes.indexOf(modelData) >= 0 ? Theme.accentFill : (Theme.light ? "#fffefa" : "#e8e4db")
            Behavior on color { ColorAnimation { duration: Theme.reduced ? 0 : 65 } }
            Text {
                visible: modelData % 12 === 0
                anchors.bottom: parent.bottom; anchors.bottomMargin: 10; anchors.horizontalCenter: parent.horizontalCenter
                text: "C" + (Math.floor(modelData / 12) - 1)
                font.pixelSize: 9; color: "#7a7975"; font.family: Theme.font
            }
        }
    }
    Repeater {
        model: piano.blacks
        Rectangle {
            required property var modelData
            x: (piano.whites.indexOf(modelData - 1) + 1) * piano.unit - width / 2
            width: piano.unit * .6
            height: piano.height * .63
            radius: 3
            color: piano.activeNotes.indexOf(modelData) >= 0 ? "#ba8849" : "#17191d"
            border.color: "#33353a"
            Behavior on color { ColorAnimation { duration: Theme.reduced ? 0 : 65 } }
        }
    }
}
