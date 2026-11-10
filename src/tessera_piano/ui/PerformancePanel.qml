import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 14
    Text { text: "INTERPRETAÇÃO"; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5; color: Theme.muted }
    Choice {
        objectName: "performanceChoice"
        Layout.fillWidth: true
        model: ["Original", "Natural", "Expressivo"]
        currentIndex: ["original", "natural", "expressive"].indexOf(backend.settings.performance)
        onActivated: index => backend.setSetting("performance", ["original", "natural", "expressive"][index])
        enabled: !backend.playback.busy
        Accessible.name: "Interpretação"
    }
    RowLayout {
        Layout.fillWidth: true; Layout.topMargin: 6
        Text { text: "Intensidade"; font.family: Theme.font; font.pixelSize: 12; color: Theme.text; Layout.fillWidth: true }
        Text { text: Math.round(intensity.value) + "%"; font.family: Theme.font; font.pixelSize: 11; color: Theme.accent }
    }
    TSlider {
        id: intensity
        Layout.fillWidth: true; from: 0; to: 100; stepSize: 1
        value: backend.settings.intensity
        enabled: !backend.playback.busy && backend.settings.performance !== "original"
        Accessible.name: "Intensidade da interpretação"
        onMoved: { if (!pressed) backend.setSetting("intensity", Math.round(value)) }
        onPressedChanged: { if (!pressed) backend.setSetting("intensity", Math.round(value)) }
    }
    Rectangle { Layout.fillWidth: true; Layout.topMargin: 6; Layout.bottomMargin: 6; height: 1; color: Theme.line }
    Text { text: "Pedal de sustentação"; font.family: Theme.font; font.pixelSize: 12; color: Theme.text }
    Choice {
        Layout.fillWidth: true
        model: ["Automático", "Apenas MIDI", "Ligado", "Desligado", "Manual"]
        currentIndex: ["auto", "midi", "on", "off", "ignore"].indexOf(backend.settings.pedal_mode)
        onActivated: index => backend.setSetting("pedal_mode", ["auto", "midi", "on", "off", "ignore"][index])
        enabled: !backend.playback.busy
        Accessible.name: "Pedal de sustentação"
    }
    Rectangle { Layout.fillWidth: true; Layout.topMargin: 6; Layout.bottomMargin: 6; height: 1; color: Theme.line }
    Text { text: "Alcance do piano"; font.family: Theme.font; font.pixelSize: 12; color: Theme.text }
    Choice {
        Layout.fillWidth: true
        model: ["61 teclas · C2–C7", "88 teclas · A0–C8"]
        currentIndex: backend.settings.layout === "88" ? 1 : 0
        onActivated: index => backend.setSetting("layout", index ? "88" : "61")
        enabled: !backend.playback.busy
        Accessible.name: "Alcance do piano"
    }
    Text { Layout.fillWidth: true; visible: backend.settings.layout === "88"; text: "Ative também 88key no jogo."; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
    Item { Layout.fillHeight: true }
}
