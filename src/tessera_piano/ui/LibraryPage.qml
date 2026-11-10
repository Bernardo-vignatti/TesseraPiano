import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    signal openPlayer()
    spacing: 16
    function focusSearch() { search.forceActiveFocus() }
    Surface {
        Layout.fillWidth: true; Layout.preferredHeight: 124
        StudioArt { anchors.right: parent.right; width: Math.min(350, parent.width * .4); height: parent.height; opacity: .45; clip: true }
        Column {
            x: 22; y: 21; width: parent.width - 215; spacing: 10
            Text { text: "SELECIONADA"; color: Theme.accent; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.6 }
            Text { width: parent.width; text: backend.song.title; color: Theme.text; font.family: Theme.titleFont; font.pixelSize: 28; elide: Text.ElideRight }
            Text { text: backend.song.id ? root.timeText(backend.song.duration) + "  ·  " + backend.settings.layout + " teclas" : "Importe um MIDI para começar."; color: Theme.muted; font.family: Theme.font; font.pixelSize: 11 }
        }
        TButton { anchors.right: parent.right; anchors.rightMargin: 20; anchors.bottom: parent.bottom; anchors.bottomMargin: 18; text: "Abrir reprodução"; glyph: "\uE768"; enabled: backend.song.id !== ""; onClicked: page.openPlayer() }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 16
        TField {
            id: search; objectName: "librarySearch"
            Layout.fillWidth: true; placeholderText: "Buscar no repertório"; leftPadding: 38
            Accessible.name: "Buscar no repertório"
            onTextChanged: backend.setQuery(text)
            Text { text: "\uE721"; font.family: "Segoe MDL2 Assets"; font.pixelSize: 14; color: Theme.muted; x: 13; anchors.verticalCenter: parent.verticalCenter }
        }
        Text { text: backend.songs.length + " músicas"; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
        TButton { text: "Importar"; glyph: "\uE898"; primary: true; enabled: !backend.playback.importing && !backend.playback.busy; onClicked: backend.importDialog() }
    }
    RowLayout {
        Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18
        Text { text: "MÚSICA"; Layout.fillWidth: true; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.5; color: Theme.faint }
        Text { text: "DURAÇÃO"; Layout.preferredWidth: 78; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.3; color: Theme.faint }
        Item { Layout.preferredWidth: 48 }
    }
    ListView {
        id: list; objectName: "songList"
        Layout.fillWidth: true; Layout.fillHeight: true
        clip: true; spacing: 5; bottomMargin: 8
        model: backend.songs
        activeFocusOnTab: true; keyNavigationEnabled: true
        onCurrentIndexChanged: { if (activeFocus && currentIndex >= 0) backend.selectSong(backend.songs[currentIndex].id) }
        Keys.onReturnPressed: page.openPlayer()
        ScrollBar.vertical: ScrollBar {}
        delegate: Rectangle {
            id: row
            required property var modelData
            required property int index
            readonly property bool selected: backend.song.id === modelData.id
            width: list.width - 10; height: 66; radius: 10
            color: selected ? Theme.accentTint : mouse.containsMouse ? Theme.surface : "transparent"
            border.color: selected ? Theme.light ? "#d0b892" : "#5a5140" : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.fast } }
            Accessible.role: Accessible.ListItem
            Accessible.name: modelData.title
            MouseArea {
                id: mouse; anchors.fill: parent; hoverEnabled: true
                onClicked: { list.currentIndex = row.index; backend.selectSong(row.modelData.id) }
                onDoubleClicked: { backend.selectSong(row.modelData.id); page.openPlayer() }
            }
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12; spacing: 14
                Rectangle {
                    Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 8
                    color: row.selected ? Theme.accentFill : Theme.surfaceTop
                    Row {
                        anchors.centerIn: parent; spacing: 3; rotation: 12
                        Repeater { model: 3; Rectangle { required property int index; width: 4; height: 17 + index * 2; radius: 1; color: row.selected ? "#49351e" : Theme.muted } }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 4
                    Text { text: row.modelData.title; Layout.fillWidth: true; elide: Text.ElideRight; font.family: Theme.font; font.pixelSize: 14; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: row.modelData.origin === "Pessoal" ? "Biblioteca pessoal" : "Coleção Tessera"; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
                }
                Text { text: root.timeText(row.modelData.duration); Layout.preferredWidth: 78; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
                TButton { glyph: row.modelData.favorite ? "\uE735" : "\uE734"; compact: true; flat: true; Accessible.name: "Favoritar " + row.modelData.title; onClicked: backend.toggleFavorite(row.modelData.id) }
            }
        }
        Column {
            anchors.centerIn: parent; visible: list.count === 0; spacing: 12
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Nenhuma música por aqui"; font.family: Theme.titleFont; font.pixelSize: 24; color: Theme.text }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Ajuste a busca ou importe um arquivo."; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
        }
    }
}
