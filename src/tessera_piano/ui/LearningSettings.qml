import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Column {
    spacing: 20
    Text { text: "MOTOR MUSICAL LOCAL"; color: Theme.faint; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5 }
    Surface {
        width: parent.width; height: modelColumn.height
        Column {
            id: modelColumn; width: parent.width
            SettingRow {
                width: parent.width; title: "Preparação da interpretação"; detail: "O modelo trabalha offline após instalar o pacote adicional."
                editor: Choice {
                    objectName: "engineChoice"; model: ["Regras musicais", "Modelo local"]
                    currentIndex: backend.settings.expression_engine === "model" ? 1 : 0
                    enabled: !backend.playback.busy && backend.features.modelReady
                    onActivated: index => backend.setSetting("expression_engine", index ? "model" : "rules")
                }
            }
            Column {
                x: 20; width: parent.width - 40; topPadding: 12; bottomPadding: 20; spacing: 10
                Text { width: parent.width; text: backend.features.modelReady ? "Pianist Transformer · instalado" : "Pacote CPU opcional · 480 MB de download · 1,6 GB instalados"; wrapMode: Text.WordWrap; color: Theme.muted; font.family: Theme.font; font.pixelSize: 12 }
                ProgressBar { width: parent.width; visible: backend.features.modelState === "installing"; value: backend.features.modelProgress; palette.highlight: Theme.accent }
                Row {
                    spacing: 8
                    TButton { objectName: "installModelButton"; text: backend.features.modelReady ? "Reinstalar motor" : "Instalar motor local"; visible: backend.features.modelState !== "installing"; enabled: !backend.playback.busy && !backend.song.preparing; onClicked: backend.installModel() }
                    TButton { text: "Cancelar instalação"; visible: backend.features.modelState === "installing"; onClicked: backend.cancelModel() }
                }
            }
        }
    }
    Text { text: "RAZER CHROMA"; color: Theme.faint; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5 }
    Surface {
        width: parent.width; height: guideColumn.height
        Column {
            id: guideColumn; width: parent.width
            SettingRow {
                width: parent.width; title: "Conferir as luzes"; detail: "Números → letras → Shift, Ctrl e Espaço."
                editor: TButton { objectName: "testChromaButton"; text: backend.features.chromaState === "testing" ? "Testando…" : "Testar teclado"; enabled: !backend.playback.busy && backend.features.chromaState !== "testing"; onClicked: backend.testChroma() }
            }
            SettingRow {
                width: parent.width; title: "As teclas acenderam corretamente"; detail: "Confirme no teclado físico antes de iniciar o modo guiado."
                editor: TSwitch { objectName: "confirmChroma"; text: checked ? "Confirmado" : "Confirmar"; checked: backend.settings.guide_calibrated; enabled: !backend.playback.busy && (backend.settings.guide_calibrated || backend.features.chromaState === "tested"); onToggled: backend.setSetting("guide_calibrated", checked) }
            }
            SettingRow { width: parent.width; title: "Antecedência das luzes (ms)"; editor: TSpinBox { from: 150; to: 2000; stepSize: 50; value: backend.settings.guide_lead; enabled: !backend.playback.busy; editable: true; onValueModified: backend.setSetting("guide_lead", value) } }
            SettingRow { width: parent.width; title: "Compensação do atraso (ms)"; detail: "Valores positivos antecipam a orientação luminosa."; editor: TSpinBox { from: -300; to: 300; stepSize: 10; value: backend.settings.guide_latency; enabled: !backend.playback.busy; editable: true; onValueModified: backend.setSetting("guide_latency", value) } }
            SettingRow { width: parent.width; title: "Progredir ao repetir"; detail: "Com 80% de acertos, aumenta 5% por trecho até 100%."; editor: TSwitch { checked: backend.settings.guide_ramp; enabled: !backend.playback.busy; text: checked ? "Ativado" : "Desativado"; onToggled: backend.setSetting("guide_ramp", checked) } }
            SettingRow { width: parent.width; title: "Brilho (%)"; editor: TSpinBox { from: 10; to: 100; stepSize: 5; value: backend.settings.guide_brightness; enabled: !backend.playback.busy; onValueModified: backend.setSetting("guide_brightness", value) } }
            SettingRow { width: parent.width; title: "Paleta das luzes"; editor: Choice { model: ["Âmbar e azul", "Turquesa e violeta"]; currentIndex: backend.settings.guide_palette === "teal" ? 1 : 0; enabled: !backend.playback.busy; onActivated: index => backend.setSetting("guide_palette", index ? "teal" : "amber") } }
            SettingRow { width: parent.width; title: "Limite de teclas simultâneas"; detail: "Inclui modificadores e Espaço. Cynosa Chroma: 10."; editor: TSpinBox { from: 2; to: 30; value: backend.settings.guide_rollover; enabled: !backend.playback.busy; onValueModified: backend.setSetting("guide_rollover", value) } }
            SettingRow { width: parent.width; title: "Ajustar posição de uma luz"; detail: "Correção para mapas físicos diferentes do padrão Razer."; editor: TButton { text: "Ajustar mapa"; enabled: !backend.playback.busy; onClicked: mapDialog.open() } }
        }
    }
    TDialog {
        id: mapDialog; objectName: "chromaMapDialog"; title: "Posição da luz"; acceptText: "Salvar posição"
        onAccepted: backend.mapChromaKey(mapKey.currentText, mapRow.value - 1, mapColumn.value - 1)
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: "Matriz Razer: 6 linhas × 22 colunas."; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
            Choice { id: mapKey; Layout.fillWidth: true; model: "1234567890qwertyuiopasdfghjklzxcvbnm".split("").concat(["shift", "ctrl", "space"]); Accessible.name: "Tecla da luz" }
            RowLayout {
                Text { text: "Linha"; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                TSpinBox { id: mapRow; from: 1; to: 6; value: backend.chromaPosition(mapKey.currentText)[0] + 1; editable: true }
                Text { text: "Coluna"; color: Theme.text; font.family: Theme.font; font.pixelSize: 12 }
                TSpinBox { id: mapColumn; from: 1; to: 22; value: backend.chromaPosition(mapKey.currentText)[1] + 1; editable: true }
            }
        }
    }
}
