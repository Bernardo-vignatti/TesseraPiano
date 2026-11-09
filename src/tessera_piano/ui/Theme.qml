pragma Singleton
import QtQuick

QtObject {
    property bool light: false
    property bool reduced: false
    readonly property color bg: light ? "#f5f3ef" : "#1b1d20"
    readonly property color side: light ? "#eeece6" : "#141619"
    readonly property color surface: light ? "#ffffff" : "#23262a"
    readonly property color hover: light ? "#e9e6df" : "#2d3035"
    readonly property color line: light ? "#dcd8d0" : "#35383d"
    readonly property color text: light ? "#252629" : "#f3f0e9"
    readonly property color muted: light ? "#686b70" : "#a2a4aa"
    readonly property color faint: light ? "#87898e" : "#747981"
    readonly property color accent: light ? "#88602a" : "#e0b979"
    readonly property color accentFill: "#e0b979"
    readonly property color accentTint: light ? "#ede4d5" : "#373126"
    readonly property color green: light ? "#25705a" : "#8cceae"
    readonly property color danger: light ? "#af4244" : "#eda3a0"
    readonly property string font: "Segoe UI"
    readonly property int motion: reduced ? 0 : 160
}
