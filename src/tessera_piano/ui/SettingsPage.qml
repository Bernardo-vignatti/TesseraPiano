import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: scroll
    signal setupRequested()
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    Column {
        width: scroll.availableWidth - 12; spacing: 20
        Text { text: "APARÊNCIA E JANELA"; color: Theme.faint; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5 }
        Rectangle {
            width: parent.width; height: appearance.height; radius: 9; color: Theme.surface; border.color: Theme.line
            Column {
                id: appearance; width: parent.width
                SettingRow { width: parent.width; title: "Tema"; detail: "Escolha uma aparência ou acompanhe o Windows."; editor: Choice { model: ["Escuro", "Claro", "Sistema"]; currentIndex: ["dark","light","system"].indexOf(backend.settings.theme); onActivated: index => backend.setSetting("theme",["dark","light","system"][index]) } }
                SettingRow { width: parent.width; title: "Reduzir movimento"; detail: "Desativa transições e animações decorativas."; editor: TSwitch { checked: backend.settings.reduced_motion; text: checked ? "Ativado" : "Desativado"; onToggled: backend.setSetting("reduced_motion",checked) } }
                SettingRow { width: parent.width; title: "Fechar para a bandeja"; detail: "Continue com o aplicativo disponível perto do relógio."; editor: TSwitch { checked: backend.settings.minimize_to_tray; text: checked ? "Ativado" : "Desativado"; onToggled: backend.setSetting("minimize_to_tray",checked) } }
            }
        }
        Text { text: "PIANO E INTERPRETAÇÃO"; color: Theme.faint; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5 }
        Rectangle {
            width: parent.width; height: instrument.height; radius: 9; color: Theme.surface; border.color: Theme.line
            Column {
                id: instrument; width: parent.width
                SettingRow { width: parent.width; title: "Alcance do piano"; detail: "Ative também 88key no jogo ao escolher 88 teclas."; editor: Choice { model: ["61 teclas · C2–C7", "88 teclas · A0–C8"]; currentIndex: backend.settings.layout === "88" ? 1 : 0; onActivated: index => backend.setSetting("layout",index ? "88" : "61") } }
                SettingRow { width: parent.width; title: "Intensidade da interpretação"; detail: "Ajusta a presença do fraseado e das articulações."; editor: Slider { from: 0; to: 100; stepSize: 1; value: backend.settings.intensity; enabled: !backend.playback.busy; onPressedChanged: { if (!pressed) backend.setSetting("intensity",Math.round(value)) } palette.highlight: Theme.accent; ToolTip.visible: pressed; ToolTip.text: Math.round(value) + "%" } }
                SettingRow { width: parent.width; title: "Velocidade"; detail: "100% mantém o andamento da interpretação."; editor: SpinBox { from: 25; to: 150; stepSize: 5; value: backend.settings.speed; editable: true; onValueModified: backend.setSetting("speed",value); palette.text: Theme.text; palette.base: Theme.bg; palette.button: Theme.hover; palette.buttonText: Theme.text } }
                SettingRow { width: parent.width; title: "Contagem antes de tocar"; detail: "Tempo para selecionar o piano no Roblox."; editor: SpinBox { from: 1; to: 30; value: backend.settings.countdown; onValueModified: backend.setSetting("countdown",value); palette.text: Theme.text; palette.base: Theme.bg; palette.button: Theme.hover; palette.buttonText: Theme.text } }
                SettingRow { width: parent.width; title: "Repetir ao terminar"; editor: TSwitch { checked: backend.settings.repeat; text: checked ? "Ativado" : "Desativado"; onToggled: backend.setSetting("repeat",checked) } }
                SettingRow { width: parent.width; title: "Entrada de teclado"; detail: "Use o modo físico; virtual é uma alternativa de compatibilidade."; editor: Choice { model: ["Teclas físicas", "Teclas virtuais"]; currentIndex: backend.settings.mode === "scan" ? 0 : 1; onActivated: index => backend.setSetting("mode",index ? "virtual" : "scan") } }
                SettingRow { width: parent.width; title: "Conferir o instrumento"; detail: "Os testes iniciam após a contagem. Volte ao piano."; editor: Row { spacing: 6; TButton { text: "Pedal"; compact: true; onClicked: backend.testInstrument("pedal") } TButton { text: "Alcance"; compact: true; onClicked: backend.testInstrument("range") } } }
            }
        }
        Text { text: "ATUALIZAÇÕES"; color: Theme.faint; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5 }
        Rectangle {
            width: parent.width; height: updatesColumn.height; radius: 9; color: Theme.surface; border.color: Theme.line
            Column {
                id: updatesColumn; width: parent.width
                SettingRow { width: parent.width; title: "Verificar automaticamente"; detail: "Consulta o GitHub uma vez por dia ao abrir o aplicativo."; editor: TSwitch { checked: backend.settings.check_updates; text: checked ? "Ativado" : "Desativado"; onToggled: backend.setSetting("check_updates",checked) } }
                SettingRow { width: parent.width; title: "Baixar atualizações automaticamente"; detail: "A instalação acontece quando você escolher atualizar."; editor: TSwitch { checked: backend.settings.auto_download; text: checked ? "Ativado" : "Desativado"; onToggled: backend.setSetting("auto_download",checked) } }
                Column {
                    width: parent.width - 40; x: 20; topPadding: 20; bottomPadding: 20; spacing: 12
                    Text { text: "Tessera Piano " + backend.version; font.family: Theme.font; font.pixelSize: 13; color: Theme.text }
                    Text { width: parent.width - 40; text: backend.update.message; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted; wrapMode: Text.WordWrap }
                    ProgressBar { width: parent.width - 40; visible: backend.update.state === "downloading"; value: backend.update.progress; palette.highlight: Theme.accent }
                    Row {
                        spacing: 9
                        TButton { text: "Verificar agora"; enabled: backend.update.state !== "checking" && backend.update.state !== "downloading"; onClicked: backend.checkUpdates() }
                        TButton { text: "Baixar " + backend.update.version; primary: true; visible: backend.update.state === "available"; onClicked: backend.downloadUpdate() }
                        TButton { text: "Instalar e reiniciar"; primary: true; visible: backend.update.state === "ready"; enabled: !backend.playback.busy; onClicked: backend.installUpdate() }
                        TButton { text: "Cancelar download"; visible: backend.update.state === "downloading"; onClicked: backend.cancelDownload() }
                    }
                }
            }
        }
        Text { text: "BIBLIOTECA E PREFERÊNCIAS"; color: Theme.faint; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5 }
        Flow {
            width: parent.width; spacing: 9
            TButton { text: "Abrir pasta de dados"; glyph: "\uE8B7"; onClicked: backend.openLink("profile") }
            TButton { text: "Desfazer exclusão"; enabled: backend.settings.deleted_songs.length > 0; onClicked: backend.undoDelete() }
            TButton { text: "Configurar novamente"; onClicked: scroll.setupRequested() }
        }
        Item { width: 1; height: 12 }
    }
}
