import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: panel
    implicitWidth: 246
    implicitHeight: Math.min(620, root.height - 180)
    contentWidth: availableWidth
    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        width: panel.availableWidth
        spacing: 12
        Text { text: "EXECUÇÃO"; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5; color: Theme.muted }
        Choice {
            objectName: "sessionChoice"; Layout.fillWidth: true; Layout.minimumWidth: 0
            model: ["Automático", "Guiado · Razer Chroma"]
            currentIndex: backend.settings.session_mode === "guided" ? 1 : 0
            enabled: !backend.playback.busy
            onActivated: index => backend.setSetting("session_mode", index ? "guided" : "auto")
            Accessible.name: "Modo de execução"
        }
        ColumnLayout {
            visible: backend.settings.session_mode === "guided"; Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 12
            Choice {
                objectName: "guideModeChoice"; Layout.fillWidth: true; Layout.minimumWidth: 0; model: ["Acompanhar", "Praticar"]
                currentIndex: backend.settings.guide_mode === "practice" ? 1 : 0; enabled: !backend.playback.busy
                onActivated: index => backend.setSetting("guide_mode", index ? "practice" : "follow")
                Accessible.name: "Orientação"
            }
            Choice {
                Layout.fillWidth: true; Layout.minimumWidth: 0; model: ["Todas as notas", "Melodia simplificada", "Acordes distribuídos"]
                currentIndex: ["full", "melody", "distributed"].indexOf(backend.settings.guide_arrangement); enabled: !backend.playback.busy
                onActivated: index => backend.setSetting("guide_arrangement", ["full", "melody", "distributed"][index])
                Accessible.name: "Arranjo manual"
            }
            Text {
                Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted
                text: backend.features.manualIssues ? "Há combinações incompatíveis. Simplifique ou distribua os acordes." : (backend.settings.guide_mode === "practice" ? "Aguarda as teclas e o pedal corretos." : "Você toca. As luzes acompanham o ritmo.")
            }
            TButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: backend.settings.guide_calibrated ? "Rever calibração" : "Configurar Chroma"; enabled: !backend.playback.busy; onClicked: root.page = 2 }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.minimumWidth: 0
            Text { text: "Velocidade"; Layout.fillWidth: true; Layout.minimumWidth: 0; font.family: Theme.font; font.pixelSize: 12; color: Theme.text }
            TSpinBox { Layout.preferredWidth: 114; Layout.minimumWidth: 100; from: 25; to: 150; stepSize: 5; value: backend.settings.speed; enabled: !backend.playback.busy; onValueModified: backend.setSetting("speed", value); Accessible.name: "Velocidade de execução" }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.minimumWidth: 0
            TButton { text: "A"; Accessible.name: "Marcar início do trecho"; compact: true; enabled: !backend.playback.busy; onClicked: backend.markLoop("a") }
            TButton { text: "B"; Accessible.name: "Marcar fim do trecho"; compact: true; enabled: !backend.playback.busy; onClicked: backend.markLoop("b") }
            TButton { text: "Limpar"; compact: true; enabled: !backend.playback.busy && backend.settings.loop_enabled; onClicked: backend.markLoop("clear") }
        }
        Text { Layout.fillWidth: true; Layout.minimumWidth: 0; visible: backend.settings.loop_enabled; text: "Repetir " + root.timeText(backend.settings.loop_start) + "–" + root.timeText(backend.settings.loop_end); font.family: Theme.font; font.pixelSize: 11; color: Theme.accent }
        Rectangle { Layout.fillWidth: true; Layout.minimumWidth: 0; height: 1; color: Theme.line }
        Text { text: "INTERPRETAÇÃO"; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5; color: Theme.muted }
        Choice {
            objectName: "performanceChoice"; Layout.fillWidth: true; Layout.minimumWidth: 0
            model: ["Original", "Natural", "Expressivo"]
            currentIndex: ["original", "natural", "expressive"].indexOf(backend.settings.performance)
            onActivated: index => backend.setSetting("performance", ["original", "natural", "expressive"][index])
            enabled: !backend.playback.busy; Accessible.name: "Interpretação"
        }
        Choice {
            objectName: "profileChoice"; Layout.fillWidth: true; Layout.minimumWidth: 0
            model: ["Perfil automático", "Contido", "Cantabile", "Rítmico"]
            currentIndex: ["auto", "restrained", "cantabile", "rhythmic"].indexOf(backend.settings.expression_profile)
            onActivated: index => backend.setSetting("expression_profile", ["auto", "restrained", "cantabile", "rhythmic"][index])
            enabled: !backend.playback.busy && backend.settings.performance !== "original"; Accessible.name: "Perfil musical"
        }
        Text { Layout.fillWidth: true; Layout.minimumWidth: 0; text: backend.song.profile ? backend.song.profile + " · " + backend.song.expressionOrigin : ""; elide: Text.ElideRight; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
        RowLayout {
            Layout.fillWidth: true; Layout.minimumWidth: 0
            Text { text: "Expressão"; font.family: Theme.font; font.pixelSize: 12; color: Theme.text; Layout.fillWidth: true; Layout.minimumWidth: 0 }
            Text { text: Math.round(intensity.value) + "%"; font.family: Theme.font; font.pixelSize: 11; color: Theme.accent }
        }
        TSlider {
            id: intensity; Layout.fillWidth: true; Layout.minimumWidth: 0; from: 0; to: 100; stepSize: 1; value: backend.settings.intensity
            enabled: !backend.playback.busy && backend.settings.performance !== "original"; Accessible.name: "Intensidade da interpretação"
            onMoved: { if (!pressed) backend.setSetting("intensity", Math.round(value)) }
            onPressedChanged: { if (!pressed) backend.setSetting("intensity", Math.round(value)) }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.minimumWidth: 0
            TButton { text: "Variar"; compact: true; enabled: !backend.playback.busy && !backend.song.preparing; onClicked: backend.setSetting("seed", (backend.settings.seed + 1) % 2147483647) }
            TButton { text: "Motor local"; compact: true; onClicked: root.page = 2 }
        }
        Rectangle { Layout.fillWidth: true; Layout.minimumWidth: 0; height: 1; color: Theme.line }
        Text { text: "Pedal de sustentação"; font.family: Theme.font; font.pixelSize: 12; color: Theme.text }
        Choice {
            Layout.fillWidth: true; Layout.minimumWidth: 0; model: ["Automático", "Apenas MIDI", "Ligado", "Desligado", "Manual"]
            currentIndex: ["auto", "midi", "on", "off", "ignore"].indexOf(backend.settings.pedal_mode)
            onActivated: index => backend.setSetting("pedal_mode", ["auto", "midi", "on", "off", "ignore"][index])
            enabled: !backend.playback.busy; Accessible.name: "Pedal de sustentação"
        }
        Text { text: "Alcance do piano"; font.family: Theme.font; font.pixelSize: 12; color: Theme.text }
        Choice {
            Layout.fillWidth: true; Layout.minimumWidth: 0; model: ["61 teclas · C2–C7", "88 teclas · A0–C8"]
            currentIndex: backend.settings.layout === "88" ? 1 : 0
            onActivated: index => backend.setSetting("layout", index ? "88" : "61")
            enabled: !backend.playback.busy; Accessible.name: "Alcance do piano"
        }
        Text { Layout.fillWidth: true; Layout.minimumWidth: 0; visible: backend.settings.layout === "88"; text: "Ative também 88key no jogo."; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
        Item { Layout.preferredHeight: 8 }
    }
}
