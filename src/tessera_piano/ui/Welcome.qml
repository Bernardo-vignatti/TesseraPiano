import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: wizard
    objectName: "setupWizard"
    property int step: 0
    property string chosenTheme: backend.settings.theme
    property string chosenLayout: backend.settings.layout
    property string chosenStyle: backend.settings.performance
    property string chosenPedal: "auto"
    property bool chosenTray: backend.settings.minimize_to_tray
    property bool chosenMotion: backend.settings.reduced_motion
    property bool chosenUpdates: backend.settings.check_updates
    width: Math.min(700, parent.width - 64)
    height: 510
    anchors.centerIn: Overlay.overlay
    modal: true; focus: true
    closePolicy: Popup.NoAutoClose
    padding: 34
    Overlay.modal: Rectangle { color: "#b00b0c0e" }
    background: Rectangle { color: Theme.bg; radius: 15; border.color: Theme.line }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motion } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.motion } }
    onStepChanged: appear.restart()
    ColumnLayout {
        anchors.fill: parent; spacing: 20
        RowLayout {
            Layout.fillWidth: true
            Row {
                spacing: 9
                Image { source: "../resources/icons/tessera-48.png"; width: 27; height: 27; sourceSize.width: 54; sourceSize.height: 54 }
                Text { text: "Tessera Piano"; anchors.verticalCenter: parent.verticalCenter; font.family: Theme.font; font.pixelSize: 16; font.weight: Font.DemiBold; color: Theme.text }
            }
            Item { Layout.fillWidth: true }
            Text { text: wizard.step ? wizard.step + " de 4" : "PRIMEIROS PASSOS"; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1; color: Theme.muted }
        }
        Item {
            id: body
            Layout.fillWidth: true; Layout.fillHeight: true
            NumberAnimation { id: appear; target: body; property: "opacity"; from: .25; to: 1; duration: Theme.motion }
            StackLayout {
                anchors.fill: parent; currentIndex: wizard.step
                ColumnLayout {
                    spacing: 17
                    Item { Layout.fillHeight: true }
                    Text { text: "Um espaço para o seu repertório."; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 32; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: "Prepare o Tessera para o seu piano. São quatro passos rápidos para escolher a aparência e o jeito de tocar."; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 14; lineHeight: 1.35; color: Theme.muted }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 65; radius: 8; color: Theme.surface; border.color: Theme.line
                        Text { anchors.fill: parent; anchors.margins: 16; text: "Sua biblioteca e suas preferências ficam neste computador. Você pode rever tudo nas configurações."; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted; verticalAlignment: Text.AlignVCenter }
                    }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    spacing: 13
                    Text { text: "Escolha a aparência"; font.family: Theme.font; font.pixelSize: 27; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: "Uma interface confortável para as suas sessões."; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
                    RowLayout {
                        Layout.fillWidth: true; Layout.topMargin: 15; spacing: 14
                        Repeater {
                            model: [{key:"dark",title:"Escuro",bg:"#1b1d20",side:"#141619",fg:"#e8e4dc"},{key:"light",title:"Claro",bg:"#f5f3ef",side:"#e8e5df",fg:"#444749"},{key:"system",title:"Sistema",bg:"#777a7b",side:"#434749",fg:"#e8e4dc"}]
                            ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 10
                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 142; radius: 9
                                    color: modelData.bg; border.width: wizard.chosenTheme === modelData.key ? 2 : 1; border.color: wizard.chosenTheme === modelData.key ? Theme.accent : Theme.line
                                    Rectangle { x: 9; y: 10; width: parent.width * .23; height: parent.height - 20; radius: 3; color: modelData.side }
                                    Column { x: parent.width * .34; y: 22; width: parent.width * .55; spacing: 10
                                        Repeater { model: 4; Rectangle { required property int index; width: parent.width * (index === 0 ? .6 : 1); height: index === 0 ? 7 : 16; radius: 3; color: modelData.fg; opacity: index === 0 ? .8 : .12 } }
                                    }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: wizard.chosenTheme=modelData.key }
                                }
                                Text { text: modelData.title; color: wizard.chosenTheme === modelData.key ? Theme.accent : Theme.muted; font.family: Theme.font; font.pixelSize: 13 }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    spacing: 14
                    Text { text: "Seu piano no Roblox"; font.family: Theme.font; font.pixelSize: 27; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: "Escolha o alcance que você usa no Visual Pianos."; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 12; Layout.topMargin: 12
                        Repeater {
                            model: [{key:"61",title:"61 teclas",range:"C2 até C7"},{key:"88",title:"88 teclas",range:"A0 até C8"}]
                            Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; Layout.preferredHeight: 91; radius: 8
                                color: wizard.chosenLayout === modelData.key ? Theme.accentTint : Theme.surface
                                border.color: wizard.chosenLayout === modelData.key ? Theme.accent : Theme.line
                                Column { anchors.centerIn: parent; spacing: 8
                                    Text { text: modelData.title; color: Theme.text; font.family: Theme.font; font.pixelSize: 19; font.weight: Font.DemiBold }
                                    Text { text: modelData.range; color: Theme.muted; font.family: Theme.font; font.pixelSize: 12 }
                                }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: wizard.chosenLayout=modelData.key }
                            }
                        }
                    }
                    Text { Layout.fillWidth: true; text: "Para 88 teclas, ative também 88key no jogo. O Tessera usa Ctrl para as notas das extremidades."; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
                    RowLayout {
                        Layout.fillWidth: true; Layout.topMargin: 9
                        Text { text: "Pedal"; Layout.fillWidth: true; font.family: Theme.font; font.pixelSize: 13; color: Theme.text }
                        Choice { model: ["Automático", "Apenas MIDI", "Ligado", "Desligado", "Manual"]; currentIndex: ["auto","midi","on","off","ignore"].indexOf(wizard.chosenPedal); onActivated: index => wizard.chosenPedal=["auto","midi","on","off","ignore"][index] }
                    }
                    Text { Layout.fillWidth: true; text: "No Visual Pianos, Espaço solto liga o pedal. O modo automático também cria sustentação para arquivos sem CC64."; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    spacing: 13
                    Text { text: "Como você quer interpretar?"; font.family: Theme.font; font.pixelSize: 27; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: "O arquivo original permanece preservado."; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
                    Repeater {
                        model: [{key:"original",title:"Original",detail:"Mantém os tempos e as articulações do arquivo."},{key:"natural",title:"Natural",detail:"Fraseado discreto e pequenas diferenças nos ataques."},{key:"expressive",title:"Expressivo",detail:"Mais presença nas respirações e no desenho das frases."}]
                        Rectangle {
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 67; radius: 8
                            color: wizard.chosenStyle === modelData.key ? Theme.accentTint : Theme.surface
                            border.color: wizard.chosenStyle === modelData.key ? Theme.accent : Theme.line
                            Column { anchors.left: parent.left; anchors.leftMargin: 17; anchors.verticalCenter: parent.verticalCenter; spacing: 5
                                Text { text: modelData.title; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.weight: Font.DemiBold }
                                Text { text: modelData.detail; color: Theme.muted; font.family: Theme.font; font.pixelSize: 12 }
                            }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: wizard.chosenStyle=modelData.key }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    spacing: 17
                    Text { text: "Os últimos detalhes"; font.family: Theme.font; font.pixelSize: 27; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: "Deixe o aplicativo do seu jeito."; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
                    TSwitch { text: "Fechar a janela para a bandeja"; checked: wizard.chosenTray; onToggled: wizard.chosenTray=checked }
                    TSwitch { text: "Reduzir animações da interface"; checked: wizard.chosenMotion; onToggled: wizard.chosenMotion=checked }
                    TSwitch { text: "Verificar novas versões no GitHub"; checked: wizard.chosenUpdates; onToggled: wizard.chosenUpdates=checked }
                    Text { Layout.fillWidth: true; text: "F6 inicia a música após a contagem. F8 ou Esc interrompem e soltam as teclas. Ao mudar de janela durante a execução, o Tessera para."; wrapMode: Text.WordWrap; lineHeight: 1.35; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
                    Item { Layout.fillHeight: true }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            TButton { text: wizard.step === 0 ? "Agora não" : "Voltar"; onClicked: { if (wizard.step === 0) { backend.skipSetup(); wizard.close() } else wizard.step-- } }
            Item { Layout.fillWidth: true }
            Row {
                visible: wizard.step > 0; spacing: 5
                Repeater { model: 4; Rectangle { required property int index; width: wizard.step === index + 1 ? 20 : 6; height: 6; radius: 3; color: wizard.step === index + 1 ? Theme.accent : Theme.line; Behavior on width { NumberAnimation { duration: Theme.motion } } } }
            }
            Item { Layout.fillWidth: true }
            TButton {
                objectName: "setupNext"
                text: wizard.step === 0 ? "Configurar meu piano" : wizard.step === 4 ? "Começar a tocar" : "Continuar"
                primary: true
                onClicked: {
                    if (wizard.step < 4) wizard.step++
                    else {
                        backend.finishSetup(wizard.chosenTheme,wizard.chosenLayout,wizard.chosenStyle,wizard.chosenPedal,wizard.chosenTray,wizard.chosenMotion)
                        backend.setSetting("check_updates",wizard.chosenUpdates)
                        wizard.close()
                    }
                }
            }
        }
    }
}
