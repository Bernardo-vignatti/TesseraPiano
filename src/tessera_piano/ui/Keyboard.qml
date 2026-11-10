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
            readonly property bool sounding: piano.activeNotes.indexOf(modelData) >= 0
            x: index * piano.unit + .5
            width: piano.unit - 1
            height: piano.height
            radius: 3
            gradient: Gradient {
                GradientStop { position: 0; color: sounding ? "#d1ac73" : "#b9c3c1" }
                GradientStop { position: .16; color: sounding ? "#e4c48f" : "#ecece3"; Behavior on color { ColorAnimation { duration: Theme.reduced ? 0 : 65 } } }
                GradientStop { position: .92; color: sounding ? "#e4bb7c" : "#dbddd5" }
                GradientStop { position: 1; color: sounding ? "#9f7950" : "#909c99" }
            }
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
            readonly property bool sounding: piano.activeNotes.indexOf(modelData) >= 0
            gradient: Gradient {
                GradientStop { position: 0; color: sounding ? "#bc965d" : "#3e4b50" }
                GradientStop { position: .1; color: sounding ? "#9d7640" : "#253039" }
                GradientStop { position: .87; color: sounding ? "#a98046" : "#10191f"; Behavior on color { ColorAnimation { duration: Theme.reduced ? 0 : 65 } } }
                GradientStop { position: 1; color: sounding ? "#80603a" : "#354149" }
            }
            border.color: "#111a20"
            Rectangle { x: 2; y: 3; width: parent.width - 4; height: 1; color: "#677477"; opacity: .5 }
        }
    }
}
